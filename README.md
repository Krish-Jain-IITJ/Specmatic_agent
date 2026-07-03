# Monday.com BI Agent

A FastAPI-powered Business Intelligence agent that answers founder-level questions by fetching **live data** from Monday.com boards.

## Architecture

```
FastAPI (Python) ──► Monday.com GraphQL API   (live board data)
                 ──► Anthropic Claude API      (BI analysis)
                 ◄── HTML/CSS/JS Frontend      (single-page chat)
```

## Features

- 🔴 **Live Monday.com API calls** — no caching, every query hits the API
- 🧠 **Short-term memory** — last 5 conversations used as context
- 🔍 **Visible tool/API trace** — right panel shows every API call in real-time
- 📊 **BI insights** — revenue, pipeline, sector performance, AR analysis
- 💬 **Conversational** — follow-up questions with context

## Setup

### 1. Create and activate the virtual environment
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

### 2. Install dependencies
```powershell
python -m pip install -r requirements.txt
```

### 3. Configure .env
```powershell
copy .env.example .env
# Edit .env with your actual keys
```

Required keys:
- `MONDAY_API_KEY` — Monday.com API key (Admin > API)
- `MONDAY_BOARD_WO` — Work Orders board ID (from board URL)
- `MONDAY_BOARD_DEALS` — Deals board ID (from board URL)
- `GROQ_API_KEY` — Groq API key for LLM access
- `ANTHROPIC_API_KEY` — Anthropic API key

### 4. Import data to Monday.com
- Import `Work_Order_Tracker_Data.xlsx` as a new board → "Work Orders"
- Import `Deal_funnel_Data.xlsx` as a new board → "Deals"
- Note the board IDs from the URLs and add to `.env`

### 5. Run
```powershell
python -m uvicorn main:app --reload --port 8000
```

Open http://localhost:8000

## Deploying on Vercel

This project can be deployed on Vercel using a Python Serverless Function entrypoint.

### 1. Add the Vercel config files
- `api/index.py` should import the FastAPI app from `main.py`
- `vercel.json` should route all requests to `/api/index.py`
- `.vercelignore` should exclude `.venv`, `.git`, and `.env`

### 2. Push your repo to GitHub
Make sure the repository is published on GitHub and contains:
- `main.py`
- `requirements.txt`
- `vercel.json`
- `api/index.py`
- `.vercelignore`

### 3. Set environment variables in Vercel
In your Vercel dashboard, go to Project Settings > Environment Variables and add:
- `MONDAY_API_KEY`
- `MONDAY_BOARD_WO`
- `MONDAY_BOARD_DEALS`
- `GROQ_API_KEY`
- `ANTHROPIC_API_KEY`

### 4. Deploy using Vercel CLI
```powershell
npm install -g vercel
cd <your-project-folder>
vercel login
vercel
```

When prompted:
- select or create your Vercel team
- set project name
- choose the root directory of this project
- accept defaults for the Python function detection

Then deploy production:
```powershell
vercel --prod
```

### 5. Verify the deployment
Open the generated Vercel URL and test the root page.

### Important notes
- Vercel serverless functions have execution time limits, so if API calls are slow you may need a different host.
- Do not store keys in `.env` for production; use Vercel environment variables instead.

## How Monday Board IDs work

When you open a board in Monday.com, the URL looks like:
```
https://yourteam.monday.com/boards/1234567890
```
The number at the end (`1234567890`) is your Board ID.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Chat UI |
| POST | `/query` | Submit BI query |
| GET | `/health` | Config status |
| GET | `/memory` | View memory |
| DELETE | `/memory` | Clear memory |

## Decision Log

### Tech Stack Choices

**FastAPI** — Async support for non-blocking Monday.com + Anthropic API calls. Auto OpenAPI docs. Minimal boilerplate.

**Plain HTML/CSS/JS** — No build step, instant loading, easy to host anywhere. The frontend is sophisticated enough without adding React overhead for a single-page chat.

**httpx** — Async HTTP client that works natively with FastAPI's async handlers.

**In-memory sessions** — The assignment requires short-term memory across 5 chats. A simple list works perfectly for a prototype; no DB overhead.

**Claude claude-opus-4-5** — Best reasoning quality for BI analysis on messy data with nulls and inconsistent formats.

### Data Strategy

Every query triggers **fresh Monday.com API calls** — no caching. The full dataset is passed to Claude with instructions to:
- Treat empty/null/nan as missing
- Normalize currency and date formats
- Communicate data quality caveats in the response

### Memory Design

Last 5 Q&A pairs are stored in memory and injected into the Claude system prompt as context. This enables follow-up questions ("show me just the energy ones" after asking about pipeline).
