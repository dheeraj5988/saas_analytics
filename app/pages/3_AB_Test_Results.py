import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from scipy import stats
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from data_loader import load_users, load_events, load_ab_tests

st.set_page_config(page_title="A/B Test Results", page_icon="🧪", layout="wide")
st.title("🧪 A/B Test Results")

users = load_users()
events = load_events()
ab = load_ab_tests()

exp_name = st.selectbox("Select Experiment", ab["experiment_name"].unique())

exp = ab[ab["experiment_name"]==exp_name]
ctrl = exp[exp["variant"]=="control"]
treat = exp[exp["variant"]=="treatment"]
n_c, n_t = len(ctrl), len(treat)

primary = "onboarding_complete" if "onboarding" in exp_name else "upgrade_click"

eu = events[events["event_type"]==primary]["user_id"].unique()
cc = ctrl["user_id"].isin(eu).sum()
tc = treat["user_id"].isin(eu).sum()
cr_c, cr_t = cc/n_c if n_c>0 else 0, tc/n_t if n_t>0 else 0
lift = (cr_t-cr_c)/cr_c*100 if cr_c>0 else 0

cont = np.array([[n_c-cc,cc],[n_t-tc,tc]])
chi2, p_val, _, _ = stats.chi2_contingency(cont)
p_pool = (cc+tc)/(n_c+n_t)
se = np.sqrt(p_pool*(1-p_pool)*(1/n_c+1/n_t)) if (n_c>0 and n_t>0) else 0
diff = cr_t-cr_c
ci_lo, ci_hi = diff-1.96*se, diff+1.96*se

h = 2*(np.arcsin(np.sqrt(max(0.001,cr_t)))-np.arcsin(np.sqrt(max(0.001,cr_c))))
se_h1 = np.sqrt(max(0.001,cr_c)*(1-cr_c)/max(1,n_c)+max(0.001,cr_t)*(1-cr_t)/max(1,n_t))
z_pow = abs(diff)/se_h1-1.96 if se_h1>0 else 0
power = stats.norm.cdf(z_pow)

# KPIs
c1,c2,c3,c4 = st.columns(4)
c1.metric("Control Rate", f"{cr_c*100:.2f}%")
c2.metric("Treatment Rate", f"{cr_t*100:.2f}%", delta=f"{lift:+.1f}%")
c3.metric("p-value", f"{p_val:.4f}", delta="Significant" if p_val<0.05 else "Not Sig")
c4.metric("Power", f"{power*100:.0f}%", delta="Adequate" if power>=0.8 else "Low")

st.divider()

col1, col2 = st.columns(2)

with col1:
    st.subheader("Conversion Comparison")
    fig = go.Figure()
    ci_c = 1.96*np.sqrt(cr_c*(1-cr_c)/n_c)*100 if n_c>0 else 0
    ci_t = 1.96*np.sqrt(cr_t*(1-cr_t)/n_t)*100 if n_t>0 else 0
    fig.add_trace(go.Bar(x=["Control","Treatment"], y=[cr_c*100,cr_t*100],
                         error_y=dict(type="data",array=[ci_c,ci_t],visible=True),
                         marker_color=["#BDC3C7","#27AE60" if cr_t>cr_c else "#E74C3C"],
                         text=[f"{cr_c*100:.2f}%",f"{cr_t*100:.2f}%"], textposition="outside"))
    fig.update_layout(height=400, yaxis_title=f"{primary} Rate (%)", margin=dict(t=10))
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Effect Size with 95% CI")
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(x=[diff*100], y=["Effect"], orientation="h",
                          error_x=dict(type="data",array=[abs(ci_hi*100-diff*100)],visible=True),
                          marker_color="#1B4F72", width=0.4))
    fig2.add_vline(x=0, line_dash="dash", line_color="#E74C3C")
    fig2.update_layout(height=200, xaxis_title="Percentage Point Difference", margin=dict(t=10))
    st.plotly_chart(fig2, use_container_width=True)

    # Decision box
    if p_val<0.05 and ci_lo>0:
        st.success(f"✅ **SHIP** — Statistically significant positive effect (p={p_val:.4f})")
    elif p_val<0.05 and ci_hi<0:
        st.error(f"❌ **KILL** — Treatment is significantly worse (p={p_val:.4f})")
    else:
        st.warning(f"⏳ **ITERATE** — Not yet significant (p={p_val:.4f}). Run longer or redesign.")

st.divider()

# Statistical details
with st.expander("📋 Full Statistical Details"):
    det = pd.DataFrame({
        "Metric": ["Sample (Control)","Sample (Treatment)","Conversions (C)","Conversions (T)",
                    "Rate (C)","Rate (T)","Absolute Lift","Relative Lift","Chi-squared","p-value",
                    "95% CI Lower","95% CI Upper","Cohen's h","Power"],
        "Value": [f"{n_c:,}",f"{n_t:,}",f"{cc:,}",f"{tc:,}",f"{cr_c*100:.3f}%",f"{cr_t*100:.3f}%",
                  f"{diff*100:+.3f} pp",f"{lift:+.2f}%",f"{chi2:.4f}",f"{p_val:.6f}",
                  f"{ci_lo*100:+.3f}%",f"{ci_hi*100:+.3f}%",f"{abs(h):.4f}",f"{power*100:.1f}%"]
    })
    st.dataframe(det, use_container_width=True, hide_index=True)

# Segmented
with st.expander("📊 Segmented Analysis"):
    exp_m = exp.merge(users[["user_id","signup_source","primary_platform"]], on="user_id")
    exp_m = exp_m.merge(events[events["event_type"]==primary][["user_id"]].drop_duplicates().assign(converted=1), on="user_id", how="left")
    exp_m["converted"] = exp_m["converted"].fillna(0)
    for seg in ["signup_source","primary_platform"]:
        st.markdown(f"**By {seg}:**")
        sr = exp_m.groupby([seg,"variant"])["converted"].mean().reset_index().pivot(index=seg,columns="variant",values="converted")
        if "control" in sr.columns and "treatment" in sr.columns:
            sr["lift_pp"] = (sr["treatment"]-sr["control"])*100
            sr = sr.reset_index()
            sr.columns = [seg,"Control Rate","Treatment Rate","Lift (pp)"]
            sr["Control Rate"] = (sr["Control Rate"]*100).round(2)
            sr["Treatment Rate"] = (sr["Treatment Rate"]*100).round(2)
            sr["Lift (pp)"] = sr["Lift (pp)"].round(2)
            st.dataframe(sr, use_container_width=True, hide_index=True)
