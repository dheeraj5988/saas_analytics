import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from data_loader import load_users, load_events, load_subscriptions, load_metrics_framework

st.set_page_config(page_title="Metrics Health", page_icon="🏥", layout="wide")
st.title("🏥 Metrics Health Dashboard")

try:
    fw = load_metrics_framework()
except:
    st.error("Run notebooks/03_ab_testing_metrics.py first to generate metrics_framework.csv")
    st.stop()

users = load_users()
events = load_events()
subs = load_subscriptions()

# Traffic light dashboard
st.subheader("Business Health at a Glance")

color_map = {"healthy":"#27AE60","warning":"#F39C12","critical":"#E74C3C"}
icon_map = {"healthy":"🟢","warning":"🟡","critical":"🔴"}

categories = fw["category"].unique()

for cat in categories:
    st.markdown(f"### {cat}")
    cat_metrics = fw[fw["category"]==cat]
    cols = st.columns(len(cat_metrics))
    for col, (_, row) in zip(cols, cat_metrics.iterrows()):
        icon = icon_map.get(row["status"],"⚪")
        col.markdown(f"""
        <div style="background:white; padding:16px; border-radius:8px;
                    border-left:4px solid {color_map.get(row['status'],'#BDC3C7')};
                    box-shadow:0 1px 3px rgba(0,0,0,0.08); margin-bottom:8px;">
            <div style="font-size:0.8rem; color:#888;">{icon} {row['metric']}</div>
            <div style="font-size:1.3rem; font-weight:bold; color:#333;">{row['current_value']}</div>
            <div style="font-size:0.75rem; color:#999;">Benchmark: {row['benchmark']}</div>
        </div>
        """, unsafe_allow_html=True)

st.divider()

# Engagement sparklines
st.subheader("📈 Engagement Trends")
events_copy = events.copy()
events_copy["event_date_dt"] = pd.to_datetime(events_copy["event_date"])
daily = events_copy.groupby("event_date_dt")["user_id"].nunique().reset_index()
daily.columns = ["date","dau"]
daily = daily.sort_values("date").tail(90)

col1, col2 = st.columns(2)

with col1:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=daily["date"],y=daily["dau"], mode="lines", fill="tozeroy",
                             line=dict(color="#1B4F72",width=2), fillcolor="rgba(27,79,114,0.1)"))
    fig.update_layout(height=250, margin=dict(t=30,b=10,l=10,r=10), title="Daily Active Users (90d)", yaxis_title="DAU")
    st.plotly_chart(fig, use_container_width=True)

with col2:
    monthly = events_copy.groupby("event_month")["user_id"].nunique().reset_index()
    monthly.columns = ["month","mau"]
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(x=monthly["month"],y=monthly["mau"],marker_color="#27AE60"))
    fig2.update_layout(height=250, margin=dict(t=30,b=10,l=10,r=10), title="Monthly Active Users", yaxis_title="MAU")
    st.plotly_chart(fig2, use_container_width=True)

# Feature adoption
st.subheader("🔧 Feature Adoption")
from data_loader import load_features
features = load_features()
feat = features.groupby("feature_name").agg(users=("user_id","nunique"),avg_usage=("times_used_30d","mean")).reset_index()
feat["adoption_%"] = (feat["users"]/len(users)*100).round(1)
feat = feat.sort_values("adoption_%", ascending=False)

fig3 = go.Figure()
fig3.add_trace(go.Bar(x=feat["feature_name"],y=feat["adoption_%"],marker_color="#1B4F72",name="Adoption %"))
fig3.add_trace(go.Scatter(x=feat["feature_name"],y=feat["avg_usage"],yaxis="y2",mode="lines+markers",
                          line=dict(color="#E74C3C",width=2),name="Avg Usage/30d"))
fig3.update_layout(height=350, yaxis_title="Adoption %", yaxis2=dict(overlaying="y",side="right",title="Avg Usage"),
                   margin=dict(t=10), legend=dict(orientation="h",y=1.1))
st.plotly_chart(fig3, use_container_width=True)

st.divider()
st.caption("Metrics framework definitions available in data/metrics_framework.csv")
