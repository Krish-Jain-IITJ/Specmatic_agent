# Monday.com BI Agent - Complete Project Documentation

**Version:** 1.0  
**Date:** April 2026  
**Author:** Development Team  
**Repository:** https://github.com/Krish-Jain-IITJ/skylark_drones_ps_re.git

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Project Overview](#project-overview)
3. [Architecture](#architecture)
4. [Features](#features)
5. [Technology Stack](#technology-stack)
6. [Setup and Installation](#setup-and-installation)
7. [API Endpoints](#api-endpoints)
8. [Development Guide](#development-guide)
9. [Deployment](#deployment)
10. [Troubleshooting](#troubleshooting)
11. [Bonus: MCP Server Integration](#bonus-mcp-server-integration)

---

## Executive Summary

The **Monday.com BI Agent** is a FastAPI-powered Business Intelligence platform that enables founders and business users to query live data from Monday.com boards using conversational AI. The system fetches real-time data, applies intelligent data cleaning, and leverages advanced LLM capabilities (Groq) to provide actionable insights.

**Key Capabilities:**
- Real-time Monday.com data fetching
- Intelligent data transformation and cleaning
- Conversational BI analysis powered by Groq LLM
- In-memory session memory for context-aware follow-up questions
- Full API transparency with detailed trace logs
- Cloud-ready for Vercel deployment

---

## Project Overview

### Problem Statement

Founders often struggle to extract meaningful insights from Monday.com data due to:
- Manual data export and analysis workflows
- Inconsistent data formats and quality issues
- Lack of quick, conversational query capabilities

### Solution

The Monday.com BI Agent provides:
- **Single chat interface** for business questions
- **Live data integration** with Monday.com GraphQL API
- **Intelligent data cleaning** that handles nulls, formats, and inconsistencies
- **AI-powered analysis** using Groq's high-performance LLM (llama-3.3-70b-versatile)
- **Conversation memory** for contextual follow-up queries

### Use Cases

1. **Pipeline Analysis** - Query deal funnel, conversion rates, and pipeline health
2. **Work Order Tracking** - Monitor project status, resource allocation, and timelines
3. **Sector Performance** - Analyze revenue by sector, growth trends, and market segments
4. **Revenue Forecasting** - Estimate pipeline closure, billing status, and AR insights
5. **Ad-hoc Analysis** - Answer custom business questions with full data access

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Frontend (HTML/CSS/JS)                    │
│                 Single-Page Chat Interface                  │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP POST /query
                           ▼
┌─────────────────────────────────────────────────────────────┐
│               FastAPI Application Server                    │
│  - Request handling                                         │
│  - Route management                                         │
│  - Response formatting                                      │
└──────┬──────────────────┬──────────────────┬────────────────┘
       │                  │                  │
       ▼                  ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Monday.com   │  │ Data Cleaner │  │ Groq LLM API │
│ GraphQL API  │  │ (Normalize)  │  │ (Reasoning)  │
│ (Live Data)  │  │              │  │              │
└──────────────┘  └──────────────┘  └──────────────┘
```

### Component Breakdown

| Component | Purpose | Technology |
|-----------|---------|------------|
| **Frontend** | User interaction, chat interface | HTML5, CSS3, Vanilla JavaScript |
| **API Server** | Request routing, data orchestration | FastAPI, Uvicorn |
| **Monday.com Integration** | Live board data fetching | httpx (async HTTP) |
| **Data Cleaning** | Format normalization, null handling | Custom Python pipeline |
| **LLM Engine** | BI analysis and reasoning | Groq API (llama-3.3-70b-versatile) |
| **Session Memory** | Context preservation across queries | In-memory Python list |

---

## Features

### 1. Live Data Integration
- **Real-time fetch** from Monday.com boards (no caching)
- **Async processing** for non-blocking API calls
- **Configurable board IDs** for Work Orders and Deals

### 2. Intelligent Data Cleaning
Automatic transformations applied to raw data:
- **Null handling**: All missing/empty values normalized
- **String formatting**: Quoted strings cleaned (e.g., `'Completed'` → `Completed`)
- **Currency**: Parsed to clean floats (removes ₹/$, commas)
- **Dates**: Standardized to ISO YYYY-MM-DD format
- **Quantities**: Structured as `{raw, numeric, unit}` objects
- **Sector names**: Normalized to canonical values
- **Status fields**: Execution status normalized (e.g., "Pause / struck" → "On Hold")
- **Billing**: Case normalization (e.g., "BIlled" → "Billed")

### 3. Conversational AI Analysis
- **Context-aware responses** using Groq's 70B reasoning model
- **Data-driven insights** with precise metrics and trends
- **Quality caveats** communicated transparently
- **Follow-up support** via 5-session memory injection

### 4. Full API Transparency
- **Detailed trace logs** showing every API call, timestamp, and error
- **Right-panel trace display** in UI for debugging
- **Quality report metadata** included in responses

### 5. Short-term Memory
- Last 5 Q&A pairs stored in-memory
- Automatically injected into LLM system prompt
- Enables follow-up questions: *"show me just the energy ones"*

---

## Technology Stack

### Backend
| Layer | Technology | Version |
|-------|-----------|---------|
| **Framework** | FastAPI | 0.115.0 |
| **Server** | Uvicorn | 0.32.0 |
| **HTTP Client** | httpx | 0.28.0 |
| **Data Model** | Pydantic | 2.10.0 |
| **Env Config** | python-dotenv | 1.0.1 |

### AI/LLM
| Service | Model | Purpose |
|---------|-------|---------|
| **Groq** | llama-3.3-70b-versatile | Primary BI analysis engine |
| **Anthropic** | claude-opus-4-5 | (Optional) Alternative for specialized tasks |
| **Google AI** | google-generativeai | (Optional) Additional model support |

### Data Integration
| Service | Purpose |
|---------|---------|
| **Monday.com GraphQL API** | Live board data, real-time updates |
| **Custom Data Cleaner** | Data normalization, quality assurance |

### Frontend
| Technology | Use |
|-----------|-----|
| **HTML5** | Semantic structure |
| **CSS3** | Responsive styling |
| **Vanilla JavaScript** | DOM manipulation, API calls, chat flow |
| **Static Files** | Logo, assets, static resources |

### DevOps/Deployment
| Tool | Purpose |
|------|---------|
| **Git** | Version control |
| **Vercel** | Serverless hosting (Python runtime) |
| **GitHub** | Repository hosting |

---

## Setup and Installation

### Prerequisites
- Python 3.10+
- pip + venv
- GitHub account
- Vercel account (for production deployment)
- API Keys:
  - Monday.com API key
  - Groq API key
  - Anthropic API key (optional)

### Local Development Setup

#### 1. Clone Repository
```bash
git clone https://github.com/Krish-Jain-IITJ/skylark_drones_ps_re.git
cd monday_bi_agent
```

#### 2. Create Virtual Environment
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

#### 3. Install Dependencies
```bash
python -m pip install -r requirements.txt
```

#### 4. Configure Environment Variables
```bash
cp .env.example .env
# Edit .env with your actual API keys
```

**Required Environment Variables:**
```
MONDAY_API_KEY=your_monday_api_key
MONDAY_BOARD_WO=12345678  # Work Orders board ID
MONDAY_BOARD_DEALS=87654321  # Deals board ID
GROQ_API_KEY=your_groq_api_key
ANTHROPIC_API_KEY=your_anthropic_key  # optional
GEMINI_API_KEY=your_gemini_key  # optional
```

#### 5. Obtain Board IDs from Monday.com
- Navigate to your Monday.com board
- Copy the board ID from the URL: `https://yourteam.monday.com/boards/[BOARD_ID]`

#### 6. Import Sample Data (Optional)
- In Monday.com, create two boards: "Work Orders" and "Deals"
- Import provided Excel files or real data
- Note the board IDs and add to `.env`

#### 7. Run Development Server
```bash
python -m uvicorn main:app --reload --port 8000
```

Open http://localhost:8000 in your browser.

---

## API Endpoints

### 1. GET `/` - Chat UI
Returns the main HTML interface.

**Response:** HTML page with chat interface

**Example:**
```bash
curl http://127.0.0.1:8000/
```

---

### 2. POST `/query` - Submit BI Query

Submit a natural language business question and receive AI-powered analysis.

**Request Body:**
```json
{
  "query": "What is our total pipeline value by sector?",
  "session_id": "default"
}
```

**Response:**
```json
{
  "answer": "Based on current data...",
  "trace": [
    { "step": "query_received", "timestamp": "2026-04-07T10:30:00" },
    { "step": "call_groq_api", "model": "llama-3.3-70b-versatile" },
    { "step": "complete", "elapsed_seconds": 3.45 }
  ],
  "elapsed": 3.45,
  "wo_count": 150,
  "deals_count": 87,
  "source": "monday_live"
}
```

**Error Response (Missing API Key):**
```json
{
  "answer": "⚠️ GROQ_API_KEY not configured",
  "trace": [],
  "error": true
}
```

**Example Usage:**
```bash
curl -X POST http://127.0.0.1:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query":"What is our revenue by sector?"}' 
```

---

### 3. GET `/health` - Health Check

Check configuration status without running queries.

**Response:**
```json
{
  "status": "ok",
  "monday_configured": true,
  "anthropic_configured": false,
  "memory_sessions": 3
}
```

**Example:**
```bash
curl http://127.0.0.1:8000/health
```

---

### 4. GET `/memory` - View Session Memory

Retrieve the last 5 Q&A pairs stored in session memory.

**Response:**
```json
{
  "sessions": [
    {
      "query": "What is our pipeline?",
      "answer": "Current pipeline: $2.5M...",
      "timestamp": "2026-04-07T10:25:00"
    }
  ]
}
```

**Example:**
```bash
curl http://127.0.0.1:8000/memory
```

---

### 5. DELETE `/memory` - Clear Session Memory

Clear all stored conversation history.

**Response:**
```json
{
  "status": "cleared"
}
```

**Example:**
```bash
curl -X DELETE http://127.0.0.1:8000/memory
```

---

### 6. GET `/quality-report` - Data Quality Metrics

Retrieve data quality statistics from the last data fetch.

**Response:**
```json
{
  "work_orders": {
    "total_records": 150,
    "fixes_applied": { "null_filled": 12, "format_normalized": 8 },
    "null_counts": { "status": 5, "date": 2 }
  },
  "deals": {
    "total_records": 87,
    "fixes_applied": { "currency_parsed": 15 },
    "null_counts": { "value": 3, "sector": 0 }
  }
}
```

**Example:**
```bash
curl http://127.0.0.1:8000/quality-report
```

---

## Development Guide

### Project Structure

```
monday_bi_agent/
├── main.py                 # FastAPI application, routes, LLM logic
├── data_cleaner.py         # Data transformation and normalization
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variables template
├── .env                    # Local environment (git-ignored)
├── quality_report.json     # Data quality metrics
├── README.md               # Quick start guide
├── PROJECT_DOCUMENTATION.md # This file
├── vercel.json             # Vercel deployment config
├── .vercelignore           # Files to exclude from Vercel
├── api/
│   └── index.py            # Vercel serverless entrypoint
├── templates/
│   └── index.html          # Frontend UI
└── static/
    └── logo.png            # Assets
```

### Adding New API Fields

1. **Update data_cleaner.py** to transform the new field
2. **Test locally** with sample Monday.com data
3. **Update ask_llm() prompt** to describe the field to the LLM
4. **Test query responses** to ensure the field is mentioned

### Modifying LLM Behavior

Edit the `system` prompt in `ask_llm()` function:
```python
system = f"""You are a senior Business Intelligence analyst.
...
YOUR JOB:
1. Answer with precise numbers...
2. If a field is null, say so...
"""
```

### Running Tests

```bash
# Verify Groq client initialization
python -c "import main; main.get_groq_client(); print('OK')"

# Test API endpoints (locally running)
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/query -H "Content-Type: application/json" -d '{"query":"test"}'
```

---

## Deployment

### Deployment to Vercel (Recommended)

#### Prerequisites
- Vercel account (free tier available)
- GitHub repository pushed
- Vercel CLI installed: `npm install -g vercel`

#### Step 1: Push to GitHub

Ensure all changes are committed and pushed:
```bash
git add .
git commit -m "Project ready for production"
git push origin main
```

#### Step 2: Connect to Vercel via Dashboard

1. Go to **https://vercel.com**
2. Log in with GitHub account
3. Click **"Add New..."** → **"Project"**
4. Select your `skylark_drones_ps_re` repository
5. Framework: Select **"Other"** (Vercel detects Python)
6. Root Directory: Leave empty
7. Click **"Deploy"**

#### Step 3: Configure Environment Variables

1. Go to **Project Settings** → **Environment Variables**
2. Add the following:
   - `MONDAY_API_KEY`
   - `MONDAY_BOARD_WO`
   - `MONDAY_BOARD_DEALS`
   - `GROQ_API_KEY`
   - `ANTHROPIC_API_KEY` (optional)

3. Click **"Save"**

#### Step 4: Redeploy

1. Trigger a new deployment by pushing to `main`:
```bash
git push origin main
```

Or manually redeploy:
2. Go to Vercel dashboard
3. Click **"Deployments"** → Latest deployment → **"Redeploy"**

#### Step 5: Verify Deployment

- Open the generated Vercel URL (e.g., `https://monday-bi-agent.vercel.app`)
- Test the `/health` endpoint
- Submit a test query

### Production Considerations

**Vercel Limitations:**
- Serverless functions have **10-second execution limit**
- Cold starts may add 1-2 seconds latency
- If queries timeout, consider:
  - Render.com (containers)
  - Railway.app (managed containers)
  - AWS Lambda (with larger timeout)
  - DigitalOcean (dedicated VM)

**Monitoring:**
- Check Vercel function logs: Project → **"Deployments"** → **"Logs"**
- Monitor error rates and execution times

**Security:**
- Never commit `.env` files
- Use Vercel's secure environment variables
- Rotate API keys periodically
- Consider IP whitelisting for Monday.com API

---

## Troubleshooting

### Issue: "Groq client not initialized"

**Cause:** `GROQ_API_KEY` not set or `groq` package not installed

**Solution:**
1. Check `.env` file has `GROQ_API_KEY` set
2. Reinstall: `pip install groq`
3. Verify: `python -c "from groq import Groq; print('OK')"`

### Issue: "Monday.com not configured"

**Cause:** Missing `MONDAY_API_KEY`, `MONDAY_BOARD_WO`, or `MONDAY_BOARD_DEALS`

**Solution:**
1. Verify all three variables are in `.env`
2. Check board IDs are correct (numeric)
3. Ensure Monday.com API key is active in team settings

### Issue: Slow Responses (>5 seconds)

**Cause:** Monday.com or Groq API latency

**Solution:**
- Check internet connection
- Verify Monday.com board has reasonable data size
- Consider increasing Groq timeout in `ask_llm()`
- For production, migrate to non-serverless hosting

### Issue: "Module not found: main"

**Cause:** Running from wrong directory or Python path issue

**Solution:**
```bash
# Ensure you're in the project root
cd C:\Users\dell\OneDrive\Desktop\ZIP\monday_bi_agent

# Run with proper Python path
python -m uvicorn main:app --reload
```

### Issue: CORS Errors

**Status:** CORS is **enabled** for all origins in this app (`allow_origins=["*"]`)

If still encountering CORS errors:
1. Clear browser cache
2. Check browser console for exact error
3. Verify request headers include `Content-Type: application/json`

### Issue: Data Quality Issues

**Symptom:** Null values not properly handled, formats inconsistent

**Solution:**
1. Check `data_cleaner.py` → `clean_and_enrich()` function
2. Inspect `quality_report.json` for applied transformations
3. Add custom transformation for specific field
4. Verify Monday.com source data is correct

---

## Bonus: MCP Server Integration

### Overview

**Model Context Protocol (MCP)** servers enable AI models to query external services and APIs in a standardized way. This project can be extended to function as an MCP server, allowing Claude and other AI models to:

- Query Monday.com boards through the agent
- Request BI analysis without direct API knowledge
- Integrate into larger AI workflows and agents

### MCP Server Architecture

```
┌─────────────────────────────────────────────┐
│      Claude / Other AI Model (Host)        │
└────────────────┬────────────────────────────┘
                 │ MCP Protocol (JSON-RPC)
                 ▼
┌─────────────────────────────────────────────┐
│  Monday BI Agent (MCP Server Implementation) │
│  - /query → answer()                        │
│  - /health → health_check()                 │
│  - /memory → get_memory()                   │
│  - /quality_report → get_quality_report()   │
└────────────────┬────────────────────────────┘
                 │
                 ▼
        Monday.com + Groq APIs
```

### How MCP Works

MCP defines a set of **Tools** that AI models can invoke:

**Example Tool: `answer_question`**
```json
{
  "name": "answer_question",
  "description": "Ask the BI agent a business question",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "The business question (e.g., 'What is our total pipeline?')"
      }
    },
    "required": ["query"]
  }
}
```

### Implementation Path

To add MCP server support:

1. **Install MCP SDK**:
```bash
pip install mcp
```

2. **Create `mcp_server.py`**:
```python
from mcp.server import Server
from mcp.types import Tool, TextContent, ToolResult
import main

app = Server("monday-bi-agent")

@app.tool()
def answer_question(query: str) -> str:
    """Answer a business intelligence question"""
    # Call main.ask_llm() internally
    return answer

mcp = app.build()
```

3. **Update `vercel.json`** for dual endpoints:
```json
{
  "builds": [
    { "src": "api/index.py", "use": "@vercel/python" },
    { "src": "mcp_server.py", "use": "@vercel/python" }
  ]
}
```

4. **Register with Claude**:
   - In Claude settings, add this as an MCP resource
   - Claude will auto-discover available tools

### Advantages of MCP Integration

✅ **Standardized Interface** - Works with any MCP-compatible AI model  
✅ **Zero Code Changes** - Existing FastAPI logic remains unchanged  
✅ **Composability** - Integrate with other AI agents and workflows  
✅ **Better Reasoning** - Claude gets structured tool schemas  
✅ **Enterprise Ready** - Industry standard for AI-service integration  

### Example Use Case

**Claude with MCP enabled:**
> "Using my Monday.com data, create a weekly revenue forecast and highlight the top 3 at-risk deals"

**Breakdown:**
1. Claude recognizes `answer_question` tool
2. Calls: `{"query": "What is our pipeline by status?"}`
3. Gets response with structured data
4. Calls again for: `{"query": "Show at-risk deals with probability < 30%"}`
5. Synthesizes data into forecast + visualization

---

## Support & Maintenance

### Reporting Issues

1. Check troubleshooting section above
2. Review function logs in Vercel dashboard
3. Create GitHub issue with:
   - Error message
   - Steps to reproduce
   - Environment (local vs. Vercel)
   - API keys status (don't share keys!)

### Code Updates

- Keep dependencies updated: `pip list --outdated`
- Monitor Groq API changes and limits
- Review Monday.com API changelog quarterly
- Performance optimize queries if latency increases

### Future Enhancements

- [ ] Add PDF report generation
- [ ] Implement caching layer (Redis)
- [ ] Build dashboard with historical analytics
- [ ] MCP server implementation
- [ ] Multi-board aggregation
- [ ] Custom metric definitions
- [ ] Scheduled reports via email
- [ ] Web3 integration for on-chain BI

---

## Conclusion

The **Monday.com BI Agent** is a production-ready platform that bridges the gap between raw business data and actionable insights. By combining Monday.com's real-time data, intelligent cleaning pipelines, and advanced LLM reasoning, it empowers founders to make data-driven decisions conversationally.

With Vercel deployment, the system is **scalable, maintainable, and cost-effective**. The optional MCP integration further extends its capabilities into broader AI workflows.

---

**Document Version:** 1.0  
**Last Updated:** April 7, 2026  
**Repository:** https://github.com/Krish-Jain-IITJ/skylark_drones_ps_re.git  
**Live URL:** (Set after Vercel deployment)

---
