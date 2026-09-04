from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles


ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "frontend" / "dist"
app = FastAPI()


def envelope(data: object) -> dict[str, object]:
    return {"ok": True, "data": data}


def dialog(index: int) -> dict[str, object]:
    return {
        "id": 100 + index,
        "title": f"Dialog {index:02d}",
        "username": f"dialog{index}",
        "unread_count": 2 if index == 1 else 0,
        "kind": "user",
        "has_avatar": False,
    }


def message(index: int) -> dict[str, object]:
    return {
        "id": index,
        "text": f"Message {index}",
        "sender_id": 501,
        "sender_name": "Alice",
        "sender_username": "alice",
        "sender_has_avatar": False,
        "date": datetime(2026, 1, 1, 12, index % 60, tzinfo=UTC).isoformat(),
        "outgoing": index % 2 == 0,
        "is_reply": False,
        "has_media": False,
        "media": None,
    }


DIALOGS = [dialog(index) for index in range(1, 46)]
MESSAGES = [message(index) for index in range(60, 0, -1)]


@app.get("/api/health")
async def health():
    return envelope({"status": "ok"})


@app.get("/api/auth/status")
async def auth_status():
    return envelope(
        {
            "connected": True,
            "authenticated": True,
            "phase": "authorized",
            "user": {
                "id": 900,
                "first_name": "Test",
                "last_name": "User",
                "username": "testuser",
                "is_bot": False,
                "has_avatar": False,
            },
        }
    )


@app.get("/api/dialogs")
async def dialogs(
    limit: int = Query(default=40),
    cursor: int = Query(default=0),
    query: str | None = None,
    refresh: bool = False,
):
    del refresh
    values = DIALOGS
    if query:
        lowered = query.casefold()
        values = [item for item in values if lowered in str(item["title"]).casefold()]
    page = values[cursor : cursor + limit + 1]
    items = page[:limit]
    has_more = len(page) > limit
    return envelope(
        {
            "items": items,
            "has_more": has_more,
            "next_cursor": cursor + len(items) if has_more else None,
        }
    )


@app.get("/api/dialogs/{chat_id}/messages")
async def messages(
    chat_id: int,
    limit: int = Query(default=40),
    cursor: int | None = None,
    refresh: bool = False,
):
    del chat_id, refresh
    values = MESSAGES
    if cursor is not None:
        values = [item for item in values if int(item["id"]) < cursor]
    page = values[: limit + 1]
    items = page[:limit]
    has_more = len(page) > limit
    return envelope(
        {
            "items": items,
            "has_more": has_more,
            "next_cursor": items[-1]["id"] if has_more and items else None,
        }
    )


@app.post("/api/dialogs/{chat_id}/read")
async def mark_read(chat_id: int):
    del chat_id
    return envelope({"read": True})


@app.get("/api/events/stream")
async def events():
    async def generate():
        await asyncio.sleep(1.5)
        payload = {
            "sequence": 1001,
            "kind": "new_message",
            "message_id": 61,
            "chat_id": 101,
            "text": "Realtime message arrived",
            "sender_id": 501,
            "sender_name": "Alice",
            "sender_username": "alice",
            "sender_has_avatar": False,
            "chat_title": "Dialog 01",
            "date": datetime.now(UTC).isoformat(),
            "outgoing": False,
            "has_media": False,
            "media": None,
        }
        yield f"id: 1001\nevent: new_message\ndata: {json.dumps(payload)}\n\n"
        while True:
            await asyncio.sleep(5)
            yield ": keep-alive\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")


@app.get("/")
async def frontend():
    return FileResponse(DIST / "index.html")


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8011, log_level="warning")
