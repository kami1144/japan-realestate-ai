"""
Property Router - 房源 API

路由：
- /api/property/list - 房源列表
- /api/property/{id} - 房源详情
- /api/property/search - 房源搜索
- /api/property/calculate - 费用计算
"""

from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from knowledge.kb import (
    get_property,
    search_properties,
    calculate_total_income,
    calculate_initial_cost,
    format_property_for_line,
    get_all_properties,
)

router = APIRouter()


class PropertySearchRequest(BaseModel):
    """房源搜索请求"""
    min_price: Optional[int] = None
    max_price: Optional[int] = None
    min_yield: Optional[float] = None
    area: Optional[str] = None


class CalculateCostRequest(BaseModel):
    """费用计算请求"""
    price: int
    deposit_months: int = 1
    key_money_months: int = 1


@router.get("/list")
async def property_list():
    """
    获取房源列表

    Returns:
        所有房源
    """
    properties = get_all_properties()
    return {
        "count": len(properties),
        "items": [
            {
                "id": p.id,
                "name": p.name,
                "address": p.address,
                "area": p.area,
                "price": p.price,
                "yield": p.yield_percent,
                "station": p.station,
            }
            for p in properties
        ],
    }


@router.get("/{property_id}")
async def property_detail(property_id: str):
    """
    获取房源详情

    Args:
        property_id: 房源 ID

    Returns:
        房源详情
    """
    prop = get_property(property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    income = calculate_total_income(property_id)

    return {
        "id": prop.id,
        "name": prop.name,
        "address": prop.address,
        "area": prop.area,
        "price": prop.price,
        "yield": prop.yield_percent,
        "management_fee": prop.management_fee,
        "repair_cost": prop.repair_cost,
        "station": prop.station,
        "walk_minutes": prop.walk_minutes,
        "build_year": prop.build_year,
        "property_type": prop.property_type,
        "income": income,
    }


@router.post("/search")
async def property_search(request: PropertySearchRequest):
    """
    搜索房源

    Returns:
        匹配的房源列表
    """
    properties = search_properties(
        min_price=request.min_price,
        max_price=request.max_price,
        min_yield=request.min_yield,
        area=request.area,
    )

    return {
        "count": len(properties),
        "items": [
            {
                "id": p.id,
                "name": p.name,
                "address": p.address,
                "area": p.area,
                "price": p.price,
                "yield": p.yield_percent,
            }
            for p in properties
        ],
    }


@router.post("/calculate")
async def calculate(request: CalculateCostRequest):
    """
    计算初期费用和收益

    Returns:
        费用和收益明细
    """
    fee = calculate_initial_cost(
        price=request.price,
        deposit_months=request.deposit_months,
        key_money_months=request.key_money_months,
    )

    # 估算���租金
    monthly_rent = int(request.price * 5 / 100 / 12)
    annual_rent = monthly_rent * 12

    return {
        "price": request.price,
        "deposit": fee.deposit,
        "key_money": fee.key_money,
        "management_fee": fee.management_fee,
        "repair_reserve": fee.repair_reserve,
        "fire_insurance": fee.fire_insurance,
        "earthquake_insurance": fee.earthquake_insurance,
        "fixed_asset_tax": fee.fixed_asset_tax,
        "city_planning_tax": fee.city_planning_tax,
        "estimated_monthly_rent": monthly_rent,
        "estimated_annual_rent": annual_rent,
    }


@router.get("/line/{property_id}")
async def property_line(property_id: str):
    """
    获取 LINE 格式的房源信息

    Args:
        property_id: 房源 ID

    Returns:
        LINE 格式化消息
    """
    prop = get_property(property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    return {"text": format_property_for_line(prop)}