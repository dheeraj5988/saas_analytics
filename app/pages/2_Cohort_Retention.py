import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from data_loader import load_users, load_events

st.set_page_config(page_title="Cohort Retention", page_icon="📅", layout="wide")
st.title("📅 Cohort Retention Analysis")

users = load_users()
events = load_events()

with st.sidebar:
    st.header("Filters")
    plan_filter = st.multiselect("Plan Type", users["plan_type"].unique(), default=users["plan_type"].unique())

fu = users[users["plan_type"].isin(plan_filter)]
fe = events[events["user_id"].isin(fu["user_id"])]

# KPIs
c1,c2,c3 = st.columns(3)
overall_ret = (1-fu["is_churned"].mean())*100
paid_churn = fu[fu["plan_type"]!="free"]["is_churned"].mean()*100 if len(fu[fu["plan_type"]!="free"])>0 else 0
free_churn = fu[fu["plan_type"]=="free"]["is_churned"].mean()*100 if len(fu[fu["plan_type"]=="free"])>0 else 0
c1.metric("Overall Retention", f"{overall_ret:.1f}%")
c2.metric("Free Churn Rate", f"{free_churn:.1f}%")
c3.metric("Paid Churn Rate", f"{paid_churn:.1f}%")

st.divider()

# Cohort matrix
fu_copy = fu.copy()
fu_copy["cohort"] = fu_copy["signup_date"].dt.to_period("M")
fe_copy = fe.copy()
fe_copy["event_ts"] = pd.to_datetime(fe_copy["event_timestamp"])
fe_copy = fe_copy.merge(fu_copy[["user_id","cohort"]], on="user_id")
fe_copy["activity_month"] = fe_copy["event_ts"].dt.to_period("M")
fe_copy["months_since"] = (fe_copy["activity_month"]-fe_copy["cohort"]).apply(lambda x: x.n if hasattr(x,'n') else 0)

cm = fe_copy[fe_copy["months_since"]>=0].groupby(["cohort","months_since"])["user_id"].nunique().reset_index().pivot(index="cohort",columns="months_since",values="user_id")
sizes = cm[0]
ret = cm.div(sizes, axis=0)*100
ret = ret.iloc[:,:8].dropna(thresh=3)
ret.index = ret.index.astype(str)

col1, col2 = st.columns([3,2])

with col1:
    st.subheader("Retention Heatmap")
    fig = px.imshow(ret, text_auto=".1f", color_continuous_scale="YlOrRd_r",
                    labels=dict(x="Months Since Signup",y="Cohort",color="Retention %"),
                    aspect="auto")
    fig.update_layout(height=450, margin=dict(t=10,b=10))
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Avg Retention Curve")
    avg_ret = ret.mean(axis=0).reset_index()
    avg_ret.columns = ["month","retention"]
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=avg_ret["month"], y=avg_ret["retention"], mode="lines+markers+text",
                              text=[f"{v:.1f}%" for v in avg_ret["retention"]], textposition="top center",
                              line=dict(color="#1B4F72",width=3), marker=dict(size=8)))
    fig2.update_layout(height=450, margin=dict(t=10,b=10), yaxis_title="Retention %",
                       xaxis_title="Months Since Signup", yaxis_range=[0, avg_ret["retention"].max()*1.2])
    st.plotly_chart(fig2, use_container_width=True)

st.divider()

# Retention by plan
st.subheader("Retention by Plan Type")
plan_ret = []
for plan in fu["plan_type"].unique():
    pu = fu[fu["plan_type"]==plan]
    plan_ret.append({"Plan":plan, "Users":len(pu), "Retained %":(1-pu["is_churned"].mean())*100,
                     "Avg Days to Churn": pu[pu["is_churned"]==1].apply(lambda r: (r["churn_date"]-r["signup_date"]).days if pd.notna(r["churn_date"]) else None, axis=1).mean()})
pr = pd.DataFrame(plan_ret).sort_values("Retained %", ascending=False)
st.dataframe(pr.style.format({"Retained %":"{:.1f}","Avg Days to Churn":"{:.0f}","Users":"{:,}"}), use_container_width=True, hide_index=True)
