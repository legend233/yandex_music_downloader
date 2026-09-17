import builtins
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch
from zipfile import ZipFile
from io import BytesIO

import tbot


class FakeBot:
    def __init__(self):
        self.messages = []
        self.documents = []
        self.answers = []

    def message_handler(self, **kwargs):
        def register(handler):
            self.on_message = handler
            return handler
        return register

    def callback_query_handler(self, **kwargs):
        def register(handler):
            self.on_callback = handler
            return handler
        return register

    def send_message(self, chat, text, **kwargs):
        message = NS(chat=NS(id=chat), text=text, message_id=len(self.messages) + 1, **kwargs)
        self.messages.append(message)
        return message

    def answer_callback_query(self, callback_id, **kwargs):
        self.answers.append((callback_id, kwargs))

    def send_document(self, chat, source, **kwargs):
        self.documents.append((chat, source.read(), kwargs))


class FrontendTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "music"
        self.root.mkdir()
        self.books = Path(self.temp.name) / "books"
        self.books.mkdir()
        self.api = Mock(folder_music=str(self.root), folder_audiobooks=str(self.books), folder_podcasts=str(self.books))
        self.api.get_artist_info.return_value = "Artist"
        self.api.get_album_info.return_value = "Album"
        self.api.get_book_info.return_value = "Book"
        self.api.get_podcast_info.return_value = "Podcast"
        self.api.search_artists.return_value = [{"id": 123, "name": "Same Name"}, {"id": 456, "name": "Same Name"}]
        self.bot = tbot.create_bot(self.api, "unused", 42, bot=FakeBot(), start_worker=False)
        self.front = self.bot.frontend

    def message(self, text, user=42, chat=100):
        self.bot.on_message(NS(text=text, from_user=NS(id=user), chat=NS(id=chat)))

    def callback_for(self, label, user=42):
        message = self.bot.messages[-1]
        markup = message.reply_markup
        button = next(button for row in markup.keyboard for button in row if label in button.text)
        return NS(id="callback", from_user=NS(id=user), message=message, data=button.callback_data)

    def click(self, label):
        call = self.callback_for(label)
        self.bot.on_callback(call)
        return call

    @property
    def state(self):
        return self.front.sessions[(100, 42)]

    def test_unauthorized_commands_input_callbacks_are_silent(self):
        for text in ("/start", "/download", "/search", "/files", "/cancel", "📥 Скачать", "📂 Файлы", "hello"):
            self.message(text, user=666)
        self.assertFalse(self.bot.messages)
        self.assertFalse(self.front.sessions)
        self.message("/search")
        token = self.state.token
        count = len(self.bot.messages)
        self.message("stolen query", user=666)
        self.bot.on_callback(self.callback_for("Отмена", user=666))
        self.assertEqual(len(self.bot.messages), count)
        self.assertEqual(self.state.token, token)
        self.assertFalse(self.bot.answers)
        self.api.search_artists.assert_not_called()
        self.message("real query")
        self.api.search_artists.assert_called_once_with("real query", page=0)

    def test_whitespace_input_does_not_interrupt_dialog(self):
        self.message("\u2003")
        self.message("/search")
        self.message(" \u2003 ")
        self.assertEqual(self.state.mode, "search_input")
        self.api.search_artists.assert_not_called()
        self.message("/files")
        self.assertEqual(self.state.mode, "file_menu")

    def test_persistent_keyboard_only_two_actions(self):
        self.message("/start")
        keyboard = self.bot.messages[0].reply_markup
        self.assertTrue(keyboard.is_persistent)
        self.assertEqual([button["text"] for row in keyboard.keyboard for button in row], ["📥 Скачать", "📂 Файлы"])
        self.message("📂 Файлы")
        self.assertEqual(self.state.mode, "file_menu")
        self.message("📥 Скачать")
        self.assertEqual(self.state.mode, "menu")

    def test_commands_do_not_send_redundant_keyboard_message(self):
        self.message("/start")
        self.assertEqual(len(self.bot.messages), 1)
        for command in ("/download", "/files", "/search", "/cancel", "📥 Скачать", "📂 Файлы"):
            count = len(self.bot.messages)
            self.message(command)
            self.assertEqual(len(self.bot.messages), count + 1)
            self.assertIsInstance(self.bot.messages[-1].reply_markup, self.front.types.InlineKeyboardMarkup)
        self.assertFalse(any(message.text == "🎵 Выберите действие:" for message in self.bot.messages))

    def test_unauthorized_url_and_confirmation_do_not_consume_state(self):
        self.message("/download")
        self.click("Альбом")
        token = self.state.token
        self.message("https://music.yandex.ru/album/999", user=666)
        self.assertEqual(self.state.token, token)
        self.assertEqual(self.state.mode, "url_input")
        self.api.get_album_info.assert_not_called()
        self.message("https://music.yandex.ru/album/123")
        call = self.callback_for("✅ Скачать", user=666)
        token = self.state.token
        count = len(self.bot.answers)
        self.bot.on_callback(call)
        self.assertEqual(self.state.token, token)
        self.assertEqual(len(self.bot.answers), count)
        self.assertTrue(self.front.queue.empty())
        self.click("✅ Скачать")
        self.assertEqual(self.front.queue.get_nowait(), (100, "album", "123"))

    def test_search_pages_selection_by_id_and_double_confirm(self):
        self.message("/search")
        self.message("artist")
        old_result = self.callback_for("ID 123")
        self.assertEqual([b.text for b in self.bot.messages[-1].reply_markup.keyboard[-3]], ["➡️"])
        self.click("➡️")
        self.assertEqual([b.text for b in self.bot.messages[-1].reply_markup.keyboard[-3]], ["⬅️", "➡️"])
        self.api.search_artists.assert_called_with("artist", page=1)
        self.bot.on_callback(old_result)
        self.api.get_artist_info.assert_not_called()
        self.click("⬅️")
        self.click("ID 456")
        self.api.get_artist_info.assert_called_once_with("456")
        confirm = self.callback_for("✅ Скачать")
        forged = NS(**vars(confirm))
        forged.message = NS(chat=NS(id=100), message_id=99999)
        self.bot.on_callback(forged)
        self.assertTrue(self.front.queue.empty())
        self.bot.on_callback(confirm)
        self.bot.on_callback(confirm)
        self.assertEqual(self.front.queue.qsize(), 1)
        self.assertEqual(self.front.queue.get_nowait(), (100, "artist", "456"))

    def test_cancel_mode_switch_and_new_render_invalidate_callbacks(self):
        for command in ("/cancel", "/files", "/download", "/search", "📂 Файлы", "📥 Скачать"):
            with self.subTest(command=command):
                self.message("/download")
                self.click("Альбом")
                self.message("https://music.yandex.ru/album/99")
                old = self.callback_for("✅ Скачать")
                self.message(command)
                self.bot.on_callback(old)
                self.assertTrue(self.front.queue.empty())
        self.message("/download")
        self.click("Альбом")
        self.message("https://music.yandex.ru/album/99")
        old = self.callback_for("✅ Скачать")
        self.click("Отмена")
        self.bot.on_callback(old)
        self.assertTrue(self.front.queue.empty())

    def test_url_modes_and_recoverable_invalid_input(self):
        for kind, label in tbot.LABELS.items():
            self.message("/download")
            self.click(label)
            self.message("https://music.yandex.ru/track/99")
            self.assertIn("не поддерживаются", self.bot.messages[-1].text)
            self.assertEqual(self.state.mode, "url_input")
            path = "artist" if kind == "artist" else "album"
            self.message(f"https://music.yandex.ru/{path}/99?other=123")
            getattr(self.api, f"get_{kind}_info").assert_called_with("99")
            self.click("✅ Скачать")
            self.assertEqual(self.front.queue.get_nowait(), (100, kind, "99"))

    def test_sessions_are_per_chat_and_user(self):
        self.message("/search", chat=100)
        self.message("/download", chat=200)
        self.assertEqual(self.state.mode, "search_input")
        self.assertEqual(self.front.sessions[(200, 42)].mode, "menu")
        call = self.callback_for("Альбом")
        call.message = NS(chat=NS(id=100), message_id=call.message.message_id)
        self.bot.on_callback(call)
        self.assertEqual(self.state.mode, "search_input")

    def test_files_pagination_directory_and_type_reset(self):
        for i in range(17):
            (self.root / f"{i:02d}.mp3").write_bytes(b"audio")
        directory = self.root / "zz-dir"
        directory.mkdir()
        self.message("/files")
        self.click("Музыка")
        self.assertEqual(len(self.state.files), 15)
        self.assertTrue(all(isinstance(p, Path) for p in self.state.files.values()))
        old = self.callback_for("00.mp3")
        self.click("➡️")
        self.assertEqual(self.state.file_page, 1)
        self.assertEqual(len(self.state.files), 3)
        self.bot.on_callback(old)
        self.assertFalse(self.bot.documents)
        self.click("16.mp3")
        self.assertEqual(self.bot.documents[-1][1], b"audio")
        self.click("⬅️")
        self.click("zz-dir")
        self.assertEqual(self.state.directory, directory)
        self.assertEqual(self.state.file_page, 0)
        self.click("⬆️")
        self.click("➡️")
        self.click("📂")
        self.click("Книги")
        self.assertEqual(self.state.root, self.books)
        self.assertEqual(self.state.file_page, 0)

    def test_files_controls_share_compact_rows(self):
        album = self.root / "album"
        album.mkdir()
        for i in range(31):
            (album / f"{i:02d}.mp3").write_bytes(b"audio")
        self.message("/files")
        self.click("Музыка")
        self.click("album")
        self.click("➡️")
        rows = self.bot.messages[-1].reply_markup.keyboard
        self.assertTrue(all(len(row) == 1 for row in rows[:-2]))
        self.assertEqual([button.text for button in rows[-2]], ["⬆️", "⬅️", "➡️", "📂"])
        self.assertEqual([button.text for button in rows[-1]], ["📦 Скачать", "❌ Отмена"])
        self.click("➡️")
        rows = self.bot.messages[-1].reply_markup.keyboard
        self.assertEqual([button.text for button in rows[-2]], ["⬆️", "⬅️", "📂"])
        self.click("⬆️")
        rows = self.bot.messages[-1].reply_markup.keyboard
        self.assertEqual([button.text for button in rows[-2]], ["📂"])
        self.assertEqual([button.text for button in rows[-1]], ["❌ Отмена"])

    def test_symlink_swap_and_send_errors_do_not_leak_or_claim_size_limit(self):
        song = self.root / "song.mp3"
        song.write_bytes(b"audio")
        secret = Path(self.temp.name) / "secret.mp3"
        secret.write_bytes(b"private")
        self.message("/files")
        self.click("Музыка")
        song.unlink()
        song.symlink_to(secret)
        with self.assertLogs("tbot", level="ERROR"):
            self.click("song.mp3")
        self.assertFalse(self.bot.documents)
        self.assertNotIn("50", self.bot.messages[-1].text)
        song.unlink()
        song.write_bytes(b"audio")
        self.message("/files")
        self.click("Музыка")
        with patch.object(self.bot, "send_document", side_effect=RuntimeError("network")), self.assertLogs("tbot", level="ERROR"):
            self.click("song.mp3")
        self.assertNotIn("50", self.bot.messages[-1].text)
        self.assertNotIn("network", self.bot.messages[-1].text)

    def test_archive_temp_cleanup_and_allowlist(self):
        album = self.root / "album"
        album.mkdir()
        (album / "song.mp3").write_bytes(b"audio")
        (album / "log.txt").write_text("private")
        (album / "link.mp3").symlink_to(album / "song.mp3")
        self.message("/files")
        self.click("Музыка")
        self.assertNotIn("archive", [action for action, _ in self.state.actions.values()])
        self.click("album")
        original = self.bot.send_document
        paths = []
        def capture(chat, stream, **kwargs):
            paths.append(Path(stream.name))
            original(chat, stream, **kwargs)
        with patch.object(self.bot, "send_document", side_effect=capture):
            self.click("📦 Скачать")
        self.assertFalse(paths[0].exists())
        self.assertFalse(paths[0].parent.exists())
        with ZipFile(BytesIO(self.bot.documents[-1][1])) as archive:
            self.assertEqual(archive.namelist(), ["song.mp3"])

    def test_worker_survives_download_and_notification_errors(self):
        self.api.download_album.side_effect = [RuntimeError("download"), "ok", "ok again"]
        for i in range(3):
            self.front.queue.put((100, "album", str(i)))
        self.front.queue.put(None)
        with patch.object(self.bot, "send_message", side_effect=RuntimeError("Telegram unavailable")), self.assertLogs("tbot", level="ERROR"):
            self.front.start_worker()
            self.front.worker.join(timeout=5)
        self.assertFalse(self.front.worker.is_alive())
        self.assertEqual(self.api.download_album.call_count, 3)
        self.assertEqual(self.front.queue.unfinished_tasks, 0)

    def test_failed_archive_delivery_cleans_temporary_directory(self):
        album = self.root / "album"
        album.mkdir()
        (album / "song.mp3").write_bytes(b"audio")
        self.message("/files")
        self.click("Музыка")
        self.click("album")
        paths = []
        def fail(chat, stream, **kwargs):
            paths.append(Path(stream.name))
            raise RuntimeError("network")
        with patch.object(self.bot, "send_document", side_effect=fail), self.assertLogs("tbot", level="ERROR"):
            self.click("📦 Скачать")
        self.assertFalse(paths[0].parent.exists())
        self.assertFalse(self.bot.documents)

    def test_api_suppressed_errors_are_not_reported_as_success(self):
        self.api.get_album_info.return_value = None
        self.message("/download")
        self.click("Альбом")
        with self.assertLogs("tbot", level="ERROR"):
            self.message("https://music.yandex.ru/album/123")
        self.assertIsNone(self.state.pending)
        self.api.download_album.return_value = None
        self.front.queue.put((100, "album", "123"))
        self.front.queue.put(None)
        with self.assertLogs("tbot", level="ERROR"):
            self.front.work()
        self.assertIn("Не удалось", self.bot.messages[-1].text)

    def test_api_errors_do_not_expose_exception_text(self):
        self.api.search_artists.side_effect = ValueError("sensitive internal details")
        self.message("/search")
        with self.assertLogs("tbot", level="ERROR"):
            self.message("artist")
        self.assertNotIn("sensitive", self.bot.messages[-1].text)

    def test_confirm_consumed_even_if_notification_fails(self):
        self.message("/search")
        self.message("artist")
        self.click("ID 123")
        call = self.callback_for("✅ Скачать")
        with patch.object(self.bot, "send_message", side_effect=RuntimeError("network")), self.assertLogs("tbot", level="ERROR"):
            self.bot.on_callback(call)
        self.bot.on_callback(call)
        self.assertEqual(self.front.queue.qsize(), 1)


