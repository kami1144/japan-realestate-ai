# Japan Real Estate AI

日本房产投资咨询 LINE Bot，使用 MiniMax AI 进行智能对话。

## 功能

- **房源咨询** - 区域、价格、收益率查询
- **费用说明** - 管理费、修缮费、初期费用等
- **规则说明** - 永住、签证、民宿合法、外国人贷款
- **资料请求** - 户型图、PDF 发送
- **智能对话** - MiniMax AI 驱动的认知翻译

## 架构

```
backend/
├── app/
│   ├── main.py           # FastAPI 入口
│   ├── modules/
│   │   ├── line_module.py    # LINE Webhook
│   │   ├── intent_module.py  # 意图分类
│   │   ├── faq_module.py    # 认知翻译 FAQ
│   │   ├── ocr_module.py    # PDF OCR
│   │   └── ai_module.py     # MiniMax AI
│   ├── routers/
│   │   ├── line.py         # /line/* 路由
│   │   └── property.py    # /api/property/* 路由
│   └── knowledge/
│       └── kb.py          # 房源知识库
└── requirements.txt
```

## 环境变量

| 变量 | 说明 |
|------|------|
| `LINE_CHANNEL_SECRET` | LINE Channel Secret |
| `LINE_CHANNEL_ACCESS_TOKEN` | LINE Access Token |
| `MINIMAX_API_KEY` | MiniMax API Key |

## 启动

```bash
# 1. 安装依赖
cd backend
pip install -r requirements.txt

# 2. 复制环境变量
cp ../.env.example ../.env
# 编辑 .env 填入实际值

# 3. 启动服务
uvicorn app.main:app --reload --port 8002
```

## API

- `GET /` - 根路径
- `GET /line/health` - 健康检查
- `GET /line/webhook` - Webhook 验证
- `POST /line/webhook` - LINE Webhook
- `GET /api/property/list` - 房源列表
- `GET /api/property/{id}` - 房源详情

## LINE 意图分类

1. **property_inquiry** - 房源咨询
2. **cost_explanation** - 费用说明
3. **rules_explanation** - 规则说明
4. **document_request** - 资料请求
5. **general** - 通用问题 → AI

## 认知翻译 FAQ

术语使用中文认知翻译，例如：
- 管理费 → 物业费
- 礼金 → 房东一次性好处费
- 利回り → 投资回报率
- 敷金 → 押金

## GitHub

https://github.com/kami1144/japan-realestate-ai