"""Regression coverage for the CSV import unedited-template guard (found
2026-09-24: committing the pricing template unedited silently overwrote
P001's real pricing data because the sample row used a real product_id)."""

from __future__ import annotations

import io

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def _template_csv(data_type: str) -> str:
    resp = client.get(f"/api/data-import/template/{data_type}")
    assert resp.status_code == 200
    return resp.json()["csv_content"]


def test_unedited_template_uses_placeholder_product_id():
    csv_content = _template_csv("pricing")
    assert "YOUR_PRODUCT_ID" in csv_content
    assert "P001" not in csv_content


def test_unedited_template_imports_zero_rows():
    csv_content = _template_csv("pricing")
    files = {"file": ("pricing_data.csv", io.BytesIO(csv_content.encode()), "text/csv")}
    resp = client.post("/api/data-import/pricing/commit", files=files)
    assert resp.status_code == 200
    body = resp.json()
    assert body["imported"] == 0
    assert body["skipped"] == 1
    assert "unknown product_id" in " ".join(body["invalid_rows"][0]["errors"])


def test_sample_values_with_real_product_id_still_rejected():
    """Even if a user only fixes product_id and leaves every other field
    as the template's example, the row must still be rejected -- that's
    the actual protection against a silent data overwrite."""
    products = client.get("/api/products").json()
    real_id = products[0]["product_id"]

    csv_content = _template_csv("pricing").replace("YOUR_PRODUCT_ID", real_id)
    files = {"file": ("pricing_data.csv", io.BytesIO(csv_content.encode()), "text/csv")}
    resp = client.post("/api/data-import/pricing/commit", files=files)
    assert resp.status_code == 200
    body = resp.json()
    assert body["imported"] == 0
    assert body["skipped"] == 1
    assert "unedited template example row" in " ".join(body["invalid_rows"][0]["errors"])
