"""
LINE Module - Handle LINE Webhook Events
"""
import os
import logging
from typing import Optional

from linebot import LineBotApi
from linebot.models import TextSendMessage, QuickReply, QuickReplyButton, MessageAction
from linebot.webhook import WebhookParser

from modules.intent_module import classify_intent, IntentType
from modules.faq_module import get_faq_answer
from modules.ai_module import call_ai

logger = logging.getLogger(__name__)

# LINE API configuration
line_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN", ""))
line_parser = WebhookParser(os.getenv("LINE_CHANNEL_SECRET", ""))


def handle_line_event(event) -> Optional[str]:
    """
    Main entry point to handle LINE events.
    Returns response message or None.
    """
    if event.type == "message":
        if hasattr(event.message, "text"):
            return handle_text_message(event.message.text, event.source)
        elif hasattr(event.message, "type") and event.message.type == "image":
            return handle_image_message(event)
    elif event.type == "postback":
        return handle_postback(event.postback.data)

    return None


def handle_text_message(text: str, source) -> str:
    """
    Handle incoming text message.
    """
    # Classify intent
    intent = classify_intent(text)
    logger.info(f"Classified intent: {intent.value} for text: {text[:50]}...")

    # Route to appropriate handler
    if intent == IntentType.PROPERTY_INQUIRY:
        return _handle_property_inquiry(text)
    elif intent == IntentType.COST_EXPLANATION:
        return _handle_cost_explanation(text)
    elif intent == IntentType.RULES_EXPLANATION:
        return _handle_rules_explanation(text)
    elif intent == IntentType.DOCUMENT_REQUEST:
        return _handle_document_request(text)
    elif intent == IntentType.GENERAL:
        # Check FAQ first
        faq_answer = get_faq_answer(text)
        if faq_answer:
            return faq_answer
        # Fall back to AI
        return call_ai(text)
    else:
        # Default to AI
        return call_ai(text)


def handle_image_message(event) -> str:
    """
    Handle incoming image message - extract property info from PDF/image.
    """
    from modules.ocr_module import extract_property_info

    try:
        message_content = line_api.get_message_content(event.message.id)
        property_info = extract_property_info(message_content)

        if property_info:
            return _format_property_info(property_info)
        else:
            return "无法识别图片中的房源信息，请提供清晰的户型图或PDF文件。"
    except Exception as e:
        logger.error(f"Error processing image: {e}")
        return "图片处理失败，请重试或提供其他格式的文件。"


def handle_postback(data: str) -> str:
    """
    Handle postback events (quick reply actions).
    """
    if data == "property_search":
        return "请告诉我您想寻找的房源条件：区域、预算、收益率等。"
    elif data == "cost_inquiry":
        return "请问您想了解哪项费用？初期费用、管理费、修缮费还是贷款相关？"
    elif data == "rules_inquiry":
        return "请问您想了解哪方面的规则？永住、签证、民宿合法还是外国人贷款？"
    elif data == "get_document":
        return "请提供您的邮箱，我会发送相关资料给您。"
    else:
        return "请告诉我您需要什么帮助。"


def _handle_property_inquiry(text: str) -> str:
    """
    Handle property inquiry intent.
    """
    from modules.ai_module import call_ai

    prompt = f"""用户询问房源信息：{text}

请以中文回答，并使用认知翻译解释日本房产术语。"""

    return call_ai(prompt)


def _handle_cost_explanation(text: str) -> str:
    """
    Handle cost explanation intent - with cognitive translation.
    """
    # Check if it's a FAQ
    faq_answer = get_faq_answer(text)
    if faq_answer:
        return faq_answer

    # Use AI for more detailed explanation
    from modules.ai_module import call_ai

    prompt = f"""用户询问日本房产费用：{text}

请用中文解释以下费用概念，并对比中国类似概念：
- 初期费用（登录许可证、火灾保险等）
- 管理费（共益费）
- 修缮费（修缮积立金）
- 固定资产税
- 、都市计划税
- 贷款相关费用"""

    return call_ai(prompt)


def _handle_rules_explanation(text: str) -> str:
    """
    Handle rules explanation intent - with legal context.
    """
    # Check if it's a FAQ
    faq_answer = get_faq_answer(text)
    if faq_answer:
        return faq_answer

    # Use AI for detailed explanation
    from modules.ai_module import call_ai

    prompt = f"""用户询问日本房产相关规则：{text}

请用中文详细解释以下内容：
1. 永住申请条件与房产关系
2. 签证类型与房产投资
3. 民宿合法化（民宿许可vs特区民宿）
4. 外国人贷款条件
5. 海外投资者的税务义务"""

    return call_ai(prompt)


def _handle_document_request(text: str) -> str:
    """
    Handle document request intent.
    """
    from modules.ai_module import call_ai

    prompt = f"""用户请求资料：{text}

请确认用户需要的资料类型（户型图、投资分析PDF、市场报告等），并引导用户提供邮箱或LINE联系方式。"""

    return call_ai(prompt)


def _format_property_info(info: dict) -> str:
    """
    Format property info for LINE response.
    """
    lines = ["📍 识别到的房源信息："]

    if info.get("address"):
        lines.append(f"地址: {info['address']}")
    if info.get("area"):
        lines.append(f"面积: {info['area']}")
    if info.get("price"):
        lines.append(f"价格: {info['price']}")
    if info.get("yield"):
        lines.append(f"利回り: {info['yield']}")
    if info.get("management_fee"):
        lines.append(f"管理费: {info['management_fee']}")
    if info.get("repair_cost"):
        lines.append(f"修缮费: {info['repair_cost']}")

    return "\n".join(lines)


def create_quick_reply_buttons() -> QuickReply:
    """
    Create quick reply buttons for common actions.
    """
    return QuickReply(
        items=[
            QuickReplyButton(action=MessageAction(label="🔍 房源咨询", text="我想找房源")),
            QuickReplyButton(action=MessageAction(label="💰 费用说明", text="费用有哪些")),
            QuickReplyButton(action=MessageAction(label="📋 规则说明", text="永住条件")),
            QuickReplyButton(action=MessageAction(label="📄 要资料", text("我要资料")),
        ]
    )


def send_response(line_id: str, text: str) -> None:
    """
    Send text response to LINE user.
    """
    line_api.push_message(
        line_id,
        TextSendMessage(text=text, quick_reply=create_quick_reply_buttons())
    )