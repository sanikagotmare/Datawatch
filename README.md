# 🔍 DataWatch — AI Data Observability Platform

> An AI-powered data quality and observability platform built with Python, FastAPI, React, Scikit-learn, Google Gemini, and ChromaDB.

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=flat&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?style=flat&logo=react&logoColor=black)
![Scikit-learn](https://img.shields.io/badge/Scikit--learn-1.4-F7931E?style=flat&logo=scikit-learn&logoColor=white)
![Google Gemini](https://img.shields.io/badge/Gemini-2.5_Flash-4285F4?style=flat&logo=google&logoColor=white)
![ChromaDB](https://img.shields.io/badge/ChromaDB-RAG-FF6B35?style=flat)
![SQLite](https://img.shields.io/badge/SQLite-003B57?style=flat&logo=sqlite&logoColor=white)

---

## What is DataWatch?

DataWatch automatically detects data quality issues in your datasets using a combination of machine learning and AI. Upload a CSV or JSON file and within seconds you get:

- **ML-powered anomaly detection** using Isolation Forest + Z-score statistics
- **Plain-English AI explanations** of every issue, powered by Google Gemini
- **Data science charts** — histograms, correlation heatmaps, box plots generated server-side
- **Self-healing engine** that automatically fixes missing values, duplicates, and type issues
- **RAG memory** — ChromaDB stores past fixes so the AI gets smarter with every upload
- **PII detection** — flags sensitive fields like email, phone, Aadhaar, PAN
- **Schema drift detection** — alerts when column types or names change between uploads
- **Database connectors** — connect directly to SQLite, PostgreSQL, or MySQL and analyze live tables

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| API Framework | FastAPI + Uvicorn | REST API, dependency injection, async |
| Database ORM | SQLAlchemy + SQLite | Data persistence |
| Auth | JWT (python-jose) + bcrypt | Secure authentication |
| ML Detection | Scikit-learn Isolation Forest | Unsupervised anomaly detection |
| Statistics | Pandas + Scipy Z-score | Missing values, outliers, duplicates |
| Data Profiling | Matplotlib + Seaborn | Server-side chart generation |
| LLM | Google Gemini 1.5 Flash | AI diagnosis + explainability |
| Vector DB | ChromaDB | RAG memory — semantic similarity search |
| Scheduler | APScheduler | Background monitoring jobs |
| Frontend | React 18 + Vite + TailwindCSS | UI |
| Charts | Recharts | Dashboard visualisations |

---

## Features

### 1. ML Anomaly Detection
Uses **Scikit-learn Isolation Forest** (unsupervised ML) alongside statistical methods:
- Missing values per column with severity scoring
- Statistical outliers using Z-score (Z > 3)
- Negative values in financial columns
- Exact duplicate rows
- Data type inconsistencies

### 2. AI Explainability Engine
Every anomaly gets a Gemini-generated explanation:
- Root cause analysis
- Business impact assessment
- Python fix code snippets with confidence scores
- PII risk summary

### 3. RAG Memory (ChromaDB)
Before every Gemini call, ChromaDB retrieves the top 5 most similar past fixes using cosine similarity and injects them into the prompt — so responses are grounded in your historical data.

### 4. Data Science Charts
Matplotlib + Seaborn generate charts server-side:
- Distribution histograms with mean/median lines
- Correlation heatmap
- Box plots for outlier visualisation
- Categorical value distribution charts
- Missing values heatmap

### 5. Self-Healing Engine
Click **Auto Heal Dataset** to automatically:
- Fill missing values (numeric → median, categorical → mode)
- Remove duplicate rows
- Coerce mistyped columns (e.g. `"1,234"` → `1234.0`)
- Flag statistical outliers without deleting them
- Download the cleaned CSV

### 6. Database Connectors
Connect to external databases and run AI analysis on live tables:
- SQLite (works out of the box)
- PostgreSQL (requires `psycopg2-binary`)
- MySQL (requires `pymysql`)

---

## Project Structure

```
datawatch-py/
├── backend/
│   ├── core/              # Config, database engine, JWT security
│   ├── models/            # SQLAlchemy table definitions
│   ├── routers/           # FastAPI route handlers
│   ├── services/          # Business logic layer
│   ├── ml/
│   │   ├── anomaly_detector.py   # Isolation Forest + Z-score
│   │   ├── data_profiler.py      # Matplotlib/Seaborn chart generation
│   │   ├── schema_detector.py    # Drift + PII detection
│   │   └── self_healer.py        # Auto-fix engine
│   ├── generate_demo_data.py     # Generates realistic messy CSVs
│   └── main.py
├── frontend/
│   └── src/
│       ├── pages/         # Dashboard, Upload, Report, DataSources, SelfHeal, Incidents
│       ├── components/    # Layout
│       ├── hooks/         # useAuth
│       └── services/      # Axios API layer
└── sample-data/           # Demo CSV files
```

---

## Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+
- Gemini API key — free at [aistudio.google.com](https://aistudio.google.com/app/apikey)

### 1. Clone the repository
```bash
git clone https://github.com/sanikagotmare/datawatch.git
cd datawatch
```

### 2. Set up the backend
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

### 3. Generate demo data
```bash
python generate_demo_data.py
```
Creates 5 realistic messy CSV files in `sample-data/` designed to trigger different detection features.

### 4. Start the backend
```bash
uvicorn main:app --reload --port 8000
```

### 5. Start the frontend
```bash
cd ../frontend
npm install
npm run dev
# Open http://localhost:5173
```

---

## Demo Walkthrough

| Step | Action | Feature shown |
|---|---|---|
| 1 | Register + Login | JWT auth |
| 2 | Upload `sales_data.csv` | ML + AI analysis pipeline |
| 3 | Report → Overview | Statistical anomalies |
| 4 | Report → Data Science | matplotlib/seaborn charts |
| 5 | Report → Issues | Gemini explanations |
| 6 | Report → Fixes | Python code with confidence scores |
| 7 | Report → AI Explainability | Root cause + business impact |
| 8 | Report → PII | Detected sensitive fields |
| 9 | Report → RAG Memory | Past fixes from ChromaDB |
| 10 | Click Auto Heal | Self-healing + download clean CSV |
| 11 | Upload hr_data_v1 then hr_data_v2 | Schema drift detection |
| 12 | Data Sources → SQLite → Analyze | Live database analysis |

---

## How the AI Pipeline Works

```
CSV Upload
    ↓
Isolation Forest ML      ← sklearn, trains on your actual data
    ↓
Z-score Statistics       ← scipy, per-column outlier detection
    ↓
PII Detection            ← regex + column name matching
    ↓
Schema Drift Check       ← compares dtypes against previous upload
    ↓
ChromaDB RAG Query       ← retrieves top-5 similar past fixes
    ↓
Gemini LLM Call          ← prompt includes ML results + RAG context
    ↓
matplotlib Charts        ← generated server-side, sent as base64 PNG
    ↓
Report saved to DB       ← full JSON in analysis_reports table
    ↓
Auto-create Incident     ← if severity is high/critical
```

---

## Environment Variables

| Variable | Description |
|---|---|
| `GEMINI_API_KEY` | Google Gemini API key (required) |
| `DATABASE_URL` | SQLAlchemy URL (default: SQLite) |
| `SECRET_KEY` | JWT signing secret |
| `CHROMA_PERSIST_DIR` | ChromaDB storage path |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT expiry (default: 1440) |

---

## License

MIT — free to use for learning and portfolio purposes.

---

*Built as a placement/internship portfolio project demonstrating Python, Data Science, AI/ML, and full-stack development.*
