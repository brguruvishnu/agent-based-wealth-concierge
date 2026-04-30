"""
milestone2_agent.py — Main LangGraph pipeline for Agentic Wealth Concierge.
Implements the CWD (Continuous Watch → Decide → Execute) model with 5 autonomous agents
and a human-in-the-loop approval step at the very end.
"""

import os
import sys
import time

# Force UTF-8 output on Windows terminals
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
import csv
from datetime import datetime
from typing import TypedDict

import pandas as pd
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from langchain_groq import ChatGroq
from langchain_core.globals import set_debug, set_verbose

set_debug(True)
set_verbose(True)

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TRANSACTIONS_PATH = os.path.join(BASE_DIR, "data", "transactions.csv")
PORTFOLIO_PATH = os.path.join(BASE_DIR, "data", "portfolio.csv")
DECISIONS_LOG_PATH = os.path.join(BASE_DIR, "data", "decisions_log.csv")
MEMORY_PATH = os.path.join(BASE_DIR, "wealth_memory")

ALERT_THRESHOLD = 40_000
BIG_PURCHASE_THRESHOLD = 5_000
DECISIONS_LOG_HEADER = [
    "timestamp", "balance", "shortfall", "trigger_type", "action_taken",
    "asset_recommended", "approved", "user_note",
]

# ─────────────────────────────────────────────
# SHARED STATE
# ─────────────────────────────────────────────

class WealthState(TypedDict):
    """Full shared state passed between all agents in the LangGraph pipeline."""
    # Monitor
    net_balance: float
    total_income: float
    total_spent: float
    big_purchases: list
    alert_triggered: bool
    shortfall: float

    # Liquidity
    liquid_available: float
    liquid_assets: list
    can_cover_shortfall: bool

    # Tax
    loss_making_assets: list
    tlh_suggestion: str

    # Memory
    past_behavior_pattern: str
    similar_past_decisions: list   # semantically matched past situations

    # Execution
    relevant_goal: str
    goal_similarity_score: float   # 0-100 how well the goal matched
    final_recommendation: str

    # Internal (not shown to user)
    _portfolio_df: list



# ─────────────────────────────────────────────
# CHROMADB HELPERS
# ─────────────────────────────────────────────

def _embedding_fn():
    return SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")

def _get_chroma_client():
    return chromadb.PersistentClient(path=MEMORY_PATH)

def _get_decision_memory_col():
    return _get_chroma_client().get_or_create_collection(
        name="decision_memory", embedding_function=_embedding_fn()
    )

def _build_situation_text(state: dict) -> str:
    bp = state.get("big_purchases", [])
    bp_str = ", ".join(b["description"] for b in bp[:2]) if bp else "none"
    loss = state.get("loss_making_assets", [])
    loss_str = ", ".join(a["asset"] for a in loss[:2]) if loss else "none"
    return (
        f"Net balance {state.get('net_balance',0):.0f}. "
        f"Shortfall {state.get('shortfall',0):.0f}. "
        f"Big purchases: {bp_str}. "
        f"Liquid available {state.get('liquid_available',0):.0f}. "
        f"Loss-making assets: {loss_str}."
    )


# ─────────────────────────────────────────────
# LLM HELPER
# ─────────────────────────────────────────────

