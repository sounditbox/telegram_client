import asyncio
import json
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

from fastapi import UploadFile
from fastapi.testclient import TestClient
from pydantic import ValidationError
from telethon import errors

from app.core.config import Settings
from app.core.errors import AuthFlowError, InvalidUpload
from app.events.broker import EventBroker
from app.main import create_app
from app.models import DialogInfo, EventRecord, MediaInfo, MessageInfo
from app.services.auth import AuthPhase, AuthService
from app.services.media import MediaService
from app.services.telegram import DialogService, FileService
from app.storage.repository import TelegramRepository
from app.telegram.gateway import DownloadedMedia, TelegramGateway
from app.telegram.handlers import TelegramEventHandlers
from app.telegram.serialization import media_info


class FakeClient:
    def __init__(self):
        self.authorized = False
        self.password_required = False

    async def is_user_authorized(self):
        return self.authorized

    async def send_code_request(self, _phone):
        return SimpleNamespace(phone_code_hash="server-side-only")

    async def sign_in(self, **kwargs):
        if self.password_required and not kwargs.get("password"):
            raise errors.SessionPasswordNeededError(request=None)
        self.authorized = True


class FakeManager:
    connected = True

    def __init__(self, client):
        self.client = client

    async def ensure_connected(self):
        return self.client

    async def is_authorized(self):
        return self.client.authorized


class AuthTests(unittest.IsolatedAsyncioTestCase):
    async def test_2fa_is_an_explicit_phase_and_hash_is_not_returned(self):
        client = FakeClient()
        client.password_required = True
        settings = Settings(API_ID=1, API_HASH="hash", SESSION_DIR="data/sessions", UPLOAD_DIR="data/uploads")
        service = AuthService(settings, FakeManager(client), AsyncMock(), AsyncMock())

        action = await service.request_code("+995555123456")
        password_action = await service.verify_code("12345")

        self.assertEqual(action.phase, AuthPhase.CODE_SENT)
        self.assertEqual(password_action.phase, AuthPhase.PASSWORD_REQUIRED)
        self.assertNotIn("server-side-only", action.model_dump_json())

    async def test_code_cannot_be_verified_without_an_active_attempt(self):
        settings = Settings(API_ID=1, API_HASH="hash")
        service = AuthService(settings, FakeManager(FakeClient()), AsyncMock(), AsyncMock())
        with self.assertRaises(AuthFlowError):
            await service.verify_code("12345")

    async def test_password_completes_two_factor_flow(self):
        client = FakeClient()
        client.password_required = True
        settings = Settings(API_ID=1, API_HASH="hash")
        service = AuthService(settings, FakeManager(client), AsyncMock(), AsyncMock())
        await service.request_code("+995555123456")
        await service.verify_code("12345")
        result = await service.verify_password("secret")
        self.assertEqual(result.phase, AuthPhase.AUTHORIZED)
        self.assertTrue(client.authorized)


class EventTests(unittest.IsolatedAsyncioTestCase):
    async def test_broker_assigns_unique_sequence_ids(self):
        broker = EventBroker()
        first = await broker.publish(kind="new_message", message_id=1, chat_id=10, text="a", sender_name="u", chat_title="c")
        second = await broker.publish(kind="new_message", message_id=1, chat_id=11, text="b", sender_name="u", chat_title="d")
        self.assertEqual((first.sequence, second.sequence), (1, 2))
        stream = broker.stream(after=1)
        block = await anext(stream)
        payload = json.loads(next(line[5:] for line in block.splitlines() if line.startswith("data:")))
        self.assertEqual(payload["chat_id"], 11)
        await stream.aclose()

    async def test_broker_drops_oldest_backlog_item_when_full(self):
        broker = EventBroker(max_events=2)
        for index in range(3):
            await broker.publish(kind="new_message", message_id=index + 1, chat_id=1, text=str(index), sender_name="u", chat_title="c")
        stream = broker.stream(after=0)
        block = await anext(stream)
        self.assertIn('"sequence": 2', block)
        await stream.aclose()

    async def test_broker_restores_sequence_and_replays_only_missing_events(self):
        broker = EventBroker()
        restored = [
            EventRecord(
                sequence=40,
                kind="new_message",
                message_id=4,
                chat_id=1,
                text="restored",
                sender_name="Alice",
                chat_title="Chat",
            )
        ]
        await broker.restore(restored)
        await broker.publish(
            kind="new_message",
            message_id=5,
            chat_id=1,
            text="next",
            sender_name="Alice",
            chat_title="Chat",
        )

        stream = broker.stream(after=40)
        block = await anext(stream)
        self.assertIn('"sequence": 41', block)
        self.assertIn('"text": "next"', block)
        await stream.aclose()


