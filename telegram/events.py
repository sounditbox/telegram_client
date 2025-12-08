recent_events = []


def add_event(event_data):
    """Добавить событие в список"""
    recent_events.append(event_data)
    if len(recent_events) > 50:
        recent_events.pop(0)


def get_recent_events():
    """Получить список последних событий"""
    return recent_events.copy()


def remove_event(message_id):
    """Удалить событие по message_id"""
    global recent_events
    recent_events = [e for e in recent_events if e.get('message_id') != message_id]
    return True
