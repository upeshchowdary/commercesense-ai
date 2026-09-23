"""
insight_agent.py  Agent 6: Insight Agent (LIVE, reasoning-only)

Takes the ResearchBundle Agent 5 produced (Phase 1) and turns it into a
structured InsightReport across four fixed categories: pricing, trend,
risk, opportunity. It has no tools of its own  it only reads what
Agent 5 already found.

THE ONE RULE THIS FILE EXISTS TO ENFORCE:
Every insight with a summary must be traceable to a specific finding
in the bundle. If nothing supports a category, the honest output is
confidence="none" / summary=None  not a plausible-sounding guess.
A clean JSON shape is not evidence. Gemini's structured output
(response_schema) guarantees the JSON is syntactically well-formed and
type-correct; it does NOT guarantee the CONTENT is true. Those are two
different problems, and only the second one is what actually matters
here.

Enforcement is two layers, not one:
  1. response_schema + response_mime_type force the model into valid,
     correctly-typed JSON matching the Insight shape. This eliminates
     the "malformed JSON" failure mode almost entirely.
  2. _apply_grounding_guardrail() checks the model's own CONTENT
     afterward and strips any insight that claims confidence without
     a citation  because a schema constrains shape, not honesty.

This agent does NOT use tool calling / automatic function calling 
it's a single structured-output call, the same reliable mechanism
Phase 1's research agent was redesigned around after Gemini's
automatic function calling proved unreliable there. No AFC advisory
warning should print for this file; if one does, that's worth
flagging, since it would mean something unexpected is configured.

Like the research agent, a transient API failure gets one retry before
falling back to an honest, fully-null report  never a crash, never a
silent guess.
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the project root (one level up from agent/) so that
# `python orchestrator.py` works without pre-exporting vars in the shell.
load_dotenv(Path(__file__).parent.parent / ".env")

from google import genai
from google.genai import types

from schema import Insight, InsightReport, ResearchBundle
from decision_log import log_decision

MODEL = os.environ.get("INSIGHT_AGENT_MODEL", "gemini-2.5-flash")
CATEGORIES = ("pricing", "trend", "risk", "opportunity")

SYSTEM_PROMPT = """You are an insight-extraction agent. You are given a \
bundle of RAW search findings about one product: snippets of text \
with their source URLs. You have no tools. Your only job is to read \
the findings and produce exactly one insight for each of these four \
categories: pricing, trend, risk, opportunity.

STRICT GROUNDING RULE  the most important rule you follow:
- Every insight with a summary MUST include the exact source_snippet \
  text (copied verbatim from the findings) that supports it, plus its \
  source_url.
- If nothing in the findings supports a category, you MUST return \
  that category with summary=null, confidence="none", \
  source_snippet=null, source_url=null. Do NOT invent a \
  plausible-sounding summary to fill the field. A well-formatted \
  guess is worse than an honest "no data found"  it will mislead \
  the seller into a decision based on nothing.
- If findings disagree (for example, multiple different prices from \
  different sources), do NOT silently pick one as if it were settled \
  fact. Either reflect the range/disagreement in the summary with \
  confidence="low" or "medium", or return confidence="none" if the \
  disagreement is too wide to be useful. Never present a single \
  cherry-picked number as if all sources agreed when they didn't.
- Never state a specific number (price, percentage, date) unless that \
  exact number appears verbatim in a finding's snippet.

