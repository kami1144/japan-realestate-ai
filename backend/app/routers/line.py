"""
LINE Router - LINE Webhook API
"""

import json
import os
import asyncio
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse

from app.modules.line_module import handle_line_event, reply_message

router = APIRouter()


@router.post("/webhook")
async def line_webhook(request: Request):
    """
    LINE Webhook Endpoint.
    Responds 200 immediately, handles AI + reply asynchronously.
    """
    body = await request.body()
    signature = request.headers.get("x-line-signature", "")

    # 解析 JSON
    try:
        body_json = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    events = body_json.get("events", [])

    # 立即响应 LINE
    async def process_event(event_data: dict):
        """Process event and reply asynchronously after response is sent."""
        try:
            class Event:
                def __init__(self, data):
                    self.type = data.get("type")
                    self.reply_token = data.get("replyToken")
                    self.source = data.get("source", {})
                    if data.get("message"):
                        self.message = type("Message", (), data.get("message", {}))()

            event = Event(event_data)
            # Run blocking AI call in thread pool
            response_text = await asyncio.to_thread(handle_line_event, event)
            if response_text and event.reply_token:
                await asyncio.to_thread(reply_message, event.reply_token, response_text)
        except Exception as e:
            print(f"[WARN] Failed to handle event: {e}")

    # 启动异步任务，不等待
    for event_data in events:
        asyncio.create_task(process_event(event_data))

    return JSONResponse(content={"status": "ok"})


@router.get("/webhook")
async def line_webhook_get():
    return {"status": "ok", "message": "LINE Webhook is active"}


@router.get("/health")
async def line_health():
    return {"status": "ok"}


class LineConfigRequest:
    pass


@router.get("/config")
async def line_config():
    return {
        "channel_secret_set": bool(os.getenv("LINE_CHANNEL_SECRET")),
        "channel_access_token_set": bool(os.getenv("LINE_CHANNEL_ACCESS_TOKEN")),
    }


@router.post("/config")
async def line_config_update():
    return {"status": "ok", "message": "Config update not implemented"}
