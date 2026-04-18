import streamlit as st
import pandas as pd
import json
import plotly.graph_objects as go
from datetime import datetime

# ── PURPOSE ───────────────────────────────────────────────────────────────────
# Dashboard reads agent_results.json produced by agent.py.
# It does NO analysis itself — it only visualises what the agent computed.
# Run order: generate_data.py → agent.py → dashboard.py
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="User NonChurn AI",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=DM+Mono:wght@400;500&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp { background: #f5f7fa; color: #1a1d23; }
section[data-testid="stSidebar"] { background: #ffffff !important; border-right: 1px solid #e8ecf0; }
section[data-testid="stSidebar"] * { color: #1a1d23 !important; }
.block-container { padding: 2rem 2.5rem !important; max-width: 1400px !important; }
.metric-card { background:#ffffff; border:1px solid #e8ecf0; border-radius:14px; padding:22px 24px 18px; position:relative; overflow:hidden; box-shadow:0 1px 4px rgba(0,0,0,0.06); min-height:110px; }
.metric-card::after { content:''; position:absolute; bottom:0; left:0; right:0; height:3px; border-radius:0 0 14px 14px; }
.metric-card.green::after { background:#10b981; }
.metric-card.amber::after { background:#f59e0b; }
.metric-card.red::after   { background:#ef4444; }
.metric-card.blue::after  { background:#3b82f6; }
.metric-label { font-size:11px; font-weight:600; letter-spacing:0.08em; text-transform:uppercase; color:#9ca3af; margin-bottom:10px; font-family:'DM Mono',monospace; }
.metric-value { font-size:34px; font-weight:700; line-height:1; margin-bottom:6px; color:#1a1d23; }
.metric-value.green { color:#10b981; }
.metric-value.amber { color:#f59e0b; }
.metric-value.red   { color:#ef4444; }
.metric-value.blue  { color:#3b82f6; }
.metric-sub { font-size:12px; color:#9ca3af; font-family:'DM Mono',monospace; }
.aha-banner { background:#f0fdf4; border:1px solid #bbf7d0; border-left:4px solid #10b981; border-radius:12px; padding:18px 22px; margin:20px 0; }
.aha-title { font-size:11px; font-weight:600; letter-spacing:0.08em; text-transform:uppercase; color:#10b981; margin-bottom:6px; font-family:'DM Mono',monospace; }
.aha-text { font-size:15px; font-weight:600; color:#064e3b; line-height:1.5; }
.aha-metrics-row { display:flex; gap:0; margin-top:14px; border:1px solid #bbf7d0; border-radius:10px; overflow:hidden; }
.aha-metric-box { flex:1; padding:12px 16px; background:#ffffff; border-right:1px solid #bbf7d0; }
.aha-metric-box:last-child { border-right:none; }
.aha-metric-val { font-size:22px; font-weight:700; color:#065f46; font-family:'DM Mono',monospace; }
.aha-metric-lbl { font-size:11px; color:#10b981; font-weight:600; text-transform:uppercase; letter-spacing:0.06em; margin-bottom:2px; }
.aha-metric-def { font-size:11px; color:#6b7280; margin-top:3px; line-height:1.4; }
.section-header { font-size:11px; font-weight:600; letter-spacing:0.1em; text-transform:uppercase; color:#9ca3af; margin:0 0 16px; font-family:'DM Mono',monospace; padding-bottom:10px; border-bottom:1px solid #f3f4f6; }
.corr-bar-container { margin:10px 0; }
.corr-bar-label { display:flex; justify-content:space-between; font-size:13px; margin-bottom:5px; color:#374151; }
.corr-bar-label span:last-child { font-family:'DM Mono',monospace; font-size:12px; font-weight:600; }
.corr-bar-track { height:8px; background:#f3f4f6; border-radius:4px; overflow:hidden; }
.corr-bar-fill  { height:100%; border-radius:4px; }
.seg-badge { display:inline-block; font-size:11px; font-weight:600; padding:3px 11px; border-radius:20px; font-family:'DM Mono',monospace; }
.seg-high  { background:#d1fae5; color:#065f46; }
.seg-risk  { background:#fef3c7; color:#92400e; }
.seg-churn { background:#fee2e2; color:#991b1b; }
div[data-testid="stDataFrame"] { border-radius:12px; overflow:hidden; border:1px solid #e8ecf0; }
h1 { font-size:26px !important; font-weight:700 !important; color:#1a1d23 !important; margin-bottom:2px !important; }
h2, h3 { color:#1a1d23 !important; }
.stMarkdown p { color:#6b7280; font-size:14px; }
hr { border-color:#e8ecf0; margin:24px 0; }
div[data-testid="stSelectbox"] label, div[data-testid="stMultiSelect"] label { font-size:12px !important; font-weight:600 !important; color:#6b7280 !important; text-transform:uppercase; letter-spacing:0.06em; }
.timeline-box { background:#ffffff; border:1px solid #e8ecf0; border-radius:14px; padding:18px 22px; margin-top:14px; box-shadow:0 1px 4px rgba(0,0,0,0.04); }
.timeline-title { font-size:11px; font-weight:600; color:#9ca3af; text-transform:uppercase; letter-spacing:0.08em; font-family:'DM Mono',monospace; margin-bottom:14px; padding-bottom:10px; border-bottom:1px solid #f3f4f6; }
.sidebar-section { font-size:11px; font-weight:600; color:#9ca3af; text-transform:uppercase; letter-spacing:0.08em; font-family:'DM Mono',monospace; margin:16px 0 8px; }
.info-pill { display:inline-block; background:#eff6ff; color:#1d4ed8; font-size:11px; font-weight:600; padding:3px 10px; border-radius:20px; font-family:'DM Mono',monospace; margin-bottom:8px; }
</style>
""", unsafe_allow_html=True)


# ── LOAD AGENT RESULTS ────────────────────────────────────────────────────────
@st.cache_data
def load_results():
    try:
        with open("agent_results.json") as f:
            return json.load(f)
    except FileNotFoundError:
        return None

results = load_results()

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚡ User NonChurn AI")
    st.markdown("<p style='font-size:13px;color:#6b7280;margin-top:-8px;'>Activation Signal Intelligence</p>", unsafe_allow_html=True)
    st.markdown("---")
    if results:
        s = results["summary"]
        sig = results["activation_signal"]
        st.markdown('<div class="sidebar-section">Dataset</div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div style='font-size:13px;color:#374151;line-height:2.2;'>
        <span style='color:#9ca3af;font-size:11px;font-family:"DM Mono",monospace;'>USERS</span><br>
        <span style='font-size:22px;font-weight:700;color:#1a1d23;'>{s['total_users']}</span><br>
        <span style='color:#9ca3af;font-size:11px;font-family:"DM Mono",monospace;'>EVENTS</span><br>
        <span style='font-size:22px;font-weight:700;color:#1a1d23;'>{s['total_events']}</span>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("---")
        st.markdown('<div class="sidebar-section">Segment summary</div>', unsafe_allow_html=True)
        segs = [
            ("High activation", s['n_high'],  "#10b981", "#d1fae5"),
            ("At risk",         s['n_risk'],   "#f59e0b", "#fef3c7"),
            ("Likely churned",  s['n_churn'],  "#ef4444", "#fee2e2"),
        ]
        for seg_name, cnt, color, bg in segs:
            pct = round(cnt / s['total_users'] * 100) if s['total_users'] else 0
            st.markdown(f"""
            <div style='background:{bg};border-radius:10px;padding:10px 14px;margin-bottom:8px;'>
              <div style='font-size:11px;font-weight:600;color:{color};font-family:"DM Mono",monospace;text-transform:uppercase;letter-spacing:0.06em;'>{seg_name}</div>
              <div style='font-size:20px;font-weight:700;color:{color};'>{cnt} <span style='font-size:13px;font-weight:500;'>users · {pct}%</span></div>
            </div>""", unsafe_allow_html=True)
        st.markdown("---")
        st.markdown('<div class="sidebar-section">Top signal</div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div style='background:#f0fdf4;border-radius:10px;padding:10px 14px;'>
          <div style='font-size:11px;color:#10b981;font-weight:600;font-family:"DM Mono",monospace;text-transform:uppercase;'>Feature</div>
          <div style='font-size:14px;font-weight:600;color:#065f46;margin:2px 0 8px;'>Collab Within 48h</div>
          <div style='font-size:11px;color:#10b981;font-weight:600;font-family:"DM Mono",monospace;text-transform:uppercase;'>Pearson r</div>
          <div style='font-size:20px;font-weight:700;color:#065f46;'>{sig['top_r']}</div>
        </div>""", unsafe_allow_html=True)

# ── GUARD: check results file exists ─────────────────────────────────────────
if results is None:
    st.error("agent_results.json not found. Please run `python agent.py` first.")
    st.stop()

# ── UNPACK RESULTS ────────────────────────────────────────────────────────────
summary  = results["summary"]
signal   = results["activation_signal"]
corrs    = results["correlations"]
users    = results["users"]

n_total = summary["total_users"]
n_high  = summary["n_high"]
n_risk  = summary["n_risk"]
n_churn = summary["n_churn"]

top_feat = results.get("top_correlation", {}).get("feature", signal["top_feature"])
top_r    = results.get("top_correlation", {}).get("r", signal["top_r"])
signal_feat = signal["top_feature"]
signal_r    = signal["top_r"]
rt_pct   = f"{signal['retention_hit']:.0%}"
rm_pct   = f"{signal['retention_miss']:.0%}"
lift_val = f"{signal['lift']}×" if signal["lift"] else "∞×"

df_users = pd.DataFrame([
    {k: v for k, v in u.items() if k != "daily_scores"}
    for u in users
])

# ── MAIN UI ───────────────────────────────────────────────────────────────────
st.markdown("# User NonChurn AI")
st.markdown(f"*{n_total} users · {summary['total_events']} events · segmented by agent*")

# KPI cards
c1, c2, c3, c4 = st.columns(4)
with c1:
    pct_act = round(n_high / n_total * 100) if n_total else 0
    st.markdown(f"""<div class="metric-card green">
    <div class="metric-label">Activated</div>
    <div class="metric-value green">{n_high}</div>
    <div class="metric-sub">score ≥ 0.65 · {pct_act}% of cohort</div>
    </div>""", unsafe_allow_html=True)
with c2:
    pct_risk = round(n_risk / n_total * 100) if n_total else 0
    st.markdown(f"""<div class="metric-card amber">
    <div class="metric-label">At risk</div>
    <div class="metric-value amber">{n_risk}</div>
    <div class="metric-sub">score 0.30–0.65 · {pct_risk}% of cohort</div>
    </div>""", unsafe_allow_html=True)
with c3:
    pct_churn = round(n_churn / n_total * 100) if n_total else 0
    st.markdown(f"""<div class="metric-card red">
    <div class="metric-label">Likely churned</div>
    <div class="metric-value red">{n_churn}</div>
    <div class="metric-sub">score &lt; 0.30 · {pct_churn}% of cohort</div>
    </div>""", unsafe_allow_html=True)
with c4:
    st.markdown(f"""<div class="metric-card blue">
    <div class="metric-label">Top correlation</div>
    <div class="metric-value blue">r={top_r:.2f}</div>
    <div class="metric-sub">{top_feat.replace("_"," ")}</div>
    </div>""", unsafe_allow_html=True)
# ── ACTIVATION SIGNAL BANNER ──────────────────────────────────────────────────
st.markdown(f"""<div class="aha-banner">
<div class="aha-title">⚡ Activation Signal Detected</div>
<div class="aha-text">{signal['description']}</div>
<div style="font-size:12px;color:#6b7280;margin-top:4px;font-family:'DM Mono',monospace;">
  Activation signal: <b>{signal_feat.replace("_"," ")}</b> · Pearson r = {signal_r} &nbsp;|&nbsp; Top corr. feature: <b>{top_feat.replace("_"," ")}</b> (r={top_r})
</div>
<div class="aha-metrics-row">
  <div class="aha-metric-box">
    <div class="aha-metric-lbl">Retention if triggered</div>
    <div class="aha-metric-val">{rt_pct}</div>
    <div class="aha-metric-def">% of users who hit the activation signal and returned in weeks 2–4. Higher = stronger signal.</div>
  </div>
  <div class="aha-metric-box">
    <div class="aha-metric-lbl">Retention if missed</div>
    <div class="aha-metric-val">{rm_pct}</div>
    <div class="aha-metric-def">% of users who never hit the signal but still returned. Lower = more exclusive signal.</div>
  </div>
  <div class="aha-metric-box">
    <div class="aha-metric-lbl">Lift</div>
    <div class="aha-metric-val">{lift_val}</div>
    <div class="aha-metric-def">How many times more likely a signal-hit user retains vs a miss. ∞ means zero miss-users retained.</div>
  </div>
  <div class="aha-metric-box">
    <div class="aha-metric-lbl">Correlation (r)</div>
    <div class="aha-metric-val">{signal_r}</div>
    <div class="aha-metric-def">Pearson r between this feature and retention. Range −1 to +1. Above 0.5 is strong; 1.0 is perfect.</div>
  </div>
</div>
</div>""", unsafe_allow_html=True)

st.markdown("---")

# ── CORRELATIONS + SEGMENTS ───────────────────────────────────────────────────
left, right = st.columns([1, 1], gap="large")

BAR_COLORS = {
    "collab_within_48h":  "#10b981",
    "teammate_joined":    "#10b981",
    "teammates_invited":  "#3b82f6",
    "sessions":           "#3b82f6",
    "tasks_added":        "#d1d5db",
    "projects_created":   "#d1d5db",
    "watched_onboarding": "#ef4444",
}
SEG_COLORS = {
    "High activation": ("#10b981", "seg-high"),
    "At risk":         ("#f59e0b", "seg-risk"),
    "Likely churned":  ("#ef4444", "seg-churn"),
}

with left:
    st.markdown('<div class="section-header">Feature correlations with retention</div>', unsafe_allow_html=True)
    for feat, r in sorted(corrs.items(), key=lambda x: abs(x[1]), reverse=True):
        label = feat.replace("_", " ").capitalize()
        pct   = int(abs(r) * 100)
        color = BAR_COLORS.get(feat, "#9ca3af")
        sign  = "+" if r >= 0 else "−"
        st.markdown(f"""
        <div class="corr-bar-container">
          <div class="corr-bar-label">
            <span>{label}</span>
            <span style="color:{color};">{sign}{abs(r):.3f}</span>
          </div>
          <div class="corr-bar-track">
            <div class="corr-bar-fill" style="width:{pct}%;background:{color};"></div>
          </div>
        </div>""", unsafe_allow_html=True)

with right:
    st.markdown('<div class="section-header">Segment breakdown</div>', unsafe_allow_html=True)
    for seg_name, (color, cls) in SEG_COLORS.items():
        cnt = {"High activation": n_high, "At risk": n_risk, "Likely churned": n_churn}.get(seg_name, 0)
        pct = round(cnt / n_total * 100) if n_total else 0
        st.markdown(f"""
        <div style="margin-bottom:16px;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
            <span class="seg-badge {cls}">{seg_name}</span>
            <span style="font-family:'DM Mono',monospace;font-size:13px;color:#374151;font-weight:500;">{cnt} users · {pct}%</span>
          </div>
          <div style="height:8px;background:#f3f4f6;border-radius:4px;overflow:hidden;">
            <div style="width:{pct}%;height:100%;background:{color};border-radius:4px;"></div>
          </div>
        </div>""", unsafe_allow_html=True)

    st.markdown('<div class="section-header" style="margin-top:20px;">Recommended actions</div>', unsafe_allow_html=True)
    actions_map = {
        "High activation": ("Show upgrade prompt immediately",    "seg-high"),
        "At risk":         ("Nudge invitee — one email closes the loop", "seg-risk"),
        "Likely churned":  ("Win-back email at 72h; exclude after 7 days", "seg-churn"),
    }
    for seg_name, (act_text, cls) in actions_map.items():
        st.markdown(f"""
        <div style="display:flex;gap:12px;align-items:flex-start;margin-bottom:12px;">
          <span class="seg-badge {cls}" style="flex-shrink:0;margin-top:2px;white-space:nowrap;">{seg_name}</span>
          <span style="font-size:13px;color:#374151;line-height:1.5;">{act_text}</span>
        </div>""", unsafe_allow_html=True)

st.markdown("---")

# ── USER TABLE ────────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">All users — scored and segmented by agent</div>', unsafe_allow_html=True)

filter_seg = st.multiselect(
    "Filter by segment",
    ["High activation", "At risk", "Likely churned"],
    default=["High activation", "At risk", "Likely churned"]
)
filtered = df_users[df_users["segment"].isin(filter_seg)].sort_values("score", ascending=False)
display_df = filtered[["user_name","score","segment","action",
                        "collab_within_48h","teammates_invited","sessions","retained"]].copy()
display_df.columns = ["User","Score","Segment","Recommended action",
                      "Collab 48h","Invites","Sessions","Retained"]
display_df["Score"]      = display_df["Score"].map(lambda x: f"{x:.3f}")
display_df["Collab 48h"] = display_df["Collab 48h"].map({1:"Yes", 0:"No"})
display_df["Retained"]   = display_df["Retained"].map({1:"Yes", 0:"No"})
st.dataframe(display_df, use_container_width=True, hide_index=True)

st.markdown("---")

# ── ACTIVATION SCORE BUILD-UP LINE CHART ─────────────────────────────────────
st.markdown('<div class="section-header">User activation score build-up · Day 0–7</div>', unsafe_allow_html=True)
st.markdown(
    "<p style='font-size:13px;color:#6b7280;margin-bottom:12px;'>"
    "Shows how the agent's activation score grew day by day as the user performed actions. "
    "A flat line = no activity. A jump = a key event fired. "
    "Green dashed line = activation threshold (0.65). Amber dotted = at-risk boundary (0.30).</p>",
    unsafe_allow_html=True
)

user_names = sorted([u["user_name"] for u in users])
chart_user = st.selectbox("Select user for score chart", user_names, key="chart_user")
chart_data = next((u for u in users if u["user_name"] == chart_user), None)

if chart_data and "daily_scores" in chart_data:
    ds = chart_data["daily_scores"]
    chart_df = pd.DataFrame(ds)
    chart_df["events_str"] = chart_df["events"].apply(
        lambda e: ", ".join(e) if e else "— no activity"
    )

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=chart_df["day"], y=chart_df["score"],
        mode="lines+markers",
        name="Activation score",
        line=dict(color="#3b82f6", width=3),
        marker=dict(size=9, color="#3b82f6", line=dict(color="white", width=2)),
        hovertemplate="<b>Day %{x}</b><br>Score: %{y:.3f}<br>Events: %{customdata}<extra></extra>",
        customdata=chart_df["events_str"]
    ))
    fig.add_hline(y=0.65, line_dash="dash", line_color="#10b981", line_width=1.5,
                  annotation_text="Activated (0.65)", annotation_position="top right",
                  annotation_font_color="#10b981", annotation_font_size=11)
    fig.add_hline(y=0.30, line_dash="dot", line_color="#f59e0b", line_width=1.5,
                  annotation_text="At risk (0.30)", annotation_position="top right",
                  annotation_font_color="#f59e0b", annotation_font_size=11)

    seg = chart_data.get("segment","")
    fill_color = "#d1fae5" if "High" in seg else ("#fef3c7" if "risk" in seg else "#fee2e2")
    fig.add_hrect(y0=0.65, y1=1.05, fillcolor="#d1fae5", opacity=0.3, line_width=0)
    fig.add_hrect(y0=0.30, y1=0.65, fillcolor="#fef3c7", opacity=0.3, line_width=0)
    fig.add_hrect(y0=-0.05, y1=0.30, fillcolor="#fee2e2", opacity=0.3, line_width=0)

    fig.update_layout(
        height=340,
        margin=dict(l=0, r=0, t=20, b=0),
        paper_bgcolor="white", plot_bgcolor="#f9fafb",
        font=dict(family="Inter", size=12, color="#374151"),
        xaxis=dict(title="Day since signup", tickmode="linear", dtick=1,
                   gridcolor="#f3f4f6", linecolor="#e8ecf0", range=[-0.2, 7.2]),
        yaxis=dict(title="Activation score", range=[-0.05, 1.1],
                   gridcolor="#f3f4f6", linecolor="#e8ecf0"),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("View day-by-day event breakdown"):
        show_df = chart_df[["day","score","events_str"]].copy()
        show_df.columns = ["Day","Score","Events fired"]
        st.dataframe(show_df, use_container_width=True, hide_index=True)

st.markdown("---")

# ── RAW EVENT LOG EXPLORER ────────────────────────────────────────────────────
st.markdown('<div class="section-header">Raw event log explorer</div>', unsafe_allow_html=True)

selected_user = st.selectbox("Select a user to inspect", user_names, key="timeline_user")
user_data     = next((u for u in users if u["user_name"] == selected_user), {})

u1, u2, u3 = st.columns(3)
with u1:
    seg_val   = user_data.get("segment", "—")
    score_val = user_data.get("score", 0)
    color_cls = "green" if score_val >= 0.65 else ("amber" if score_val >= 0.30 else "red")
    st.markdown(f"""<div class="metric-card {color_cls}">
    <div class="metric-label">Activation score</div>
    <div class="metric-value {color_cls}">{score_val:.3f}</div>
    </div>""", unsafe_allow_html=True)
with u2:
    sc = "green" if "High" in seg_val else ("amber" if "risk" in seg_val else "red")
    st.markdown(f"""<div class="metric-card {sc}">
    <div class="metric-label">Segment</div>
    <div class="metric-value {sc}" style="font-size:18px;">{seg_val}</div>
    </div>""", unsafe_allow_html=True)
with u3:
    act = user_data.get("action","—")
    st.markdown(f"""<div class="metric-card blue">
    <div class="metric-label">Recommended action</div>
    <div class="metric-value blue" style="font-size:14px;margin-top:8px;">{act}</div>
    </div>""", unsafe_allow_html=True)

# ── COLOUR LEGEND — rendered outside try block to avoid Streamlit HTML issue ──
st.markdown("""
<div style="background:#ffffff;border:1px solid #e8ecf0;border-radius:12px;
            padding:14px 20px;margin-bottom:12px;">
  <div style="font-size:11px;font-weight:600;color:#9ca3af;font-family:'DM Mono',monospace;
              text-transform:uppercase;letter-spacing:0.08em;margin-bottom:12px;">
    Colour legend
  </div>
  <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:10px 32px;">
    <div style="display:flex;align-items:flex-start;gap:10px;">
      <div style="width:10px;height:10px;border-radius:50%;background:#3b82f6;margin-top:3px;flex-shrink:0;"></div>
      <div><div style="font-size:12px;font-weight:600;color:#1e40af;">Blue — Setup</div>
           <div style="font-size:11px;color:#6b7280;">signed up, created workspace</div></div>
    </div>
    <div style="display:flex;align-items:flex-start;gap:10px;">
      <div style="width:10px;height:10px;border-radius:50%;background:#8b5cf6;margin-top:3px;flex-shrink:0;"></div>
      <div><div style="font-size:12px;font-weight:600;color:#5b21b6;">Purple — Solo work</div>
           <div style="font-size:11px;color:#6b7280;">created project, added task</div></div>
    </div>
    <div style="display:flex;align-items:flex-start;gap:10px;">
      <div style="width:10px;height:10px;border-radius:50%;background:#f59e0b;margin-top:3px;flex-shrink:0;"></div>
      <div><div style="font-size:12px;font-weight:600;color:#92400e;">Orange — Social attempt</div>
           <div style="font-size:11px;color:#6b7280;">invited teammate, teammate joined</div></div>
    </div>
    <div style="display:flex;align-items:flex-start;gap:10px;">
      <div style="width:10px;height:10px;border-radius:50%;background:#10b981;margin-top:3px;flex-shrink:0;"></div>
      <div><div style="font-size:12px;font-weight:600;color:#065f46;">Green — Activation moment</div>
           <div style="font-size:11px;color:#6b7280;">teammate commented, task assigned — collab confirmed</div></div>
    </div>
    <div style="display:flex;align-items:flex-start;gap:10px;">
      <div style="width:10px;height:10px;border-radius:50%;background:#d1d5db;margin-top:3px;flex-shrink:0;"></div>
      <div><div style="font-size:12px;font-weight:600;color:#374151;">Gray — Return visit</div>
           <div style="font-size:11px;color:#6b7280;">logged in on a later day</div></div>
    </div>
    <div style="display:flex;align-items:flex-start;gap:10px;">
      <div style="width:10px;height:10px;border-radius:50%;background:#ef4444;margin-top:3px;flex-shrink:0;"></div>
      <div><div style="font-size:12px;font-weight:600;color:#991b1b;">Red — Confusion signal</div>
           <div style="font-size:11px;color:#6b7280;">viewed onboarding — predicts churn</div></div>
    </div>
  </div>
  <div style="margin-top:12px;padding-top:10px;border-top:1px solid #f3f4f6;
              font-size:11px;color:#9ca3af;font-family:'DM Mono',monospace;">
    Retained user journey: Blue → Purple → Orange → Green &nbsp;|&nbsp;
    Churned user stops at Blue or Purple, never reaches Orange.
  </div>
</div>
""", unsafe_allow_html=True)

# Load raw events for this user from events.csv
try:
    raw_df = pd.read_csv("events.csv", parse_dates=["timestamp"])
    user_events = raw_df[raw_df["user_name"] == selected_user].sort_values("timestamp")

    # ── EVENT TIMELINE ───────────────────────────────────────────────────────
    st.markdown(f"""
    <div class="timeline-box">
    <div class="timeline-title">Raw event log · {selected_user} · {len(user_events)} events from events.csv</div>
    """, unsafe_allow_html=True)

    EVENT_COLORS = {
        "signed_up":"#3b82f6","created_workspace":"#3b82f6",
        "created_project":"#8b5cf6","added_task":"#8b5cf6",
        "invited_teammate":"#f59e0b","teammate_joined":"#f59e0b",
        "teammate_commented":"#10b981","assigned_task":"#10b981","teammate_added_task":"#10b981",
        "logged_in":"#d1d5db","viewed_onboarding":"#ef4444",
    }
    for _, row in user_events.iterrows():
        color  = EVENT_COLORS.get(row["event"], "#d1d5db")
        ts_str = row["timestamp"].strftime("%b %d · %H:%M")
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:14px;padding:9px 0;border-bottom:1px solid #f3f4f6;font-size:13px;">
          <div style="width:9px;height:9px;border-radius:50%;background:{color};flex-shrink:0;"></div>
          <div style="font-family:'DM Mono',monospace;font-size:11px;color:#9ca3af;min-width:110px;">{ts_str}</div>
          <div style="color:#374151;font-weight:500;">{row['event'].replace('_',' ')}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)
except FileNotFoundError:
    st.warning("events.csv not found — run generate_data.py first.")

st.markdown("""
<div style="margin-top:32px;text-align:center;font-family:'DM Mono',monospace;font-size:11px;color:#d1d5db;">
User NonChurn AI · built with Streamlit · aakashbhanushali20
</div>
""", unsafe_allow_html=True)
# ── AGENT REASONING ───────────────────────────────────────────────────────────
st.markdown("---")
st.markdown('<div class="section-header">Agent reasoning and signal definition</div>', unsafe_allow_html=True)

agent_reasoning = signal.get("agent_reasoning", "")
if agent_reasoning:
    st.markdown(f"""
    <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-left:4px solid #10b981;
                border-radius:12px;padding:18px 22px;margin-bottom:16px;">
      <div style="font-size:11px;font-weight:600;color:#10b981;font-family:'DM Mono',monospace;
                  text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px;">
        Why Claude chose this activation signal
      </div>
      <div style="font-size:14px;color:#064e3b;line-height:1.7;">{agent_reasoning}</div>
    </div>""", unsafe_allow_html=True)
else:
    st.markdown("""
    <div style="background:#f9fafb;border:1px solid #e8ecf0;border-radius:12px;
                padding:16px 20px;color:#9ca3af;font-size:13px;">
    Agent reasoning not available. Run agent.py to generate AI-powered analysis.
    </div>""", unsafe_allow_html=True)

# ── GROWTH REPORT ─────────────────────────────────────────────────────────────
growth_report = results.get("growth_report", "")
if growth_report:
    st.markdown("---")
    st.markdown('<div class="section-header">AI-generated growth report</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div style="background:#ffffff;border:1px solid #e8ecf0;border-radius:14px;
                padding:24px 28px;box-shadow:0 1px 4px rgba(0,0,0,0.04);">
      <pre style="font-family:'DM Mono',monospace;font-size:12px;color:#374151;
                  white-space:pre-wrap;line-height:1.8;margin:0;">{growth_report}</pre>
    </div>""", unsafe_allow_html=True)

# ── AGENT LOG ─────────────────────────────────────────────────────────────────
agent_log = results.get("agent_log", [])
if agent_log:
    st.markdown("---")
    st.markdown('<div class="section-header">Agent decision log</div>', unsafe_allow_html=True)
    st.markdown("<p style='font-size:13px;color:#6b7280;margin-bottom:12px;'>Every tool call and reasoning step Claude took to arrive at the final analysis.</p>", unsafe_allow_html=True)
    with st.expander(f"View full agent log ({len(agent_log)} steps)", expanded=False):
        for entry in agent_log:
            step = entry.get("step", "?")
            etype = entry.get("type", "")
            if etype == "thought":
                st.markdown(f"""
                <div style="display:flex;gap:12px;align-items:flex-start;
                            padding:10px 0;border-bottom:1px solid #f3f4f6;">
                  <div style="background:#eff6ff;color:#1d4ed8;font-size:11px;font-weight:600;
                              padding:2px 8px;border-radius:10px;font-family:'DM Mono',monospace;
                              flex-shrink:0;margin-top:2px;">Step {step}</div>
                  <div style="font-size:13px;color:#374151;line-height:1.6;">
                    {entry.get('content','')}</div>
                </div>""", unsafe_allow_html=True)
            elif etype == "tool_call":
                tool  = entry.get("tool","")
                inp   = entry.get("inputs", {})
                COLOR = {"load_events":"#8b5cf6","compute_user_features":"#3b82f6",
                         "run_correlations":"#f59e0b","analyse_feature":"#10b981",
                         "define_activation_signal":"#10b981","score_and_segment_users":"#f59e0b",
                         "generate_growth_report":"#3b82f6","save_results":"#6b7280"}
                color = COLOR.get(tool, "#6b7280")
                inp_str = json.dumps(inp, indent=2) if inp else "no inputs"
                st.markdown(f"""
                <div style="display:flex;gap:12px;align-items:flex-start;
                            padding:10px 0;border-bottom:1px solid #f3f4f6;">
                  <div style="background:{color}20;color:{color};font-size:11px;font-weight:600;
                              padding:2px 8px;border-radius:10px;font-family:'DM Mono',monospace;
                              flex-shrink:0;margin-top:2px;">Tool</div>
                  <div>
                    <div style="font-size:13px;font-weight:600;color:#1a1d23;font-family:'DM Mono',monospace;">
                      {tool}</div>
                    <div style="font-size:11px;color:#9ca3af;font-family:'DM Mono',monospace;
                                margin-top:4px;white-space:pre-wrap;">{inp_str[:300]}</div>
                  </div>
                </div>""", unsafe_allow_html=True)

st.markdown("""
<div style="margin-top:40px;text-align:center;font-family:'DM Mono',monospace;font-size:11px;color:#d1d5db;">
User NonChurn AI - Powered by Claude AI Agent - Built by Aakash Bhanushali
</div>
""", unsafe_allow_html=True)
# ── ASK ABOUT A USER ──────────────────────────────────────────────────────────
st.markdown("---")
st.markdown('<div class="section-header">Ask about a user</div>', unsafe_allow_html=True)
st.markdown(
    "<p style='font-size:13px;color:#6b7280;margin-bottom:16px;'>"
    "Ask Claude anything about your users. Try: <em>\"Tell me about Sarah\"</em>, "
    "<em>\"Who is most at risk this week?\"</em>, "
    "<em>\"Why did Marcus churn?\"</em>, "
    "<em>\"Which users should I email today?\"</em></p>",
    unsafe_allow_html=True
)

# Build a compact user context for Claude to reason over
def build_user_context(users_data):
    lines = []
    for u in users_data:
        retained_str = "RETAINED" if u.get("retained") == 1 else "CHURNED"
        collab       = "YES" if u.get("collab_within_48h") else "NO"
        lines.append(
            f"{u['user_name']} | score={u.get('score',0):.3f} | "
            f"segment={u.get('segment','?')} | {retained_str} | "
            f"collab_48h={collab} | invites={u.get('teammates_invited',0)} | "
            f"sessions={u.get('sessions',0)} | projects={u.get('projects_created',0)} | "
            f"tasks={u.get('tasks_added',0)} | "
            f"action={u.get('action','?')} | "
            f"signup={u.get('signup_date','?')}"
        )
    return "\n".join(lines)

user_context = build_user_context(users)

sig_ctx = (
    f"Activation Signal: {signal.get('description','collab within 48h')}\n"
    f"Pearson r: {signal.get('top_r',0)}\n"
    f"Retention if triggered: {signal.get('retention_hit',0):.0%}\n"
    f"Retention if missed: {signal.get('retention_miss',0):.0%}\n"
    f"Lift: {round(signal['lift'],1) if signal.get('lift') else 'infinite'}x\n"
    f"Total users: {summary.get('total_users',0)} | "
    f"High activation: {summary.get('n_high',0)} | "
    f"At risk: {summary.get('n_risk',0)} | "
    f"Likely churned: {summary.get('n_churn',0)}"
)

CHAT_SYSTEM = f"""You are User NonChurn AI, an expert growth analyst embedded in a SaaS analytics dashboard.

You have full access to the user dataset below. Answer questions about specific users, segments, trends, and recommended actions with clarity and precision.

ACTIVATION SIGNAL CONTEXT
{sig_ctx}

USER DATASET (one row per user)
Format: name | score | segment | retained_status | collab_48h | invites | sessions | projects | tasks | recommended_action | signup_date
{user_context}

SEGMENT DEFINITIONS
High activation: score >= 0.65 — user completed the social loop, collab happened within 48h
At risk: score 0.30-0.65 — invited someone but teammate did not act in time
Likely churned: score < 0.30 — solo user or ghost, no meaningful collaboration

SCORING FORMULA
score = collab_within_48h x 0.50 + teammate_joined x 0.25 + invites/3 x 0.15 + sessions/7 x 0.10

When asked about a specific user, always include:
1. Their segment and score
2. Whether they are predicted retained or churned and why
3. What they did and did not do in week 1
4. The recommended action for them
5. A plain-English summary in 2-3 sentences

Be direct, specific, and data-driven. Do not hedge unnecessarily. If a user is not in the dataset, say so clearly."""

import anthropic as _anthropic

# Initialise session chat history
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Display chat history
for msg in st.session_state.chat_history:
    role  = msg["role"]
    text  = msg["content"]
    align = "flex-end" if role == "user" else "flex-start"
    bg    = "#eff6ff" if role == "user" else "#f0fdf4"
    color = "#1e40af" if role == "user" else "#065f46"
    border= "#bfdbfe" if role == "user" else "#bbf7d0"
    label = "You" if role == "user" else "NonChurn AI"
    st.markdown(f"""
    <div style="display:flex;justify-content:{align};margin-bottom:12px;">
      <div style="max-width:80%;background:{bg};border:1px solid {border};
                  border-radius:12px;padding:12px 16px;">
        <div style="font-size:10px;font-weight:600;color:{color};
                    font-family:'DM Mono',monospace;text-transform:uppercase;
                    letter-spacing:0.06em;margin-bottom:6px;">{label}</div>
        <div style="font-size:13px;color:#1a1d23;line-height:1.7;white-space:pre-wrap;">{text}</div>
      </div>
    </div>""", unsafe_allow_html=True)

# Input box
with st.form("chat_form", clear_on_submit=True):
    col_input, col_btn = st.columns([5, 1])
    with col_input:
        user_q = st.text_input(
            "Your question",
            placeholder="e.g. Tell me about Sarah, or Who should I email today?",
            label_visibility="collapsed"
        )
    with col_btn:
        submitted = st.form_submit_button("Ask", use_container_width=True)

if submitted and user_q.strip():
    st.session_state.chat_history.append({"role": "user", "content": user_q.strip()})

    # Build messages for Claude
    messages = [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state.chat_history
    ]

    with st.spinner("NonChurn AI is thinking..."):
        try:
            client   = _anthropic.Anthropic()
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                system=CHAT_SYSTEM,
                messages=messages
            )
            answer = response.content[0].text
        except Exception as e:
            answer = f"Error calling Claude: {str(e)}\n\nMake sure ANTHROPIC_API_KEY is set."

    st.session_state.chat_history.append({"role": "assistant", "content": answer})
    st.rerun()

# Clear chat button
if st.session_state.chat_history:
    if st.button("Clear conversation"):
        st.session_state.chat_history = []
        st.rerun()

st.markdown("""
<div style="margin-top:40px;text-align:center;font-family:'DM Mono',monospace;font-size:11px;color:#d1d5db;">
User NonChurn AI - Powered by Claude AI Agent - Built by Aakash Bhanushali
</div>
""", unsafe_allow_html=True)
