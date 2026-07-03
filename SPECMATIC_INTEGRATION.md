# Specmatic Integration — Contract-Driven Testing for Monday.com BI Agent

## Overview

This document describes the Specmatic contract testing integration for the Monday.com BI Agent FastAPI application. The integration demonstrates how contract-driven development catches real bugs before they reach production.

---

## 1. What Is Contract Testing?

Contract testing validates that an API implementation matches its published contract (OpenAPI spec). Instead of testing the happy path manually, Specmatic:

1. **Reads your OpenAPI spec** as the single source of truth
2. **Generates test scenarios** from the spec examples and edge cases
3. **Runs them against the live app** over HTTP
4. **Fails fast** when the app violates the contract (e.g., wrong HTTP status code)

This catches bugs that unit tests miss — especially REST semantics bugs like:
- ✅ Returning 200 OK when you should return 503 Service Unavailable
- ✅ Accepting a required field in the request but never using it
- ✅ Missing fields in response bodies

---

## 2. Two Real Bugs Found in `main.py`

### Bug A: Error Responses Return HTTP 200 Instead of Error Codes

**Location:** `handle_query()` function (lines ~209, ~215, ~223, ~230, ~255, ~268)

**Problem:**
Every error path in the query handler returned `JSONResponse({...error: true})` without setting `status_code`:

```python
# BEFORE (BUG)
if not GROQ_API_KEY:
    return JSONResponse({
        "answer": "⚠️ GROQ_API_KEY not set in environment variables",
        "trace": trace,
        "error": True
    })  # ← No status_code! Defaults to 200 OK
```

**Why This Is Bad:**
- Any HTTP client that checks status codes (curl, httpx, Postman, Specmatic) will treat a failed Monday.com fetch as a successful response
- Frontend applications won't know to display an error state
- Monitoring dashboards won't alert on failures
- REST API contract is violated: errors should use 4xx/5xx status codes

**Fix Applied:**
```python
# AFTER (FIXED)
if not GROQ_API_KEY:
    return JSONResponse({
        "answer": "⚠️ GROQ_API_KEY not set in environment variables",
        "trace": trace,
        "error": True
    }, status_code=503)  # ← Service Unavailable (config error)
```

**Status Codes Used:**
- **503 Service Unavailable** — Groq/Monday.com not configured or client initialization failed
- **502 Bad Gateway** — Upstream Monday.com or Groq API calls failed
- **200 OK** — Success path only

---

### Bug B: `session_id` Parameter Parsed but Never Used

**Location:** `QueryRequest` model (line 50), `handle_query()` function (lines 275-285)

**Problem:**
The API accepts `session_id` in every query request, but it was never used to isolate conversation memory:

```python
# BEFORE (BUG)
class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = "default"  # ← Parsed but ignored

conversation_memory = []  # ← Single global list, shared by ALL sessions

# In handle_query():
conversation_memory.append({...})  # ← Adds to global list, ignoring session_id

# In /memory GET:
return {"sessions": conversation_memory}  # ← Returns ALL sessions' data
```

**Why This Is Bad:**
- Two different callers with different `session_id` values read and pollute each other's memory
- The API contract implied per-session isolation (look at the OpenAPI spec — `/memory` should take a `session_id` parameter); the code didn't enforce it
- A malicious or buggy client can read private conversations from another session
- If user A asks sensitive questions, user B with a different `session_id` can see them

**Fix Applied:**

```python
# AFTER (FIXED)
conversation_memory: dict[str, list] = {}  # ← Key by session_id

# In handle_query():
conversation_memory.setdefault(req.session_id, []).append({...})  # ← Per-session
if len(conversation_memory[req.session_id]) > 5:
    conversation_memory[req.session_id].pop(0)

# In build_memory_ctx():
def build_memory_ctx(session_id: str) -> str:
    session_history = conversation_memory.get(session_id, [])  # ← Scoped query
    ...

# In /memory GET & DELETE:
async def get_memory(session_id: str = "default"):
    return {"sessions": conversation_memory.get(session_id, [])}  # ← Session-scoped
```

