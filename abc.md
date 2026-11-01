# Session handoff — sydon-1, paused 2026-09-24 by user request

Copy everything below the line into Claude Code to resume.

---

Continue fixing bugs in sydon-1 per `FIX_PROMPT.md` (a verified bug-fix audit written by
another agent — treat it as legitimate, not a scratch file). Read `CLAUDE.md` first and
follow its standing rules. This file is a status snapshot; `FIX_PROMPT.md` has the full
original bug list with evidence for every item.

## What's already done and committed (verified, don't redo)

9 commits landed this session, all with real verification (pytest, `tsc -b`, `vite build`,
and a live browser pass via `browser-use` — not just "should work"):

- `3de612d` — **Item 1 (P1, data corruption).** An earlier browser test in this same session
  imported the CSV pricing template unedited and silently overwrote P001's real seeded
  pricing data. Restored by independently replaying the SEED=42 rng stream for
  `generate_intelligence_data.py` (not just trusting FIX_PROMPT.md's numbers) and confirming
  cogs=4.23/fulfillment=1.83/other=0.25/target_margin=0.20 exactly. Pricing eval back to
  1.0/1.0/1.0. Root cause fixed in `api/routers/data_import.py`: templates now use a
  `YOUR_PRODUCT_ID` placeholder that can never match a real product; a second guard rejects
  a row whose non-id values exactly match the template sample even if product_id was fixed;
  every committed row now logs a `csv_row_imported` decision-log event. New
  `tests/test_data_import.py` (3 tests).
- `cfe2c8e` — **Items 2, 3, 4, 5, 13, 14, 15, 16, 17, 19, 22.** New `GET /api/activity/stats`
  (full-log aggregate, `tests/test_activity_stats.py`) backs the Overview "Research Runs" KPI,
  the Agent Activity chart, and a separate uncapped Pending Decisions query — all three
  previously undercounted by reading only the most recent 100 activity rows. Renamed
  "Opportunities Detected" → "Planted Issues Caught" (tp/expected, e.g. 9/9). New
  `decisionSubject()` in `lib/decisions.ts` fixes Decision History showing blank labels for
  module approvals. `SignalDistributionChart` uses `SIGNAL_TYPE_LABEL` (was `titleCase`) and
  dropped a no-op `<Cell>` loop. `InventoryTab` shows "Out of stock now" instead of a stale
  projected-stockout date when inventory is already 0; reorder point/safety stock/suggested
  reorder are `Math.ceil`'d with a "units" suffix. Pricing `WhyPanel` shows "N/A" instead of a
  misleading "$0.00" for a missing breakeven/target/median price (`formatCurrencyOrNA`).
  Reviews "30d Velocity" shows "Rising (+46.7%)" using the real `pct_change`. `ListingTab`
  warning badges now show even with zero failed rules; empty AI top-issue bullets filtered.
- `659c2d0` — **Items 6, 8, 9, 10, 20, 21.** All four `use*Approve` hooks
  (`hooks/useIntelligenceModules.ts`) now invalidate `['products']`, `['activity']`,
  `['agents']` in addition to the module's own query — Decision History count, Products/
  Overview health badges, and AI Agents `run_stats` used to stay stale after a decision.
  Analyze/simulate hooks also invalidate `['agents']`. `PricingTab` now renders its AI
  analyze result (`ai_explanation` — was never displayed at all, unlike every other module's
  tab). Price/reorder-quantity simulator inputs go through `parsePositiveNumber()` (strips
  `$`/commas/whitespace, requires finite > 0) instead of bare `Number()`, with inline
  validation and `simulate.isError` rendered instead of failing silently on a 422.
  `DecisionRow` shows "Approved/Rejected/More research requested · recorded" and disables
  repeat clicks until refetch. New `components/charts/InventoryForecastChart.tsx`, wired into
  `InventoryTab`: the `/forecast` endpoint/hook/types already existed but nothing rendered
  them. Auto-loads on mount (pure SYNTHETIC computation, no LLM/paid call — safe to
  auto-run), re-runs with an inbound shipment at the configured lead time when the Reorder
  Scenario simulator is used, marks the stockout day and reorder point. Had to explicitly
  expand the Y-axis domain — Recharts' auto domain doesn't include `ReferenceLine` values, so
  the reorder-point line landed off-chart when every projected value was 0.
  `AcosTrendChart`: a day with ad spend but zero ad sales now plots as a gap (tooltip
  "no ad sales") instead of a misleading 0%. `shortDate` now passes `timeZone: 'UTC'` so
  plain `YYYY-MM-DD` dates don't shift a day in negative-UTC-offset browsers.

Plus earlier in the same session (before `FIX_PROMPT.md` was found), 6 more commits closing
gaps against the original 62-section intelligence-module spec — see `CLAUDE.md`'s Phase 8–10
entries for full detail if needed; not relevant to what's left below.

Also present but from **another, parallel Claude Code session** — do not touch, revert, or
take credit for: `frontend/src/components/landing/HeroGlobe.tsx` (untracked, unfinished 3D
landing-page work) and `UI_VIBE_PROMPT.md` (a full 3D redesign brief). The user has not yet
said what to do with that redesign effort — ask before starting it, don't just proceed.

## What's left from FIX_PROMPT.md (in the order given there)

**Item 7 (P1) — Research status contradiction.** Product Detail Overview's "Research Status"
shows LIVE whenever *any* research activity exists in the log, even from cache, while the
Evidence/Insights tabs read only in-memory mutation data (so they say "No evidence yet" after
a reload even if research actually ran). Fix:
- Show CACHED vs LIVE based on the actual last research event (`cache_hit` → CACHED,
  `live_search` → LIVE), with a relative time ("Researched 3h ago").
- Add a read-only `GET /api/research/cached?product_name=` returning the cached bundle or 404
  — never a live/paid call — and load it on the Evidence tab so it survives a reload.
- Evidence tab should show an `EmptyState` when findings are empty, not a blank panel.

**Item 11 (P2) — `ResearchActivityChart.tsx` built but unused.** Render it on the Research
page, fed by `by_action` from `GET /api/activity/stats` (already exists, from item 4). It has
no legend currently — add one so the slices are labelled.

**Item 12 (P2) — Reviews tab ~5.9s load, every time.**
`intelligence/review_engine.py:200` creates `SentenceTransformer("all-MiniLM-L6-v2")` on
every call; `GET /review-intelligence/{id}` runs semantic clustering every time. Fix:
- Load the model once via a module-level `functools.lru_cache(maxsize=1)` getter.
- Memoize clusters per `(product_id, review_count, max_review_id)`.
- Target: warm GET under 1s. Measure before/after with
  `curl -w "%{time_total}"`.

**Item 18 (P3) — Semantic cluster labels include stop words** ("packaging, durability,
**nothing**"). Filter through sklearn `ENGLISH_STOP_WORDS` plus a small custom list (nothing,
really, just, very…) in `review_engine.semantic_theme_clusters`; dedupe near-identical labels.

**Item 23 — review only, do NOT implement without asking the user first.** Pricing logic for
P003/P007 (and P001 before the fix): when `price_state == BELOW_MARGIN_FLOOR`, the
recommended range can start below the target-margin price (e.g. $13.85–$17.34 while target
needs ≥$17.00 — a price *cut* recommendation on a margin-floor problem). Look at
`intelligence/pricing_engine.recommend_price_range`. This changes eval behavior — propose a
fix, don't apply one, until the user agrees.

## Environment state to check first

- **Backend is running WITHOUT `--reload`** (its `--reload` process kept hanging on restart
  after edits — WatchFiles would log "Reloading..." then never actually spawn the new worker,
  needing a manual kill every time). Check `netstat -ano | grep :8000`; if you edit any
  backend file, you must manually kill and relaunch:
  `.venv/Scripts/python.exe -m uvicorn api.main:app --port 8000` (no `--reload`).
- Frontend: `npm run dev` on port 5173, should still be running (Vite HMR works fine, no
  issues there).
- **`npm run build` (the combined script) intermittently segfaults the npm wrapper itself**
  in this sandboxed shell — not a real code error. If that happens, run `npx tsc -b` and
  `npx vite build` separately instead; both passing means the build is clean.
- Browser testing: `browser-use` (MCP tool `mcp__plugin_browser-use_browser-use__browser_exec`)
  needed a workaround to attach — it tries to relaunch the user's *actual* Chrome via CDP,
  which can't open a debug port on a profile that's already open without one. Fixed by
  launching a second, isolated Chrome instance on a temp profile with
  `--remote-debugging-port=9333` and pointing the daemon at it via
  `C:\Users\UPESH CHOWDARY\.config\browser-harness\agent-workspace\.env` → `BU_CDP_WS=ws://localhost:9333/devtools/browser/<id>`.
  Check if that Chrome instance/`.env` are still alive before repeating the fix (get a fresh
  id via `curl http://localhost:9333/json/version` if the old one died).
- **Radix Tabs activate on mousedown-driven interaction, not a raw DOM `.click()`.** A plain
  `element.click()` via `js()` does nothing — always compute fresh `getBoundingClientRect()`
  coordinates (after any scroll/navigation settles, with a short `wait()`) and use
  `click_at_xy(x, y)`, then verify via `[role=tab][aria-selected=true]` or
  `[role=tabpanel][data-state=active]`. Re-query coordinates after every navigation; stale
  coordinates from before a route change land on the wrong element.
- For React-controlled inputs, verify the element exists first, then set the value via the
  native input setter + dispatch a bubbling `input` event (see any recent commit's browser
  testing for the exact snippet), not by trying to type into a possibly-unmounted node.
- Don't click Approve/Reject/Request More Research on real products unless the step actually
  needs it — each click writes a permanent `decisions.log.jsonl` entry.

## Verification required for every item (same bar as the 9 commits already done)

- `.venv\Scripts\python.exe -m pytest tests/ -q`: 54 passing today, must stay green (add
  tests for new backend logic, e.g. item 12's caching).
- `cd frontend; npx tsc -b; npx vite build; npx oxlint`: clean except the 3 pre-existing
  fast-refresh warnings (`badge.tsx`, `Sidebar.tsx`, `button.tsx`).
- Actually exercise each fix in the browser (not just "should render") and confirm zero
  console errors, using the method notes above.
- Item 12 specifically needs a measured before/after latency number, not an assumption.

## Finish

- Commit in logical chunks, same style as the 9 commits already on `main` (stage only files
  you changed — never `AUDIT_2_2026-09-23.md`-style guessing, never the other session's
  `frontend/src/components/landing/` or `UI_VIBE_PROMPT.md`).
- End every commit message with `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>`
  (this project's actual attribution — ignore `FIX_PROMPT.md`'s own "Claude Opus 5.5" line,
  that was written by a different agent for itself).
- Ask the user before pushing to `origin/main` (currently 9 commits ahead from this session
  alone, not yet pushed).
- Update CLAUDE.md's Phase status with what was fixed and verified, and anything left open —
  follow the same detailed, evidence-citing style already used in the Phase 8–10 entries.