def get_llm() -> ChatGroq:
    """Instantiate the Groq LLM using the environment API key."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError("GROQ_API_KEY not found in environment. Check your .env file.")
    return ChatGroq(
        model="llama-3.3-70b-versatile",
        groq_api_key=api_key,
        temperature=0.3,
    )


def invoke_with_retry(llm: ChatGroq, prompt: str, retries: int = 1) -> str:
    """Call the LLM with one automatic retry on quota/rate-limit errors."""
    for attempt in range(retries + 1):
        try:
            response = llm.invoke(prompt)
            return response.content
        except Exception as e:
            err = str(e)
            if ("429" in err or "rate_limit" in err.lower()) and attempt < retries:
                print("   ⚠️  Rate limited. Waiting 30s before retry...")
                time.sleep(30)
            else:
                raise


# ─────────────────────────────────────────────
# AGENT 1: MONITOR AGENT
# ─────────────────────────────────────────────

def monitor_agent(state: WealthState) -> WealthState:
    """Read transactions.csv, compute balance, flag big purchases, and trigger alert."""
    print("\n🔍 MONITOR AGENT — Scanning transactions...")

    try:
        df = pd.read_csv(TRANSACTIONS_PATH)
    except FileNotFoundError:
        raise FileNotFoundError(
            f"❌ transactions.csv not found at {TRANSACTIONS_PATH}. "
            "Please ensure the data/ directory exists with the correct files."
        )

    total_income = df[df["amount"] > 0]["amount"].sum()
    total_spent = abs(df[df["amount"] < 0]["amount"].sum())
    net_balance = total_income - total_spent

    # Big purchases: single expense > ₹5,000 (ignore small noise below ₹1,000)
    expenses = df[df["amount"] < 0].copy()
    expenses["abs_amount"] = expenses["amount"].abs()
    big_purchases_df = expenses[expenses["abs_amount"] > BIG_PURCHASE_THRESHOLD]
    big_purchases = [
        {"description": row["description"], "amount": row["abs_amount"]}
        for _, row in big_purchases_df.iterrows()
    ]

    alert_triggered = net_balance < ALERT_THRESHOLD
    shortfall = max(0, ALERT_THRESHOLD - net_balance)

    print(f"   💵 Total Income : ₹{total_income:,.0f}")
    print(f"   💸 Total Spent  : ₹{total_spent:,.0f}")
    print(f"   🏦 Net Balance  : ₹{net_balance:,.0f}")
    if big_purchases:
        print(f"   🚨 Big purchases this month:")
        for bp in big_purchases:
            print(f"      • {bp['description']} — ₹{bp['amount']:,.0f}")
    if alert_triggered:
        print(f"   ⚠️  ALERT: Balance below ₹{ALERT_THRESHOLD:,.0f}! Shortfall = ₹{shortfall:,.0f}")
    else:
        print("   ✅ Balance is healthy. No action needed.")

    return {
        **state,
        "net_balance": float(net_balance),
        "total_income": float(total_income),
        "total_spent": float(total_spent),
        "big_purchases": big_purchases,
        "alert_triggered": bool(alert_triggered),
        "shortfall": float(shortfall),
    }


def should_continue(state: WealthState) -> str:
    """Conditional edge: route to liquidity check only if alert triggered."""
    if state["alert_triggered"]:
        return "liquidity_check_agent"
    print("\n✅ All clear — finances look healthy. No recommendations needed today.")
    return END


# ─────────────────────────────────────────────
# AGENT 2: LIQUIDITY CHECK AGENT
# ─────────────────────────────────────────────

def liquidity_check_agent(state: WealthState) -> WealthState:
    """Read portfolio.csv, identify liquid funds, and determine if shortfall can be covered."""
    print("\n💰 LIQUIDITY CHECK AGENT — Evaluating redeemable assets...")

    try:
        df = pd.read_csv(PORTFOLIO_PATH)
    except FileNotFoundError:
        raise FileNotFoundError(
            f"❌ portfolio.csv not found at {PORTFOLIO_PATH}. "
            "Please ensure the data/ directory exists with the correct files."
        )

    # Priority order: liquid_fund → mutual_fund → equity
    PRIORITY = {"liquid_fund": 1, "mutual_fund": 2, "equity": 3}
    df["priority"] = df["type"].map(PRIORITY).fillna(9)
    df["current_value"] = df["units"] * df["current_price"]
    df_sorted = df.sort_values("priority")

    liquid_df = df[df["type"] == "liquid_fund"].copy()
    liquid_df["current_value"] = liquid_df["units"] * liquid_df["current_price"]
    liquid_available = liquid_df["current_value"].sum()

    liquid_assets = [
        {"asset": row["asset"], "value": row["current_value"], "type": row["type"]}
        for _, row in df_sorted.iterrows()
    ]

    can_cover_shortfall = liquid_available >= state["shortfall"]

    print(f"   🏊 Total Liquid Funds Available : ₹{liquid_available:,.0f}")
    for _, row in liquid_df.iterrows():
        print(f"      • {row['asset']} — ₹{row['current_value']:,.0f}")

    if can_cover_shortfall:
        print(f"   ✅ Liquid funds alone can cover shortfall of ₹{state['shortfall']:,.0f}")
    else:
        remaining = state["shortfall"] - liquid_available
        print(f"   ⚠️  Partial coverage — ₹{remaining:,.0f} still needed from equity/mutual funds")

    return {
        **state,
        "liquid_available": float(liquid_available),
        "liquid_assets": liquid_assets,
        "can_cover_shortfall": bool(can_cover_shortfall),
        "_portfolio_df": df_sorted.to_dict("records"),
    }


# ─────────────────────────────────────────────
# AGENT 3: TAX AGENT (Tax-Loss Harvesting)
# ─────────────────────────────────────────────

def tax_agent(state: WealthState) -> WealthState:
    """Compute unrealized P&L for all holdings and generate tax-loss harvesting suggestion."""
    print("\n🧾 TAX AGENT — Analysing unrealized P&L for tax efficiency...")

    portfolio = state.get("_portfolio_df", [])
    if not portfolio:
        return {**state, "loss_making_assets": [], "tlh_suggestion": "No portfolio data available."}

    df = pd.DataFrame(portfolio)
    df["unrealized_pnl"] = (df["current_price"] - df["buy_price"]) * df["units"]
    df["pnl_pct"] = ((df["current_price"] - df["buy_price"]) / df["buy_price"]) * 100

    loss_assets = df[df["unrealized_pnl"] < 0].sort_values("unrealized_pnl")
    profit_assets = df[df["unrealized_pnl"] >= 0]

    print("   📊 Unrealized P&L Summary:")
    for _, row in df.iterrows():
        sign = "🔴" if row["unrealized_pnl"] < 0 else "🟢"
        print(
            f"      {sign} {row['asset']}: ₹{row['unrealized_pnl']:,.0f} "
            f"({row['pnl_pct']:.1f}%)"
        )

    loss_making_assets = loss_assets.to_dict("records")

    if not loss_assets.empty:
        top_loss = loss_assets.iloc[0]
        tlh_suggestion = (
            f"🧾 Tax-Loss Harvesting Opportunity: Sell {top_loss['asset']} "
            f"({top_loss['units']:.0f} units @ ₹{top_loss['current_price']:,.0f}) "
            f"to realise a loss of ₹{abs(top_loss['unrealized_pnl']):,.0f}. "
            f"Under Indian tax law, this realised loss can offset STCG/LTCG gains from "
            f"profitable holdings like {profit_assets.iloc[0]['asset'] if not profit_assets.empty else 'other assets'}, "
            f"reducing your tax liability. STCG is taxed at 15% and LTCG at 10% — "
            f"harvesting this loss first maximises your net-of-tax return."
        )
        print(f"\n   {tlh_suggestion}")
    else:
        # No loss assets — recommend selling oldest holding at LTCG rate
        oldest = df.iloc[-1]
        tlh_suggestion = (
            f"No loss-making assets found. If liquidation is needed, prefer selling "
            f"{oldest['asset']} (held longest) to qualify for LTCG at 10% rather than "
            f"STCG at 15% — saving tax on any gains realised."
        )
        print(f"   ℹ️  {tlh_suggestion}")

    return {
        **state,
        "loss_making_assets": loss_making_assets,
        "tlh_suggestion": tlh_suggestion,
    }


# ─────────────────────────────────────────────
# AGENT 4: MEMORY AGENT (Vector-Enhanced)
# ─────────────────────────────────────────────

def memory_agent(state: WealthState) -> WealthState:
    """Search ChromaDB decision_memory for semantically similar past situations.
    Falls back to CSV pattern analysis when the vector store is empty."""
    print("\n🧠 MEMORY AGENT — Searching vector memory for similar situations...")

    situation_text = _build_situation_text(state)
    similar_decisions: list = []
    pattern = "No past decisions recorded yet — this will improve as you keep using the system."

    try:
        col = _get_decision_memory_col()
        count = col.count()
        if count == 0:
            raise ValueError("vector store empty")
        n = min(3, count)
        results = col.query(query_texts=[situation_text], n_results=n)
        ids   = results["ids"][0]
        docs  = results["documents"][0]
        metas = results["metadatas"][0]
        dists = results["distances"][0]

        for i in range(len(ids)):
            sim = round(max(0.0, 1.0 - dists[i] / 2.0) * 100, 1)
            similar_decisions.append({
                "situation":         docs[i],
                "approved":          metas[i].get("approved", "unknown"),
                "asset_recommended": metas[i].get("asset_recommended", "—"),
                "shortfall":         metas[i].get("shortfall", "0"),
                "timestamp":         metas[i].get("timestamp", ""),
                "similarity":        sim,
                "user_note":         metas[i].get("user_note", ""),
            })

        approved_m = [d for d in similar_decisions if d["approved"] == "True"]
        total = len(similar_decisions)
        pct   = int(len(approved_m) / total * 100) if total else 0
        top   = approved_m[0]["asset_recommended"] if approved_m else "N/A"

        # Include the user's own written reasoning from similar past decisions
        reasoning_notes = [
            ("Approved" if d["approved"] == "True" else "Rejected") + ": " + d["user_note"]
            for d in similar_decisions
            if d.get("user_note", "").strip()
            and "no explanation" not in d["user_note"].lower()
            and "via dashboard" not in d["user_note"].lower()
        ]
        reasoning_block = ""
        if reasoning_notes:
            reasoning_block = (
                " User reasoning from similar past situations: "
                + " | ".join(reasoning_notes[:2]) + "."
            )

        pattern = (
            f"Found {total} semantically similar past situation(s) "
            f"(top match: {similar_decisions[0]['similarity']}% similar). "
            f"You approved {len(approved_m)}/{total} ({pct}%) of comparable cases. "
            f"Previously recommended: {top}."
            f"{reasoning_block}"
        )
        print(f"   📜 Vector pattern: {pattern}")

    except Exception as e:
        print(f"   ⚠️  {e} — falling back to CSV.")
        try:
            df = pd.read_csv(DECISIONS_LOG_PATH)
            rel = df[df["approved"].astype(str).str.lower() == "true"].tail(3)
            if not rel.empty:
                total = len(rel)
                liq = rel["asset_recommended"].str.contains(
                    "liquid|BeES|Liquid Fund", case=False, na=False).sum()
                pct = int(liq / total * 100)
                top = "liquid fund" if liq >= total - liq else "equity"
                pct2 = pct if top == "liquid fund" else 100 - pct
                pattern = (
                    f"Based on {total} past CSV decision(s), you preferred "
                    f"{top} redemptions {pct2}% of the time."
                )
        except FileNotFoundError:
            pass

    return {
        **state,
        "past_behavior_pattern":  pattern,
        "similar_past_decisions": similar_decisions,
    }


# ─────────────────────────────────────────────
# AGENT 5: EXECUTION AGENT (LLM-Powered)
# ─────────────────────────────────────────────

def execution_agent(state: WealthState) -> WealthState:
    """Query ChromaDB for relevant goal and call LLM to generate a final actionable recommendation."""
    print("\n🤖 EXECUTION AGENT — Generating recommendation via LLM...")

    # 1. Semantic search in ChromaDB for the most relevant user goal
    goal_similarity = 0.0
    try:
        collection = _get_chroma_client().get_collection(
            name="user_goals", embedding_function=_embedding_fn()
        )
        results = collection.query(
            query_texts=["emergency fund liquidity cash flow shortfall"],
            n_results=1,
        )
        relevant_goal = results["documents"][0][0] if results["documents"] else "No goal found."
        raw_dist = results["distances"][0][0] if results.get("distances") else 1.0
        goal_similarity = round(max(0.0, 1.0 - raw_dist / 2.0) * 100, 1)
    except Exception as e:
        print(f"   ⚠️  ChromaDB goal query failed: {e}")
        relevant_goal = "Maintain financial stability and an emergency fund."

    print(f"   🎯 Most relevant goal: {relevant_goal}")

    # 2. Build context for big purchases
    big_purchase_text = ""
    if state.get("big_purchases"):
        items = [f"{bp['description']} (₹{bp['amount']:,.0f})" for bp in state["big_purchases"]]
        big_purchase_text = "Big purchases this month: " + ", ".join(items) + "."
    else:
        big_purchase_text = "No single expense exceeded ₹5,000 this month."

    # 3. Build context for liquid assets
    liquid_lines = []
    for asset in state.get("liquid_assets", []):
        if asset["type"] == "liquid_fund":
            liquid_lines.append(f"  • {asset['asset']}: ₹{asset['value']:,.0f} (liquid fund)")
    liquid_text = "\n".join(liquid_lines) if liquid_lines else "No liquid funds available."

    # 4. Compose the full prompt
    prompt = f"""You are a personal wealth concierge AI for an Indian young professional.