---

## 3. OpenAPI Spec (`specmatic/openapi.yaml`)

The spec defines the "truth" about what the API should do — including correct status codes and examples:

**Key sections:**

- **`/query` POST** — Returns 200 on success, **502 on upstream errors, 503 on config errors**
  ```yaml
  responses:
    "200": {...success schema}
    "502": {...upstream failure schema}
    "503": {...config unavailable schema}
  ```

- **`/memory` GET/DELETE** — Accepts `session_id` query parameter to scope results
  ```yaml
  parameters:
    - name: session_id
      in: query
      schema: { type: string }
      description: Session identifier (defaults to 'default' if not provided)
  ```

- **All error responses include `"error": true` field** to match the implementation

---

## 4. How Specmatic Catches These Bugs

### Running Specmatic

```bash
# Terminal 1 — Start the app
python -m uvicorn main:app --reload --port 8000

# Terminal 2 — Run contract tests
docker run --rm -v "$(pwd)":/specmatic -w /specmatic \
  specmatic/specmatic test --testBaseURL http://host.docker.internal:8000
```

On **Windows**, if using Docker Desktop, `host.docker.internal` automatically resolves to localhost.

### Expected Test Output (BEFORE FIX)

Specmatic will fail on `/query` endpoint:

```
❌ FAILED: POST /query
  
  Expected: status 502 (upstream failure scenario)
  Received: status 200
  
  Response body: {"answer": "❌ Failed to fetch Monday data: ...", "error": true}
  
  Reason: Spec requires 502 when monday_error occurs; app returned 200
```

The test generates this scenario automatically from the spec's status code definitions and your OpenAPI examples.

### Expected Test Output (AFTER FIX)

All tests pass:

```
✅ PASSED: GET /health
✅ PASSED: GET /quality-report
✅ PASSED: POST /query (200 success path)
✅ PASSED: POST /query (502 upstream error path)
✅ PASSED: POST /query (503 config unavailable path)
✅ PASSED: POST /query (422 malformed request)
✅ PASSED: GET /memory
✅ PASSED: DELETE /memory

Test Summary: 8 passed, 0 failed
```

---

## 5. Demonstrating Bug B (Session Isolation)

Pure schema testing (Specmatic) cannot catch business-logic bugs. Bug B requires a **scenario test** with assertions on behavior:

```python
# example_session_isolation_test.py
# This is NOT pure Specmatic; it's a custom integration test

import httpx

async def test_sessions_are_isolated():
    base_url = "http://localhost:8000"
    
    # Session A asks a question
    resp_a = httpx.post(f"{base_url}/query", json={
        "query": "What is our revenue?",
        "session_id": "session-a"
    })
    assert resp_a.status_code == 200
    
    # Session B asks a different question
    resp_b = httpx.post(f"{base_url}/query", json={
        "query": "What is our headcount?",
        "session_id": "session-b"
    })
    assert resp_b.status_code == 200
    
    # Session A retrieves memory — should only see its own question
    memory_a = httpx.get(f"{base_url}/memory?session_id=session-a").json()
    assert len(memory_a["sessions"]) == 1
    assert "revenue" in memory_a["sessions"][0]["query"]
    assert "headcount" not in memory_a["sessions"][0]["query"]
    
    # Session B retrieves memory — should NOT see A's question
    memory_b = httpx.get(f"{base_url}/memory?session_id=session-b").json()
    assert len(memory_b["sessions"]) == 1
    assert "headcount" in memory_b["sessions"][0]["query"]
    assert "revenue" not in memory_b["sessions"][0]["query"]
```

**Key insight:** Contract compliance ≠ Business logic correctness. Specmatic catches HTTP semantics; you must write scenario tests for domain logic.

---

## 6. Files Changed

