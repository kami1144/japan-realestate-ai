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
        import logging, datetime
        log = logging.getLogger("uvicorn.error")
        log.info(f"[LINE] Async task started ts={datetime.datetime.now().isoformat()}")
        try:
            class Event:
                def __init__(self, data):
                    self.type = data.get("type")
                    self.reply_token = data.get("replyToken")
                    self.source = data.get("source", {})
                    if data.get("message"):
                        self.message = type("Message", (), data.get("message", {}))()

            event = Event(event_data)
            log.info(f"[LINE] Processing event type={event.type} reply_token={event.reply_token[:20] if event.reply_token else None}...")
            
            # Run blocking AI call in thread pool
            response_text = await asyncio.to_thread(handle_line_event, event)
            log.info(f"[LINE] Got response: {response_text[:50] if response_text else None}...")

            if response_text and event.reply_token:
                # 重新获取意图以决定 Quick Reply
                from app.modules.intent_module import classify_intent
                from app.modules.line_module import get_quick_reply
                message_text = event.message.text if hasattr(event, "message") and hasattr(event.message, "text") else ""
                intent = classify_intent(message_text)
                quick_reply = get_quick_reply(intent)
                await asyncio.to_thread(reply_message, event.reply_token, response_text, quick_reply)
                log.info(f"[LINE] Reply sent with quick_reply intent={intent}")
            elif not response_text:
                log.warning(f"[LINE] No response generated for event")
            elif not event.reply_token:
                log.warning(f"[LINE] No reply_token in event")
        except Exception as e:
            log.error(f"[LINE] Failed to handle event: {e}", exc_info=True)

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
