#!/usr/bin/env python3
"""Single-user Telegram frontend. Importing this module never imports API."""

import logging
import os
import secrets
import threading
from dataclasses import dataclass, field
from pathlib import Path
from queue import Queue
from tempfile import TemporaryDirectory

from bot_support import (PAGE_SIZE, archive_media, list_media, open_media,
                         parse_media_url, validate_allowed_id)

log = logging.getLogger(__name__)
LABELS = {"artist": "🎤 Артист", "album": "💿 Альбом", "book": "📚 Книга", "podcast": "🎙 Подкаст"}


@dataclass
class Session:
    mode: str = "idle"
    token: str = ""
    message_id: int | None = None
    actions: dict = field(default_factory=dict)
    kind: str = ""
    pending: tuple | None = None
    query: str = ""
    search_page: int = 0
    root: Path | None = None
    directory: Path | None = None
    file_page: int = 0
    files: dict = field(default_factory=dict)

    def invalidate(self):
        self.token = ""
        self.actions.clear()
        self.message_id = None


class Frontend:
    def __init__(self, api, bot, allowed_id):
        from telebot import types
        self.types = types
        self.api, self.bot = api, bot
        self.allowed_id = validate_allowed_id(allowed_id)
        self.sessions = {}
        self.queue = Queue()
        self.lock = threading.RLock()
        self.worker = None
        self.reply = types.ReplyKeyboardMarkup(resize_keyboard=True, is_persistent=True)
        self.reply.row("📥 Скачать", "📂 Файлы")

    def authorized(self, event):
        return getattr(getattr(event, "from_user", None), "id", None) == self.allowed_id

    def notify(self, chat, text):
        try:
            self.bot.send_message(chat, str(text)[:4000], parse_mode=None)
        except Exception:
            log.exception("Telegram notification failed")

    def start_worker(self):
        if self.worker is None:
            self.worker = threading.Thread(target=self.work, name="download-worker", daemon=True)
            self.worker.start()

    def work(self):
        while True:
            job = self.queue.get()
            try:
                if job is None:  # shutdown sentinel, also useful for offline tests
                    return
                chat, kind, media_id = job
                try:
                    result = getattr(self.api, f"download_{kind}")(media_id)
                    # Legacy API functions decorated with logger.catch return None on failure.
                    if result is None:
                        raise RuntimeError("Downloader returned no result")
                except Exception:
                    log.exception("Download failed: %s %s", kind, media_id)
                    self.notify(chat, "❌ Не удалось выполнить загрузку. Попробуйте позже.")
                else:
                    self.notify(chat, result or "✅ Загрузка завершена.")
            finally:
                self.queue.task_done()

    def render(self, chat, state, text, buttons, footer_rows=()):
        state.invalidate()
        state.token = secrets.token_hex(8)
        markup = self.types.InlineKeyboardMarkup(row_width=1)
        for row in [[button] for button in buttons] + list(footer_rows):
            row_buttons = []
            for label, action, payload in row:
                key = str(len(state.actions))
                state.actions[key] = (action, payload)
                row_buttons.append(self.types.InlineKeyboardButton(label[:100], callback_data=f"{state.token}:{key}"))
            if row_buttons:
                markup.row(*row_buttons)
        try:
            message = self.bot.send_message(chat, str(text)[:4000], reply_markup=markup, parse_mode=None)
            state.message_id = message.message_id
        except Exception:
            state.invalidate()
            raise

    @staticmethod
    def cancel_button():
        return ("❌ Отмена", "cancel", None)

    def download_menu(self, chat, state):
        state.mode = "menu"
        state.pending = None
        buttons = [(label + " по ссылке", "kind", kind) for kind, label in LABELS.items()]
        buttons += [("🔎 Поиск артиста по имени", "search", None), self.cancel_button()]
        self.render(chat, state, "📥 Что скачать? Выберите тип или поиск артиста.", buttons)

    def search_prompt(self, chat, state):
        state.mode, state.pending = "search_input", None
        self.render(chat, state, "🔎 Введите имя артиста или группы.", [self.cancel_button()])

    def file_menu(self, chat, state):
        state.mode, state.pending = "file_menu", None
        self.render(chat, state, "📂 Выберите раздел:", [
            ("🎵 Музыка", "root", "music"), ("📚 Книги", "root", "book"),
            ("🎙 Подкасты", "root", "podcast"), self.cancel_button()])

    def search_results(self, chat, state):
        results = self.api.search_artists(state.query, page=state.search_page)
        buttons = []
        for artist in results:
            media_id = str(artist["id"])
            if media_id.isascii() and media_id.isdigit():
                buttons.append((f"🎤 {artist['name']} · ID {media_id}", "artist", media_id))
        navigation = []
        if state.search_page:
            navigation.append(("⬅️", "search_page", state.search_page - 1))
        if results:
            navigation.append(("➡️", "search_page", state.search_page + 1))
        state.mode = "results"
        self.render(chat, state, f"🔎 {state.query[:300]} — страница {state.search_page + 1}\n"
                    + ("Выберите артиста:" if buttons and results else "Ничего не найдено."), buttons,
                    footer_rows=[navigation, [("🔎 Другой запрос", "search", None)], [self.cancel_button()]])

    def confirm(self, chat, state, kind, media_id):
        info = getattr(self.api, f"get_{kind}_info")(media_id)
        if not isinstance(info, str) or not info.strip():
            raise RuntimeError("No media information returned")
        state.mode, state.pending = "confirm", (kind, media_id)
        self.render(chat, state, f"{str(info)[:3500]}\n\n{LABELS[kind]} · ID {media_id}\nДобавить в очередь?",
                    [("✅ Скачать", "confirm", None), self.cancel_button()])

    def files_page(self, chat, state):
        entries = list_media(state.root, state.directory)
        last = max(0, (len(entries) - 1) // PAGE_SIZE)
        state.file_page = max(0, min(state.file_page, last))
        start = state.file_page * PAGE_SIZE
        state.files = {str(i): path for i, (path, _) in enumerate(entries[start:start + PAGE_SIZE])}
        buttons = [(f"{'📁' if is_dir else '📄'} {path.name}", "file", str(i))
                   for i, (path, is_dir) in enumerate(entries[start:start + PAGE_SIZE])]
        navigation = []
        actions = []
        if state.directory != state.root:
            navigation.append(("⬆️", "up", None))
            actions.append(("📦 Скачать", "archive", None))
        if state.file_page:
            navigation.append(("⬅️", "file_page", state.file_page - 1))
        if state.file_page < last:
            navigation.append(("➡️", "file_page", state.file_page + 1))
        navigation.append(("📂", "files", None))
        actions.append(self.cancel_button())
        state.mode = "files"
        display = state.directory.relative_to(state.root).as_posix()
        self.render(chat, state, f"📂 /{'' if display == '.' else display}\nСтраница {state.file_page + 1}/{last + 1}"
                    + ("\nКаталог пуст." if not entries else ""), buttons,
                    footer_rows=[navigation, actions])

    def message(self, message):
        if not self.authorized(message):
            return
        with self.lock:
            chat = message.chat.id
            key = (chat, message.from_user.id)
            state = self.sessions.setdefault(key, Session())
            text = getattr(message, "text", None) or ""
            words = text.split(maxsplit=1)
            command = words[0].split("@")[0] if words else ""
            try:
                if command in {"/start", "/download", "/files", "/search", "/cancel"} or text in {"📥 Скачать", "📂 Файлы"}:
                    state.invalidate()
                    state.pending = None
                    if command == "/start":
                        state.mode = "idle"
                        self.bot.send_message(
                            chat,
                            "🎵 Скачивайте музыку, книги и подкасты по ссылкам Яндекс Музыки.\n"
                            "📥 /download — скачать\n📂 /files — просмотр файлов\n"
                            "🔎 /search — поиск артиста по имени",
                            reply_markup=self.reply,
                        )
                    elif command == "/files" or text == "📂 Файлы":
                        self.file_menu(chat, state)
                    elif command == "/search":
                        self.search_prompt(chat, state)
                    elif command == "/cancel":
                        self.cancel(chat, state)
                    else:
                        self.download_menu(chat, state)
                elif state.mode == "search_input":
                    state.invalidate()
                    if not text.strip() or text.startswith("/"):
                        self.search_prompt(chat, state)
                    else:
                        state.query, state.search_page = text.strip()[:300], 0
                        self.search_results(chat, state)
                elif state.mode == "url_input":
                    state.invalidate()
                    try:
                        media_id = parse_media_url(text, state.kind)
                    except ValueError as error:
                        self.render(chat, state, str(error), [self.cancel_button()])
                        return
                    self.confirm(chat, state, state.kind, media_id)
                else:
                    self.notify(chat, "Используйте /download, /search или /files.")
            except Exception:
                self.recover(chat, state)

    def cancel(self, chat, state):
        state.mode, state.pending = "idle", None
        self.render(chat, state, "❌ Действие отменено. Уже поставленные в очередь загрузки продолжатся.",
                    [("📥 Скачать", "download", None), ("📂 Файлы", "files", None)])

    def recover(self, chat, state):
        log.exception("Frontend operation failed")
        state.invalidate()
        state.mode, state.pending = "idle", None
        self.notify(chat, "❌ Не удалось выполнить действие. Проверьте доступность сервиса или файла и повторите /download, /search или /files.")

    def callback(self, call):
        if not self.authorized(call):
            return
        with self.lock:
            message = getattr(call, "message", None)
            if message is None:
                return
            chat = message.chat.id
            state = self.sessions.get((chat, call.from_user.id))
            token, sep, index = (getattr(call, "data", None) or "").partition(":")
            if (not state or not sep or not state.token or token != state.token
                    or message.message_id != state.message_id or index not in state.actions):
                self.answer(call, "Кнопка устарела. Откройте меню заново.")
                return
            action, payload = state.actions[index]
            state.invalidate()  # consume BEFORE queueing, network calls or further rendering
            self.answer(call)
            try:
                self.dispatch(chat, state, action, payload)
            except Exception:
                self.recover(chat, state)

    def answer(self, call, text=None):
        try:
            self.bot.answer_callback_query(call.id, text=text)
        except Exception:
            log.exception("Callback acknowledgement failed")

    def dispatch(self, chat, state, action, payload):
        if action == "cancel":
            self.cancel(chat, state)
        elif action == "download":
            self.download_menu(chat, state)
        elif action == "files":
            self.file_menu(chat, state)
        elif action == "search":
            self.search_prompt(chat, state)
        elif action == "kind":
            state.kind, state.mode, state.pending = payload, "url_input", None
            self.render(chat, state, f"{LABELS[payload]}: отправьте ссылку Яндекс Музыки.\n"
                        "Треки и плейлисты не поддерживаются.", [self.cancel_button()])
        elif action == "artist":
            self.confirm(chat, state, "artist", payload)
        elif action == "search_page":
            state.search_page = payload
            self.search_results(chat, state)
        elif action == "confirm" and state.mode == "confirm" and state.pending:
            kind, media_id = state.pending
            state.pending, state.mode = None, "idle"
            self.queue.put((chat, kind, media_id))
            self.render(chat, state, "✅ Загрузка добавлена в очередь.",
                        [("📥 Скачать ещё", "download", None), ("📂 Файлы", "files", None)])
        elif action == "root":
            attribute = {"music": "folder_music", "book": "folder_audiobooks", "podcast": "folder_podcasts"}[payload]
            root = getattr(self.api, attribute)
            if not root:
                raise ValueError("Каталог не настроен")
            state.root = state.directory = Path(root).absolute()
            state.file_page = 0
            self.files_page(chat, state)
        elif action == "file_page":
            state.file_page = payload
            self.files_page(chat, state)
        elif action == "up":
            if state.directory != state.root:
                state.directory = state.directory.parent
            state.file_page = 0
            self.files_page(chat, state)
        elif action == "file":
            path = state.files[payload]
            # Re-list securely: paths may have disappeared or become links since rendering.
            current = dict(list_media(state.root, state.directory))
            if path not in current:
                raise ValueError("Файл больше недоступен")
            if current[path]:
                state.directory, state.file_page = path, 0
            else:
                with open_media(state.root, path) as source:
                    self.bot.send_document(chat, source, visible_file_name=path.name)
            self.files_page(chat, state)
        elif action == "archive":
            with TemporaryDirectory(prefix="tbot-") as temp:
                archive = Path(temp) / "media.zip"
                archive_media(state.root, state.directory, archive)
                with archive.open("rb") as source:
                    self.bot.send_document(chat, source, visible_file_name="media.zip")
            self.files_page(chat, state)


def create_bot(api, token, allowed_id, *, bot=None, start_worker=True):
    """Inject a bot double and disable worker startup for deterministic offline tests."""
    allowed_id = validate_allowed_id(allowed_id)
    if bot is None:
        import telebot
        bot = telebot.TeleBot(token, threaded=False)
    frontend = Frontend(api, bot, allowed_id)
    bot.frontend = frontend
    bot.message_handler(func=lambda message: True, content_types=[
        "text", "audio", "document", "photo", "sticker", "video", "voice", "contact", "location"
    ])(frontend.message)
    bot.callback_query_handler(func=lambda call: True)(frontend.callback)
    if start_worker:
        frontend.start_worker()
    return bot


def main():
    from dotenv import load_dotenv
    load_dotenv()
    try:
        allowed_id = validate_allowed_id(os.getenv("TELEGRAM_ALLOWED_USER_ID"))
    except ValueError as error:
        raise SystemExit(str(error)) from None
    token = os.getenv("TELEGRAMM_TOKEN")
    if not token:
        raise SystemExit("Не задан TELEGRAMM_TOKEN — токен Telegram-бота.")
    import API
    from telebot import apihelper
    proxy = os.getenv("TELEGRAM_PROXY_URL")
    apihelper.proxy = {"https": proxy} if proxy else None
    logging.basicConfig(level=logging.INFO)
    bot = create_bot(API, token, allowed_id)
    bot.infinity_polling(skip_pending=True)


if __name__ == "__main__":
    main()