class StartupTests(unittest.TestCase):
    def test_invalid_env_fails_before_api_import_or_bot_creation(self):
        real_import = builtins.__import__
        def guarded_import(name, *args, **kwargs):
            if name == "API":
                self.fail("API imported before authorization validation")
            return real_import(name, *args, **kwargs)
        for value in (None, "", "0", "-5", "not-an-id"):
            env = {} if value is None else {"TELEGRAM_ALLOWED_USER_ID": value}
            with self.subTest(value=value), patch.dict(os.environ, env, clear=True), \
                    patch("dotenv.load_dotenv"), patch("builtins.__import__", side_effect=guarded_import), \
                    patch("tbot.create_bot") as factory:
                with self.assertRaisesRegex(SystemExit, "TELEGRAM_ALLOWED_USER_ID"):
                    tbot.main()
                factory.assert_not_called()

    def test_factory_validates_before_constructing_telegram_bot(self):
        with patch("telebot.TeleBot") as factory:
            with self.assertRaises(ValueError):
                tbot.create_bot(Mock(), "unused", 0)
            factory.assert_not_called()

    def test_factory_disables_threaded_handlers(self):
        with patch("telebot.TeleBot", return_value=FakeBot()) as factory:
            tbot.create_bot(Mock(), "token", 42, start_worker=False)
            factory.assert_called_once_with("token", threaded=False)


if __name__ == "__main__":
    unittest.main()