class HandlerTests(unittest.TestCase):
    def test_register_is_idempotent(self):
        client = SimpleNamespace(
            handlers=[],
            add_event_handler=lambda callback, event: client.handlers.append((callback, event)),
            remove_event_handler=lambda callback: None,
        )
        handlers = TelegramEventHandlers(client, EventBroker())
        handlers.register()
        handlers.register()
        self.assertEqual(len(client.handlers), 2)


class FileTests(unittest.IsolatedAsyncioTestCase):
    async def test_upload_is_cleaned_and_filename_is_sanitized(self):
        root = Path(tempfile.mkdtemp(prefix="telegram-desk-test-"))
        settings = Settings(API_ID=1, API_HASH="hash", SESSION_DIR=root / "s", UPLOAD_DIR=root / "u", MAX_UPLOAD_BYTES=1024)
        gateway = SimpleNamespace(send_file=AsyncMock(return_value=7))
        service = FileService(settings, gateway)
        upload = UploadFile(filename="../../bad?.txt", file=BytesIO(b"payload"))
        result = await service.send("1", upload, caption="")
        self.assertEqual(result.filename, "bad.txt")
        self.assertEqual(list(settings.upload_dir.iterdir()), [])
        for path in sorted(root.glob("**/*"), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
        root.rmdir()

    async def test_oversized_upload_is_rejected_and_cleaned(self):
        root = Path(tempfile.mkdtemp(prefix="telegram-desk-test-"))
        settings = Settings(API_ID=1, API_HASH="hash", UPLOAD_DIR=root / "u", MAX_UPLOAD_BYTES=1024)
        service = FileService(settings, SimpleNamespace(send_file=AsyncMock()))
        upload = UploadFile(filename="large.bin", file=BytesIO(b"x" * 1025))
        with self.assertRaises(InvalidUpload):
            await service.send("1", upload, caption="")
        self.assertEqual(list(settings.upload_dir.iterdir()), [])
        settings.upload_dir.rmdir()
        root.rmdir()


class FakeMediaGateway:
    def __init__(self):
        self.avatar_calls = 0
        self.media_calls = 0

    async def download_avatar(self, _entity_id):
        self.avatar_calls += 1
        return b"jpeg"

    async def download_message_media(self, _chat_id, _message_id, destination, _max_bytes):
        self.media_calls += 1
        path = destination.with_suffix(".jpg")
        path.write_bytes(b"image")
        return DownloadedMedia(path=path, media_type="image/jpeg", filename="photo.jpg")


class MediaTests(unittest.IsolatedAsyncioTestCase):
    async def test_avatar_and_message_media_are_cached(self):
        root = Path(tempfile.mkdtemp(prefix="telegram-desk-media-"))
        gateway = FakeMediaGateway()
        settings = Settings(API_ID=1, API_HASH="hash", MEDIA_CACHE_DIR=root)
        service = MediaService(settings, gateway)
        await service.avatar("10")
        await service.avatar("10")
        first = await service.message_media("10", 20)
        second = await service.message_media("10", 20)
        self.assertEqual(gateway.avatar_calls, 1)
        self.assertEqual(gateway.media_calls, 1)
        self.assertEqual(first.path, second.path)
        first.path.unlink()
        root.rmdir()

    def test_photo_metadata_is_serialized(self):
        message = SimpleNamespace(
            id=9,
            photo=object(),
            voice=None,
            video=None,
            audio=None,
            sticker=None,
            file=SimpleNamespace(name=None, ext=".jpg", mime_type="image/jpeg", size=120),
        )
        media = media_info(message)
        self.assertEqual(media.kind, "photo")
        self.assertEqual(media.filename, "media_9.jpg")


class RepositoryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="telegram-desk-db-"))
        self.repository = TelegramRepository(self.root / "cache.sqlite3")
        await self.repository.initialize()

    async def asyncTearDown(self):
        for path in self.root.iterdir():
            path.unlink()
        self.root.rmdir()

    async def test_dialogs_and_messages_round_trip(self):
        await self.repository.store_dialogs(
            [
                DialogInfo(id=20, title="Second", kind="group"),
                DialogInfo(id=10, title="First", kind="user", unread_count=2),
            ]
        )
        await self.repository.store_messages(
            10,
            [
                MessageInfo(id=2, text="new", sender_name="Alice"),
                MessageInfo(
                    id=1,
                    text="photo",
                    sender_name="Alice",
                    has_media=True,
                    media=MediaInfo(
                        kind="photo",
                        mime_type="image/jpeg",
                        filename="one.jpg",
                        size=12,
                    ),
                ),
            ],
        )

        dialogs = await self.repository.list_dialogs(10)
        messages = await self.repository.list_messages("10", 10)

        self.assertEqual([dialog.id for dialog in dialogs], [20, 10])
        self.assertEqual([message.id for message in messages], [2, 1])
        self.assertEqual(messages[1].media.filename, "one.jpg")

    async def test_event_updates_existing_message_before_delivery(self):
        await self.repository.store_messages(
            10,
            [MessageInfo(id=7, text="before", sender_name="Alice")],
        )
        stored = await self.repository.store_event(
            EventRecord(
                sequence=1,
                kind="message_edited",
                message_id=7,
                chat_id=10,
                text="after",
                sender_name="Alice",
                chat_title="Chat",
            )
        )

        messages = await self.repository.list_messages(10, 10)
        self.assertEqual(messages[0].text, "after")
        self.assertGreater(stored.sequence, 0)

        reopened = TelegramRepository(self.root / "cache.sqlite3")
        await reopened.initialize()
        persisted_events = await reopened.list_events()
        self.assertEqual(persisted_events[-1].sequence, stored.sequence)
        self.assertEqual(persisted_events[-1].text, "after")

    async def test_dialog_cursor_and_search_are_applied_in_storage(self):
        await self.repository.store_dialogs(
            [
                DialogInfo(id=1, title="Alpha", kind="user"),
                DialogInfo(id=2, title="Beta 100%", kind="group"),
                DialogInfo(id=3, title="Gamma", kind="channel"),
            ]
        )

        second_page = await self.repository.list_dialogs(2, cursor=1)
        search = await self.repository.list_dialogs(10, query="100%")

        self.assertEqual([dialog.id for dialog in second_page], [2, 3])
        self.assertEqual([dialog.id for dialog in search], [2])


