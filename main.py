from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import os
import json
from typing import Optional
from dotenv import load_dotenv
from datetime import datetime
from pathlib import Path
from data_cleaner import clean_work_order, clean_deal, clean_and_enrich
from fastapi.staticfiles import StaticFiles
from groq import Groq

load_dotenv()

app = FastAPI(title="Monday.com BI Agent")
app.mount("/static", StaticFiles(directory="static"), name="static")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Load environment variables
GROQ_API_KEY      = os.getenv("GROQ_API_KEY", "").strip()
MONDAY_API_KEY    = os.getenv("MONDAY_API_KEY", "").strip()
MONDAY_BOARD_WO   = os.getenv("MONDAY_BOARD_WO", "").strip()
MONDAY_BOARD_DEALS = os.getenv("MONDAY_BOARD_DEALS", "").strip()
MONDAY_API_URL    = "https://api.monday.com/v2"

# Remove module-level client initialization - will initialize in handler
groq_client = None

# Per-session conversation memory: keys are session_id, values are lists of {query, answer, timestamp}
conversation_memory: dict[str, list] = {}
_BASE = Path(__file__).parent


def _load_json(filename: str) -> list:
    p = _BASE / filename
    return json.loads(p.read_text()) if p.exists() else []


# Load pre-cleaned local data (from uploaded Excel files)
# LOCAL_WO_CLEAN    = _load_json("wo_clean.json")
# LOCAL_DEALS_CLEAN = _load_json("deals_clean.json")
LOCAL_QR          = json.loads((_BASE / "quality_report.json").read_text()) if (_BASE / "quality_report.json").exists() else {}


class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = "default"


# ─── Monday.com helpers ───────────────────────────────────────────────────────

async def monday_gql(gql: str, variables: dict = None) -> dict:
    headers = {"Authorization": MONDAY_API_KEY, "Content-Type": "application/json", "API-Version": "2024-01"}
    payload = {"query": gql}
    if variables:
        payload["variables"] = variables
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(MONDAY_API_URL, json=payload, headers=headers)
        r.raise_for_status()
        return r.json()


async def fetch_board(board_id: str) -> tuple:
    gql = """
    query ($boardId: ID!, $limit: Int!) {
      boards(ids: [$boardId]) {
        columns { id title type }
        items_page(limit: $limit) {
          items { id name column_values { id text value } }
        }
      }
    }
    """
    data = await monday_gql(gql, {"boardId": board_id, "limit": 500})
    board = (data.get("data", {}).get("boards", []) or [{}])[0]
    return board.get("columns", []), board.get("items_page", {}).get("items", [])


def board_to_raw_records(cols: list, items: list) -> list:
    col_map = {c["id"]: c["title"] for c in cols}
    return [
        {"name": item["name"], "id": item["id"],
         **{col_map.get(cv["id"], cv["id"]): cv.get("text") or "" for cv in item.get("column_values", [])}}
        for item in items
    ]


async def get_live_data(trace: list) -> tuple[list, list, dict]:
    """Fetch from Monday.com, clean on the fly, return (wo, deals, quality_report)."""
    raw_wo, raw_deals = [], []

    for label, board_id, key, store in [
        ("Work Orders", MONDAY_BOARD_WO,   "work_orders", raw_wo),
        ("Deals",       MONDAY_BOARD_DEALS,"deals",       raw_deals),
    ]:
        trace.append({"step": f"fetch_{key}", "action": f"POST {MONDAY_API_URL} → boards(ids:[{board_id}]) items_page(limit:500)", "board": label, "timestamp": datetime.now().isoformat()})
        try:
            cols, items = await fetch_board(board_id)
            raw = board_to_raw_records(cols, items)
            store.extend(raw)
            trace.append({"step": f"{key}_fetched", "source": "monday_live", "raw_records": len(raw)})
        except Exception as e:
            trace.append({"step": f"{key}_error", "error": str(e)})

    trace.append({"step": "cleaning_data", "action": "Running data_cleaner.clean_and_enrich()", "timestamp": datetime.now().isoformat()})
    clean_wo, clean_deals, qr = clean_and_enrich(raw_wo, raw_deals)
    trace.append({"step": "cleaning_complete", "wo_clean": len(clean_wo), "deals_clean": len(clean_deals),
                  "wo_fixes": qr["work_orders"]["fixes_applied"], "deals_fixes": qr["deals"]["fixes_applied"]})
    return clean_wo, clean_deals, qr

# ─── Claude ───────────────────────────────────────────────────────────────────

def build_memory_ctx(session_id: str) -> str:
    session_history = conversation_memory.get(session_id, [])
    if not session_history:
        return ""
    lines = ["=== CONVERSATION MEMORY (last sessions) ==="]
    for i, c in enumerate(session_history[-5:], 1):
        lines.append(f"\n[Session {i}] Q: {c['query']}\nA: {c['answer'][:400]}…")
    return "\n".join(lines)


def format_quality_summary(qr: dict) -> str:
    if not qr:
        return ""
    wo = qr.get("work_orders", {})
    deals = qr.get("deals", {})
    lines = ["=== DATA QUALITY REPORT (already applied) ===",
             f"Work Orders: {wo.get('total_records',0)} records — fixes: {wo.get('fixes_applied',{})}",
             f"  Notable nulls: {dict(list(wo.get('null_counts',{}).items())[:6])}",
             f"Deals: {deals.get('total_records',0)} records — fixes: {deals.get('fixes_applied',{})}",
             f"  Notable nulls: {dict(list(deals.get('null_counts',{}).items())[:6])}"]
    return "\n".join(lines)


