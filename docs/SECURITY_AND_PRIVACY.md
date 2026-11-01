# CommerceSense AI v3 — Security, Compliance & Privacy Specification

> **Security Document:** `docs/SECURITY_AND_PRIVACY.md`  
> **Status:** Canonical Security & Compliance Policy  
> **Target Version:** CommerceSense AI v3  

---

## 1. Compliance & Zero Amazon Scraping Policy

CommerceSense AI v3 is engineered from first principles to be fully compliant with Amazon's **Developer Agreement**, **Data Protection Policy (DPP)**, and **Acceptable Use Policy (AUP)**.

```
+==================================================================================================+
|                        ZERO AMAZON WEB SCRAPING COMPLIANCE CHARTER                               |
+==================================================================================================+
| 1. CommerceSense AI v3 strictly prohibits the automated scraping of Amazon customer-facing       |
|    web pages (amazon.com, amazon.in, etc.).                                                      |
| 2. The codebase contains ZERO headless browser scrapers, HTML parsers for retail product pages,   |
|    CAPTCHA solving services, residential proxy rotators, or unofficial scraping SDKs.            |
| 3. All Amazon catalog, pricing, sales, and inventory data is acquired strictly through:          |
|    a) The Official Amazon Selling Partner API (SP-API) using registered developer credentials.    |
|    b) Direct seller data imports via standardized CSV files provided by the account owner.        |
| 4. Violations of this policy are treated as critical functional defects and will be rejected.     |
+==================================================================================================+
```

---

## 2. Credential Security & Encryption at Rest

Amazon seller credentials provide access to sensitive commercial data and must be protected with enterprise-grade hygiene.

### 2.1 Encryption Standards
- **Algorithm:** AES-256 in CBC mode with HMAC-SHA256 (via Python `cryptography.fernet.Fernet`).
- **Encrypted Elements:**
  * Amazon SP-API LWA Client Secret (`AMAZON_SP_API_CLIENT_SECRET`)
  * Amazon SP-API Refresh Token (`AMAZON_SP_API_REFRESH_TOKEN`)
  * AWS IAM User Secret Access Key / STS Session Tokens
- **Master Encryption Key (`MASTER_ENCRYPTION_KEY`):**
  * Stored strictly in environment variables or hardware key stores; **never** committed to version control, stored in SQLite/PostgreSQL, or logged to disk.

### 2.2 Credential Masking & Health Exposure Rules
- API endpoints (such as `GET /api/health` and `GET /api/settings`) must **never** return raw secrets, hashed values, or token fragments.
- Only boolean status flags are permitted:
  ```json
  {
    "status": "ok",
    "sp_api_configured": true,
    "lwa_token_valid": true,
    "ollama_connected": true,
    "free_only_mode": true
  }
  ```
- Any PR or commit exposing secret values in error responses or logs is rejected by continuous integration.

---

## 3. Strict FREE_ONLY Network Egress Gate

To ensure zero financial leakage and enforce the Free-First guarantee, the application layer includes a **Network Egress Guardrail (`providers/gate.py`)**.

### 3.1 Egress Interceptor Architecture
All outbound HTTP/HTTPS requests originating from Python (`httpx`, `requests`, `urllib`) pass through an explicit domain validator:

```
                  Outbound HTTP Request
                           |
                           v
          +----------------------------------+
          | Is Destination Domain in         |
          | Approved Allowlist?              |
          +----------------+-----------------+
                           |
            +--------------+--------------+
            | YES                         | NO
            v                             v
  +--------------------+        +-----------------------------------------+
  | Forward Request to |        | RAISE FreeFirstPolicyViolationError     |
  | External Endpoint  |        | Abort call, log blocked domain to trace |
  +--------------------+        +-----------------------------------------+
```

### 3.2 Approved Domain Allowlist
Only the following domain patterns are permitted:
1. `sellingpartnerapi-eu.amazon.com` (Official Amazon SP-API EU Endpoint)
2. `api.amazon.com` (Amazon LWA Token Exchange)
3. `api.gdeltproject.org` (GDELT 2.0 Doc API)
4. `*.google.com` (Public RSS News Feeds only)
5. `localhost` / `127.0.0.1` (Local Ollama, PostgreSQL, Valkey/Redis)

All other external domains—including paid search engines (Tavily, SerpAPI), commercial Amazon APIs (Keepa, Sorftime), and external LLM endpoints (OpenAI, Anthropic, Google AI Studio)—are blocked at runtime when `FREE_ONLY=true`.

---

## 4. Local AI Privacy & Ollama Isolation

When local AI features are utilized (e.g. summarizing review themes or proposing title rewrites), privacy is preserved by strictly containing inference within the local environment:

1. **Local Boundary:** All LLM inference occurs on `http://localhost:11434`. No prompt data ever leaves the seller’s local machine or host server.
2. **Prompt Data Sanitization:**
   - Prompts sent to Ollama are scrubbed of sensitive identifiers:
     * Seller Account IDs and Merchant IDs are stripped.
     * Customer names and personally identifiable information (PII) from customer reviews are sanitized.
     * Financial profit totals are abstracted into relative percentages.
3. **Deterministic Air-Gap:** If the local Ollama instance is shut down, the system continues operating normally using local deterministic rule engines.

---

## 5. Immutable Decision Log & Audit Trail

Trust requires total accountability. Every action taken by the system or confirmed by a human operator is appended to an immutable audit log (`decisions.log.jsonl` and PostgreSQL `audit_events`).

### 5.1 Audit Entry Schema
```json
{
  "timestamp": "2026-10-31T00:50:00.000Z",
  "actor": "operator@seller.com",
  "actor_type": "HUMAN",
  "agent": "pricing_intelligence",
  "product_id": "P001",
  "product_name": "Stainless Steel Garlic Press",
  "action": "price_change_approved",
  "detail": {
    "previous_price": 14.99,
    "approved_price": 16.50,
    "target_margin_price": 13.85,
    "breakeven_price": 9.20,
    "reason": "Aligned with Tier 1 competitor while defending 24% contribution margin"
  },
  "provenance": "SELLER_INPUT"
}
```

### 5.2 Audit Integrity Rules
- The audit log is **append-only**. No `UPDATE` or `DELETE` operations are supported.
- Log write failures do not fail silently; if the audit trace cannot be persisted, the associated operational change is aborted.
- Log entries are sanitized to ensure no authorization tokens or API secrets are written to disk.

