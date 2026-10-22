from __future__ import annotations

from fastapi import APIRouter

from api import deps  # noqa: F401
from api.intelligence_common import RunTracker, get_product_or_404

import intelligence_db as idb
from decision_log import log_decision
from providers.recalls import check_recalls

router = APIRouter(tags=["safety"])


@router.get("/products/{product_id}/recalls")
def get_product_recalls(product_id: str) -> dict:
    """On-demand US CPSC recall check for one product (free, no API key).
    Only runs when the UI/user asks for it -- never automatically. Returns
    possible name matches with CPSC links; see providers/recalls.py for the
    grounding rules and what this does not prove."""
    product = get_product_or_404(product_id)
    listing = idb.get_listing_data(product_id)
    brand = dict(listing).get("brand") if listing else None

    with RunTracker(product_id, "recalls", "LIVE"):
        result = check_recalls(product["name"], brand)

    log_decision(
        agent="recall_check", product_name=product["name"], action="recall_search",
        detail={
            "available": result["available"], "provenance": result["provenance"],
            "terms": result["queried_terms"], "matches": len(result["matches"]),
            "error": result.get("error"),
        },
    )
    return {"product_id": product_id, **result}
