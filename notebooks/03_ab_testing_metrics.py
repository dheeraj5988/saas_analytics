#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SaaS Product Analytics — A/B Testing & Metrics Framework
Sprint 3C | Author: Dheeraj Sharma
Run: python notebooks/03_ab_testing_metrics.py
"""
import logging
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)
COLORS = {'primary':'#1B4F72','accent1':'#E74C3C','accent2':'#27AE60','accent3':'#F39C12','accent4':'#8E44AD','neutral':'#BDC3C7','bg':'#FAFAFA'}
sns.set_theme(style='whitegrid', font_scale=1.1)
plt.rcParams.update({'figure.facecolor':COLORS['bg'],'axes.facecolor':'#FFFFFF','axes.edgecolor':COLORS['neutral'],'grid.color':'#EEEEEE','font.family':'sans-serif','figure.dpi':120})
DATA_DIR = Path(__file__).parent.parent / "data"
CHARTS_DIR = Path(__file__).parent.parent / "charts"
CHARTS_DIR.mkdir(exist_ok=True)

def load_data():
    users = pd.read_csv(DATA_DIR/"users.csv", parse_dates=["signup_date","churn_date"])
    events = pd.read_csv(DATA_DIR/"events.csv", parse_dates=["event_timestamp"])
    ab_tests = pd.read_csv(DATA_DIR/"ab_tests.csv", parse_dates=["assigned_date"])
    subs = pd.read_csv(DATA_DIR/"subscriptions.csv", parse_dates=["start_date","end_date"])
    sessions = pd.read_csv(DATA_DIR/"sessions.csv", parse_dates=["start_time","end_time"])
    features = pd.read_csv(DATA_DIR/"features.csv", parse_dates=["first_used_date"])
    return users, events, ab_tests, subs, sessions, features

def analyze_ab_test(ab_data, events, users, exp_name, primary_event, secondary_events=None, chart_num="08"):
    print("\n"+"="*70)
    print(f"A/B TEST ANALYSIS: {exp_name}")
    print("="*70)
    exp = ab_data[ab_data["experiment_name"]==exp_name].copy()
    ctrl = exp[exp["variant"]=="control"]
    treat = exp[exp["variant"]=="treatment"]
    n_c, n_t = len(ctrl), len(treat)
    print(f"\n  Sample: Control={n_c:,} | Treatment={n_t:,}")
    print(f"\n  HYPOTHESIS:")
    print(f"  H0: {exp_name} has NO effect on {primary_event} rate")
    print(f"  H1: {exp_name} CHANGES {primary_event} rate")

    eu = events[events["event_type"]==primary_event]["user_id"].unique()
    cc = ctrl["user_id"].isin(eu).sum()
    tc = treat["user_id"].isin(eu).sum()
    cr_c, cr_t = cc/n_c, tc/n_t
    lift = (cr_t-cr_c)/cr_c*100 if cr_c>0 else 0

    print(f"\n  PRIMARY METRIC: {primary_event}")
    print(f"  {'':30s} {'Control':>12s} {'Treatment':>12s}")
    print(f"  {'-'*60}")
    print(f"  {'Sample size':30s} {n_c:>12,} {n_t:>12,}")
    print(f"  {'Conversions':30s} {cc:>12,} {tc:>12,}")
    print(f"  {'Conversion rate':30s} {cr_c*100:>11.2f}% {cr_t*100:>11.2f}%")
    print(f"  {'Relative lift':30s} {'':>12s} {lift:>+11.2f}%")

    # Chi-squared
    cont = np.array([[n_c-cc,cc],[n_t-tc,tc]])
    chi2, p_val, dof, _ = stats.chi2_contingency(cont)
    print(f"\n  CHI-SQUARED: chi2={chi2:.4f}, p={p_val:.6f}")
    print(f"  Significant at 5%? {'YES' if p_val<0.05 else 'NO'}")

    # Confidence interval
    p_pool = (cc+tc)/(n_c+n_t)
    se = np.sqrt(p_pool*(1-p_pool)*(1/n_c+1/n_t))
    diff = cr_t - cr_c
    ci_lo, ci_hi = diff-1.96*se, diff+1.96*se
    print(f"\n  95% CI: [{ci_lo*100:+.3f}%, {ci_hi*100:+.3f}%] (absolute pp)")
    if ci_lo>0: print(f"  -> Entire CI positive — treatment better")
    elif ci_hi<0: print(f"  -> Entire CI negative — treatment worse")
    else: print(f"  -> CI crosses zero — uncertain")

    # Effect size
    h = 2*(np.arcsin(np.sqrt(cr_t))-np.arcsin(np.sqrt(cr_c)))
    el = "Small" if abs(h)<0.2 else "Medium" if abs(h)<0.5 else "Large"
    print(f"\n  EFFECT SIZE: Cohen's h={abs(h):.4f} ({el})")

    # Power
    se_h1 = np.sqrt(cr_c*(1-cr_c)/n_c+cr_t*(1-cr_t)/n_t)
    z_pow = abs(diff)/se_h1-1.96 if se_h1>0 else 0
    power = stats.norm.cdf(z_pow)
    print(f"  POWER: {power*100:.1f}% {'(adequate)' if power>=0.8 else '(underpowered)'}")

    # Novelty check
    exp_ev = exp.merge(events[events["event_type"]==primary_event][["user_id"]].drop_duplicates(), on="user_id", how="left", indicator=True)
    exp_ev["converted"] = (exp_ev["_merge"]=="both").astype(int)
    med_d = exp["assigned_date"].median()
    early = exp_ev[exp_ev["assigned_date"]<=med_d]
    late = exp_ev[exp_ev["assigned_date"]>med_d]
    el_lift = (early[early["variant"]=="treatment"]["converted"].mean()-early[early["variant"]=="control"]["converted"].mean())*100
    ll_lift = (late[late["variant"]=="treatment"]["converted"].mean()-late[late["variant"]=="control"]["converted"].mean())*100
    print(f"\n  NOVELTY CHECK: Early={el_lift:+.2f}pp, Late={ll_lift:+.2f}pp")
    if abs(el_lift)>2*abs(ll_lift) and abs(ll_lift)>0.1: print(f"  -> Possible novelty effect")
    else: print(f"  -> No strong novelty effect")

    # Segmented
    print(f"\n  SEGMENTED ANALYSIS:")
    exp_m = exp.merge(users[["user_id","signup_source","primary_platform"]], on="user_id")
    exp_m = exp_m.merge(events[events["event_type"]==primary_event][["user_id"]].drop_duplicates().assign(converted=1), on="user_id", how="left")
    exp_m["converted"] = exp_m["converted"].fillna(0).astype(int)
    for seg in ["signup_source","primary_platform"]:
        print(f"  By {seg}:")
        sr = exp_m.groupby([seg,"variant"])["converted"].mean().reset_index().pivot(index=seg, columns="variant", values="converted")
        if "control" in sr.columns and "treatment" in sr.columns:
            sr["lift"] = (sr["treatment"]-sr["control"])*100
            for idx, row in sr.iterrows():
                print(f"    {idx:20s} ctrl:{row['control']*100:5.2f}% treat:{row['treatment']*100:5.2f}% lift:{row['lift']:+.2f}pp")

    # Secondary
    if secondary_events:
        print(f"\n  SECONDARY METRICS:")
        for se_evt in secondary_events:
            su = events[events["event_type"]==se_evt]["user_id"].unique()
            sc = ctrl["user_id"].isin(su).mean()*100
            st = treat["user_id"].isin(su).mean()*100
            print(f"    {se_evt:25s} ctrl:{sc:.2f}% treat:{st:.2f}% lift:{st-sc:+.2f}pp")

    # Chart
    fig, axes = plt.subplots(1,2, figsize=(14,5))
    rates = [cr_c*100, cr_t*100]
    cis = [1.96*np.sqrt(cr_c*(1-cr_c)/n_c)*100, 1.96*np.sqrt(cr_t*(1-cr_t)/n_t)*100]
    bcol = [COLORS['neutral'], COLORS['accent2'] if cr_t>cr_c else COLORS['accent1']]
    axes[0].bar(["Control","Treatment"], rates, yerr=cis, capsize=8, color=bcol, edgecolor='white', error_kw={'linewidth':2})
    for i,(r,c) in enumerate(zip(rates,cis)):
        axes[0].text(i, r+c+0.5, f'{r:.2f}%', ha='center', fontweight='bold', fontsize=11)
    axes[0].set_title(f'{primary_event} Rate\n(p={p_val:.4f}{"*" if p_val<0.05 else ""})', fontweight='bold')
    axes[0].set_ylabel(f'Rate (%)')
    axes[1].barh(["Effect"], [diff*100], xerr=[[abs(ci_lo*100-diff*100)]], color=COLORS['primary'], capsize=8, edgecolor='white', height=0.4, error_kw={'linewidth':2})
    axes[1].axvline(x=0, color=COLORS['accent1'], linestyle='--', linewidth=1.5)
    axes[1].set_title(f'Lift: {diff*100:+.2f}pp [CI: {ci_lo*100:+.1f}, {ci_hi*100:+.1f}]', fontweight='bold')
    axes[1].set_xlabel('pp difference')
    for ax in axes: sns.despine(ax=ax)
    plt.suptitle(f'A/B Test: {exp_name}', fontsize=15, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(CHARTS_DIR/f'{chart_num}_ab_{exp_name.replace(" ","_")}.png', dpi=150, bbox_inches='tight')
    plt.show()

    # Decision
    if p_val<0.05 and ci_lo>0: dec="SHIP"
    elif p_val<0.05 and ci_hi<0: dec="KILL"
    else: dec="ITERATE"
    print(f"\n  DECISION: {dec}")
    if cr_t>cr_c:
        inc = 10000*(cr_t-cr_c)
        print(f"  Revenue impact: ~{inc:.0f} extra conversions/month -> ~${inc*50:,.0f} MRR")
    print("="*70)
    return {"experiment":exp_name,"cr_control":cr_c,"cr_treatment":cr_t,"lift_pct":lift,"p_value":p_val,"ci_lower":ci_lo*100,"ci_upper":ci_hi*100,"power":power,"decision":dec}

def build_metrics_framework(users, events, subs, sessions, features_df):
    print("\n"+"="*70)
    print("BUSINESS HEALTH METRICS FRAMEWORK (AARRR)")
    print("="*70)
    total = len(users)
    active_subs = subs[subs["end_date"].isna()]
    events["event_date"] = events["event_timestamp"].dt.date
    events["event_month"] = events["event_timestamp"].dt.to_period("M")
    lm = events["event_month"].max()
    le = events[events["event_month"]==lm]
    mau = le["user_id"].nunique()
    avg_dau = le.groupby("event_date")["user_id"].nunique().mean()
    stick = avg_dau/mau*100 if mau>0 else 0
    metrics = []
    def add(cat,name,val,bench,st): metrics.append({"category":cat,"metric":name,"current_value":val,"benchmark":bench,"status":st})
    ms = users.groupby(users["signup_date"].dt.to_period("M")).size()
    add("Acquisition","Monthly Signups",f"{ms.iloc[-1]:,}","Growing","healthy")
    ob = events[events["event_type"]=="onboarding_complete"]["user_id"].nunique()/total*100
    add("Activation","Onboarding Rate",f"{ob:.1f}%","60-80%","healthy" if ob>50 else "warning")
    fu = events[events["event_type"]=="feature_use"]["user_id"].nunique()/total*100
    add("Activation","Feature Adoption",f"{fu:.1f}%","40-60%","healthy" if fu>40 else "warning")
    add("Engagement","MAU",f"{mau:,}","Growing","healthy")
    add("Engagement","DAU/MAU Stickiness",f"{stick:.1f}%",">25%","healthy" if stick>25 else "warning")
    ret = (1-users["is_churned"].mean())*100
    add("Retention","Overall Retention",f"{ret:.1f}%",">70%","healthy" if ret>70 else "warning")
    fc = users[users["plan_type"]=="free"]["is_churned"].mean()*100
    pc = users[users["plan_type"]!="free"]["is_churned"].mean()*100
    add("Retention","Free Churn",f"{fc:.1f}%","<30%","healthy" if fc<30 else "warning")
    add("Retention","Paid Churn",f"{pc:.1f}%","<10%","healthy" if pc<10 else "warning" if pc<20 else "critical")
    mrr = active_subs["mrr"].sum()
    arpu = active_subs["mrr"].mean() if len(active_subs)>0 else 0
    add("Revenue","MRR",f"${mrr:,.0f}","Growing","healthy")
    add("Revenue","ARPU",f"${arpu:.2f}",">$40","healthy" if arpu>40 else "warning")
    up = events[events["event_type"]=="payment_success"]["user_id"].nunique()/total*100
    add("Revenue","Free-to-Paid",f"{up:.1f}%","3-7%","healthy" if up>3 else "warning")
    inv = events[events["event_type"]=="invite_sent"]["user_id"].nunique()/total*100
    add("Referral","Invite Rate",f"{inv:.1f}%",">10%","healthy" if inv>10 else "warning")
    df = pd.DataFrame(metrics)
    print(f"\n  {'Category':14s} {'Metric':22s} {'Current':>10s} {'Bench':>8s} Status")
    print(f"  {'-'*65}")
    cc=""
    for _,r in df.iterrows():
        cl = r["category"] if r["category"]!=cc else ""
        cc=r["category"]
        icon={"healthy":"OK","warning":"!!","critical":"XX"}.get(r["status"],"--")
        print(f"  {cl:14s} {r['metric']:22s} {r['current_value']:>10s} {r['benchmark']:>8s} [{icon}]")

    fig, ax = plt.subplots(figsize=(12,7))
    cmap = {'healthy':COLORS['accent2'],'warning':COLORS['accent3'],'critical':COLORS['accent1']}
    cl = [cmap.get(r["status"],COLORS['neutral']) for _,r in df.iterrows()]
    ax.barh(range(len(df)), [1]*len(df), color=cl, edgecolor='white', height=0.7)
    ax.set_yticks(range(len(df)))
    ax.set_yticklabels([r["metric"] for _,r in df.iterrows()], fontsize=9)
    ax.invert_yaxis()
    ax.set_xlim(0,1.5); ax.set_xticks([])
    for i,(_,r) in enumerate(df.iterrows()):
        ax.text(1.05, i, r["current_value"], va='center', fontsize=9, fontweight='bold')
    ax.set_title('Metrics Health Dashboard\n(Green=Healthy  Yellow=Warning  Red=Critical)', fontsize=14, fontweight='bold', pad=15)
    sns.despine(left=True, bottom=True)
    plt.tight_layout()
    plt.savefig(CHARTS_DIR/'10_metrics_health_dashboard.png', dpi=150, bbox_inches='tight')
    plt.show()
    df.to_csv(DATA_DIR/"metrics_framework.csv", index=False)
    logger.info("Saved data/metrics_framework.csv")
    return df

def main():
    logger.info("Starting Sprint 3C...")
    users, events, ab_tests, subs, sessions, features_df = load_data()
    r1 = analyze_ab_test(ab_tests, events, users, "new_onboarding_flow", "onboarding_complete", ["feature_use","invite_sent"], "08")
    r2 = analyze_ab_test(ab_tests, events, users, "pricing_page_redesign", "upgrade_click", ["payment_success"], "09")
    fw = build_metrics_framework(users, events, subs, sessions, features_df)
    print("\n"+"="*70)
    print("EXECUTIVE SUMMARY")
    print("="*70)
    print(f"\n  1. Onboarding test: {r1['decision']} (lift={r1['lift_pct']:+.1f}%, p={r1['p_value']:.4f})")
    print(f"  2. Pricing test:    {r2['decision']} (lift={r2['lift_pct']:+.1f}%, p={r2['p_value']:.4f})")
    print(f"  3. Top priority:    Fix onboarding completion (biggest funnel drop-off)")
    print(f"\n  Charts: charts/08-10 | Data: data/metrics_framework.csv")
    logger.info("Sprint 3C complete.")

if __name__=="__main__":
    main()
