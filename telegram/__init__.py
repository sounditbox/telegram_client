from .client import client
from .handlers import setup_event_handlers
from .auth import auth_state
from .dialogs import get_dialogs, get_chat_participants, mark_chat_as_read
from .messages import get_chat_messages, send_message_to, validate_entity
from .events import get_recent_events, remove_event
from .user import get_client_info

__all__ = [
    'client',
    'setup_event_handlers',
    'auth_state',
    'get_dialogs',
    'get_chat_participants',
    'mark_chat_as_read',
    'get_chat_messages',
    'send_message_to',
    'validate_entity',
    'get_recent_events',
    'remove_event',
    'get_client_info',
]

