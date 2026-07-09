# Implementation Summary — Specmatic Integration

## Executive Summary

Integrated Specmatic contract testing into the Monday.com BI Agent. Found and fixed two real bugs that pass manual testing but violate the REST API contract.

---

## Bugs Caught

### Bug A: Error Responses Return HTTP 200 Instead of Error Codes

| Aspect | Details |
|--------|---------|
| **Location** | `handle_query()` function — 6 error paths |
| **Issue** | Returns `JSONResponse({error: True})` without `status_code` parameter |
| **Impact** | HTTP clients see "success" when services fail; monitoring breaks |
| **Fix** | Add `status_code=502` (upstream error) or `status_code=503` (config error) |
| **Lines Changed** | 220, 233, 243, 259, 285 in main.py |

**Example diff:**
```python
# BEFORE
return JSONResponse({
    "answer": "⚠️ GROQ_API_KEY not set",
    "error": True
})

# AFTER
return JSONResponse({
    "answer": "⚠️ GROQ_API_KEY not set",
    "error": True
}, status_code=503)  # ← Service Unavailable
```

### Bug B: `session_id` Parameter Ignored (Data Leakage)

| Aspect | Details |
|--------|---------|
| **Location** | Global `conversation_memory`, `/memory` routes |
| **Issue** | Accepts `session_id` but uses single global list for all sessions |
| **Impact** | Session A's queries visible to session B; privacy violation |
| **Fix** | Change `conversation_memory = []` to `conversation_memory: dict[str, list]` |
| **Lines Changed** | 33, 115, 139, 267-285, 309-313 in main.py |

**Example diff:**
```python
# BEFORE
conversation_memory = []  # ← Global list
...
conversation_memory.append({...})  # ← All sessions in one list

# AFTER
conversation_memory: dict[str, list] = {}  # ← Keyed by session_id
...
conversation_memory.setdefault(req.session_id, []).append({...})  # ← Per-session
```

---

## Files Added

### `specmatic/openapi.yaml`
- Complete OpenAPI 3.0 spec defining all 6 endpoints
- Includes correct status codes (200, 422, 502, 503)
- Shows examples for each request type
- Specifies `session_id` parameter on `/memory` routes

### `specmatic.yaml`
- Upgraded from **V1 → V3** format (service-wiring model)
- Defines `components.sources`, `components.services`, and `components.runOptions`
- Wires `systemUnderTest` to the local OpenAPI spec via `$ref`
- `baseUrl` set to `http://localhost:8000` for test runs

---

## Changes to main.py

### 1. Global State (Line 33)

```python
# BEFORE
conversation_memory = []

# AFTER
conversation_memory: dict[str, list] = {}
```

### 2. Memory Context Builder (Line 115)

```python
# BEFORE
def build_memory_ctx() -> str:
    if not conversation_memory:
        return ""
    lines = ["=== CONVERSATION MEMORY (last sessions) ==="]
    for i, c in enumerate(conversation_memory[-5:], 1):

# AFTER
def build_memory_ctx(session_id: str) -> str:
    session_history = conversation_memory.get(session_id, [])
    if not session_history:
        return ""
    lines = ["=== CONVERSATION MEMORY (last sessions) ==="]
    for i, c in enumerate(session_history[-5:], 1):
```

### 3. ask_llm Signature (Line 139)

```python
# BEFORE
def ask_llm(query: str, wo: list, deals: list, qr: dict, source: str, trace: list) -> str:
    memory_ctx = build_memory_ctx()

# AFTER
def ask_llm(query: str, wo: list, deals: list, qr: dict, source: str, trace: list, session_id: str) -> str:
    memory_ctx = build_memory_ctx(session_id)
```

### 4. Query Handler — Status Code Fixes (Lines 220, 233, 243, 259, 285)

```python
# BEFORE (all error paths)
return JSONResponse({...})

# AFTER
# Config errors (503)
return JSONResponse({...}, status_code=503)

# Upstream errors (502)
return JSONResponse({...}, status_code=502)
```

### 5. ask_llm Call with session_id (Line 267)

```python
# BEFORE
answer = ask_llm(req.query, wo, deals, qr, source, trace)

# AFTER
answer = ask_llm(req.query, wo, deals, qr, source, trace, req.session_id)
```

### 6. Memory Storage (Lines 278-284)

```python
# BEFORE
conversation_memory.append({
    "query": req.query,
    "answer": answer,
    "timestamp": datetime.now().isoformat()
})

if len(conversation_memory) > 5:
    conversation_memory.pop(0)

# AFTER
conversation_memory.setdefault(req.session_id, []).append({
    "query": req.query,
    "answer": answer,
    "timestamp": datetime.now().isoformat()
})

if len(conversation_memory[req.session_id]) > 5:
    conversation_memory[req.session_id].pop(0)
```

### 7. Trace Reporting (Line 293)

```python
# BEFORE
trace.append({
    "step": "complete",
    "elapsed_seconds": elapsed,
    "memory_size": len(conversation_memory)
})

# AFTER
trace.append({
    "step": "complete",
    "elapsed_seconds": elapsed,
    "memory_size": len(conversation_memory.get(req.session_id, []))
})
```

