import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from data_loader import load_users, load_events

st.set_page_config(page_title="Funnel Analysis", page_icon="🔄", layout="wide")
st.title("🔄 Funnel Analysis")

users = load_users()
events = load_events()

# Filters
with st.sidebar:
    st.header("Filters")
    sources = st.multiselect("Signup Source", users["signup_source"].unique(), default=users["signup_source"].unique())
    platforms = st.multiselect("Platform", users["primary_platform"].unique(), default=users["primary_platform"].unique())

filtered_users = users[(users["signup_source"].isin(sources)) & (users["primary_platform"].isin(platforms))]
filtered_events = events[events["user_id"].isin(filtered_users["user_id"])]
total = len(filtered_users)

# Funnel
stages = [("Signup","signup_complete"),("Onboard Start","onboarding_start"),("Onboard Complete","onboarding_complete"),("Feature Use","feature_use"),("Invite Sent","invite_sent"),("Upgrade Click","upgrade_click"),("Payment","payment_success")]
funnel = []
for label, etype in stages:
    cnt = filtered_events[filtered_events["event_type"]==etype]["user_id"].nunique()
    funnel.append({"stage":label,"users":cnt,"pct":cnt/total*100 if total>0 else 0})

col1, col2 = st.columns([3,2])

with col1:
    st.subheader("Conversion Funnel")
    fig = go.Figure(go.Funnel(
        y=[f["stage"] for f in funnel],
        x=[f["users"] for f in funnel],
        textinfo="value+percent initial",
        marker=dict(color=["#1B4F72","#2471A3","#2E86C1","#27AE60","#F39C12","#E67E22","#E74C3C"]),
        connector=dict(line=dict(color="#BDC3C7"))
    ))
    fig.update_layout(height=450, margin=dict(t=10,b=10))
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Drop-off Analysis")
    for i in range(1, len(funnel)):
        prev, curr = funnel[i-1], funnel[i]
        drop = (1-curr["users"]/prev["users"])*100 if prev["users"]>0 else 0
        color = "🔴" if drop>40 else "🟡" if drop>20 else "🟢"
        st.markdown(f"{color} **{prev['stage']}** → **{curr['stage']}**: {drop:.1f}% drop-off")

st.divider()

# Funnel by source comparison
st.subheader("Funnel by Signup Source")
source_data = []
for src in filtered_users["signup_source"].unique():
    su = filtered_users[filtered_users["signup_source"]==src]["user_id"]
    se = filtered_events[filtered_events["user_id"].isin(su)]
    t = len(su)
    if t == 0: continue
    ob = se[se["event_type"]=="onboarding_complete"]["user_id"].nunique()/t*100
    fu = se[se["event_type"]=="feature_use"]["user_id"].nunique()/t*100
    up = se[se["event_type"]=="payment_success"]["user_id"].nunique()/t*100
    source_data.append({"source":src,"Onboarding %":ob,"Feature Use %":fu,"Upgrade %":up})

if source_data:
    import pandas as pd
    sf = pd.DataFrame(source_data).set_index("source")
    fig2 = px.bar(sf.reset_index().melt(id_vars="source"), x="source", y="value", color="variable", barmode="group",
                  color_discrete_sequence=["#1B4F72","#F39C12","#27AE60"])
    fig2.update_layout(height=350, yaxis_title="Rate (%)", xaxis_title="", legend_title="")
    st.plotly_chart(fig2, use_container_width=True)
