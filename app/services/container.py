from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings
from app.events.broker import EventBroker
from app.services.auth import AuthService
from app.services.media import MediaService
from app.services.telegram import (
    AccountService,
    DialogService,
    EventService,
    FileService,
    MessagingService,
)
from app.telegram.gateway import TelegramGateway
from app.telegram.manager import TelegramClientManager


@dataclass(slots=True)
class Services:
    manager: TelegramClientManager
    auth: AuthService
    account: AccountService
    dialogs: DialogService
    messaging: MessagingService
    files: FileService
    events: EventService
    media: MediaService


def build_services(settings: Settings) -> Services:
    broker = EventBroker()
    manager = TelegramClientManager(settings, broker)
    gateway = TelegramGateway(manager)
    return Services(
        manager=manager,
        auth=AuthService(settings, manager, gateway, broker),
        account=AccountService(gateway),
        dialogs=DialogService(gateway),
        messaging=MessagingService(gateway),
        files=FileService(settings, gateway),
        events=EventService(broker),
        media=MediaService(settings, gateway),
    )
