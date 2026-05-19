"""
LINE Router - LINE Webhook API

路由：
- /line/webhook - LINE Webhook
- /line/config - LINE 配置
- /line/health - 健康检查
"""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from linebot.webhook import WebhookPayload
from pydantic import BaseModel

from modules.line_module import handle_line_event, line_parser, line_api

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
    # 解析签名
    signature = request.headers.get("x-line-signature", "")
    body = await request.body()

    # 验证签名（生产环境应验证）
    # try:
    #     line_parser.validate_signature(body, signature)
    # except InvalidSignatureError:
    #     raise HTTPException(status_code=400, detail="Invalid signature")

    # 解析事件
    try:
        events = line_parser.parse(body.decode("utf-8"), signature)
    except Exception as e:
        print(f"[WARN] Failed to parse LINE event: {e}")
        # 开发环境直接解析
        try:
            import json
            body_json = json.loads(body)
            events = []
            for event_data in body_json.get("events", []):
                events.append(event_data)
        except:
            raise HTTPException(status_code=400, detail="Invalid payload")

    # 处理事件
    for event in events:
        try:
            response_text = handle_line_event(event)
            if response_text:
                # 回复用户
                reply_token = getattr(event, "reply_token", None)
                if reply_token:
                    line_api.reply_message(reply_token, response_text)
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
    import os

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