"""
SaaS Product Analytics — Interactive Dashboard
================================================
Main entry point. Run with: streamlit run app/app.py
"""
import streamlit as st

st.set_page_config(
    page_title="SaaS Product Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    .block-container {padding-top: 1.5rem; padding-bottom: 1rem;}
    [data-testid="stMetric"] {
        background: white; padding: 12px 16px; border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }
    [data-testid="stMetricLabel"] {font-size: 0.85rem;}
    [data-testid="stMetricValue"] {font-size: 1.4rem;}
    .stTabs [data-baseweb="tab-list"] {gap: 8px;}
    .stTabs [data-baseweb="tab"] {padding: 8px 20px; font-weight: 500;}
    h1 {color: #1B4F72;}
    h2 {color: #1B4F72; border-bottom: 2px solid #1B4F72; padding-bottom: 6px;}
</style>
""", unsafe_allow_html=True)

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from data_loader import load_users, load_events, load_subscriptions, load_sessions

users = load_users()
events = load_events()
subs = load_subscriptions()
sessions = load_sessions()

active_subs = subs[subs["end_date"].isna()]

# --- Header ---
st.title("📊 SaaS Product Analytics Dashboard")
st.caption("Interactive analytics for a SaaS project management platform · Built by Dheeraj Sharma")

# --- KPI Row ---
c1, c2, c3, c4, c5 = st.columns(5)

total_users = len(users)
mau_events = events[events["event_month"] == events["event_month"].max()]
mau = mau_events["user_id"].nunique()
current_mrr = active_subs["mrr"].sum()
churn_rate = users["is_churned"].mean() * 100
avg_dau = mau_events.groupby("event_date")["user_id"].nunique().mean()
stickiness = avg_dau / mau * 100 if mau > 0 else 0

c1.metric("Total Users", f"{total_users:,}")
c2.metric("MAU", f"{mau:,}")
c3.metric("MRR", f"${current_mrr:,.0f}")
c4.metric("Churn Rate", f"{churn_rate:.1f}%")
c5.metric("DAU/MAU Stickiness", f"{stickiness:.1f}%")

st.divider()

# --- Quick Charts ---
import plotly.express as px
import plotly.graph_objects as go

col1, col2 = st.columns(2)

with col1:
    st.subheader("📈 User Growth")
    user_growth = users.groupby(users["signup_date"].dt.to_period("M")).size().reset_index()
    user_growth.columns = ["month", "signups"]
    user_growth["month"] = user_growth["month"].astype(str)
    user_growth["cumulative"] = user_growth["signups"].cumsum()
    fig = go.Figure()
    fig.add_trace(go.Bar(x=user_growth["month"], y=user_growth["signups"], name="New Signups", marker_color="#1B4F72", opacity=0.7))
    fig.add_trace(go.Scatter(x=user_growth["month"], y=user_growth["cumulative"], name="Cumulative", yaxis="y2", line=dict(color="#E74C3C", width=3)))
    fig.update_layout(yaxis2=dict(overlaying="y", side="right", title="Cumulative"), height=350, margin=dict(t=10,b=10), legend=dict(orientation="h", y=1.12))
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("💰 MRR Trend")
    subs_monthly = subs.groupby(subs["start_date"].dt.to_period("M"))["mrr"].sum().cumsum().reset_index()
    subs_monthly.columns = ["month", "cumulative_mrr"]
    subs_monthly["month"] = subs_monthly["month"].astype(str)
    fig2 = px.area(subs_monthly, x="month", y="cumulative_mrr", color_discrete_sequence=["#27AE60"])
    fig2.update_layout(height=350, margin=dict(t=10,b=10), yaxis_title="Cumulative MRR ($)")
    st.plotly_chart(fig2, use_container_width=True)

# --- Plan Distribution ---
col3, col4 = st.columns(2)
with col3:
    st.subheader("👥 Plan Distribution")
    plan_dist = users["plan_type"].value_counts().reset_index()
    plan_dist.columns = ["plan", "count"]
    fig3 = px.pie(plan_dist, values="count", names="plan", color_discrete_sequence=["#1B4F72","#E74C3C","#27AE60","#F39C12"], hole=0.45)
    fig3.update_layout(height=300, margin=dict(t=10,b=10))
    st.plotly_chart(fig3, use_container_width=True)

with col4:
    st.subheader("🌍 Signup Sources")
    src_dist = users["signup_source"].value_counts().reset_index()
    src_dist.columns = ["source", "count"]
    fig4 = px.bar(src_dist, x="count", y="source", orientation="h", color_discrete_sequence=["#1B4F72"])
    fig4.update_layout(height=300, margin=dict(t=10,b=10), yaxis_title="", xaxis_title="Users")
    st.plotly_chart(fig4, use_container_width=True)

st.caption("Navigate to detailed pages using the sidebar ←")