class FakePaginationGateway:
    def __init__(self):
        self.dialogs = [
            DialogInfo(id=index, title=f"Dialog {index}", kind="user")
            for index in range(1, 6)
        ]
        self.messages = [
            MessageInfo(id=index, text=str(index), sender_name="Alice")
            for index in range(7, 0, -1)
        ]

    async def list_dialogs(self, limit):
        return self.dialogs[:limit]

    async def list_messages(self, _chat_id, limit, *, before_id=None):
        messages = self.messages
        if before_id is not None:
            messages = [message for message in messages if message.id < before_id]
        return messages[:limit]


class PaginationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="telegram-desk-page-"))
        self.repository = TelegramRepository(self.root / "cache.sqlite3")
        await self.repository.initialize()
        self.service = DialogService(FakePaginationGateway(), self.repository)

    async def asyncTearDown(self):
        for path in self.root.iterdir():
            path.unlink()
        self.root.rmdir()

    async def test_dialog_pages_do_not_overlap(self):
        first = await self.service.list(2)
        second = await self.service.list(2, cursor=first.next_cursor)

        self.assertEqual([dialog.id for dialog in first.items], [1, 2])
        self.assertEqual([dialog.id for dialog in second.items], [3, 4])
        self.assertTrue(first.has_more)

    async def test_message_cursor_loads_older_history(self):
        first = await self.service.messages("10", 3)
        second = await self.service.messages("10", 3, before_id=first.next_cursor)

        self.assertEqual([message.id for message in first.items], [7, 6, 5])
        self.assertEqual([message.id for message in second.items], [4, 3, 2])
        self.assertTrue(second.has_more)


class ConfigurationTests(unittest.TestCase):
    def test_public_bind_requires_access_token(self):
        with self.assertRaises(ValidationError):
            Settings(API_ID=1, API_HASH="hash", APP_HOST="0.0.0.0")

    def test_health_does_not_start_telegram_client(self):
        settings = Settings(API_ID=1, API_HASH="hash")
        response = TestClient(create_app(settings)).get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["status"], "ok")

    def test_access_token_protects_api(self):
        settings = Settings(API_ID=1, API_HASH="hash", ACCESS_TOKEN="long-secret")
        response = TestClient(create_app(settings)).get("/api/auth/status")
        self.assertEqual(response.status_code, 401)


class ArchitectureTests(unittest.TestCase):
    def test_routes_do_not_import_telethon_or_global_client(self):
        for route in Path("app/api/routes").glob("*.py"):
            source = route.read_text(encoding="utf-8")
            self.assertNotIn("from telethon", source)
            self.assertNotIn("import telethon", source)
            self.assertNotIn("client.", source)


if __name__ == "__main__":
    unittest.main()
