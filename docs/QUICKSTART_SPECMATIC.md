# Quick Start Guide — Running Specmatic Tests

This guide walks you through running contract tests against the Monday.com BI Agent.

## Prerequisites

- **Docker** installed (for Specmatic container)
- **Python 3.10+** with dependencies installed
- **Valid .env** with GROQ_API_KEY and MONDAY_API_KEY

## Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 2: Start the App

```bash
# Terminal 1 — from the monday_bi_agent directory
python -m uvicorn main:app --reload --port 8000
```

Output:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete
```

## Step 3: Verify Health

In a new terminal, check the app is responding:

```bash
curl -s http://localhost:8000/health | python -m json.tool
```

Expected:
```json
{
  "status": "ok",
  "monday_configured": true,
  "groq_configured": true,
  "memory_sessions": 0
}
```

## Step 4: Run Specmatic Contract Tests

```bash
# Terminal 2 — from the monday_bi_agent directory
docker run --rm \
  -v "$(pwd)":/specmatic \
  -w /specmatic \
  specmatic/specmatic test \
  --testBaseURL http://host.docker.internal:8000
```

**On Windows (CMD):**
```cmd
docker run --rm ^
  -v "%cd%":/specmatic ^
  -w /specmatic ^
  specmatic/specmatic test ^
  --testBaseURL http://host.docker.internal:8000
```

**On Windows (PowerShell):**
```powershell
docker run --rm `
  -v "$(Get-Location):/specmatic" `
  -w /specmatic `
  specmatic/specmatic test `
  --testBaseURL http://host.docker.internal:8000
```

## Expected Output

### Success (After Fixes Applied)

```
Loading contract from: specmatic/contracts/openapi.yaml
Tests generated: 15
Tests passed: 15
Tests failed: 0

✅ All contract tests passed!
```

### Report Location

HTML report generated at:
```
build/reports/specmatic/html/index.html
```

Open in browser:
```bash
# Linux/macOS
open build/reports/specmatic/html/index.html

# Windows
start build\reports\specmatic\html\index.html
```

## Testing Session Isolation (Manual Test)

Verify that sessions are properly isolated:

```bash
# Terminal 3 — test session isolation

# Query from session-001
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is our revenue?", "session_id": "session-001"}'

# Query from session-002
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is our headcount?", "session_id": "session-002"}'

# Check session-001 memory — should only see revenue question
curl http://localhost:8000/memory?session_id=session-001 | python -m json.tool

# Check session-002 memory — should only see headcount question
curl http://localhost:8000/memory?session_id=session-002 | python -m json.tool
```

Expected:
- Session 001's memory contains only the "revenue" query
- Session 002's memory contains only the "headcount" query
- They are completely isolated

## Testing Status Codes (Manual Test)

Verify error paths return correct HTTP status codes:

```bash
# Simulate Groq unavailable by unsetting GROQ_API_KEY in .env, restart app

# This should return 503 (Service Unavailable)
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is our revenue?"}' \
  -w "\nHTTP Status: %{http_code}\n"

# Expected output:
# HTTP Status: 503
```

## Troubleshooting

### "Connection refused" on `host.docker.internal:8000`

**On Windows/macOS:** Docker Desktop should automatically resolve `host.docker.internal`. If not, try:
```bash
docker run --rm \
  -v "$(pwd)":/specmatic \
  -w /specmatic \
  --network host \
  specmatic/specmatic test \
  --testBaseURL http://localhost:8000
```

**On Linux:** `host.docker.internal` doesn't work by default. Use the host's IP:
```bash
HOST_IP=$(hostname -I | awk '{print $1}')
docker run --rm \
  -v "$(pwd)":/specmatic \
  -w /specmatic \
  specmatic/specmatic test \
  --testBaseURL http://$HOST_IP:8000
```

### Specmatic container fails to pull

```bash
# Ensure Docker daemon is running
docker version

# Pull the image manually
docker pull specmatic/specmatic

# Then re-run the test
```

### App returns 200 instead of 502/503

This means the code still has Bug A. Check that `main.py` has `status_code=502` and `status_code=503` on all error return paths in `handle_query()`.

## What Each Test Covers

| Test | Validates | Status Code Expected |
|------|-----------|---------------------|
| GET /health | Service is running, config present | 200 |
| GET /quality-report | Static report available | 200 |
| GET /memory | Sessions parameter scoped correctly | 200 |
| DELETE /memory | Clear operation works | 200 |
| POST /query (success) | Answer generated, all fields present | 200 |
| POST /query (missing query) | Validation catches empty query | 422 |
| POST /query (upstream failure) | Monday/Groq error → Bad Gateway | 502 |
| POST /query (config unavailable) | Missing API keys → Service Unavailable | 503 |

---

## For Coding Round Submission

Include these artifacts:

1. **Screenshots:**
   - ✅ App starting (uvicorn running on 8000)
   - ✅ Health check passing
   - ✅ Specmatic tests passing
   - ✅ HTML report (success)

2. **Code changes:**
   - `specmatic/contracts/openapi.yaml` (the contract)
   - `specmatic.yaml` (config)
   - Diffs in `main.py` (bugs fixed)

3. **Documentation:**
   - `SPECMATIC_INTEGRATION.md` (this document)
   - `QUICKSTART_SPECMATIC.md` (this guide)

---

## Explanation for Interview

> "This project demonstrates contract-driven development. I wrote an OpenAPI spec that defines what the API **should** do, then ran Specmatic to test the implementation against the spec. It caught two real bugs:
> 
> **Bug A:** Error paths were returning HTTP 200 instead of 502/503, violating REST semantics. Any client checking status codes would treat failures as success.
> 
> **Bug B:** The API accepted a `session_id` parameter but never used it, so conversation memory leaked between sessions.
> 
> Both are exactly the kind of bug manual testing misses because the app 'basically works' — but the contract is violated. I fixed both and now the tests pass. This is why contract-driven development matters: it codifies the agreement between client and server at a level that pure functionality testing can't catch."
