#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SaaS Product Analytics — Funnel, Cohort & Retention Analysis
================================================================
Sprint 3B: EDA + Visualizations for product analytics.

Author: Dheeraj Sharma

Run:
    python notebooks/02_funnel_retention_analysis.py
    (or paste sections into Jupyter)

Input:  data/*.csv (from Sprint 3A)
Output: charts/*.png (7 product analytics visualizations)
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
from pathlib import Path

COLORS = {
    'primary': '#1B4F72', 'accent1': '#E74C3C', 'accent2': '#27AE60',
    'accent3': '#F39C12', 'accent4': '#8E44AD', 'neutral': '#BDC3C7', 'bg': '#FAFAFA',
}
PALETTE = [COLORS['primary'], COLORS['accent1'], COLORS['accent2'],
           COLORS['accent3'], COLORS['accent4']]
sns.set_theme(style='whitegrid', font_scale=1.1)
plt.rcParams.update({
    'figure.facecolor': COLORS['bg'], 'axes.facecolor': '#FFFFFF',
    'axes.edgecolor': COLORS['neutral'], 'grid.color': '#EEEEEE',
    'font.family': 'sans-serif', 'figure.dpi': 120,
})

DATA_DIR = Path(__file__).parent.parent / "data"
CHARTS_DIR = Path(__file__).parent.parent / "charts"
CHARTS_DIR.mkdir(exist_ok=True)


# ================================================================
# %% [markdown]
# # SaaS Product Analytics — Funnel, Cohort & Retention
# ================================================================

# %%  LOAD DATA
print("Loading datasets...")
users = pd.read_csv(DATA_DIR / "users.csv", parse_dates=["signup_date", "churn_date"])
events = pd.read_csv(DATA_DIR / "events.csv", parse_dates=["event_timestamp"])
sessions = pd.read_csv(DATA_DIR / "sessions.csv", parse_dates=["start_time", "end_time"])
subscriptions = pd.read_csv(DATA_DIR / "subscriptions.csv", parse_dates=["start_date", "end_date"])
features = pd.read_csv(DATA_DIR / "features.csv", parse_dates=["first_used_date"])

print(f"Users: {len(users):,} | Events: {len(events):,} | Sessions: {len(sessions):,}")
print(f"Subscriptions: {len(subscriptions):,} | Features: {len(features):,}")


# ================================================================
# %% [markdown]
# ## 1. Conversion Funnel
# ================================================================

# %%  Chart 1: Full Conversion Funnel
funnel_stages = [
    ("Signup", "signup_complete"),
    ("Onboard Start", "onboarding_start"),
    ("Onboard Complete", "onboarding_complete"),
    ("Feature Use", "feature_use"),
    ("Invite Sent", "invite_sent"),
    ("Upgrade Click", "upgrade_click"),
    ("Payment", "payment_success"),
]

funnel_data = []
total_users = len(users)
for label, etype in funnel_stages:
    count = events[events["event_type"] == etype]["user_id"].nunique()
    funnel_data.append({"stage": label, "users": count, "pct": count / total_users * 100})

funnel_df = pd.DataFrame(funnel_data)

fig, ax = plt.subplots(figsize=(12, 6))
bars = ax.barh(funnel_df["stage"][::-1], funnel_df["pct"][::-1],
               color=[COLORS['accent2'] if i < 3 else COLORS['accent3'] if i < 5
                      else COLORS['accent1'] for i in range(len(funnel_df))][::-1],
               edgecolor='white', height=0.6)

for bar, row in zip(bars, funnel_df.iloc[::-1].itertuples()):
    ax.text(bar.get_width() + 0.8, bar.get_y() + bar.get_height()/2,
            f'{row.users:,} ({row.pct:.1f}%)', va='center', fontsize=10, fontweight='bold')

ax.set_title('User Conversion Funnel', fontsize=14, fontweight='bold', pad=15)
ax.set_xlabel('% of Total Signups', fontsize=11)
ax.set_xlim(0, 110)
sns.despine(left=True)
plt.tight_layout()
plt.savefig(CHARTS_DIR / '01_conversion_funnel.png', dpi=150, bbox_inches='tight')
plt.show()

# Print drop-off
print("\nFUNNEL DROP-OFF ANALYSIS:")
for i in range(1, len(funnel_df)):
    drop = (1 - funnel_df.iloc[i]["users"] / funnel_df.iloc[i-1]["users"]) * 100
    print(f"  {funnel_df.iloc[i-1]['stage']} → {funnel_df.iloc[i]['stage']}: {drop:.1f}% drop-off")


# %% [markdown]
# ### KEY INSIGHT — Funnel
# - The **biggest drop-off is between Onboarding Start → Onboarding Complete** —
#   this is where the product loses the most potential active users
# - This directly validates why A/B Test 1 ("new_onboarding_flow") targets this
#   exact stage — if onboarding completion improves by 10%, it compounds
#   through every downstream stage
# - **Upgrade Click → Payment** drop-off reveals pricing friction (users consider
#   upgrading but abandon during checkout)


# ================================================================
# %% [markdown]
# ## 2. Funnel by Signup Source
# ================================================================

# %%  Chart 2: Funnel Comparison by Source
source_funnel = []
for source in users["signup_source"].unique():
    source_users = users[users["signup_source"] == source]["user_id"]
    total = len(source_users)
    source_events = events[events["user_id"].isin(source_users)]

    onboarded = source_events[source_events["event_type"] == "onboarding_complete"]["user_id"].nunique()
    feature = source_events[source_events["event_type"] == "feature_use"]["user_id"].nunique()
    paid = source_events[source_events["event_type"] == "payment_success"]["user_id"].nunique()

    source_funnel.append({
        "source": source, "total": total,
        "onboard_rate": onboarded / total * 100,
        "feature_rate": feature / total * 100,
        "upgrade_rate": paid / total * 100,
    })

sf = pd.DataFrame(source_funnel).sort_values("upgrade_rate", ascending=False)

fig, ax = plt.subplots(figsize=(10, 6))
x = np.arange(len(sf))
w = 0.25
ax.bar(x - w, sf["onboard_rate"], w, label="Onboarding %", color=COLORS['primary'])
ax.bar(x, sf["feature_rate"], w, label="Feature Use %", color=COLORS['accent3'])
ax.bar(x + w, sf["upgrade_rate"], w, label="Upgrade %", color=COLORS['accent2'])
ax.set_xticks(x)
ax.set_xticklabels(sf["source"], rotation=15, ha='right')
ax.set_title('Funnel Metrics by Signup Source', fontsize=14, fontweight='bold', pad=15)
ax.set_ylabel('Conversion Rate (%)', fontsize=11)
ax.legend(fontsize=10)
sns.despine()
plt.tight_layout()
plt.savefig(CHARTS_DIR / '02_funnel_by_source.png', dpi=150, bbox_inches='tight')
plt.show()


# %% [markdown]
# ### KEY INSIGHT — Source Quality
# - Not all signup sources are equal: **referral** users tend to activate and
#   convert at higher rates because they have a trusted recommendation
# - **Paid channels** (Google, Facebook) bring volume but may show lower
#   activation — worth calculating effective CAC adjusted for activation rate


# ================================================================
# %% [markdown]
# ## 3. Cohort Retention
# ================================================================

# %%  Chart 3: Monthly Cohort Retention Heatmap
users["cohort"] = users["signup_date"].dt.to_period("M")
events_with_cohort = events.merge(users[["user_id", "cohort"]], on="user_id")
events_with_cohort["activity_month"] = events_with_cohort["event_timestamp"].dt.to_period("M")
events_with_cohort["months_since"] = (
    (events_with_cohort["activity_month"] - events_with_cohort["cohort"])
    .apply(lambda x: x.n if hasattr(x, 'n') else 0)
)

cohort_matrix = (
    events_with_cohort[events_with_cohort["months_since"] >= 0]
    .groupby(["cohort", "months_since"])["user_id"]
    .nunique()
    .reset_index()
    .pivot(index="cohort", columns="months_since", values="user_id")
)

cohort_sizes = cohort_matrix[0]
retention = cohort_matrix.div(cohort_sizes, axis=0) * 100
retention = retention.iloc[:, :8]  # Cap at 7 months
# Keep cohorts with at least 3 months of data
retention = retention.dropna(thresh=3)
retention.index = retention.index.astype(str)

fig, ax = plt.subplots(figsize=(14, 8))
sns.heatmap(retention, annot=True, fmt='.1f', cmap='YlOrRd_r',
            linewidths=0.5, linecolor='white',
            cbar_kws={'label': 'Retention Rate (%)'},
            ax=ax, vmin=0)
ax.set_title('Monthly Cohort Retention Heatmap\n(% of cohort active in month N)',
             fontsize=14, fontweight='bold', pad=15)
ax.set_xlabel('Months Since Signup', fontsize=11)
ax.set_ylabel('Signup Cohort', fontsize=11)
plt.tight_layout()
plt.savefig(CHARTS_DIR / '03_cohort_retention_heatmap.png', dpi=150, bbox_inches='tight')
plt.show()


# %%  Chart 4: Average Retention Curve
avg_retention = retention.mean(axis=0)

fig, ax = plt.subplots(figsize=(10, 5))
ax.plot(avg_retention.index, avg_retention.values, marker='o', linewidth=2.5,
        color=COLORS['primary'], markersize=8)
ax.fill_between(avg_retention.index, avg_retention.values, alpha=0.08, color=COLORS['primary'])

for i, val in enumerate(avg_retention.values[:7]):
    ax.text(avg_retention.index[i], val + 1.5, f'{val:.1f}%',
            ha='center', fontsize=9, fontweight='bold', color=COLORS['primary'])

ax.set_title('Average Retention Curve', fontsize=14, fontweight='bold', pad=15)
ax.set_xlabel('Months Since Signup', fontsize=11)
ax.set_ylabel('Retention Rate (%)', fontsize=11)
ax.set_ylim(bottom=0)
sns.despine()
plt.tight_layout()
plt.savefig(CHARTS_DIR / '04_retention_curve.png', dpi=150, bbox_inches='tight')
plt.show()

print(f"\nMonth 0: {avg_retention.iloc[0]:.1f}%")
if len(avg_retention) > 1:
    print(f"Month 1: {avg_retention.iloc[1]:.1f}% — CRITICAL first-month retention")
if len(avg_retention) > 3:
    print(f"Month 3: {avg_retention.iloc[3]:.1f}% — 3-month retention")


# %% [markdown]
# ### KEY INSIGHT — Retention
# - **Month 0 → Month 1 is the steepest drop** — this is the activation cliff.
#   Users who survive Month 1 retain at much higher rates thereafter.
# - Product strategy implication: everything you do in the first 7 days
#   determines long-term retention. Post-signup email drips, in-app tooltips,
#   and onboarding checklists should be concentrated here.
# - Compare this curve against SaaS benchmarks: 40-50% Month 1 retention
#   is "good" for B2B SaaS; <20% signals a product-market fit concern.


# ================================================================
# %% [markdown]
# ## 4. Engagement Metrics
# ================================================================

# %%  Chart 5: DAU/WAU/MAU + Stickiness Trend
events["event_date"] = events["event_timestamp"].dt.date
events["event_month"] = events["event_timestamp"].dt.to_period("M")

# Monthly metrics
monthly_metrics = (
    events.groupby("event_month")
    .agg(
        mau=("user_id", "nunique"),
        total_events=("event_id", "count"),
    )
    .reset_index()
)

# Average DAU per month
daily_active = events.groupby(["event_month", "event_date"])["user_id"].nunique().reset_index()
avg_dau = daily_active.groupby("event_month")["user_id"].mean().reset_index()
avg_dau.columns = ["event_month", "avg_dau"]

monthly_metrics = monthly_metrics.merge(avg_dau, on="event_month")
monthly_metrics["stickiness"] = monthly_metrics["avg_dau"] / monthly_metrics["mau"] * 100
monthly_metrics["month_str"] = monthly_metrics["event_month"].astype(str)

fig, axes = plt.subplots(1, 2, figsize=(15, 5))

# DAU & MAU trend
axes[0].plot(monthly_metrics["month_str"], monthly_metrics["mau"],
             marker='o', linewidth=2, color=COLORS['primary'], label='MAU')
axes[0].plot(monthly_metrics["month_str"], monthly_metrics["avg_dau"],
             marker='s', linewidth=2, color=COLORS['accent3'], label='Avg DAU')
axes[0].set_title('MAU & Average DAU Trend', fontweight='bold', fontsize=13)
axes[0].set_ylabel('Users')
axes[0].legend(fontsize=10)
axes[0].tick_params(axis='x', rotation=45)

# Stickiness
axes[1].bar(monthly_metrics["month_str"], monthly_metrics["stickiness"],
            color=COLORS['accent2'], edgecolor='white')
axes[1].axhline(y=25, color=COLORS['accent1'], linestyle='--', alpha=0.7, label='Good benchmark (25%)')
axes[1].set_title('Stickiness (DAU/MAU Ratio)', fontweight='bold', fontsize=13)
axes[1].set_ylabel('DAU/MAU (%)')
axes[1].legend(fontsize=10)
axes[1].tick_params(axis='x', rotation=45)

for ax in axes:
    sns.despine(ax=ax)
plt.tight_layout()
plt.savefig(CHARTS_DIR / '05_engagement_metrics.png', dpi=150, bbox_inches='tight')
plt.show()


# %% [markdown]
# ### KEY INSIGHT — Engagement
# - **DAU/MAU stickiness above 25% is considered "good"** for B2B SaaS.
#   Consumer apps (like social media) target 50%+.
# - If MAU is growing but stickiness is flat or declining, you're acquiring
#   users faster than you're engaging them — a retention time bomb.
# - Watch for: stickiness rising with flat MAU = existing users getting more
#   engaged (healthy); stickiness falling with rising MAU = growth-at-all-costs
#   is diluting quality.


# ================================================================
# %% [markdown]
# ## 5. Feature Adoption
# ================================================================

# %%  Chart 6: Feature Adoption Rates
feat_adoption = (
    features.groupby("feature_name")
    .agg(
        users_adopted=("user_id", "nunique"),
        avg_usage=("times_used_30d", "mean"),
    )
    .reset_index()
)
feat_adoption["adoption_pct"] = feat_adoption["users_adopted"] / len(users) * 100
feat_adoption = feat_adoption.sort_values("adoption_pct", ascending=True)

fig, axes = plt.subplots(1, 2, figsize=(14, 5))

axes[0].barh(feat_adoption["feature_name"], feat_adoption["adoption_pct"],
             color=COLORS['primary'], edgecolor='white')
axes[0].set_title('Feature Adoption Rate (%)', fontweight='bold', fontsize=13)
axes[0].set_xlabel('% of Users')

axes[1].barh(feat_adoption["feature_name"], feat_adoption["avg_usage"],
             color=COLORS['accent3'], edgecolor='white')
axes[1].set_title('Avg Monthly Usage (times/30d)', fontweight='bold', fontsize=13)
axes[1].set_xlabel('Avg Uses per Month')

for ax in axes:
    sns.despine(ax=ax, left=True)
plt.tight_layout()
plt.savefig(CHARTS_DIR / '06_feature_adoption.png', dpi=150, bbox_inches='tight')
plt.show()


# ================================================================
# %% [markdown]
# ## 6. MRR & Revenue
# ================================================================

# %%  Chart 7: MRR Growth + Churn Trend
subscriptions["start_month"] = subscriptions["start_date"].dt.to_period("M")
mrr_new = subscriptions.groupby("start_month")["mrr"].sum().reset_index()
mrr_new.columns = ["month", "new_mrr"]

# Churned MRR
churned_subs = subscriptions[subscriptions["end_date"].notna()].copy()
churned_subs["end_month"] = churned_subs["end_date"].dt.to_period("M")
mrr_lost = churned_subs.groupby("end_month")["mrr"].sum().reset_index()
mrr_lost.columns = ["month", "churned_mrr"]

mrr_trend = mrr_new.merge(mrr_lost, on="month", how="left").fillna(0)
mrr_trend["net_new_mrr"] = mrr_trend["new_mrr"] - mrr_trend["churned_mrr"]
mrr_trend["cumulative_mrr"] = mrr_trend["net_new_mrr"].cumsum()
mrr_trend["month_str"] = mrr_trend["month"].astype(str)

fig, axes = plt.subplots(1, 2, figsize=(15, 5))

# MRR components
x = np.arange(len(mrr_trend))
axes[0].bar(x, mrr_trend["new_mrr"], label='New MRR', color=COLORS['accent2'], edgecolor='white')
axes[0].bar(x, -mrr_trend["churned_mrr"], label='Churned MRR', color=COLORS['accent1'], edgecolor='white')
axes[0].set_xticks(x[::2])
axes[0].set_xticklabels(mrr_trend["month_str"].iloc[::2], rotation=45, ha='right')
axes[0].set_title('Monthly MRR: New vs Churned', fontweight='bold', fontsize=13)
axes[0].set_ylabel('MRR ($)')
axes[0].legend(fontsize=10)
axes[0].axhline(y=0, color='black', linewidth=0.5)

# Cumulative MRR
axes[1].plot(mrr_trend["month_str"], mrr_trend["cumulative_mrr"],
             marker='o', linewidth=2.5, color=COLORS['primary'])
axes[1].fill_between(mrr_trend["month_str"], mrr_trend["cumulative_mrr"],
                     alpha=0.08, color=COLORS['primary'])
axes[1].set_title('Cumulative Net MRR Growth', fontweight='bold', fontsize=13)
axes[1].set_ylabel('Cumulative MRR ($)')
axes[1].tick_params(axis='x', rotation=45)

for ax in axes:
    sns.despine(ax=ax)
plt.tight_layout()
plt.savefig(CHARTS_DIR / '07_mrr_trend.png', dpi=150, bbox_inches='tight')
plt.show()

# Print summary
active_subs = subscriptions[subscriptions["end_date"].isna()]
print(f"\nREVENUE SUMMARY:")
print(f"  Active subscriptions: {len(active_subs):,}")
print(f"  Current MRR:          ${active_subs['mrr'].sum():,.2f}")
print(f"  Avg ARPU (paid):      ${active_subs['mrr'].mean():,.2f}")


# %% [markdown]
# ### KEY INSIGHT — Revenue
# - **Net MRR = New MRR - Churned MRR.** As long as the green bars
#   (new) are taller than the red bars (churned), the business is growing.
# - If churned MRR starts approaching new MRR, you're hitting the
#   **growth ceiling** — the business needs to either reduce churn OR
#   increase expansion revenue (upsells, plan upgrades).
# - **Net Revenue Retention (NRR) > 100%** means existing customers alone
#   would grow revenue even with zero new customers — the gold standard
#   for SaaS businesses.


# ================================================================
# %% METRICS GLOSSARY
# ================================================================
print("\n" + "=" * 65)
print("METRICS GLOSSARY — Definitions Used in This Analysis")
print("=" * 65)
glossary = {
    "DAU": "Daily Active Users — unique users who triggered ≥1 event on a given day",
    "WAU": "Weekly Active Users — unique users active in a 7-day window",
    "MAU": "Monthly Active Users — unique users active in a calendar month",
    "Stickiness": "DAU/MAU ratio — measures how habitually users return (>25% = good)",
    "MRR": "Monthly Recurring Revenue — sum of all active subscription monthly fees",
    "NRR": "Net Revenue Retention — (MRR at end + expansion - contraction - churn) / MRR at start",
    "ARPU": "Average Revenue Per User — MRR / active paying users",
    "Cohort": "Group of users who signed up in the same calendar month",
    "Retention": "% of cohort users who are active (≥1 event) in month N after signup",
    "Activation": "User completed onboarding AND used at least one core feature",
    "Churn": "User stopped using the product (no events for 30+ days, or cancelled subscription)",
}
for metric, definition in glossary.items():
    print(f"  {metric:15s} {definition}")
print("=" * 65)
print("\nSprint 3B complete. Charts saved to charts/. Next: Sprint 3C — A/B Testing.")
