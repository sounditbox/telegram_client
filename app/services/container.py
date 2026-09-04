from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings
from app.events.broker import EventBroker
from app.services.auth import AuthService
from app.services.media import MediaService
from app.services.sync import PersistingEventPublisher, SynchronizationService
from app.services.telegram import (
    AccountService,
    DialogService,
    EventService,
    FileService,
    MessagingService,
)
from app.telegram.gateway import TelegramGateway
from app.telegram.manager import TelegramClientManager
from app.storage.repository import TelegramRepository


@dataclass(slots=True)
class Services:
    repository: TelegramRepository
    manager: TelegramClientManager
    auth: AuthService
    account: AccountService
    dialogs: DialogService
    messaging: MessagingService
    files: FileService
    events: EventService
    media: MediaService
    sync: SynchronizationService


def build_services(settings: Settings) -> Services:
    broker = EventBroker()
    repository = TelegramRepository(settings.database_path)
    publisher = PersistingEventPublisher(repository, broker)
    manager = TelegramClientManager(settings, publisher)
    gateway = TelegramGateway(manager)
    sync = SynchronizationService(settings, manager, gateway, repository, broker)
    return Services(
        repository=repository,
        manager=manager,
        auth=AuthService(settings, manager, gateway, broker, repository),
        account=AccountService(gateway),
        dialogs=DialogService(gateway, repository),
        messaging=MessagingService(gateway),
        files=FileService(settings, gateway),
        events=EventService(broker),
        media=MediaService(settings, gateway),
        sync=sync,
    )