Analyse the following financial situation and provide a structured recommendation.

--- CURRENT SNAPSHOT ---
Current Bank Balance: ₹{state['net_balance']:,.0f}
Alert Threshold: ₹40,000
Shortfall: ₹{state['shortfall']:,.0f}
{big_purchase_text}

--- LIQUID ASSETS AVAILABLE ---
{liquid_text}
Total Liquid Available: ₹{state['liquid_available']:,.0f}
Can Cover Shortfall Fully: {state['can_cover_shortfall']}

--- TAX EFFICIENCY INSIGHT ---
{state['tlh_suggestion']}

--- PAST BEHAVIOUR PATTERN ---
{state['past_behavior_pattern']}

--- USER'S STATED FINANCIAL GOAL ---
"{relevant_goal}"

--- YOUR TASK ---
Respond in EXACTLY this format (3 clearly labelled sections):

**Situation:** (1–2 sentences) Describe what is happening with the user's finances right now.

**Proposed Action:** (2–3 sentences) Provide a specific, actionable recommendation. Name the exact asset, the exact rupee amount to redeem/sell, and why this is the best choice given the tax and liquidity context above.

**Goal Alignment:** (1 sentence) Explain how this action protects or advances the user's stated goal.

Be specific. Use ₹ amounts. Do not be vague. Do not suggest generic advice.
End your response with exactly this line:
Do you approve this action? (yes / no / later)"""

    # 5. Call LLM
    llm = get_llm()
    print("   📡 Calling Groq (llama-3.3-70b-versatile)...")
    recommendation = invoke_with_retry(llm, prompt)

    print("\n" + "═" * 60)
    print("🤖 WEALTH CONCIERGE RECOMMENDATION")
    print("═" * 60)
    print(recommendation)
    print("═" * 60)

    return {
        **state,
        "relevant_goal":         relevant_goal,
        "goal_similarity_score": goal_similarity,
        "final_recommendation":  recommendation,
    }


# ─────────────────────────────────────────────
# HUMAN APPROVAL + LOGGING (outside the graph)
# ─────────────────────────────────────────────

def human_approval(state: WealthState) -> tuple[bool, str]:
    """Prompt the human for approval and return (approved, user_note)."""
    print("\n🔔 HUMAN-IN-THE-LOOP: Your approval is required.")
    while True:
        answer = input("   Enter your decision (yes / no / later): ").strip().lower()
        if answer in ("yes", "no", "later"):
            break
        print("   ⚠️  Please type 'yes', 'no', or 'later'.")
    note = ""
    if answer in ("no", "later"):
        note = input("   Optional note (press Enter to skip): ").strip()
    return answer == "yes", note


def log_decision(state: WealthState, approved: bool, user_note: str) -> None:
    """Append the agent's recommendation and human decision to decisions_log.csv."""
    os.makedirs(os.path.dirname(DECISIONS_LOG_PATH), exist_ok=True)
    file_exists = os.path.isfile(DECISIONS_LOG_PATH)

    # Determine asset recommended from tlh_suggestion
    tlh = state.get("tlh_suggestion", "")
    asset_recommended = "Liquid Funds"
    if "Sell " in tlh:
        try:
            asset_recommended = tlh.split("Sell ")[1].split(" ")[0]
        except IndexError:
            pass

    row = {
        "timestamp": datetime.now().isoformat(),
        "balance": state["net_balance"],
        "shortfall": state["shortfall"],
        "trigger_type": "low_balance",
        "action_taken": state["final_recommendation"][:200].replace("\n", " "),
        "asset_recommended": asset_recommended,
        "approved": approved,
        "user_note": user_note,
    }

    with open(DECISIONS_LOG_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=DECISIONS_LOG_HEADER)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

    # Also embed and store in ChromaDB for future semantic search
    try:
        col = _get_decision_memory_col()
        col.add(
            ids=[f"decision_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"],
            documents=[_build_situation_text(state)],
            metadatas=[{
                "approved":          str(approved),
                "asset_recommended": asset_recommended,
                "shortfall":         str(state.get("shortfall", 0)),
                "timestamp":         row["timestamp"],
                "user_note":         user_note or "",
            }],
        )
        print("   🧠 Decision embedded in ChromaDB decision_memory.")
    except Exception as e:
        print(f"   ⚠️  Vector memory storage failed (non-fatal): {e}")

    if approved:
        print("\n✅ Decision APPROVED and logged.")
    else:
        print("\n❌ Decision NOT approved. Logged for future learning.")


