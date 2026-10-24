"""Tests for Boston 311 parsing and idempotent ingestion."""

from __future__ import annotations

import pytest
from sqlalchemy import delete, func, select

from app.db.session import async_session_factory
from app.ingestion.parser import ParseError, parse_datetime, parse_record
from app.ingestion.service import IngestionService
from app.models.historical_request import Historical311Request

# A realistic raw record shaped like the Boston 311 CKAN API.
RAW = {
    "case_enquiry_id": "101005839033",
    "open_dt": "2025-01-02 09:50:33.593",
    "closed_dt": "2025-01-02 10:37:03.13",
    "case_status": "Closed",
    "closure_reason": "Case Closed. Resolved",
    "case_title": "Requests for Street Cleaning",
    "subject": "Public Works Department",
    "reason": "Street Cleaning",
    "type": "Requests for Street Cleaning",
    "queue": "PWDx_District 10A: Roxbury",
    "department": "PWDx",
    "neighborhood": "Fenway / Kenmore",
    "location_street_name": "115 Jersey St",
    "location_zipcode": "02215",
    "latitude": "42.3426",
    "longitude": "-71.0971",
    "source": "Citizens Connect App",
}


def test_parse_record_maps_fields() -> None:
    parsed = parse_record(RAW, city_id=1)
    assert parsed["case_enquiry_id"] == "101005839033"
    assert parsed["case_type"] == "Requests for Street Cleaning"
    assert parsed["reason"] == "Street Cleaning"
    assert parsed["department"] == "PWDx"
    assert parsed["neighborhood"] == "Fenway / Kenmore"
    assert abs(parsed["latitude"] - 42.3426) < 1e-6
    assert parsed["opened_at"] is not None
    assert parsed["closed_at"] is not None


def test_parse_record_missing_key_raises() -> None:
    with pytest.raises(ParseError):
        parse_record({"open_dt": "2025-01-01 00:00:00"}, city_id=1)


def test_parse_datetime_formats() -> None:
    assert parse_datetime("2025-01-02 09:50:33.593") is not None
    assert parse_datetime("2025-01-02 09:50:33") is not None
    assert parse_datetime("not a date") is None
    assert parse_datetime(None) is None


def test_parse_record_drops_zero_coordinates() -> None:
    parsed = parse_record({**RAW, "latitude": "0", "longitude": "0"}, city_id=1)
    assert parsed["latitude"] is None
    assert parsed["longitude"] is None


@pytest.fixture
async def clean_historical(boston_city_id: int):
    """Clear historical rows for the test city before/after."""
    async with async_session_factory() as session:
        await session.execute(delete(Historical311Request))
        await session.commit()
    yield boston_city_id
    async with async_session_factory() as session:
        await session.execute(delete(Historical311Request))
        await session.commit()


async def test_ingestion_is_idempotent(clean_historical: int) -> None:
    city_id = clean_historical
    records = [
        {**RAW, "case_enquiry_id": f"case-{i}"} for i in range(5)
    ]

    async with async_session_factory() as session:
        svc = IngestionService(session)
        first = await svc.ingest_records(records, city_id=city_id)

    assert first.fetched == 5
    assert first.inserted == 5
    assert first.updated == 0

    # Re-ingest the same records: should update, not duplicate.
    async with async_session_factory() as session:
        svc = IngestionService(session)
        second = await svc.ingest_records(records, city_id=city_id)

    assert second.inserted == 0
    assert second.updated == 5

    async with async_session_factory() as session:
        total = await session.scalar(select(func.count()).select_from(Historical311Request))
    assert total == 5


async def test_ingestion_skips_invalid(clean_historical: int) -> None:
    city_id = clean_historical
    records = [
        {**RAW, "case_enquiry_id": "valid-1"},
        {"open_dt": "2025-01-01 00:00:00"},  # missing key -> skipped
    ]
    async with async_session_factory() as session:
        svc = IngestionService(session)
        result = await svc.ingest_records(records, city_id=city_id)

    assert result.inserted == 1
    assert result.skipped == 1