def ask_llm(query: str, wo: list, deals: list, qr: dict, source: str, trace: list, session_id: str) -> str:
    memory_ctx = build_memory_ctx(session_id)
    quality_ctx = format_quality_summary(qr)
    source_note = "DATA SOURCE: Live Monday.com API (real-time fetch per query)"

    system = f"""You are a senior Business Intelligence analyst.
                A founder is asking a business question.

                Give clear, structured insights.
         
{source_note}

{quality_ctx}

{memory_ctx}

DATA IS PRE-CLEANED. The following transformations have already been applied:
- All missing/null/nan/empty values → null (Python None)
- Quoted strings like "'Completed'" → "Completed"  
- Currency fields → clean float values (no ₹/$, no commas)
- Dates → ISO YYYY-MM-DD strings
- Quantities like "5360 HA" → {{raw, numeric, unit}} objects
- Sector names → normalized canonical names
- Execution status → normalized (e.g. "Pause / struck" → "On Hold")
- Header-row contamination rows → removed from Deals
- Billing status casing fixed (e.g. "BIlled" → "Billed")

YOUR JOB:
1. Answer with precise numbers, percentages, trends from the clean data.
2. If a field is null, say so — don't guess. Mention data gaps that affect your answer.
3. Use the quality report above to caveat limitations.
4. Use clear sections and bullet points. Highlight key metrics prominently.
5. Use conversation memory for follow-up questions.

WORK ORDERS SAMPLE (first 20 rows):
{json.dumps(wo[:5], default=str)}

DEALS SAMPLE (first 20 rows):
{json.dumps(deals[:5], default=str)}
"""

    trace.append({"step": "call_groq_api", "action": "Using Groq API",
                   "model": "llama-3.3-70b-versatile", "wo_records": len(wo), "deals_records": len(deals),
                  "query": query[:120], "timestamp": datetime.now().isoformat()})

    chat_completion = groq_client.chat.completions.create(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": query}
        ],
        model="llama-3.3-70b-versatile",
    )
    return chat_completion.choices[0].message.content


# ─── Routes ──────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
  return (_BASE / "templates" / "index.html").read_text(encoding="utf-8")

@app.post("/query")
async def handle_query(req: QueryRequest):
    trace = []
    t0 = datetime.now()

    trace.append({
        "step": "query_received",
        "query": req.query,
        "timestamp": t0.isoformat()
    })

    # ✅ Check API keys and initialize Groq client
    if not GROQ_API_KEY:
        return JSONResponse({
            "answer": "⚠️ GROQ_API_KEY not set in environment variables",
            "trace": trace,
            "error": True
        }, status_code=503)

    if " " in GROQ_API_KEY:
        return JSONResponse({
            "answer": "⚠️ GROQ_API_KEY contains invalid characters (spaces). Please check your configuration.",
            "trace": trace,
            "error": True
        }, status_code=503)

    # Initialize Groq client if not already done
    global groq_client
    if groq_client is None:
        try:
            groq_client = Groq(api_key=GROQ_API_KEY)
            trace.append({"step": "groq_init", "status": "success"})
        except Exception as e:
            trace.append({"step": "groq_init", "status": "failed", "error": str(e)})
            return JSONResponse({
                "answer": f"⚠️ Failed to initialize Groq client: {e}",
                "trace": trace,
                "error": True
            }, status_code=503)

    if not (MONDAY_API_KEY and MONDAY_BOARD_WO and MONDAY_BOARD_DEALS):
        return JSONResponse({
            "answer": "⚠️ Monday.com not configured. Please set MONDAY_API_KEY and BOARD IDs.",
            "trace": trace,
            "error": True
        }, status_code=503)

    # ✅ ALWAYS use live data (NO fallback)
    trace.append({"step": "data_source", "mode": "monday_live"})

    try:
        wo, deals, qr = await get_live_data(trace)
        source = "monday_live"
    except Exception as e:
        trace.append({
            "step": "monday_error",
            "error": str(e)
        })
        return JSONResponse({
            "answer": f"❌ Failed to fetch Monday data: {e}",
            "trace": trace,
            "error": True
        }, status_code=502)

    # ✅ Call Groq
    try:
        answer = ask_llm(req.query, wo, deals, qr, source, trace, req.session_id)
    except Exception as e:
        trace.append({
            "step": "groq_error",
            "error": str(e)
        })
        return JSONResponse({
            "answer": f"❌ Groq API error: {e}",
            "trace": trace,
            "error": True
        }, status_code=502)

    # ✅ Memory (per-session)
    conversation_memory.setdefault(req.session_id, []).append({
        "query": req.query,
        "answer": answer,
        "timestamp": datetime.now().isoformat()
    })

    if len(conversation_memory[req.session_id]) > 5:
        conversation_memory[req.session_id].pop(0)

    elapsed = round((datetime.now() - t0).total_seconds(), 2)

    trace.append({
        "step": "complete",
        "elapsed_seconds": elapsed,
        "memory_size": len(conversation_memory.get(req.session_id, []))
    })

    return JSONResponse({
        "answer": answer,
        "trace": trace,
        "elapsed": elapsed,
        "wo_count": len(wo),
        "deals_count": len(deals),
        "source": source
    })
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "monday_configured": bool(MONDAY_API_KEY and MONDAY_BOARD_WO and MONDAY_BOARD_DEALS),
        "groq_configured": bool(GROQ_API_KEY),
        "memory_sessions": len(conversation_memory)
    }

@app.get("/memory")
async def get_memory(session_id: str = "default"):
    return {"sessions": conversation_memory.get(session_id, [])}

@app.delete("/memory")
async def clear_memory(session_id: str = "default"):
    conversation_memory[session_id] = []
    return {"status": "cleared"}

@app.get("/quality-report")
async def quality_report():
    return LOCAL_QR