# ─────────────────────────────────────────────
# BUILD THE LANGGRAPH
# ─────────────────────────────────────────────

def build_graph() -> object:
    """Construct and compile the LangGraph StateGraph pipeline."""
    builder = StateGraph(WealthState)

    builder.add_node("monitor_agent", monitor_agent)
    builder.add_node("liquidity_check_agent", liquidity_check_agent)
    builder.add_node("tax_agent", tax_agent)
    builder.add_node("memory_agent", memory_agent)
    builder.add_node("execution_agent", execution_agent)

    builder.add_edge(START, "monitor_agent")
    builder.add_conditional_edges(
        "monitor_agent",
        should_continue,
        {
            "liquidity_check_agent": "liquidity_check_agent",
            END: END,
        },
    )
    builder.add_edge("liquidity_check_agent", "tax_agent")
    builder.add_edge("tax_agent", "memory_agent")
    builder.add_edge("memory_agent", "execution_agent")
    builder.add_edge("execution_agent", END)

    return builder.compile(debug=True)


# ─────────────────────────────────────────────
# MAIN ENTRYPOINT
# ─────────────────────────────────────────────

def run_pipeline(interactive: bool = True) -> WealthState:
    """Execute the full CWD agent pipeline and handle human approval."""
    print("\n" + "━" * 60)
    print("   💼 AGENTIC WEALTH CONCIERGE — CWD MODEL")
    print("   Continuous Watch → Decide → Execute")
    print("━" * 60)

    app = build_graph()

    initial_state: WealthState = {
        "net_balance": 0.0,
        "total_income": 0.0,
        "total_spent": 0.0,
        "big_purchases": [],
        "alert_triggered": False,
        "shortfall": 0.0,
        "liquid_available": 0.0,
        "liquid_assets": [],
        "can_cover_shortfall": False,
        "loss_making_assets": [],
        "tlh_suggestion": "",
        "past_behavior_pattern": "",
        "similar_past_decisions": [],
        "relevant_goal": "",
        "goal_similarity_score": 0.0,
        "final_recommendation": "",
        "_portfolio_df": [],
    }

    final_state = app.invoke(initial_state)

    if final_state.get("alert_triggered") and final_state.get("final_recommendation"):
        if interactive:
            approved, user_note = human_approval(final_state)
            log_decision(final_state, approved, user_note)
        return final_state

    return final_state


if __name__ == "__main__":
    import subprocess
    import sys
    dashboard_path = os.path.join(BASE_DIR, "streamlit_dashboard.py")
    print("\n🚀 Launching Wealth Concierge Streamlit Dashboard...")
    subprocess.run([sys.executable, "-m", "streamlit", "run", dashboard_path])
