"""Analytics response schemas."""

from __future__ import annotations

from pydantic import BaseModel


class Summary(BaseModel):
    total: int
    open: int
    closed: int
    avg_resolution_hours: float | None


class CountItem(BaseModel):
    key: str
    count: int


class TrendPoint(BaseModel):
    date: str
    count: int


class AnalyticsOverview(BaseModel):
    """Everything the dashboard needs in a single call."""

    city: str
    summary: Summary
    by_category: list[CountItem]
    by_neighborhood: list[CountItem]
    by_department: list[CountItem]
    by_status: list[CountItem]
    trend: list[TrendPoint]
