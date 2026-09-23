"""
data_import.py — CSV import for the four intelligence modules. No Amazon
API required: this is the primary way a seller (or a judge) gets real
data into the four modules without any external credentials. Never
silently discards a bad row — every row that fails validation is reported
with its specific error, not dropped quietly.
"""

from __future__ import annotations

import csv
import io
from datetime import date

from fastapi import APIRouter, HTTPException, UploadFile

from api import deps  # noqa: F401

import db
import intelligence_db as idb

router = APIRouter(tags=["data-import"])

_TEMPLATES = {
    "listing": {
        "columns": ["product_id", "title", "brand", "product_type", "bullets", "description", "image_count"],
        "sample_row": ["P001", "Example Product Title", "AcmeBrand", "Kitchen",
                        "Bullet one|Bullet two|Bullet three", "A short product description.", "5"],
    },
    "pricing": {
        "columns": ["product_id", "cogs", "referral_fee_pct", "fulfillment_fee", "other_cost", "target_margin_pct"],
        "sample_row": ["P001", "5.81", "0.15", "3.09", "0.45", "0.30"],
    },
    "reviews": {
        "columns": ["product_id", "rating", "review_text", "review_date"],
        "sample_row": ["P001", "4", "Works great, very durable.", "2026-08-01"],
    },
    "inventory": {
        "columns": ["product_id", "lead_time_days", "safety_days", "moq", "reorder_multiple"],
        "sample_row": ["P001", "14", "5", "50", "25"],
    },
}


def _known_product_ids() -> set[str]:
    return {p["product_id"] for p in db.get_products()}


@router.get("/data-import/template/{data_type}")
def download_template(data_type: str) -> dict:
    if data_type not in _TEMPLATES:
        raise HTTPException(status_code=404, detail=f"Unknown data type: {data_type}")
    spec = _TEMPLATES[data_type]
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(spec["columns"])
    writer.writerow(spec["sample_row"])
    return {"data_type": data_type, "filename": f"{data_type}_data.csv", "csv_content": buf.getvalue()}


def _validate_rows(data_type: str, rows: list[dict]) -> dict:
    spec = _TEMPLATES[data_type]
    known_ids = _known_product_ids()
    valid, invalid = [], []
    seen_single_row_types: set[str] = set()

    for i, row in enumerate(rows, start=2):  # header is row 1
        errors = []
        missing = [c for c in spec["columns"] if not (row.get(c) or "").strip()]
        if missing:
            errors.append(f"missing field(s): {', '.join(missing)}")

        pid = (row.get("product_id") or "").strip()
        if pid and pid not in known_ids:
            errors.append(f"unknown product_id: {pid}")
        if data_type != "reviews" and pid:
            if pid in seen_single_row_types:
                errors.append(f"duplicate product_id: {pid}")
            seen_single_row_types.add(pid)

        if data_type == "pricing":
            for f in ("cogs", "referral_fee_pct", "fulfillment_fee", "other_cost", "target_margin_pct"):
                try:
                    float(row.get(f, ""))
                except ValueError:
                    errors.append(f"{f} must be a number")
        if data_type == "reviews":
            try:
                r = int(row.get("rating", ""))
                if not (1 <= r <= 5):
                    errors.append("rating must be 1-5")
            except ValueError:
                errors.append("rating must be an integer 1-5")
            try:
                date.fromisoformat(row.get("review_date", ""))
            except ValueError:
                errors.append("review_date must be YYYY-MM-DD")
        if data_type == "inventory":
            for f in ("lead_time_days", "safety_days"):
                try:
                    int(row.get(f, ""))
                except ValueError:
                    errors.append(f"{f} must be an integer")
        if data_type == "listing":
            try:
                int(row.get("image_count", ""))
            except ValueError:
                errors.append("image_count must be an integer")

        if errors:
            invalid.append({"row": i, "data": row, "errors": errors})
        else:
            valid.append(row)

    return {
        "valid_rows": valid, "invalid_rows": invalid,
        "valid_count": len(valid), "invalid_count": len(invalid), "total_rows": len(rows),
    }


async def _read_csv_rows(data_type: str, file: UploadFile) -> list[dict]:
    if data_type not in _TEMPLATES:
        raise HTTPException(status_code=404, detail=f"Unknown data type: {data_type}")
    raw = await file.read()
    content = raw.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content))
    missing_cols = [c for c in _TEMPLATES[data_type]["columns"] if c not in (reader.fieldnames or [])]
    if missing_cols:
        raise HTTPException(status_code=422, detail=f"CSV is missing required column(s): {', '.join(missing_cols)}")
    return list(reader)


@router.post("/data-import/{data_type}/validate")
async def validate_csv(data_type: str, file: UploadFile) -> dict:
    rows = await _read_csv_rows(data_type, file)
    return {"data_type": data_type, **_validate_rows(data_type, rows)}


@router.post("/data-import/{data_type}/commit")
async def commit_csv(data_type: str, file: UploadFile) -> dict:
    rows = await _read_csv_rows(data_type, file)
    result = _validate_rows(data_type, rows)

    imported = 0
    for row in result["valid_rows"]:
        pid = row["product_id"].strip()
        if data_type == "listing":
            bullets = [b.strip() for b in row["bullets"].split("|") if b.strip()]
            idb.upsert_listing_data(
                pid, row["title"], row["brand"], row["product_type"], bullets,
                row["description"], None, {}, [], int(row["image_count"]), "ACTIVE",
            )
        elif data_type == "pricing":
            idb.upsert_pricing_data(
                pid, float(row["cogs"]), float(row["referral_fee_pct"]),
                float(row["fulfillment_fee"]), float(row["other_cost"]), float(row["target_margin_pct"]),
            )
        elif data_type == "reviews":
            idb.insert_review_item(pid, int(row["rating"]), row["review_text"], row["review_date"], True, "csv")
        elif data_type == "inventory":
            idb.upsert_inventory_config(
                pid, int(row["lead_time_days"]), int(row["safety_days"]),
                int(row["moq"]) if (row.get("moq") or "").strip() else None,
                int(row["reorder_multiple"]) if (row.get("reorder_multiple") or "").strip() else None,
            )
        imported += 1

    return {"data_type": data_type, "imported": imported, "skipped": result["invalid_count"], "invalid_rows": result["invalid_rows"]}
