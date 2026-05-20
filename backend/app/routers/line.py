"""
LINE Router - LINE Webhook API

路由：
- /line/webhook - LINE Webhook
- /line/config - LINE 配置
- /line/health - 健康检查
"""

import json
import os
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.modules.line_module import handle_line_event, reply_message

router = APIRouter()


class WebhookRequest(BaseModel):
    """Webhook 请求体"""
    pass


@router.post("/webhook")
async def line_webhook(request: Request):
    """
    LINE Webhook Endpoint

    处理来自 LINE 平台的所有事件。
    """
    print(f"[LINE WEBHOOK] Received request: {request.method}")
    # 解析请求体
    body = await request.body()
    print(f"[LINE WEBHOOK] Body size: {len(body)} bytes")
    signature = request.headers.get("x-line-signature", "")

    # 解析 JSON
    try:
        body_json = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    events = body_json.get("events", [])

    # 处理事件
    for event_data in events:
        print(f"[DEBUG] Processing event: {event_data}")
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
                try:
                    reply_message(event.reply_token, response_text)
                except Exception as e:
                    print(f"[WARN] Failed to reply: {e}")
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

    Returns:
        健康状态
    """
    return {"status": "ok"}


class LineConfigRequest(BaseModel):
    """LINE 配置请求"""
    pass


@router.get("/config")
async def line_config():
    """
    LINE 配置信息

    Returns:
        LINE 配置
    """
    return {
        "channel_secret_set": bool(os.getenv("LINE_CHANNEL_SECRET")),
        "channel_access_token_set": bool(os.getenv("LINE_CHANNEL_ACCESS_TOKEN")),
    }


@router.post("/config")
async def line_config_update(config: LineConfigRequest):
    """
    更新 LINE 配置（预留）
    """
    return {"status": "ok", "message": "Config update not implemented"}