### Files Added
- **`specmatic/openapi.yaml`** — The contract definition
- **`specmatic.yaml`** — Specmatic config pointing to the spec

### Files Modified
- **`main.py`** — All error paths now return correct status codes; memory is per-session

**Summary of changes in `main.py`:**

| Change | Line(s) | Type | Impact |
|--------|---------|------|--------|
| `conversation_memory: dict[str, list] = {}` | 33 | Bug B Fix | Keyed by session_id |
| `def build_memory_ctx(session_id: str)` | 115 | Bug B Fix | Scoped to session |
| `ask_llm(..., session_id: str)` | 139 | Bug B Fix | Passes session to prompt context |
| `status_code=503` on GROQ_API_KEY missing | 220 | Bug A Fix | Config error returns 503 |
| `status_code=503` on GROQ init failed | 233 | Bug A Fix | Config error returns 503 |
| `status_code=503` on Monday not configured | 243 | Bug A Fix | Config error returns 503 |
| `status_code=502` on monday_error | 259 | Bug A Fix | Upstream error returns 502 |
| `ask_llm(..., req.session_id)` | 267 | Bug B Fix | Passes session to LLM context |
| `conversation_memory.setdefault(req.session_id, [])` | 278 | Bug B Fix | Appends to session-scoped list |
| `status_code=502` on groq_error | 285 | Bug A Fix | Upstream error returns 502 |
| `memory_size: len(conversation_memory.get(req.session_id, []))` | 293 | Bug B Fix | Trace reports session-scoped size |
| `async def get_memory(session_id: str = "default")` | 309 | Bug B Fix | Returns only requested session |
| `async def clear_memory(session_id: str = "default")` | 312 | Bug B Fix | Clears only requested session |

---

## 7. Running the Complete Demo

### Step 1: Start the App

```bash
# From the monday_bi_agent directory
# Make sure .env has valid GROQ_API_KEY and MONDAY_API_KEY

python -m uvicorn main:app --reload --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete
```

### Step 2: Verify the App Works

```bash
# In a new terminal
curl -s http://localhost:8000/health | python -m json.tool
```

Response:
```json
{
  "status": "ok",
  "monday_configured": true,
  "groq_configured": true,
  "memory_sessions": 0
}
```

### Step 3: Run Specmatic Tests

```bash
# Ensure you have Docker installed
docker run --rm -v "$(pwd)":/specmatic -w /specmatic \
  specmatic/specmatic test --testBaseURL http://host.docker.internal:8000
```

Expected result (all pass):
```
✅ All tests passed!
```

### Step 4: View the HTML Report

```bash
# Report is generated in build/reports/specmatic/html/
# Open it in your browser
start build\reports\specmatic\html\index.html
```

---

## 8. What This Demonstrates

✅ **Contract-driven development finds real bugs**
- Bug A (wrong HTTP status codes) — Classic REST semantics violation
- Bug B (ignored session_id) — API contract mismatch

✅ **Schema-based testing (Specmatic) has limits**
- Catches HTTP-layer bugs automatically
- Requires scenario/integration tests for business logic

✅ **The fixes are production-ready**
- Status codes follow HTTP spec (5xx for config/upstream errors)
- Session isolation prevents cross-session data leakage
- Backward compatible (session_id defaults to "default")

---

## 9. Next Steps for Production

1. **Add authentication** — Prevent arbitrary session_id spoofing
2. **Add rate limiting** — Protect Groq/Monday.com quota
3. **Add metrics** — Track per-session query latency, error rates
4. **Add integration tests** — Run scenario tests in CI/CD
5. **Refresh the HTML UI** — Display status codes, session indicator

---

## References

- [Specmatic Documentation](https://specmatic.in)
- [OpenAPI 3.0 Spec](https://swagger.io/specification/)
- [HTTP Status Codes](https://httpwg.org/specs/rfc7231.html)
- [REST API Best Practices](https://restfulapi.net/)
