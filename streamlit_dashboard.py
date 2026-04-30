"""
streamlit_dashboard.py — Interactive Streamlit UI for Agentic Wealth Concierge.
5 tabs: Run Agent, My Goals, My Transactions, My Portfolio, Decision History.
All financial data is fully editable from the dashboard and persists to disk.
"""

import os
import sys
import uuid
import shutil
import streamlit as st
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv, set_key

# ──────────────────────────────────────────
# BOOT
# ──────────────────────────────────────────
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(dotenv_path=_env_path, override=False)

BASE_DIR          = os.path.dirname(os.path.abspath(__file__))
PORTFOLIO_PATH    = os.path.join(BASE_DIR, "data", "portfolio.csv")
TRANSACTIONS_PATH = os.path.join(BASE_DIR, "data", "transactions.csv")
DECISIONS_LOG_PATH= os.path.join(BASE_DIR, "data", "decisions_log.csv")
MEMORY_PATH       = os.path.join(BASE_DIR, "wealth_memory")

DECISIONS_LOG_HEADER = [
    "timestamp", "balance", "shortfall", "trigger_type",
    "action_taken", "asset_recommended", "approved", "user_note",
]
CATEGORIES  = ["Income", "Housing", "Food", "Shopping", "Utilities", "Entertainment", "Other"]
ASSET_TYPES = ["liquid_fund", "mutual_fund", "equity"]

