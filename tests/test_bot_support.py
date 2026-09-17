import os
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from bot_support import (archive_media, list_media, open_media, parse_media_url,
                         validate_allowed_id)


class ValidationTests(unittest.TestCase):
    def test_allowed_id(self):
        for value in (None, "", "0", "-1", "+1", "1.0", "abc", " 42", True, 0, 1.5, "１２"):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "TELEGRAM_ALLOWED_USER_ID"):
                validate_allowed_id(value)
        self.assertEqual(validate_allowed_id("123"), 123)
        self.assertEqual(validate_allowed_id(42), 42)

    def test_supported_urls(self):
        for host in ("ru", "com", "by", "kz", "uz", "com.tr"):
            for scheme in ("http", "https"):
                for kind in ("artist", "album", "book", "podcast"):
                    path = "artist" if kind == "artist" else "album"
                    with self.subTest(host=host, kind=kind, scheme=scheme):
                        self.assertEqual(parse_media_url(f"{scheme}://music.yandex.{host}/{path}/123/?foo=456", kind), "123")

    def test_rejected_urls(self):
        urls = ["https://music.yandex.ru.evil/album/1", "https://evil/album/1",
                "https://user@music.yandex.ru/album/1", "https://music.yandex.ru:443/album/1",
                "ftp://music.yandex.ru/album/1", "music.yandex.ru/album/1",
                "https://music.yandex.ru/album/-1", "https://music.yandex.ru/album/１２",
                "https://music.yandex.ru/album/1/extra", "https://music.yandex.ru/album/%31",
                "https://music.yandex.ru/al\tbum/1",
                "https://[invalid/album/1"]
        for url in urls:
            with self.subTest(url=url), self.assertRaises(ValueError):
                parse_media_url(url, "album")
        for path in ("/album/1/track/2", "/track/2", "/users/me/playlists/123"):
            with self.assertRaisesRegex(ValueError, "треки|треки и плейлисты"):
                parse_media_url("https://music.yandex.ru" + path, "album")
        with self.assertRaises(ValueError):
            parse_media_url("https://music.yandex.ru/album/1", "artist")
        for kind in ("album", "book", "podcast"):
            with self.assertRaises(ValueError):
                parse_media_url("https://music.yandex.ru/artist/1", kind)


class FilesystemTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "media"
        self.root.mkdir()
        self.album = self.root / "album"
        self.album.mkdir()
        (self.album / "song.mp3").write_bytes(b"audio")
        (self.album / "cover.jpg").write_bytes(b"cover")
        for name in (".env", "log.log", "log.txt", "secrets.txt", "credentials.txt", "script.py"):
            (self.album / name).write_text("private")
        self.outside = self.base / "outside"
        self.outside.mkdir()
        (self.outside / "private.mp3").write_bytes(b"private")
        (self.album / "linked.mp3").symlink_to(self.outside / "private.mp3")
        (self.album / "linked-dir").symlink_to(self.outside, target_is_directory=True)
        (self.album / "loop").symlink_to(self.album, target_is_directory=True)

    def test_listing_filters_links_secrets_and_extensions(self):
        self.assertEqual({path.name for path, _ in list_media(self.root, self.album)}, {"song.mp3", "cover.jpg"})

    def test_open_rejects_symlinks_escape_and_secret_files(self):
        for path in (self.album / "linked.mp3", self.album / "linked-dir/private.mp3",
                     self.outside / "private.mp3", self.root / "../outside/private.mp3",
                     self.album / "log.txt", self.album / ".env"):
            with self.subTest(path=path), self.assertRaises((ValueError, OSError)):
                with open_media(self.root, path):
                    self.fail("unsafe open")
        with open_media(self.root, self.album / "song.mp3") as stream:
            self.assertEqual(stream.read(), b"audio")

    def test_root_or_parent_symlink_rejected(self):
        alias = self.base / "alias"
        alias.symlink_to(self.root, target_is_directory=True)
        for root in (alias, alias / "album"):
            with self.assertRaises(OSError):
                list_media(root, root)

    def test_archive_is_filtered_and_root_forbidden(self):
        archive = self.base / "output.zip"
        nested = self.album / "disc"
        nested.mkdir()
        (nested / "track.flac").write_bytes(b"track")
        (nested / "secret.txt").write_text("private")
        archive_media(self.root, self.album, archive)
        with ZipFile(archive) as output:
            self.assertEqual(set(output.namelist()), {"song.mp3", "cover.jpg", "disc/track.flac"})
            self.assertEqual(output.read("song.mp3"), b"audio")
        with self.assertRaises(ValueError):
            archive_media(self.root, self.root, archive)

    def test_link_swap_after_listing_rejected(self):
        path = self.album / "song.mp3"
        self.assertIn(path, dict(list_media(self.root, self.album)))
        path.unlink()
        path.symlink_to(self.outside / "private.mp3")
        with self.assertRaises(OSError):
            with open_media(self.root, path):
                self.fail("link followed")

    @unittest.skipUnless(hasattr(os, "mkfifo"), "POSIX required")
    def test_special_file_not_listed_or_opened(self):
        path = self.album / "pipe.mp3"
        os.mkfifo(path)
        self.assertNotIn(path, dict(list_media(self.root, self.album)))
        with self.assertRaises(ValueError):
            with open_media(self.root, path):
                self.fail("FIFO opened")


if __name__ == "__main__":
    unittest.main()
