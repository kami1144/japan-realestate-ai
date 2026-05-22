"""
LINE Module - Handle LINE Webhook Events

使用 httpx 直接调用 LINE API，不依赖 line-bot-sdk。
"""
import os
import logging
from typing import Optional, List, Any
import httpx

from app.modules.intent_module import classify_intent, IntentType
from app.modules.faq_module import get_faq_answer
from app.modules.ai_module import call_ai

logger = logging.getLogger(__name__)

# LINE API 配置
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
LINE_API_BASE = "https://api.line.me/v2/bot"


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
    logger.info(f"Classified intent: {intent} for text: {text[:50]}...")

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
    from app.modules.ocr_module import extract_property_info

    try:
        message_content = get_message_content(event.message.id)
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
    处理房源咨询：先用 KB 搜索，匹配到房源则返回结构化信息，
    未匹配到则由 AI 补充回答。
    """
    from app.modules.ai_module import call_ai
    from app.knowledge.kb import search_properties, format_property_for_line, get_all_properties

    # 尝试从文本中提取搜索条件
    area_kw = None
    for kw in ["东京", "大阪", "涩谷", "新宿", "浅草", "横滨"]:
        if kw in text:
            area_kw = kw
            break

    min_yield = None
    for yield_kw in ["利回り", "回报率", "收益率"]:
        if yield_kw in text:
            # 尝试提取数字
            import re
            m = re.search(r"(\d+(?:\.\d+)?)\s*[%％]", text)
            if m:
                min_yield = float(m.group(1))
                break

    min_price = None
    max_price = None
    import re
    price_m = re.search(r"(\d+)00\s*万", text)
    if price_m:
        min_price = int(price_m.group(1)) * 100

    # KB 搜索
    results = search_properties(
        min_price=min_price,
        max_price=max_price,
        min_yield=min_yield,
        area=area_kw,
    )

    if results:
        lines = [f"为您找到 {len(results)} 个符合条件的房源：\n"]
        for prop in results[:3]:  # 最多返回3个
            lines.append(format_property_for_line(prop))
            lines.append("")
        if len(results) > 3:
            lines.append(f"还有 {len(results) - 3} 个房源，告诉我您的具体需求，我帮您筛选。")
        return "\n".join(lines)
    else:
        # 无 KB 结果，用 AI，附带 FAQ 知识
        faq_context = "已知房源：新宿物件(3500万/5.2%)、涩谷物件(4200万/4.8%)、大阪难波物件(2800万/6.1%)"
        prompt = f"用户询问房源信息：{text}\n\n{faq_context}\n\n请以中文回答，结合已知房源信息推荐，并使用认知翻译解释日本房产术语。"
        return call_ai(prompt)


def _handle_cost_explanation(text: str) -> str:
    """
    处理费用咨询：先用 KB 费用计算器，再用 FAQ，最后 AI。
    """
    from app.modules.faq_module import get_faq_answer
    from app.modules.ai_module import call_ai
    from app.knowledge.kb import calculate_initial_cost

    # 1. 尝试从文本提取价格计算初期费用
    import re
    price_m = re.search(r"(\d+)万", text)
    if price_m:
        price = int(price_m.group(1))
        fee = calculate_initial_cost(price)
        lines = [
            f"💰 初期费用估算（房价 {price} 万円）：",
            f"",
            f"※ 租金按表面利回り5%估算（月租约 {fee.deposit * 10000:,} 円）",
            f"",
            f"  敷金（押金）：{fee.deposit * 10000:,} 円",
            f"  礼金（好处费）：{fee.key_money * 10000:,} 円",
            f"  火灾保险：{fee.fire_insurance:,} 円/年",
            f"  地震保险：{fee.earthquake_insurance:,} 円/年",
            f"  固定资产税：{fee.fixed_asset_tax:,} 円/年",
            f"  都市计划税：{fee.city_planning_tax:,} 円/年",
        ]
        return "\n".join(lines)

    # 2. 查 FAQ
    faq_answer = get_faq_answer(text)
    if faq_answer:
        return faq_answer

    # 3. 最后走 AI
    prompt = f"用户询问日本房产费用：{text}\n\n请用中文解释，并对比中国类似概念。"
    return call_ai(prompt)


def _handle_rules_explanation(text: str) -> str:
    """
    处理规则咨询：先查结构化规则知识库 → FAQ → AI。
    """
    from app.modules.faq_module import get_faq_answer, search_rules_knowledge
    from app.modules.ai_module import call_ai

    # 1. 先查结构化规则知识库
    rules_answer = search_rules_knowledge(text)
    if rules_answer:
        return rules_answer

    # 2. 再查 FAQ
    faq_answer = get_faq_answer(text)
    if faq_answer:
        return faq_answer

    # 3. 最后才走 AI
    prompt = f"用户询问日本房产相关规则：{text}\n\n请用中文详细解释，并对比中国相关制度。"
    return call_ai(prompt)


def _handle_document_request(text: str) -> str:
    from app.modules.ai_module import call_ai
    prompt = f"用户请求资料：{text}\n\n请确认用户需要的资料类型（户型图、投资分析PDF、市场报告等），并引导用户提供邮箱或LINE联系方式。"
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


def get_message_content(message_id: str) -> bytes:
    """
    Get message content from LINE API.

    Args:
        message_id: LINE message ID

    Returns:
        Content bytes
    """
    if not LINE_CHANNEL_ACCESS_TOKEN:
        raise ValueError("LINE_CHANNEL_ACCESS_TOKEN not set")

    with httpx.Client() as client:
        response = client.get(
            f"{LINE_API_BASE}/message/{message_id}/content",
            headers={"Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"},
        )
        response.raise_for_status()
        return response.content


def reply_message(reply_token: str, text: str, quick_reply: List[Any] = None) -> None:
    """
    Reply to LINE user.

    Args:
        reply_token: LINE reply token
        text: Reply text
        quick_reply: Optional list of quick reply items
    """
    if not LINE_CHANNEL_ACCESS_TOKEN:
        raise ValueError("LINE_CHANNEL_ACCESS_TOKEN not set")

    message = {"type": "text", "text": text}
    if quick_reply:
        message["quickReply"] = {"items": quick_reply}

    with httpx.Client(timeout=10.0) as client:
        response = client.post(
            f"{LINE_API_BASE}/message/reply",
            headers={
                "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
                "Content-Type": "application/json",
            },
            json={
                "replyToken": reply_token,
                "messages": [message],
            },
        )
        response.raise_for_status()


def push_message(line_id: str, text: str) -> None:
    """
    Push message to LINE user.

    Args:
        line_id: LINE user ID
        text: Message text
    """
    if not LINE_CHANNEL_ACCESS_TOKEN:
        raise ValueError("LINE_CHANNEL_ACCESS_TOKEN not set")

    with httpx.Client() as client:
        response = client.post(
            f"{LINE_API_BASE}/message/push",
            headers={
                "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
                "Content-Type": "application/json",
            },
            json={
                "to": line_id,
                "messages": [{"type": "text", "text": text}],
            },
        )
        response.raise_for_status()


# Quick Reply 按钮配置（按意图）
QUICK_REPLY_ITEMS = {
    "default": [
        {"type": "action", "action": {"type": "message", "label": "🔍 房源咨询", "text": "我想找房源"}},
        {"type": "action", "action": {"type": "message", "label": "💰 费用说明", "text": "费用有哪些"}},
        {"type": "action", "action": {"type": "message", "label": "📋 规则说明", "text": "永住条件"}},
        {"type": "action", "action": {"type": "message", "label": "📄 要资料", "text": "我要资料"}},
    ],
    IntentType.PROPERTY_INQUIRY: [
        {"type": "action", "action": {"type": "message", "label": "💰 费用说明", "text": "费用有哪些"}},
        {"type": "action", "action": {"type": "message", "label": "📋 规则说明", "text": "永住条件"}},
        {"type": "action", "action": {"type": "message", "label": "📄 要资料", "text": "我要资料"}},
    ],
    IntentType.COST_EXPLANATION: [
        {"type": "action", "action": {"type": "message", "label": "🔍 房源咨询", "text": "我想找房源"}},
        {"type": "action", "action": {"type": "message", "label": "📋 规则说明", "text": "永住条件"}},
        {"type": "action", "action": {"type": "message", "label": "📄 要资料", "text": "我要资料"}},
    ],
    IntentType.RULES_EXPLANATION: [
        {"type": "action", "action": {"type": "message", "label": "🔍 房源咨询", "text": "我想找房源"}},
        {"type": "action", "action": {"type": "message", "label": "💰 费用说明", "text": "费用有哪些"}},
        {"type": "action", "action": {"type": "message", "label": "📄 要资料", "text": "我要资料"}},
    ],
    IntentType.DOCUMENT_REQUEST: [
        {"type": "action", "action": {"type": "message", "label": "🔍 房源咨询", "text": "我想找房源"}},
        {"type": "action", "action": {"type": "message", "label": "💰 费用说明", "text": "费用有哪些"}},
        {"type": "action", "action": {"type": "message", "label": "📋 规则说明", "text": "永住条件"}},
    ],
}


def get_quick_reply(intent: str) -> List[Any]:
    """根据意图返回对应的 Quick Reply 按钮列表。"""
    return QUICK_REPLY_ITEMS.get(intent, QUICK_REPLY_ITEMS["default"])


def send_response(line_id: str, text: str) -> None:
    """
    Send text response to LINE user.
    """
    push_message(line_id, text)