Return exactly four insight objects, one per category, in the order:
pricing, trend, risk, opportunity.
"""


def _build_user_message(bundle: ResearchBundle) -> str:
    if not bundle.findings:
        return (
            f"Product: {bundle.product_name}\n\n"
            "No findings were gathered. Return all four categories with "
            'summary=null, confidence="none".'
        )

    lines = [f"Product: {bundle.product_name}\n\nFindings:"]
    for i, f in enumerate(bundle.findings, 1):
        lines.append(
            f"[{i}] source: {f.source_url}\n    query: {f.query}\n    text: {f.snippet}"
        )
    return "\n\n".join(lines)


def _fill_missing_categories(insights: list[Insight]) -> list[Insight]:
    """The schema guarantees each returned object is shaped correctly;
    it does not guarantee all 4 categories were returned exactly once.
    Never assume completeness  check it, and de-duplicate defensively."""
    by_category: dict[str, Insight] = {}
    for insight in insights:
        by_category.setdefault(insight.category, insight)  # keep first occurrence

    for cat in CATEGORIES:
        if cat not in by_category:
            by_category[cat] = Insight(category=cat, summary=None, confidence="none")

    return [by_category[cat] for cat in CATEGORIES]


def _apply_grounding_guardrail(insights: list[Insight]) -> list[Insight]:
    """Second line of defense on top of the schema: if the model
    claims a confident summary but attached no source_snippet, strip
    it back to null rather than trust the model's self-report. A
    schema guarantees shape, never honesty."""
    for insight in insights:
        if insight.is_fabricated_risk():
            insight.summary = None
            insight.confidence = "none"
            insight.source_snippet = None
            insight.source_url = None
    return insights


def _norm(s: str) -> str:
    return " ".join(s.split()).lower()


def _apply_source_match_guardrail(
    insights: list[Insight], bundle: ResearchBundle
) -> list[Insight]:
    """Rule 4 is "must cite a source_snippet that actually appears in
    Agent 5's findings"  not just "has a non-empty source_snippet".
    The grounding guardrail above only checks the latter, which lets a
    fluent, well-formatted but INVENTED quote pass as grounded. This
    checks the former: the cited snippet must be a literal (whitespace
    normalized, case-insensitive) substring of some finding's snippet,
    and the source_url is then trusted from that finding  not
    whatever the model claimed  since a matching snippet with a
    mismatched URL is itself suspicious."""
    corpus = [(_norm(f.snippet), f.source_url) for f in bundle.findings if f.snippet]
    for insight in insights:
        if insight.confidence == "none" or not insight.source_snippet:
            continue
        needle = _norm(insight.source_snippet)
        match_url = next((url for text, url in corpus if needle and needle in text), None)
        if match_url is None:
            log_decision(
                agent="insight_agent",
                product_name=bundle.product_name,
                action="grounding_strip",
                detail={
                    "category": insight.category,
                    "reason": "source_snippet not found verbatim in any finding",
                    "claimed_snippet": insight.source_snippet[:200],
                },
            )
            insight.summary = None
            insight.confidence = "none"
            insight.source_snippet = None
            insight.source_url = None
        else:
            insight.source_url = match_url
    return insights


_PRICE_PATTERN = re.compile(r"\$\s?\d{1,4}(?:\.\d{2})?")


def _find_distinct_prices(bundle: ResearchBundle) -> set[str]:
    """Extract distinct dollar-amount mentions across all findings  a
    cheap, deterministic signal for whether the source data actually
    disagrees on price. NOT a source of truth for what the price is;
    it exists only to catch the model being overconfident when the
    underlying evidence is visibly inconsistent.

    Verified against real output: the prompt instruction telling the
    model not to cherry-pick a single price did NOT reliably work on
    its own (Bose QuietComfort Ultra test  the model confidently
    synthesized $449 + $269 as "high" confidence while the bundle
    actually contained 4+ distinct price points from independent
    sources). Same lesson as the grounding guardrail: never trust a
    prompt instruction alone when a cheap code-level check can verify
    it instead."""
    prices: set[str] = set()
    for f in bundle.findings:
        for match in _PRICE_PATTERN.findall(f.snippet):
            prices.add(match.replace(" ", ""))
    return prices


def _apply_price_disagreement_guardrail(
    insights: list[Insight], bundle: ResearchBundle
) -> list[Insight]:
    """If the pricing insight claims "high" confidence but the source
    findings actually contain 3+ distinct price mentions, downgrade to
    "medium" rather than let a single confident-sounding synthesis
    stand unquestioned. Logged explicitly so the downgrade is visible,
    never silent."""
    distinct_prices = _find_distinct_prices(bundle)
    pricing_insight = next(
        (i for i in insights if i.category == "pricing"), None
    )
    if (
        pricing_insight is not None
        and pricing_insight.confidence == "high"
        and len(distinct_prices) >= 3
    ):
        pricing_insight.confidence = "medium"
        log_decision(
            agent="insight_agent",
            product_name=bundle.product_name,
            action="price_disagreement_downgrade",
            detail={
                "reason": (
                    "3+ distinct price mentions found across findings; "
                    "downgraded high confidence to medium rather than "
                    "trust a single high-confidence synthesis"
                ),
                "distinct_prices_found": sorted(distinct_prices),
            },
        )
    return insights


def _call_gemini_for_insights(
    client: genai.Client, bundle: ResearchBundle
) -> list[Insight]:
    """One structured-output call. Raises on any failure  the caller
    handles retry/fallback, this function never guesses."""
    response = client.models.generate_content(
        model=MODEL,
        contents=_build_user_message(bundle),
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=list[Insight],
            max_output_tokens=2048,
            # See the matching comment in research_agent.py's _plan_queries:
            # the SDK defaults to its AFC code path on every call unless
            # this is set, regardless of whether tools are passed. Without
            # it, this file's own "No AFC advisory warning should print"
            # claim above was false in practice (verified: the warning did
            # print). Disabling it explicitly makes that claim actually true.
            automatic_function_calling=types.AutomaticFunctionCallingConfig(
                disable=True
            ),
        ),
    )
    insights_raw = response.parsed
    if not insights_raw:
        raise ValueError("Gemini returned no parsed output (possibly truncated)")
    # Defensive: coerce whatever came back into real Insight instances,
    # whether the SDK handed back model instances or dicts.
    return [
        item if isinstance(item, Insight) else Insight.model_validate(item)
        for item in insights_raw
    ]


def run_insight_agent(bundle: ResearchBundle) -> InsightReport:
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    insights: list[Insight] | None = None
    last_error: Exception | None = None

    for attempt in range(2):  # one try, one retry  same pattern as the research agent
        try:
            insights = _call_gemini_for_insights(client, bundle)
            break
        except Exception as exc:  # noqa: BLE001  fail loud and safe, never guess
            last_error = exc
            log_decision(
                agent="insight_agent",
                product_name=bundle.product_name,
                action="insight_attempt_failed",
                detail={"attempt": attempt + 1, "reason": str(exc)},
            )

    if insights is None:
        # Both attempts failed  fall back to an honest, fully-null
        # report rather than crash or guess.
        log_decision(
            agent="insight_agent",
            product_name=bundle.product_name,
            action="insight_generation_failed_fallback",
            detail={"reason": str(last_error)},
        )
        insights = [
            Insight(category=c, summary=None, confidence="none") for c in CATEGORIES
        ]

    insights = _fill_missing_categories(insights)
    insights = _apply_grounding_guardrail(insights)
    insights = _apply_source_match_guardrail(insights, bundle)
    insights = _apply_price_disagreement_guardrail(insights, bundle)

    grounded = sum(1 for i in insights if i.confidence != "none")
    report = InsightReport(
        product_name=bundle.product_name,
        insights=insights,
        generated_at=datetime.now(timezone.utc).isoformat(),
        grounded_count=grounded,
        ungrounded_count=len(insights) - grounded,
    )

    log_decision(
        agent="insight_agent",
        product_name=bundle.product_name,
        action="insight_generated",
        detail={
            "grounded_count": report.grounded_count,
            "ungrounded_count": report.ungrounded_count,
        },
    )

    return report


if __name__ == "__main__":
    import json
    import sys

    from research_agent import run_research_agent

    product = " ".join(sys.argv[1:]) or "Anker PowerCore 10000 portable charger"
    bundle = run_research_agent(product)
    report = run_insight_agent(bundle)
    print(json.dumps(report.model_dump(), indent=2))