st.set_page_config(
    page_title="Agentic Wealth Concierge",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────
# CSS
# ──────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.stApp {
    background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
    min-height: 100vh;
}
.main-header { text-align: center; padding: 1.5rem 0 0.8rem 0; }
.main-header h1 {
    font-size: 2.4rem; font-weight: 700;
    background: linear-gradient(135deg, #a78bfa, #60a5fa, #34d399);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text; margin-bottom: 0.2rem;
}
.main-header p { color: #94a3b8; font-size: 0.95rem; letter-spacing: 0.05em; }

.glass-card {
    background: rgba(255,255,255,0.05); backdrop-filter: blur(20px);
    border: 1px solid rgba(255,255,255,0.1); border-radius: 16px;
    padding: 1.4rem; margin: 0.8rem 0;
}
.insight-card {
    background: linear-gradient(135deg, rgba(124,58,237,0.15), rgba(59,130,246,0.15));
    border: 1px solid rgba(124,58,237,0.4); border-radius: 16px;
    padding: 1.5rem; margin: 1rem 0;
    box-shadow: 0 4px 24px rgba(124,58,237,0.15);
}
.rec-card {
    background: linear-gradient(135deg, rgba(124,58,237,0.2), rgba(59,130,246,0.2));
    border: 1px solid rgba(124,58,237,0.5); border-radius: 16px;
    padding: 2rem; margin: 1.5rem 0;
    box-shadow: 0 8px 32px rgba(124,58,237,0.2);
}
.alert-card {
    background: rgba(239,68,68,0.1); border: 1px solid rgba(239,68,68,0.4);
    border-radius: 12px; padding: 1rem 1.5rem; margin: 0.8rem 0;
}
.success-card {
    background: rgba(52,211,153,0.1); border: 1px solid rgba(52,211,153,0.4);
    border-radius: 12px; padding: 1rem 1.5rem; margin: 0.8rem 0;
}
.metric-card {
    background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08);
    border-radius: 12px; padding: 1.1rem; text-align: center;
    transition: transform 0.2s ease;
}
.metric-card:hover { transform: translateY(-2px); }
.metric-label { color: #94a3b8; font-size: 0.78rem; font-weight: 500; text-transform: uppercase; letter-spacing: 0.08em; }
.metric-value { color: #f1f5f9; font-size: 1.5rem; font-weight: 700; margin-top: 0.3rem; }
.profit  { color: #34d399 !important; }
.loss    { color: #f87171 !important; }

.agent-badge {
    display: inline-flex; align-items: center; gap: 0.5rem;
    padding: 0.4rem 1rem; border-radius: 9999px;
    font-size: 0.83rem; font-weight: 500; margin: 0.25rem 0;
}
.badge-done    { background: rgba(52,211,153,0.15); border: 1px solid rgba(52,211,153,0.4); color: #34d399; }
.badge-running { background: rgba(251,191,36,0.15);  border: 1px solid rgba(251,191,36,0.4);  color: #fbbf24; }

.stTabs [data-baseweb="tab-list"] {
    gap: 0.4rem; background: rgba(255,255,255,0.03);
    border-radius: 12px; padding: 0.3rem;
}
.stTabs [data-baseweb="tab"] { border-radius: 9px; color: #94a3b8; font-weight: 500; }
.stTabs [aria-selected="true"] {
    background: rgba(124,58,237,0.3) !important; color: #a78bfa !important;
}
div[data-testid="column"] .stButton > button {
    width: 100%; border-radius: 10px; font-weight: 600;
    padding: 0.6rem 1rem; border: none; transition: all 0.2s ease;
}
div[data-testid="column"] .stButton > button:hover {
    transform: translateY(-1px); box-shadow: 0 4px 15px rgba(0,0,0,0.3);
}
.scan-btn > button {
    background: linear-gradient(135deg, #7c3aed, #2563eb) !important;
    color: white !important; font-size: 1.05rem !important;
    padding: 0.75rem 2rem !important; border-radius: 12px !important; width: 100% !important;
}
.goal-box {
    background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.1);
    border-radius: 12px; padding: 0.8rem 1rem; margin: 0.4rem 0;
}
hr { border-color: rgba(255,255,255,0.07); }
.stDataFrame { border-radius: 12px; overflow: hidden; }

/* Sidebar */
section[data-testid="stSidebar"] {
    background: rgba(15,12,41,0.95) !important;
    border-right: 1px solid rgba(255,255,255,0.07);
}
</style>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────
# SIDEBAR — API KEY
# ──────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Configuration")
    st.markdown("---")
    _existing_key = os.environ.get("GROQ_API_KEY", "")
    _api_input = st.text_input(
        "Groq API Key", value=_existing_key, type="password",
        placeholder="gsk_…", help="https://console.groq.com/keys",
        key="sidebar_api_key",
    )
    if st.button("💾  Save Key", use_container_width=True, key="save_key_btn"):
        if _api_input.strip():
            if not os.path.exists(_env_path):
                tpl = os.path.join(BASE_DIR, ".env.template")
                shutil.copy(tpl, _env_path) if os.path.exists(tpl) else open(_env_path,"w").close()
            set_key(_env_path, "GROQ_API_KEY", _api_input.strip())
            os.environ["GROQ_API_KEY"] = _api_input.strip()
            st.success("✅ Key saved!")
        else:
            st.error("Enter a valid key.")
    _live = os.environ.get("GROQ_API_KEY", "")
    if _live:
        st.markdown(
            f'<div style="background:rgba(52,211,153,0.1);border:1px solid rgba(52,211,153,0.3);'
            f'border-radius:8px;padding:0.5rem 1rem;margin-top:0.5rem;font-size:0.8rem;color:#34d399;">'
            f'🔑 Active: ...{_live[-6:]}</div>', unsafe_allow_html=True)
    else:
        st.markdown(
            '<div style="background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.3);'
            'border-radius:8px;padding:0.5rem 1rem;margin-top:0.5rem;font-size:0.8rem;color:#f87171;">'
            '⚠️ No API key</div>', unsafe_allow_html=True)
    st.markdown("---")
    st.markdown(
        "<p style='color:#64748b;font-size:0.75rem;'>Free key →<br>"
        "<a href='https://console.groq.com/keys' target='_blank' style='color:#a78bfa;'>"
        "console.groq.com/keys</a></p>", unsafe_allow_html=True)


# ──────────────────────────────────────────
# HEADER
# ──────────────────────────────────────────
st.markdown("""
<div class="main-header">
  <h1>💼 Agentic Wealth Concierge</h1>
  <p>Autonomous CWD Model · Continuous Watch → Decide → Execute</p>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════
# HELPERS — DATA I/O
# ══════════════════════════════════════════

def load_csv(path: str, default_cols: list) -> pd.DataFrame:
    """Load a CSV file or return an empty DataFrame with default columns."""
    try:
        return pd.read_csv(path)
    except FileNotFoundError:
        return pd.DataFrame(columns=default_cols)


def save_csv(df: pd.DataFrame, path: str) -> None:
    """Save a DataFrame to CSV, creating parent dirs if needed."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path, index=False)


def load_decisions() -> pd.DataFrame | None:
    """Load decisions_log.csv; return None if it doesn't exist yet."""
    try:
        return pd.read_csv(DECISIONS_LOG_PATH)
    except FileNotFoundError:
        return None


def log_decision_from_ui(state: dict, approved: bool, user_note: str) -> None:
    """Persist approval decision to decisions_log.csv."""
    from milestone2_agent import log_decision
    log_decision(state, approved, user_note)


# ══════════════════════════════════════════
# HELPERS — CHROMADB GOALS
# ══════════════════════════════════════════

def _get_collection():
    """Return the ChromaDB goals collection, creating it if needed."""
    import chromadb
    from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
    fn = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
    client = chromadb.PersistentClient(path=MEMORY_PATH)
    return client.get_or_create_collection(name="user_goals", embedding_function=fn)


def get_all_goals() -> list[tuple[str, str]]:
    """Return list of (id, text) tuples for every stored goal."""
    try:
        result = _get_collection().get()
        return list(zip(result["ids"], result["documents"]))
    except Exception:
        return []


def sync_goals_to_chroma(goals: list[tuple[str, str]]) -> None:
    """Atomically replace all ChromaDB goals with the given list."""
    col = _get_collection()
    existing = col.get()
    if existing["ids"]:
        col.delete(ids=existing["ids"])
    if goals:
        ids, docs = zip(*goals)
        col.add(ids=list(ids), documents=list(docs))


# ══════════════════════════════════════════
# HELPERS — MEMORY INSIGHTS
# ══════════════════════════════════════════

def compute_memory_insights(df: pd.DataFrame | None) -> dict | None:
    """Summarise past decisions into a behaviour pattern dict."""
    if df is None or df.empty:
        return None
    df = df.copy()
    df["approved_bool"] = df["approved"].astype(str).str.lower() == "true"
    total     = len(df)
    approved  = df["approved_bool"].sum()
    approval_rate = int(approved / total * 100) if total else 0

    approved_df = df[df["approved_bool"]]
    if not approved_df.empty:
        liquid = approved_df["asset_recommended"].str.contains(
            "liquid|BeES|Liquid", case=False, na=False).sum()
        equity = len(approved_df) - liquid
        if liquid >= equity:
            preferred, pct = "Liquid Funds", int(liquid / len(approved_df) * 100)
        else:
            preferred, pct = "Equity / Mutual Fund", int(equity / len(approved_df) * 100)
    else:
        preferred, pct = "N/A", 0

    avg_shortfall = df["shortfall"].mean() if "shortfall" in df.columns else 0

    # Natural language pattern sentence
    if approved >= 3:
        pattern = (
            f"Based on {int(approved)} approved decisions, you preferred **{preferred}** "
            f"redemptions {pct}% of the time. "
            f"Average shortfall handled: ₹{avg_shortfall:,.0f}."
        )
    elif approved > 0:
        pattern = f"Only {int(approved)} approved decision(s) so far — keep using the system to build a stronger pattern."
    else:
        pattern = "No approved decisions yet. Approve your first recommendation to start building memory."

    return {
        "total": total,
        "approved": int(approved),
        "approval_rate": approval_rate,
        "preferred_asset": preferred,
        "preferred_pct": pct,
        "avg_shortfall": avg_shortfall,
        "pattern": pattern,
    }


# ══════════════════════════════════════════
# TABS
# ══════════════════════════════════════════
tab_run, tab_goals, tab_txn, tab_port, tab_hist = st.tabs([
    "🤖  Run Agent",
    "🎯  My Goals",
    "💳  My Transactions",
    "📈  My Portfolio",
    "📜  Decision History",
])


# ═══════════════════════════════════════════
# TAB 1 — RUN AGENT
# ═══════════════════════════════════════════
with tab_run:
    st.markdown("### 🔍 Autonomous Financial Analysis")
    st.markdown(
        "<p style='color:#94a3b8;margin-top:-0.5rem;'>The 5-agent pipeline runs fully autonomously. "
        "You only decide at the very final step.</p>", unsafe_allow_html=True)

    if not os.environ.get("GROQ_API_KEY"):
        st.markdown("""
        <div class="alert-card">
          <h4 style="color:#f87171;margin:0 0 0.4rem;">🔑 Groq API Key Required</h4>
          <p style="color:#94a3b8;margin:0;line-height:1.6;">
            Enter your key in the <strong style="color:#a78bfa;">sidebar ←</strong>, then click <em>Save Key</em>.<br>
            Free key at <a href="https://console.groq.com/keys" target="_blank" style="color:#60a5fa;">console.groq.com/keys</a>
          </p>
        </div>""", unsafe_allow_html=True)

    col_btn, _ = st.columns([1, 3])
    with col_btn:
        st.markdown('<div class="scan-btn">', unsafe_allow_html=True)
        scan_clicked = st.button(
            "🚀  Scan My Finances", key="scan_btn",
            use_container_width=True,
            disabled=not bool(os.environ.get("GROQ_API_KEY")),
        )
        st.markdown('</div>', unsafe_allow_html=True)

    if scan_clicked:
        for k in ("agent_state", "decision_made", "approved_status"):
            st.session_state.pop(k, None)

        st.markdown("---")
        st.markdown("#### ⚙️ Agent Pipeline Status")

        AGENT_LABELS = [
            ("🔍", "Monitor Agent",        "Scanning transactions & computing balance…"),
            ("💰", "Liquidity Agent",       "Evaluating redeemable assets…"),
            ("🧾", "Tax Agent",             "Identifying tax-loss harvesting opportunities…"),
            ("🧠", "Memory Agent",          "Retrieving past decision patterns…"),
            ("🤖", "Execution Agent",       "Calling Groq LLM for recommendation…"),
        ]

        def render_badges(done: list, running: int | None = None) -> str:
            """Render HTML pipeline status badges."""
            html = '<div style="display:flex;flex-direction:column;gap:0.3rem;">'
            for i, (icon, name, desc) in enumerate(AGENT_LABELS):
                if i < len(done):
                    cls, si, lbl = "badge-done", "✅", done[i]
                elif i == running:
                    cls, si, lbl = "badge-running", "⏳", desc
                else:
                    cls, si, lbl = "", "⬜", "Waiting…"
                html += (f'<div class="agent-badge {cls}">{si} {icon} '
                         f'<strong>{name}</strong>'
                         f'<span style="color:#94a3b8;font-weight:400"> — {lbl}</span></div>')
            return html + "</div>"

        placeholder = st.empty()
        done_labels: list[str] = []
        result_state = None
        error_msg = None

        try:
            import io
            import contextlib
            from milestone2_agent import (
                monitor_agent, liquidity_check_agent, tax_agent,
                memory_agent, execution_agent, WealthState,
            )

            state: WealthState = {
                "net_balance": 0.0, "total_income": 0.0, "total_spent": 0.0,
                "big_purchases": [], "alert_triggered": False, "shortfall": 0.0,
                "liquid_available": 0.0, "liquid_assets": [], "can_cover_shortfall": False,
                "loss_making_assets": [], "tlh_suggestion": "", "past_behavior_pattern": "",
                "relevant_goal": "", "goal_similarity_score": 0.0, "final_recommendation": "",
                "similar_past_decisions": [], "_portfolio_df": [],
            }

            log_capture = io.StringIO()
            with contextlib.redirect_stdout(log_capture), contextlib.redirect_stderr(log_capture):
                placeholder.markdown(render_badges([], 0), unsafe_allow_html=True)
                state = monitor_agent(state)
                done_labels.append(f"Balance ₹{state['net_balance']:,.0f} | Alert: {'YES ⚠️' if state['alert_triggered'] else 'No ✅'}")

                if not state["alert_triggered"]:
                    placeholder.markdown(render_badges(done_labels), unsafe_allow_html=True)
                    st.markdown("""
                    <div class="success-card">
                      <h4 style="color:#34d399;margin:0">✅ All Clear!</h4>
                      <p style="color:#94a3b8;margin:0.5rem 0 0;">Balance is above ₹40,000. No action needed.</p>
                    </div>""", unsafe_allow_html=True)
                    st.session_state["verbose_logs"] = log_capture.getvalue()
                    st.stop()

                placeholder.markdown(render_badges(done_labels, 1), unsafe_allow_html=True)
                state = liquidity_check_agent(state)
                done_labels.append(f"Liquid ₹{state['liquid_available']:,.0f} | Covers: {'Yes' if state['can_cover_shortfall'] else 'Partial'}")

                placeholder.markdown(render_badges(done_labels, 2), unsafe_allow_html=True)
                state = tax_agent(state)
                done_labels.append(f"Found {len(state.get('loss_making_assets',[]))} loss asset(s) for TLH")

                placeholder.markdown(render_badges(done_labels, 3), unsafe_allow_html=True)
                state = memory_agent(state)
                done_labels.append("Behaviour pattern extracted from history")

                placeholder.markdown(render_badges(done_labels, 4), unsafe_allow_html=True)
                state = execution_agent(state)
                done_labels.append("LLM recommendation generated ✨")

            placeholder.markdown(render_badges(done_labels), unsafe_allow_html=True)
            result_state = state
            # ← KEY FIX: save so the approval block (outside scan_clicked) can access it
            st.session_state["agent_state"] = result_state
            st.session_state.pop("pipeline_error", None)
            st.session_state["verbose_logs"] = log_capture.getvalue()

        except Exception as exc:
            st.session_state['pipeline_error'] = str(exc)
            st.session_state.pop("agent_state", None)

    # ── Show pipeline error ────────────────────────────────────────────────
    if st.session_state.get("pipeline_error"):
        st.error(f"❌ Pipeline error: {st.session_state['pipeline_error']}")

    # ── Recommendation + approval (OUTSIDE scan block — survives reruns) ───
    elif "agent_state" in st.session_state and not st.session_state.get("decision_made"):
        result_state = st.session_state["agent_state"]

        st.markdown("---")
        st.markdown("#### 📊 Financial Snapshot")
        c1, c2, c3, c4 = st.columns(4)
        for col_obj, label, val in [
            (c1, "Net Balance",      f"₹{result_state['net_balance']:,.0f}"),
            (c2, "Shortfall",        f"₹{result_state['shortfall']:,.0f}"),
            (c3, "Liquid Available", f"₹{result_state['liquid_available']:,.0f}"),
            (c4, "Big Purchases",    str(len(result_state.get("big_purchases", [])))),
        ]:
            col_obj.markdown(
                f'<div class="metric-card"><div class="metric-label">{label}</div>'
                f'<div class="metric-value">{val}</div></div>',
                unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("#### 🤖 Agent Recommendation")
        
        if st.session_state.get("verbose_logs"):
            with st.expander("🔍 Verbose Agent execution logs (Required)", expanded=False):
                logs_txt = st.session_state["verbose_logs"]
                if len(logs_txt) > 20000:
                    logs_txt = logs_txt[:20000] + "\n\n... [LOG TRUNCATED FOR UI RENDERING]"
                st.code(logs_txt, language="log")

        rec = result_state.get("final_recommendation", "")
        st.markdown(
            f'<div class="rec-card"><pre style="white-space:pre-wrap;font-family:Inter,sans-serif;'
            f'color:#e2e8f0;font-size:0.93rem;line-height:1.75;margin:0;">{rec}</pre></div>',
            unsafe_allow_html=True)

        st.markdown("#### 🔔 Your Decision")
        st.markdown(
            "<p style='color:#94a3b8;margin-top:-0.5rem;font-size:0.88rem;'>"
            "Approve or reject — then <strong style='color:#a78bfa;'>tell the AI why</strong>. "
            "Your reasoning is stored and makes future suggestions smarter.</p>",
            unsafe_allow_html=True)

        if not st.session_state.get("decision_pending"):
            cy, cn, cl = st.columns(3)
            with cy:
                if st.button("✅  Approve", key="approve_btn", use_container_width=True):
                    st.session_state["decision_pending"] = "approved"
                    st.rerun()
            with cn:
                if st.button("❌  Reject", key="reject_btn", use_container_width=True):
                    st.session_state["decision_pending"] = "rejected"
                    st.rerun()
            with cl:
                if st.button("🕐  Decide Later", key="later_btn", use_container_width=True):
                    st.session_state["decision_pending"] = "deferred"
                    st.rerun()

        if st.session_state.get("decision_pending") and not st.session_state.get("decision_made"):
            pending = st.session_state["decision_pending"]
            icons  = {"approved": "✅", "rejected": "❌", "deferred": "🕐"}
            colors = {"approved": "#34d399", "rejected": "#f87171", "deferred": "#fbbf24"}
            icon, clr = icons[pending], colors[pending]
            st.markdown(
                f'<div style="background:rgba(167,139,250,0.08);border:1px solid '
                f'rgba(167,139,250,0.3);border-radius:14px;padding:1.3rem 1.5rem;margin-top:.8rem;">'
                f'<h4 style="color:#a78bfa;margin:0 0 .4rem;">💬 Tell the AI Why You {pending.title()}d</h4>'
                f'<p style="color:#94a3b8;font-size:.83rem;margin:0 0 .5rem;">This is the most '
                f'valuable signal you can give. The AI will recall your reasoning next time '
                f'a similar situation arises.</p>'
                '<p style="color:#64748b;font-size:.78rem;font-style:italic;margin:0;">Example: &quot;Bharati chart looks bullish, sell Titan instead&quot; or &quot;Emergency fund first, cannot touch investments now&quot;</p>'
                f'</div>',
                unsafe_allow_html=True)
            user_rationale = st.text_area(
                label="Your reasoning",
                placeholder="Explain your thinking here...",
                height=90,
                key="rationale_input",
                label_visibility="collapsed",
            )
            c_confirm, c_skip = st.columns([2, 1])
            with c_confirm:
                if st.button(
                    f"{icon} Confirm {pending.title()} & Save Reasoning to AI Memory",
                    key="confirm_btn", use_container_width=True
                ):
                    approved_bool = (pending == "approved")
                    note = user_rationale.strip() or f"{pending.title()}d via dashboard"
                    log_decision_from_ui(result_state, approved_bool, note)
                    st.session_state.update({
                        "decision_made": True, "approved_status": pending,
                        "saved_rationale": user_rationale.strip(),
                    })
                    st.session_state.pop("decision_pending", None)
                    st.rerun()
            with c_skip:
                if st.button("Skip", key="skip_btn", use_container_width=True):
                    approved_bool = (pending == "approved")
                    log_decision_from_ui(
                        result_state, approved_bool,
                        f"{pending.title()}d via dashboard (no explanation)")
                    st.session_state.update({"decision_made": True, "approved_status": pending})
                    st.session_state.pop("decision_pending", None)
                    st.rerun()

    # ── Decision confirmation ───────────────────────────────────────────────
    if st.session_state.get("decision_made"):
        status = st.session_state.get("approved_status", "")
        msgs = {
            "approved": (
                '<div class="success-card"><h4 style="color:#34d399;margin:0">✅ Approved & Logged</h4>'
                '<p style="color:#94a3b8;margin:.4rem 0 0;">Decision saved. '
                'The Memory Agent will use this to improve future suggestions. '
                'Check the Decision History tab.</p></div>'
            ),
            "rejected": (
                '<div class="alert-card"><h4 style="color:#f87171;margin:0">❌ Rejected & Logged</h4>'
                '<p style="color:#94a3b8;margin:.4rem 0 0;">'
                'Rejection noted — the agent will factor this in next time.</p></div>'
            ),
            "deferred": (
                '<div class="glass-card"><h4 style="color:#fbbf24;margin:0">🕐 Deferred</h4>'
                '<p style="color:#94a3b8;margin:.4rem 0 0;">'
                'Marked for later. Scan again anytime to revisit.</p></div>'
            ),
        }
        st.markdown(msgs.get(status, ""), unsafe_allow_html=True)
        saved = st.session_state.get("saved_rationale", "")
        if saved:
            st.markdown(
                f'<div style="background:rgba(167,139,250,0.08);border:1px solid '
                f'rgba(167,139,250,0.2);border-radius:10px;padding:.8rem 1.2rem;margin-top:.5rem;">'
                f'<span style="color:#a78bfa;font-size:.8rem;font-weight:600;">'
                f'💬 Your reasoning stored in AI memory:</span>'
                f'<p style="color:#e2e8f0;font-size:.88rem;margin:.35rem 0 0;line-height:1.6;">{saved}</p>'
                f'</div>',
                unsafe_allow_html=True)




# ═══════════════════════════════════════════
# TAB 2 — MY GOALS
# ═══════════════════════════════════════════
with tab_goals:
    st.markdown("### 🎯 My Financial Goals")
    st.markdown(
        "<p style='color:#94a3b8;margin-top:-0.5rem;'>"
        "These goals are stored in AI memory (ChromaDB). The Execution Agent semantically searches them "
        "every time it builds a recommendation. Edit freely — changes sync instantly.</p>",
        unsafe_allow_html=True)

    # Load goals into session state only on first render or after a save
    if "goals" not in st.session_state or st.session_state.get("goals_reload"):
        with st.spinner("Loading goals from AI memory…"):
            st.session_state["goals"] = get_all_goals()   # [(id, text), ...]
        st.session_state["goals_reload"] = False

    goals: list[tuple[str, str]] = st.session_state["goals"]

    if not goals:
        st.markdown(
            '<div class="glass-card" style="text-align:center;padding:2rem;">'
            '<div style="font-size:2.5rem;">🎯</div>'
            '<h3 style="color:#f1f5f9;margin:.4rem 0;">No Goals Yet</h3>'
            '<p style="color:#94a3b8;">Add your first financial goal below.</p></div>',
            unsafe_allow_html=True)

    # Render each goal as an editable text area + delete button
    updated_goals: list[tuple[str, str]] = []
    for idx, (gid, gtext) in enumerate(goals):
        col_text, col_del = st.columns([11, 1])
        with col_text:
            new_text = st.text_area(
                f"Goal {idx+1}", value=gtext, height=80,
                key=f"goal_text_{gid}", label_visibility="collapsed")
            updated_goals.append((gid, new_text.strip()))
        with col_del:
            st.markdown("<div style='height:1.6rem'></div>", unsafe_allow_html=True)
            if st.button("🗑️", key=f"del_goal_{gid}", help="Delete this goal"):
                st.session_state["goals"] = [(i, t) for i, t in goals if i != gid]
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    col_add, col_save, col_spacer = st.columns([2, 2, 4])

    with col_add:
        if st.button("➕  Add New Goal", use_container_width=True, key="add_goal_btn"):
            new_id = f"goal_{uuid.uuid4().hex[:8]}"
            st.session_state["goals"] = goals + [(new_id, "")]
            st.rerun()

    with col_save:
        if st.button("💾  Sync to AI Memory", use_container_width=True, key="save_goals_btn",
                     type="primary"):
            valid = [(gid, txt) for gid, txt in updated_goals if txt]
            if not valid:
                st.error("Add at least one goal before saving.")
            else:
                with st.spinner("Syncing to ChromaDB…"):
                    try:
                        sync_goals_to_chroma(valid)
                        st.session_state["goals"] = valid
                        st.session_state["goals_reload"] = True
                        st.success(f"✅ {len(valid)} goal(s) synced to AI memory!")
                    except Exception as e:
                        st.error(f"Sync failed: {e}")

    st.markdown("---")
    st.markdown(
        f"<p style='color:#64748b;font-size:0.82rem;'>💡 <strong style='color:#94a3b8;'>{len(goals)} goal(s)</strong> "
        f"currently in AI memory · Last saved to: <code style='color:#a78bfa;'>{MEMORY_PATH}</code></p>",
        unsafe_allow_html=True)


# ═══════════════════════════════════════════
# TAB 3 — MY TRANSACTIONS
# ═══════════════════════════════════════════
with tab_txn:
    st.markdown("### 💳 My Transactions")
    st.markdown(
        "<p style='color:#94a3b8;margin-top:-0.5rem;'>"
        "Edit, add or delete rows inline. Upload a CSV to replace all data. "
        "Click <em>Save Changes</em> — the agent uses this data on every scan.</p>",
        unsafe_allow_html=True)

    # File uploader
    uploaded_txn = st.file_uploader(
        "Upload transactions CSV (optional — replaces current data)",
        type=["csv"], key="txn_upload")
    if uploaded_txn:
        df_uploaded = pd.read_csv(uploaded_txn)
        save_csv(df_uploaded, TRANSACTIONS_PATH)
        st.success("✅ Uploaded and saved!")

    # Load current data
    TXN_COLS = ["date", "description", "amount", "category"]
    df_txn = load_csv(TRANSACTIONS_PATH, TXN_COLS)
    if "date" in df_txn.columns:
        df_txn["date"] = pd.to_datetime(df_txn["date"], errors="coerce").dt.strftime("%Y-%m-%d")

    st.markdown("#### ✏️ Edit Transactions")

    edited_txn = st.data_editor(
        df_txn,
        num_rows="dynamic",
        use_container_width=True,
        height=360,
        column_config={
            "date":        st.column_config.TextColumn("Date (YYYY-MM-DD)"),
            "description": st.column_config.TextColumn("Description", width="large"),
            "amount":      st.column_config.NumberColumn("Amount (₹)", format="%.2f",
                                                          help="Negative = expense, Positive = income"),
            "category":    st.column_config.SelectboxColumn("Category", options=CATEGORIES),
        },
        key="txn_editor",
    )

    col_save_txn, col_reset_txn, _ = st.columns([2, 2, 4])
    with col_save_txn:
        if st.button("💾  Save Changes", key="save_txn", use_container_width=True, type="primary"):
            save_csv(edited_txn, TRANSACTIONS_PATH)
            st.success("✅ Transactions saved!")

    with col_reset_txn:
        if st.button("↩️  Reset to Default", key="reset_txn", use_container_width=True):
            default = {
                "date":        ["2026-04-01","2026-04-02","2026-04-03","2026-04-05",
                                "2026-04-06","2026-04-07","2026-04-09","2026-04-10",
                                "2026-04-11","2026-04-13","2026-04-14","2026-04-15",
                                "2026-04-16","2026-04-16","2026-04-16"],
                "description": ["Salary Credit - TCS Ltd","Rent Payment - Sobha Apartments",
                                "Swiggy - Dinner Order","Zomato - Lunch",
                                "BESCOM Electricity Bill","Zepto - Grocery Delivery",
                                "Myntra - Summer Clothing","Swiggy - Weekend Brunch",
                                "New Balance Sneakers - Nykaa Fashion","Zomato - Pizza Night",
                                "Netflix Subscription","Swiggy Instamart - Essentials",
                                "Airtel Postpaid Bill","Amazon Prime Annual","Zepto - Weekend Supplies"],
                "amount":      [60000,-15000,-650,-480,-2200,-1350,-3800,-890,-6500,-720,-649,-980,-599,-1499,-1250],
                "category":    ["Income","Housing","Food","Food","Utilities","Food","Shopping",
                                "Food","Shopping","Food","Entertainment","Food","Utilities",
                                "Entertainment","Food"],
            }
            df_def = pd.DataFrame(default)
            save_csv(df_def, TRANSACTIONS_PATH)
            st.success("✅ Reset to default mock data!")
            st.rerun()

    # Live summary
    st.markdown("---")
    st.markdown("#### 📊 Live Summary")
    income  = edited_txn[edited_txn["amount"] > 0]["amount"].sum() if "amount" in edited_txn.columns else 0
    expense = abs(edited_txn[edited_txn["amount"] < 0]["amount"].sum()) if "amount" in edited_txn.columns else 0
    balance = income - expense
    cs1, cs2, cs3, cs4 = st.columns(4)
    bal_class = "profit" if balance >= 40000 else "loss"
    for col_obj, lbl, val, cls in [
        (cs1, "Total Income",  f"₹{income:,.0f}",  "profit"),
        (cs2, "Total Spent",   f"₹{expense:,.0f}", "loss"),
        (cs3, "Net Balance",   f"₹{balance:,.0f}", bal_class),
        (cs4, "Rows",          str(len(edited_txn)), ""),
    ]:
        col_obj.markdown(
            f'<div class="metric-card"><div class="metric-label">{lbl}</div>'
            f'<div class="metric-value {cls}">{val}</div></div>',
            unsafe_allow_html=True)
    if balance < 40000:
        st.markdown(
            f'<div class="alert-card" style="margin-top:0.5rem;">'
            f'⚠️ <strong style="color:#f87171;">Balance below ₹40,000</strong> — '
            f'shortfall of <strong style="color:#f87171;">₹{40000-balance:,.0f}</strong>. '
            f'Scanning finances will trigger the agent pipeline.</div>',
            unsafe_allow_html=True)
    else:
        st.markdown(
            '<div class="success-card" style="margin-top:0.5rem;">'
            '✅ <strong style="color:#34d399;">Balance is healthy</strong> — '
            'above the ₹40,000 alert threshold.</div>',
            unsafe_allow_html=True)


# ═══════════════════════════════════════════
# TAB 4 — MY PORTFOLIO
# ═══════════════════════════════════════════
with tab_port:
    st.markdown("### 📈 My Portfolio")
    st.markdown(
        "<p style='color:#94a3b8;margin-top:-0.5rem;'>"
        "Edit holdings inline or upload a CSV. The Tax Agent uses this data to find "
        "tax-loss harvesting opportunities.</p>", unsafe_allow_html=True)

    uploaded_port = st.file_uploader(
        "Upload portfolio CSV (optional — replaces current data)",
        type=["csv"], key="port_upload")
    if uploaded_port:
        df_up = pd.read_csv(uploaded_port)
        save_csv(df_up, PORTFOLIO_PATH)
        st.success("✅ Uploaded and saved!")

    PORT_COLS = ["asset", "type", "units", "current_price", "buy_price"]
    df_port = load_csv(PORTFOLIO_PATH, PORT_COLS)

    st.markdown("#### ✏️ Edit Holdings")
    edited_port = st.data_editor(
        df_port,
        num_rows="dynamic",
        use_container_width=True,
        height=260,
        column_config={
            "asset":         st.column_config.TextColumn("Asset Name"),
            "type":          st.column_config.SelectboxColumn("Type", options=ASSET_TYPES),
            "units":         st.column_config.NumberColumn("Units", format="%.2f"),
            "current_price": st.column_config.NumberColumn("Current Price (₹)", format="%.2f"),
            "buy_price":     st.column_config.NumberColumn("Buy Price (₹)", format="%.2f"),
        },
        key="port_editor",
    )

    col_sp1, col_sp2, _ = st.columns([2, 2, 4])
    with col_sp1:
        if st.button("💾  Save Changes", key="save_port", use_container_width=True, type="primary"):
            save_csv(edited_port, PORTFOLIO_PATH)
            st.success("✅ Portfolio saved!")
    with col_sp2:
        if st.button("↩️  Reset to Default", key="reset_port", use_container_width=True):
            default_port = pd.DataFrame({
                "asset":         ["Nifty BeES","HDFC Liquid Fund","Reliance Industries","Bharti Airtel","HDFC Flexi Cap Fund"],
                "type":          ["liquid_fund","liquid_fund","equity","equity","mutual_fund"],
                "units":         [150, 1200, 25, 80, 500],
                "current_price": [225.50, 1420.75, 2980.00, 1150.00, 98.30],
                "buy_price":     [210.00, 1380.00, 2100.00, 1300.00, 85.00],
            })
            save_csv(default_port, PORTFOLIO_PATH)
            st.success("✅ Reset to default mock portfolio!")
            st.rerun()

    # Analytics
    st.markdown("---")
    st.markdown("#### 📊 Portfolio Analytics")
    if not edited_port.empty and all(c in edited_port.columns for c in ["units","current_price","buy_price"]):
        ep = edited_port.copy()
        ep["current_value"] = ep["units"] * ep["current_price"]
        ep["unrealized_pnl"] = (ep["current_price"] - ep["buy_price"]) * ep["units"]
        ep["pnl_pct"] = ((ep["current_price"] - ep["buy_price"]) / ep["buy_price"].replace(0,1)) * 100

        total_invested = (ep["buy_price"] * ep["units"]).sum()
        total_current  = ep["current_value"].sum()
        total_pnl      = total_current - total_invested
        total_pct      = (total_pnl / total_invested * 100) if total_invested else 0
        pnl_cls        = "profit" if total_pnl >= 0 else "loss"
        sign           = "+" if total_pnl >= 0 else ""

        pa1, pa2, pa3, pa4 = st.columns(4)
        for col_obj, lbl, val, cls in [
            (pa1, "Portfolio Value", f"₹{total_current:,.0f}", ""),
            (pa2, "Total Invested",  f"₹{total_invested:,.0f}", ""),
            (pa3, "Unrealized P&L",  f"{sign}₹{total_pnl:,.0f}", pnl_cls),
            (pa4, "Overall Return",  f"{sign}{total_pct:.1f}%", pnl_cls),
        ]:
            col_obj.markdown(
                f'<div class="metric-card"><div class="metric-label">{lbl}</div>'
                f'<div class="metric-value {cls}">{val}</div></div>',
                unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        for _, row in ep.iterrows():
            pnl  = row.get("unrealized_pnl", 0)
            pct  = row.get("pnl_pct", 0)
            clr  = "#34d399" if pnl >= 0 else "#f87171"
            sg   = "+" if pnl >= 0 else ""
            atype = str(row.get("type","")).replace("_"," ").title()
            st.markdown(
                f'<div class="glass-card" style="margin:.35rem 0;padding:.9rem 1.4rem;">'
                f'<div style="display:flex;justify-content:space-between;align-items:center;">'
                f'<div><span style="color:#f1f5f9;font-weight:600;font-size:1rem;">{row.get("asset","")}</span>'
                f'<span style="color:#94a3b8;font-size:0.78rem;margin-left:.8rem;">{atype} · {row.get("units",0):.0f} units</span></div>'
                f'<div style="text-align:right;">'
                f'<div style="color:#f1f5f9;font-weight:600;">₹{row.get("current_value",0):,.0f}</div>'
                f'<div style="color:{clr};font-size:0.83rem;font-weight:600;">{sg}₹{pnl:,.0f} ({sg}{pct:.1f}%)</div>'
                f'</div></div></div>',
                unsafe_allow_html=True)


# ═══════════════════════════════════════════
# TAB 5 — DECISION HISTORY
# ═══════════════════════════════════════════
with tab_hist:
    st.markdown("### 📜 Decision History & Memory Insights")

    df_log = load_decisions()
    insights = compute_memory_insights(df_log)

    # ── Memory Insights Card ──
    if insights:
        st.markdown(
            f'<div class="insight-card">'
            f'<h4 style="color:#a78bfa;margin:0 0 1rem 0;">🧠 What the AI Has Learned About You</h4>'
            f'<p style="color:#e2e8f0;line-height:1.8;margin:0 0 1.2rem 0;">{insights["pattern"]}</p>'
            f'<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:0.8rem;">'
            f'<div style="background:rgba(255,255,255,0.05);border-radius:10px;padding:.8rem;text-align:center;">'
            f'<div style="color:#94a3b8;font-size:0.72rem;text-transform:uppercase;letter-spacing:.06em;">Total Decisions</div>'
            f'<div style="color:#f1f5f9;font-size:1.4rem;font-weight:700;">{insights["total"]}</div></div>'
            f'<div style="background:rgba(255,255,255,0.05);border-radius:10px;padding:.8rem;text-align:center;">'
            f'<div style="color:#94a3b8;font-size:0.72rem;text-transform:uppercase;letter-spacing:.06em;">Approved</div>'
            f'<div style="color:#34d399;font-size:1.4rem;font-weight:700;">{insights["approved"]}</div></div>'
            f'<div style="background:rgba(255,255,255,0.05);border-radius:10px;padding:.8rem;text-align:center;">'
            f'<div style="color:#94a3b8;font-size:0.72rem;text-transform:uppercase;letter-spacing:.06em;">Approval Rate</div>'
            f'<div style="color:#60a5fa;font-size:1.4rem;font-weight:700;">{insights["approval_rate"]}%</div></div>'
            f'<div style="background:rgba(255,255,255,0.05);border-radius:10px;padding:.8rem;text-align:center;">'
            f'<div style="color:#94a3b8;font-size:0.72rem;text-transform:uppercase;letter-spacing:.06em;">Preferred Asset</div>'
            f'<div style="color:#fbbf24;font-size:1rem;font-weight:700;margin-top:.2rem;">{insights["preferred_asset"]}</div></div>'
            f'</div></div>',
            unsafe_allow_html=True)
    else:
        st.markdown(
            '<div class="glass-card" style="text-align:center;padding:2rem;">'
            '<div style="font-size:2.5rem;">🧠</div>'
            '<h3 style="color:#f1f5f9;margin:.4rem 0;">No Memory Yet</h3>'
            '<p style="color:#94a3b8;">Run the agent and approve or reject a recommendation.<br>'
            'Every decision teaches the AI your financial preferences.</p></div>',
            unsafe_allow_html=True)

    if df_log is None or df_log.empty:
        st.markdown(
            '<div class="glass-card" style="text-align:center;padding:2rem;margin-top:1rem;">'
            '<p style="color:#94a3b8;">No decision records found.</p></div>',
            unsafe_allow_html=True)
    else:
        st.markdown("---")
        col_flt, col_cnt = st.columns([2, 1])
        with col_flt:
            flt = st.selectbox("Filter:", ["All", "Approved ✅", "Rejected ❌"], key="hist_filter")
        with col_cnt:
            st.markdown(
                f'<div class="metric-card" style="margin-top:1.6rem;">'
                f'<div class="metric-label">Records</div>'
                f'<div class="metric-value">{len(df_log)}</div></div>',
                unsafe_allow_html=True)

        filtered = df_log.copy()
        filtered["approved"] = filtered["approved"].astype(str).str.lower()
        if flt == "Approved ✅":
            filtered = filtered[filtered["approved"] == "true"]
        elif flt == "Rejected ❌":
            filtered = filtered[filtered["approved"] != "true"]

        if filtered.empty:
            st.info("No records match the filter.")
        else:
            # Styled table
            def style_approved(val):
                """Colour-code the approved column."""
                return "color:#34d399;font-weight:600;" if str(val).lower()=="true" else "color:#f87171;font-weight:600;"

            display_cols = [c for c in DECISIONS_LOG_HEADER if c in filtered.columns]
            styled = (
                filtered[display_cols]
                .sort_values("timestamp", ascending=False)
                .style
                .map(style_approved, subset=["approved"])
                .format({"balance": "₹{:,.0f}", "shortfall": "₹{:,.0f}"})
            )
            st.dataframe(styled, use_container_width=True)

            # Decision cards (newest 5)
            st.markdown("---")
            st.markdown("#### 🗃️ Recent Decisions")
            for _, row in filtered.sort_values("timestamp", ascending=False).head(5).iterrows():
                ok = str(row.get("approved","")).lower() == "true"
                bg  = "rgba(52,211,153,0.07)" if ok else "rgba(248,113,113,0.07)"
                bdr = "rgba(52,211,153,0.3)"  if ok else "rgba(248,113,113,0.3)"
                badge = "✅ Approved" if ok else "❌ Rejected"
                bcol  = "#34d399" if ok else "#f87171"
                note_html = ""
                if str(row.get("user_note","")).strip():
                    note_html = (f'<p style="color:#94a3b8;font-style:italic;'
                                 f'margin:.3rem 0 0;font-size:0.83rem;">Note: {row["user_note"]}</p>')
                st.markdown(
                    f'<div style="background:{bg};border:1px solid {bdr};border-radius:12px;'
                    f'padding:1.1rem 1.4rem;margin:.45rem 0;">'
                    f'<div style="display:flex;justify-content:space-between;align-items:flex-start;">'
                    f'<div><span style="color:{bcol};font-weight:700;">{badge}</span>'
                    f'<span style="color:#64748b;font-size:0.78rem;margin-left:.8rem;">{str(row.get("timestamp",""))[:19]}</span></div>'
                    f'<div style="text-align:right;">'
                    f'<div style="color:#f1f5f9;font-size:0.83rem;">Balance: ₹{float(row.get("balance",0)):,.0f}</div>'
                    f'<div style="color:#f87171;font-size:0.83rem;">Shortfall: ₹{float(row.get("shortfall",0)):,.0f}</div>'
                    f'</div></div>'
                    f'<div style="margin-top:.6rem;">'
                    f'<span style="color:#a78bfa;font-weight:600;font-size:0.82rem;">Asset: </span>'
                    f'<span style="color:#e2e8f0;font-size:0.82rem;">{row.get("asset_recommended","—")}</span></div>'
                    f'<p style="color:#cbd5e1;font-size:0.82rem;margin:.4rem 0 0;line-height:1.55;">'
                    f'{str(row.get("action_taken",""))[:280]}…</p>{note_html}</div>',
                    unsafe_allow_html=True)

