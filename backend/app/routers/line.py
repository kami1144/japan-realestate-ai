"""
LINE Router - LINE Webhook API

路由：
- /webhook - LINE Webhook
- /config - LINE 配置
- /health - 健康检查
"""

import json
import os
import asyncio
import threading
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse

from app.modules.line_module import handle_line_event, reply_message

router = APIRouter()


def _do_reply(reply_token: str, text: str):
    """Background thread target for LINE reply."""
    try:
        reply_message(reply_token, text)
    except Exception as e:
        print(f"[WARN] Reply failed: {e}")


@router.post("/webhook")
async def line_webhook(request: Request):
    """
    LINE Webhook Endpoint

    处理来自 LINE 平台的所有事件。
    """
    body = await request.body()
    signature = request.headers.get("x-line-signature", "")

    # 解析 JSON
    try:
        body_json = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    events = body_json.get("events", [])

    # 处理事件
    for event_data in events:
        try:
            # 创建简单的 Event 对象
            class Event:
                def __init__(self, data):
                    self.type = data.get("type")
                    self.reply_token = data.get("replyToken")
                    self.source = data.get("source", {})
                    if data.get("message"):
                        self.message = type("Message", (), data.get("message", {}))()

            event = Event(event_data)
            response_text = handle_line_event(event)

            if response_text and event.reply_token:
                # Non-blocking reply in background thread
                t = threading.Thread(target=_do_reply, args=(event.reply_token, response_text))
                t.start()
        except Exception as e:
            print(f"[WARN] Failed to handle event: {e}")

    return JSONResponse(content={"status": "ok"})


@router.get("/webhook")
async def line_webhook_get():
    """
    LINE Webhook GET (验证可用性)
    """
    return {"status": "ok", "message": "LINE Webhook is active"}


@router.get("/health")
async def line_health():
    """
    LINE 健康检查
    """
    return {"status": "ok"}


class LineConfigRequest:
    pass


@router.get("/config")
async def line_config():
    """
    LINE 配置信息
    """
    return {
        "channel_secret_set": bool(os.getenv("LINE_CHANNEL_SECRET")),
        "channel_access_token_set": bool(os.getenv("LINE_CHANNEL_ACCESS_TOKEN")),
    }


@router.post("/config")
async def line_config_update():
    """
    更新 LINE 配置（预留）
    """
    return {"status": "ok", "message": "Config update not implemented"}
