# 💼 Agentic Wealth Concierge

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://python.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2%2B-orange)](https://github.com/langchain-ai/langgraph)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.35%2B-red?logo=streamlit)](https://streamlit.io)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-0.5%2B-purple)](https://www.trychroma.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-green)](LICENSE)

> An autonomous **multi-agent financial advisor** built with LangGraph, ChromaDB, and Groq (LLaMA 3).  
> The system continuously monitors your finances, evaluates tax-efficient liquidation strategies, recalls your past preferences via vector memory, and surfaces a single rupee-denominated recommendation — all without human input until the final approval step.

---

## 🧠 Architecture — The CWD Model

**CWD = Continuous Watch → Decide → Execute**

The system runs autonomously end-to-end through a 5-agent LangGraph pipeline:

```
Transactions / Portfolio
        │
        ▼
 ┌─────────────┐
 │Monitor Agent│  ← Reads transactions, detects balance shortfalls & large spends
 └──────┬──────┘
        ▼
 ┌────────────────────┐
 │Liquidity Check Agent│  ← Identifies liquid assets to sell (liquid_fund → equity)
 └──────────┬─────────┘
            ▼
 ┌──────────────┐
 │  Tax Agent   │  ← Computes unrealised P&L; spots tax-loss harvesting opportunities
 └──────┬───────┘
        ▼
 ┌──────────────┐
 │ Memory Agent │  ← Queries past decisions for behavioural patterns
 └──────┬───────┘
        ▼
 ┌────────────────────┐
 │  Execution Agent   │  ← Queries ChromaDB goals + calls Groq LLM → final recommendation
 └────────────────────┘
        │
        ▼
   Human Approval (yes / no)
```

---

## 🤖 What Each Agent Does

| Agent | Role |
|---|---|
| 🔍 **Monitor Agent** | Reads `transactions.csv`, computes balance, flags large purchases (>₹5,000), triggers alert if balance <₹40,000 |
| 💰 **Liquidity Check Agent** | Scans portfolio for liquid funds; prioritises `liquid_fund → mutual_fund → equity` as last resort |
| 🧾 **Tax Agent** | Computes unrealised P&L per holding; identifies tax-loss harvesting opportunities under Indian tax law |
| 🧠 **Memory Agent** | Queries `decisions_log.csv` for past approved decisions; generates a behavioural pattern string |
| 🤖 **Execution Agent** | Queries ChromaDB for the most relevant financial goal; builds a rich prompt; calls Groq LLM for the final recommendation |

---

## ⚙️ Setup Instructions

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/WealthConciergeApplication.git
cd WealthConciergeApplication
```

### 2. Create a virtual environment

```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Add your Groq API key

```bash
copy .env.template .env      # Windows
# cp .env.template .env      # macOS / Linux
```

Open `.env` and replace `your_key_here` with your actual Groq key from:  
👉 <https://console.groq.com/keys> (free tier available)

### 5. Seed ChromaDB with financial goals *(run once)*

```bash
python setup_memory.py
```

---

## 🚀 Running the Application

### Option A — Streamlit Dashboard *(recommended)*

```bash
streamlit run streamlit_dashboard.py
```

### Option B — Terminal (interactive CLI)

```bash
python milestone2_agent.py
```

---

## 📁 Project Structure

```
WealthConciergeApplication/
├── .env.template               # Copy to .env and add your Groq key
├── requirements.txt            # Python dependencies
├── setup_memory.py             # One-time ChromaDB seeding script
├── milestone2_agent.py         # LangGraph 5-agent pipeline (CLI mode)
├── streamlit_dashboard.py      # Streamlit UI with 3 tabs
├── fix_encoding.py             # CSV encoding utility
├── data/
│   ├── transactions.csv        # Sample bank transactions (April 2026)
│   ├── portfolio.csv           # Sample investment portfolio (5 holdings)
│   └── decisions_log.csv       # Auto-generated audit log of all decisions
├── scenarios/                  # Pre-built financial scenarios for demos
│   ├── scenario1_gadget_spree/
│   ├── scenario2_medical_emergency/
│   ├── scenario3_wedding_expenses/
│   ├── scenario4_market_crash/
│   └── scenario5_job_loss/
└── wealth_memory/              # Auto-generated ChromaDB vector store (gitignored)
```

---

## 📊 Sample Portfolio

| Asset | Type | Unrealised P&L |
|---|---|---|
| Nifty BeES | Liquid Fund | +₹2,325 |
| HDFC Liquid Fund | Liquid Fund | +₹49,650 |
| Reliance Industries | Equity | +₹22,000 ✅ |
| Bharti Airtel | Equity | −₹12,000 ❌ *(TLH opportunity)* |
| HDFC Flexi Cap Fund | Mutual Fund | +₹6,650 |

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Agent Orchestration | [LangGraph](https://github.com/langchain-ai/langgraph) |
| LLM Backend | [Groq](https://groq.com) (LLaMA 3 — ultra-fast inference) |
| Vector Memory | [ChromaDB](https://www.trychroma.com) + sentence-transformers |
| Dashboard | [Streamlit](https://streamlit.io) |
| Data | Pandas / CSV |

---

## 🔒 Security

- **Never commit your `.env` file.** It is already listed in `.gitignore`.
- The `.env.template` is safe to commit — it contains no secrets.
- If you accidentally committed a real key, **revoke it immediately** at <https://console.groq.com/keys>.

---

## 📄 License

[MIT](LICENSE) — free to use, modify, and distribute.
