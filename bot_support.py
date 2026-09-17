"""Telegram-independent validation and confined filesystem operations."""

import os
import re
import shutil
import stat
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlsplit
from zipfile import ZIP_DEFLATED, ZipFile

PAGE_SIZE = 15
HOSTS = {f"music.yandex.{suffix}" for suffix in ("ru", "com", "by", "kz", "uz", "com.tr")}
EXTENSIONS = {".mp3", ".flac", ".m4a", ".aac", ".ogg", ".opus", ".wav", ".wma",
              ".aiff", ".alac", ".m4b", ".jpg", ".jpeg", ".png", ".txt", ".lrc", ".pdf", ".epub"}


def validate_allowed_id(value):
    if not isinstance(value, (str, int)) or isinstance(value, bool) or not re.fullmatch(r"[0-9]+", str(value)) or int(value) <= 0:
        raise ValueError("TELEGRAM_ALLOWED_USER_ID должен быть положительным целым числом (ID пользователя Telegram).")
    return int(value)


def parse_media_url(value, kind):
    """Return the ID only when both the origin and selected media type match."""
    if kind not in {"artist", "album", "book", "podcast"}:
        raise ValueError("Неизвестный тип загрузки.")
    value = value.strip()
    try:
        url = urlsplit(value)
        valid = (url.scheme in {"http", "https"} and url.netloc in HOSTS
                 and not re.search(r"\s", value))
    except ValueError:
        valid = False
    if not valid:
        raise ValueError("Нужна ссылка http/https на music.yandex.ru/com/by/kz/uz или music.yandex.com.tr.")
    if re.search(r"/(track|tracks|playlist|playlists)(/|$)", url.path):
        raise ValueError("Ссылки на треки и плейлисты не поддерживаются.")
    match = re.fullmatch(r"/(artist|album)/([0-9]+)/?", url.path)
    if not match:
        raise ValueError("Нужна ссылка вида /artist/123 или /album/123; треки и плейлисты не поддерживаются.")
    expected = "artist" if kind == "artist" else "album"
    if match[1] != expected:
        raise ValueError(f"Для выбранного типа нужна ссылка /{expected}/123.")
    return match[2]


def allowed_name(name):
    lower = name.lower()
    return (not lower.startswith(".")
            and not re.search(r"(^|[._\- ])(log|logs|secret|secrets|token|tokens|password|passwords|credentials|config|env)([._\- ]|$)", lower))


def relative_parts(root, path):
    root, path = Path(root).absolute(), Path(path).absolute()
    try:
        parts = path.relative_to(root).parts
    except ValueError:
        raise ValueError("Доступ вне выбранного каталога запрещён.") from None
    if any(part in {"..", "."} or not allowed_name(part) for part in parts):
        raise ValueError("Недоступный путь.")
    return root, parts


@contextmanager
def directory_fd(root, path):
    """Open every component without following symlinks, including root ancestors.

    Linux dir_fd + O_NOFOLLOW also prevent a link swap between validation and open.
    """
    root, parts = relative_parts(root, path)
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    fd = os.open("/", flags)
    try:
        for part in root.parts[1:] + parts:
            if part == "..":
                raise ValueError("Недоступный путь.")
            next_fd = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        yield fd
    finally:
        os.close(fd)


def list_media(root, directory):
    entries = []
    with directory_fd(root, directory) as fd:
        for name in os.listdir(fd):
            if not allowed_name(name):
                continue
            try:
                mode = os.stat(name, dir_fd=fd, follow_symlinks=False).st_mode
            except FileNotFoundError:
                continue
            is_dir = stat.S_ISDIR(mode)
            if is_dir or (stat.S_ISREG(mode) and Path(name).suffix.lower() in EXTENSIONS):
                entries.append((Path(directory) / name, is_dir))
    return sorted(entries, key=lambda item: (not item[1], item[0].name.casefold(), item[0].name))


@contextmanager
def open_media(root, path):
    path = Path(path)
    relative_parts(root, path)
    if not allowed_name(path.name) or path.suffix.lower() not in EXTENSIONS:
        raise ValueError("Этот тип файла недоступен.")
    with directory_fd(root, path.parent) as fd:
        file_fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
    try:
        if not stat.S_ISREG(os.fstat(file_fd).st_mode):
            raise ValueError("Можно отправлять только обычные файлы.")
        stream = os.fdopen(file_fd, "rb")
    except BaseException:
        os.close(file_fd)
        raise
    with stream:
        yield stream


def archive_media(root, directory, destination):
    """Write only allowed regular files; destination must be a caller-owned temp path."""
    _, parts = relative_parts(root, directory)
    if not parts:
        raise ValueError("Архивировать можно только подкаталог.")
    directory = Path(directory)
    with ZipFile(destination, "w", compression=ZIP_DEFLATED) as archive:
        def visit(current):
            for path, is_dir in list_media(root, current):
                if is_dir:
                    visit(path)
                else:
                    with open_media(root, path) as source, archive.open(path.relative_to(directory).as_posix(), "w") as target:
                        shutil.copyfileobj(source, target)
        visit(directory)