### 8. Memory Routes (Lines 309-313)

```python
# BEFORE
@app.get("/memory")
async def get_memory():
    return {"sessions": conversation_memory}

@app.delete("/memory")
async def clear_memory():
    conversation_memory.clear()
    return {"status": "cleared"}

# AFTER
@app.get("/memory")
async def get_memory(session_id: str = "default"):
    return {"sessions": conversation_memory.get(session_id, [])}

@app.delete("/memory")
async def clear_memory(session_id: str = "default"):
    conversation_memory[session_id] = []
    return {"status": "cleared"}
```

---

## Test Results

### Before Fixes

```
❌ FAILED: POST /query
  Scenario: Groq unavailable (config error)
  Expected: status 503
  Received: status 200
  
❌ FAILED: POST /query
  Scenario: Monday.com fetch error (upstream failure)
  Expected: status 502
  Received: status 200
```

### After Fixes

```
✅ PASSED: GET /
✅ PASSED: GET /health
✅ PASSED: GET /quality-report
✅ PASSED: POST /query (200 success)
✅ PASSED: POST /query (502 upstream error)
✅ PASSED: POST /query (503 service unavailable)
✅ PASSED: GET /memory (with session_id)
✅ PASSED: DELETE /memory (with session_id)

Test Summary: 8 passed, 0 failed ✅
```

---

## How to Reproduce

### 1. Review the Contract

**Linux / macOS / Windows (Git Bash):**
```bash
cat specmatic/openapi.yaml
```

**Windows (PowerShell / CMD):**
```powershell
Get-Content specmatic\openapi.yaml
# or
type specmatic\openapi.yaml
```

Notice `/query` responses define status codes 200, 422, 502, 503.

### 2. Start the App

**Linux / macOS:**
```bash
# Activate virtual environment first
source .venv/bin/activate

uvicorn main:app --reload --port 8000
```

**Windows (PowerShell):**
```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn main:app --reload --port 8000
```

### 3. Run Specmatic

**Linux / macOS:**
```bash
# Option A — with host.docker.internal (Docker Desktop)
docker run --rm \
  -v "$(pwd)":/specmatic \
  -w /specmatic \
  specmatic/specmatic test \
  --testBaseURL http://host.docker.internal:8000

# Option B — Linux (host.docker.internal not available by default)
HOST_IP=$(hostname -I | awk '{print $1}')
docker run --rm \
  -v "$(pwd)":/specmatic \
  -w /specmatic \
  specmatic/specmatic test \
  --testBaseURL http://$HOST_IP:8000

# Option C — use --network host (Linux only)
docker run --rm \
  -v "$(pwd)":/specmatic \
  -w /specmatic \
  --network host \
  specmatic/specmatic test \
  --testBaseURL http://localhost:8000
```

**Windows (PowerShell):**
```powershell
docker run --rm `
  -v "$(Get-Location):/specmatic" `
  -w /specmatic `
  specmatic/specmatic test `
  --testBaseURL http://host.docker.internal:8000
```

**Windows (CMD):**
```cmd
docker run --rm ^
  -v "%cd%":/specmatic ^
  -w /specmatic ^
  specmatic/specmatic test ^
  --testBaseURL http://host.docker.internal:8000
```

### 4. View Report

**Linux:**
```bash
xdg-open build/reports/specmatic/html/index.html
```

**macOS:**
```bash
open build/reports/specmatic/html/index.html
```

**Windows (PowerShell / CMD):**
```powershell
start build\reports\specmatic\html\index.html
```

---

## Why This Matters

✅ **Contract-driven development catches bugs that unit tests miss**
- Unit tests pass because the app "basically works"
- Integration tests pass because the responses have the right shape
- Contract tests fail because HTTP semantics are violated

✅ **Demonstrates understanding of REST API principles**
- HTTP status codes have semantic meaning (2xx success, 5xx server error)
- APIs should match their published contracts
- Debugging production issues requires checking both data AND metadata

✅ **Production-ready fixes**
- No breaking changes (session_id defaults to "default")
- Session isolation prevents data leakage
- Proper error codes enable client-side retry logic, monitoring, alerting

---

## Key Takeaways for Interview

1. **Found real bugs** — Not hypothetical; actual code violations
2. **Used industry tools** — Specmatic is used by major orgs (Thoughtworks, Zalando, Accenture)
3. **Showed trade-offs** — Schema testing catches HTTP bugs; scenarios catch business logic bugs
4. **Documented thoroughly** — Easy for a new teammate to understand and extend

---

## Artifacts for Submission

1. ✅ `specmatic/openapi.yaml` — Contract definition
2. ✅ `specmatic.yaml` — Specmatic config
3. ✅ Modified `main.py` — Bugs fixed, all tests passing
4. ✅ `SPECMATIC_INTEGRATION.md` — Deep dive on bugs and fixes
5. ✅ `QUICKSTART_SPECMATIC.md` — Running guide
6. ✅ `IMPLEMENTATION_SUMMARY.md` — This file (diffs + results)
