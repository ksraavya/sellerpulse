# SellerPulse AI

A lightweight, voice-first, agentic Virtual Key Account Manager prototype.

## Stack
- Frontend: React + Vite
- Backend: Python + FastAPI
- Agent orchestration: LangGraph (added in the orchestration milestone)
- Seller data: validated JSON mock data
- Voice: browser-based real-time voice integration (added later)

This is a modular monolith. We intentionally do not use PostgreSQL, Docker, Redis, SQLAlchemy, or microservices for this take-home assignment.

## Structure
```text
sellerpulse-ai/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/routes/sellers.py
│   │   ├── schemas/
│   │   ├── repositories/
│   │   ├── services/seller_service.py
│   │   └── core/config.py
│   ├── data/sellers/
│   │   ├── demo-seller.json
│   │   └── stable-seller.json
│   ├── tests/
│   ├── .env.example
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── App.jsx
│       ├── main.jsx
│       └── styles.css
├── .gitignore
└── README.md
```

## Prerequisites
- Python 3.11+
- Node.js 20+
- npm

## Backend (Windows PowerShell)
```powershell
cd backend
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```
Backend: http://localhost:8000  
Health: http://localhost:8000/api/health  
Sellers: http://localhost:8000/api/sellers  
Seller context: http://localhost:8000/api/sellers/demo-seller  
API docs: http://localhost:8000/docs

## Frontend
Open a second terminal:
```powershell
cd frontend
npm install
npm run dev
```
Frontend: http://localhost:5173

The frontend checks the backend health endpoint. Run both applications to see the connection status.

## Environment
Copy `backend/.env.example` to `backend/.env`. No API key is needed yet. Add provider credentials only when the relevant milestone is implemented. Never expose secret keys in frontend variables.

`SELLER_DATA_DIR` optionally points at a different mock seller directory. When it is unset, the backend reads `backend/data/sellers`.

## Seller data
`GET /api/sellers` returns profile summaries. `GET /api/sellers/{seller_id}` returns the validated seller context: profile, products, inventory, monthly sales, and product performance.

The two bundled sellers are synthetic demonstration records, not Snapdeal data.

- `demo-seller` — declining orders, rising cancellations, and stock below the reorder point.
- `stable-seller` — steady orders, low cancellations, and healthy stock.

File layout, field rules, and how to add another seller are documented in `backend/data/README.md`. The JSON directory is read once per process. Restart the API after adding or editing a seller file.

## Checks
Backend:
```powershell
cd backend
pytest -q
```
Frontend:
```powershell
cd frontend
npm run build
```

## Milestones
- SP-01 — Fresh project foundation
- SP-02 — Seller data and domain layer
- SP-03 — Math Agent
- SP-04 — Diagnostic Agent
- SP-05 — Recommendation Agent
- SP-06 — LangGraph orchestration, conversation memory and escalation
- SP-07 — Voice integration
- SP-08 — Seller dashboard and UI polish
- SP-09 — Testing, deployment and submission
