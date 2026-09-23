# sydon-1 — Upgrade prompt (features + UI + 3D/animation), 2026-09-23

Frontend state when this was written (20:35): another agent had set up routing, the page layout
(AppShell/Sidebar/Topbar), 9 navigation pages, shared components, hooks, `lib/api.ts` and `lib/types.ts`,
and a CSS 3D `CubeHero` + `PipelineFlow` on the Landing page. The pages were still placeholders and
`App.tsx` still showed the starter page. This prompt tells the next agent to finish and polish that
work, not start over.

---

```
You are upgrading sydon-1 (Amazon Seller Copilot, CUBE Buildathon practice build). Read CLAUDE.md,
README.md and AUDIT_2026-09-23.md first; every standing rule in CLAUDE.md applies and wins over this prompt.
Only Tavily + Gemini at runtime, no new API keys, all tracing through agent/decision_log.py,
Agent 6 runs only on a human click, LIVE vs SYNTHETIC visually distinct everywhere, never claim
something works without running it.

COORDINATION: another agent may be building frontend/src (pages were 10-line stubs at 20:35 on
2026-09-23). Before editing any file, check git status + mtimes; if a file changed in the last ~15 min,
stop and ask me. Build ON the existing structure (components/ui, components/shared, components/cube,
hooks/, lib/api.ts, lib/types.ts, index.css tokens), don't replace it. Never run POST /api/signals/run
or live Gemini/Tavily calls without asking me first.

PHASE 0 — Foundation (do first, verify before moving on)
- Apply the fixes in AUDIT_2026-09-23.md, priority items 1–5 (grounding substring check, search-error
  findings, API validation/error codes, tsconfig TS5101, remove Vite template).
- Wire main.tsx: QueryClientProvider + BrowserRouter + routes for Landing and all 9 pages; delete
  App.css/App.tsx template, hero/react/vite assets; set <title> and favicon.
- Every page gets real data, loading skeleton, empty state, error state (ApiError.detail). Zero dead buttons:
  every clickable element calls a real endpoint or navigates somewhere real.

PHASE 1 — New features (backend additive under api/, logic stays in agent/ signals/ eval/)
1. "This Week's Attention Brief" (the product's one-sentence outcome): a ranked list of products that need
   action, each with the signal, plain-English WHY, and an estimated $ at risk computed deterministically:
   stockout = avg daily units × base_price × projected days out; PPC waste = ad_spend − ad_sales/target ROAS;
   rank drop = units-lost trend × price. New GET /api/brief. Mark it SYNTHETIC.
2. Live pipeline streaming: GET /api/intelligence/stream (SSE) emitting stage events (queries planned,
   each search, findings count, insight generated, each guardrail strip/downgrade) sourced from the same
   log_decision calls, not a second mechanism. The UI shows them as a live timeline.
3. Signal → Research bridge: on a signal or product page, a "Research this live" button (human click,
   confirm dialog showing it will call paid APIs) that runs the intelligence pipeline for that product.
4. Evidence viewer: for each insight show the cited snippet highlighted inside its original finding,
   with source URL, retrieved_at, and a "grounded ✓ / stripped ✗" badge. Show the price-disagreement
   downgrade reason when it fired.
5. Decision Center: queue of pending insights + signals; Approve / Reject (reason required) /
   Request more research / Snooze 7 days; per-product decision history; all via POST /api/decisions.
6. What-if simulator (deterministic, SYNTHETIC): reorder quantity + lead-time sliders → projected days
   of stock and stockout date chart; ad budget slider → projected waste.
7. Evaluation 2.0: confusion matrix, per-detector precision/recall, grounding rate across all past runs
   (parsed from the decision log), and a "re-run eval" button.
8. Command palette (cmdk is already installed): Ctrl/Cmd+K to jump to any product, signal, page or action.
9. Export: download the weekly brief as Markdown (and print-friendly CSS for PDF).
10. Settings: show key status (booleans only, from /api/health), cache TTL, demo mode toggle, reduce-motion toggle.

PHASE 2 — Visual upgrade, 3D and motion
- 3D hero: upgrade components/cube/CubeHero.tsx to react-three-fiber (add three, @react-three/fiber,
  @react-three/drei). Glassy bevelled cube, soft bloom/rim light, slow idle spin, drag-to-rotate,
  faces = RESEARCH / INSIGHT / SIGNAL / EVIDENCE / DECISION / CUBE; clicking a face navigates to that
  section. Lazy-load it (React.lazy + Suspense), keep the existing CSS cube as fallback when WebGL is
  unavailable or prefers-reduced-motion is set. Fix the current hover-resume jump (resume from the
  current angle, not the initial one).
- Animated pipeline: PipelineFlow nodes light up and a particle travels between them as SSE stage
  events arrive during a live run; idle state shows a subtle pulse.
- 3D risk map on Overview (optional, lazy): 14 products as a grid of bars, height = $ at risk,
  colour = severity, hover tooltip, click → product detail. Must have a 2D table equivalent.
- Motion system with framer-motion: AnimatePresence page transitions, staggered list/card entrance,
  KPI count-up, layout animations when filtering/sorting tables, chart draw-in, gentle pulse on
  high-severity badges, 3D tilt-on-hover for KPI and insight cards, card flip for evidence (summary ↔ source).
  Put durations/easings in one motion tokens file; honour prefers-reduced-motion everywhere.
- Visual polish: keep the index.css token palette (dark-first); add a subtle animated grid/noise
  background, glass panels, consistent 8px spacing, a clear type scale, focus rings, mobile layout
  (sidebar becomes a sheet on small screens — components/ui/sheet.tsx exists).
- LIVE / CACHED / SYNTHETIC / DEMO badges (tokens already exist in index.css) on every data surface,
  plus a global legend in the Topbar.
- Check the "·" and "—" characters in Landing.tsx / Sidebar.tsx render correctly (no mojibake).

GUARDRAILS
- Performance: 3D chunk code-split; main bundle stays under ~300 KB gzipped; 60fps on a mid laptop;
  pause the 3D render loop when the tab is hidden or the canvas is offscreen.
- Accessibility: every animation respects reduced motion; 3D elements have keyboard and 2D equivalents;
  WCAG AA contrast.
- No new backend secrets, no new LLM providers, no second logging mechanism.

VERIFY (show real output, don't summarise away failures)
- py_compile + FastAPI TestClient tests for every new endpoint (incl. 422/404/503 cases); offline
  grounding test with a fake bundle.
- npm run build and npx oxlint both clean; report bundle sizes.
- Run backend (uvicorn api.main:app --port 8000) + frontend (npm run dev), click every page and every
  button, and list anything that still does nothing. Test with reduced motion on and WebGL disabled.
- Update CLAUDE.md phase status at the end; propose (don't make) commits grouped by phase.
```
