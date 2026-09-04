from __future__ import annotations

import mimetypes

from app.models import MediaInfo


def media_info(message: object) -> MediaInfo | None:
    file = getattr(message, "file", None)
    if file is None and getattr(message, "photo", None) is None:
        return None

    if getattr(message, "photo", None) is not None:
        kind = "photo"
    elif getattr(message, "voice", None) is not None:
        kind = "voice"
    elif getattr(message, "video", None) is not None:
        kind = "video"
    elif getattr(message, "audio", None) is not None:
        kind = "audio"
    elif getattr(message, "sticker", None) is not None:
        kind = "sticker"
    else:
        kind = "document"

    extension = getattr(file, "ext", None) or (".jpg" if kind == "photo" else "")
    filename = getattr(file, "name", None) or f"media_{getattr(message, 'id', 'file')}{extension}"
    mime_type = getattr(file, "mime_type", None) or mimetypes.guess_type(filename)[0]
    if mime_type is None:
        mime_type = "image/jpeg" if kind in {"photo", "sticker"} else "application/octet-stream"
    return MediaInfo(
        kind=kind,
        mime_type=mime_type,
        filename=filename,
        size=getattr(file, "size", None),
    )
