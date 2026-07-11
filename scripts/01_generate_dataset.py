#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SaaS Product Analytics — Synthetic Dataset Generator
================================================================
Sprint 3A: Generate a realistic SaaS product dataset simulating
a project management tool (think Asana/Notion).

Author: Dheeraj Sharma

Why synthetic?
  No good public SaaS product dataset exists. Real companies guard
  this data fiercely (it's their competitive advantage). Generating
  it ourselves shows we UNDERSTAND the data shape and relationships
  that product analysts work with daily.

Tables generated:
  1. users        (10,000 users)
  2. events       (500,000+ events)
  3. sessions     (100,000+ sessions)
  4. subscriptions (paid user records)
  5. ab_tests     (2 experiments)
  6. features     (feature adoption tracking)

Run:
    python scripts/01_generate_dataset.py

Output:
    data/*.csv  (6 CSV files for Streamlit app)
    MySQL: saas_product_analytics database (for SQL analysis)
"""

import os
import logging
from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

# --- Config ---
SEED = 42
np.random.seed(SEED)

N_USERS = 10_000
DATE_START = datetime(2025, 6, 1)
DATE_END = datetime(2026, 5, 31)
TOTAL_DAYS = (DATE_END - DATE_START).days

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "saas_product_analytics")


def random_timestamp(start, end):
    """Generate a random datetime between start and end."""
    delta = end - start
    random_seconds = np.random.randint(0, int(delta.total_seconds()))
    return start + timedelta(seconds=int(random_seconds))


# ================================================================
# TABLE 1: USERS
# ================================================================
def generate_users():
    """
    10,000 users with realistic distributions:
    - 60% free, 25% basic, 10% pro, 5% enterprise
    - Signups spread over 12 months (more recent months = more users, growth curve)
    - Churn built in: ~30% free churn in 30d, ~10% paid churn
    """
    logger.info("Generating users table...")

    # Signup dates: weighted toward recent months (exponential growth)
    days_offsets = np.random.exponential(scale=TOTAL_DAYS * 0.4, size=N_USERS)
    days_offsets = np.clip(days_offsets, 0, TOTAL_DAYS).astype(int)
    # Flip so most signups are recent (growth pattern)
    days_offsets = TOTAL_DAYS - days_offsets
    signup_dates = [DATE_START + timedelta(days=int(d)) for d in days_offsets]

    # Plan distribution
    plans = np.random.choice(
        ["free", "basic", "pro", "enterprise"],
        size=N_USERS,
        p=[0.60, 0.25, 0.10, 0.05]
    )

    # Signup source
    sources = np.random.choice(
        ["organic", "paid_google", "paid_facebook", "referral", "direct"],
        size=N_USERS,
        p=[0.35, 0.25, 0.15, 0.15, 0.10]
    )

    # Country (US-heavy SaaS)
    countries = np.random.choice(
        ["US", "UK", "IN", "DE", "CA", "AU", "BR", "FR", "JP", "Other"],
        size=N_USERS,
        p=[0.40, 0.12, 0.10, 0.08, 0.07, 0.05, 0.05, 0.04, 0.04, 0.05]
    )

    # Industry
    industries = np.random.choice(
        ["technology", "marketing", "finance", "healthcare", "education",
         "ecommerce", "consulting", "media", "nonprofit", "other"],
        size=N_USERS,
        p=[0.20, 0.15, 0.12, 0.10, 0.10, 0.08, 0.08, 0.07, 0.05, 0.05]
    )

    # Platform preference (affects event generation)
    platforms = np.random.choice(
        ["web", "ios", "android"],
        size=N_USERS,
        p=[0.55, 0.25, 0.20]
    )

    # Churn: free users churn heavily, paid users less
    churn_probs = np.where(plans == "free", 0.30,
                  np.where(plans == "basic", 0.10,
                  np.where(plans == "pro", 0.06, 0.03)))
    is_churned = np.random.binomial(1, churn_probs)

    # Churn date: 7-90 days after signup for churned users
    churn_days = np.random.exponential(scale=25, size=N_USERS).astype(int)
    churn_days = np.clip(churn_days, 7, 120)
    churn_dates = [
        signup_dates[i] + timedelta(days=int(churn_days[i])) if is_churned[i] else None
        for i in range(N_USERS)
    ]
    # Cap churn dates at DATE_END
    churn_dates = [
        min(d, DATE_END) if d is not None else None for d in churn_dates
    ]

    users = pd.DataFrame({
        "user_id": [f"u_{i:05d}" for i in range(N_USERS)],
        "signup_date": signup_dates,
        "signup_source": sources,
        "plan_type": plans,
        "country": countries,
        "industry": industries,
        "primary_platform": platforms,
        "is_churned": is_churned,
        "churn_date": churn_dates,
    })

    logger.info(f"  Users: {len(users):,} | Churned: {users['is_churned'].sum():,} "
                f"({users['is_churned'].mean()*100:.1f}%)")
    return users


# ================================================================
# TABLE 2: EVENTS
# ================================================================
def generate_events(users):
    """
    500K+ events following a realistic funnel:
    page_view → signup_complete → onboarding_start → onboarding_complete →
    feature_use → invite_sent → upgrade_click → payment_success

    Active users: 50-200 events. Churned users: 5-20 events.
    Weekday-heavy, business-hours-weighted.
    """
    logger.info("Generating events table...")

    event_types_funnel = [
        "page_view", "signup_complete", "onboarding_start",
        "onboarding_complete", "feature_use", "invite_sent",
        "upgrade_click", "payment_success",
    ]

    all_events = []
    session_counter = 0

    for _, user in users.iterrows():
        uid = user["user_id"]
        signup = user["signup_date"]
        churned = user["is_churned"]
        churn_dt = user["churn_date"]
        plan = user["plan_type"]
        platform = user["primary_platform"]

        # Active window
        end_date = churn_dt if (churned and churn_dt) else DATE_END
        if signup >= end_date:
            continue
        active_days = (end_date - signup).days
        if active_days <= 0:
            continue

        # Event count: power-law distribution
        if churned:
            n_events = max(3, int(np.random.exponential(8)))
            n_events = min(n_events, 25)
        else:
            base = 30 if plan == "free" else 80 if plan == "basic" else 120 if plan == "pro" else 180
            n_events = max(10, int(np.random.exponential(base)))
            n_events = min(n_events, 300)

        # Generate event timestamps (weekday + business hours bias)
        event_times = []
        for _ in range(n_events):
            day_offset = np.random.randint(0, max(active_days, 1))
            event_day = signup + timedelta(days=day_offset)
            # Weekday bias: 80% weekday, 20% weekend
            if event_day.weekday() >= 5 and np.random.random() < 0.6:
                event_day += timedelta(days=(7 - event_day.weekday()))
                if event_day > end_date:
                    event_day = end_date - timedelta(days=1)
            # Hour: business hours weighted
            hour = int(np.random.normal(14, 3))  # peak at 2 PM
            hour = max(6, min(hour, 23))
            minute = np.random.randint(0, 60)
            second = np.random.randint(0, 60)
            ts = event_day.replace(hour=hour, minute=minute, second=second)
            event_times.append(ts)

        event_times.sort()

        # Assign event types following funnel logic
        # First events are always signup flow, then feature usage
        for idx, ts in enumerate(event_times):
            if idx == 0:
                etype = "signup_complete"
            elif idx == 1:
                etype = "onboarding_start"
            elif idx == 2:
                etype = np.random.choice(
                    ["onboarding_complete", "page_view"],
                    p=[0.70, 0.30]
                )
            else:
                # Regular usage: mostly feature_use and page_view
                if plan != "free" and np.random.random() < 0.02:
                    etype = "payment_success"
                elif np.random.random() < 0.04:
                    etype = "upgrade_click"
                elif np.random.random() < 0.05:
                    etype = "invite_sent"
                else:
                    etype = np.random.choice(
                        ["feature_use", "page_view"],
                        p=[0.65, 0.35]
                    )

            # Assign to sessions (group events within 30min)
            if idx == 0 or (ts - event_times[max(0, idx-1)]).total_seconds() > 1800:
                session_counter += 1
            session_id = f"s_{session_counter:07d}"

            # Platform: mostly primary, occasionally switch
            evt_platform = platform if np.random.random() < 0.85 else np.random.choice(["web", "ios", "android"])

            all_events.append({
                "event_id": f"e_{len(all_events):07d}",
                "user_id": uid,
                "event_type": etype,
                "event_timestamp": ts,
                "session_id": session_id,
                "platform": evt_platform,
            })

    events = pd.DataFrame(all_events)

    # Add some intentional messiness:
    # 1. ~0.5% duplicate events (same user, same event, same second)
    n_dupes = int(len(events) * 0.005)
    dupe_indices = np.random.choice(len(events), n_dupes, replace=False)
    dupes = events.iloc[dupe_indices].copy()
    dupes["event_id"] = [f"e_dup_{i:05d}" for i in range(n_dupes)]
    events = pd.concat([events, dupes], ignore_index=True)

    # 2. ~20 users with 0 events (edge case: signed up but never did anything)
    # Already handled: some users with very short active windows may have 0 events

    events = events.sort_values("event_timestamp").reset_index(drop=True)
    logger.info(f"  Events: {len(events):,} (including {n_dupes} intentional duplicates)")
    return events


# ================================================================
# TABLE 3: SESSIONS
# ================================================================
def generate_sessions(events):
    """Aggregate events into sessions with duration and page counts."""
    logger.info("Generating sessions table...")

    session_stats = (
        events.groupby("session_id")
        .agg(
            user_id=("user_id", "first"),
            start_time=("event_timestamp", "min"),
            end_time=("event_timestamp", "max"),
            events_count=("event_id", "count"),
            platform=("platform", "first"),
        )
        .reset_index()
    )
    # Pages viewed: proportional to events, with some noise
    session_stats["pages_viewed"] = (session_stats["events_count"] * np.random.uniform(0.8, 2.0, len(session_stats))).astype(int).clip(lower=1)

    # Add some timezone inconsistency (intentional messiness)
    # ~2% of sessions have end_time = start_time (single-event sessions, realistic)
    single_event = session_stats["events_count"] == 1
    session_stats.loc[single_event, "end_time"] = session_stats.loc[single_event, "start_time"]

    logger.info(f"  Sessions: {len(session_stats):,}")
    return session_stats


# ================================================================
# TABLE 4: SUBSCRIPTIONS
# ================================================================
def generate_subscriptions(users):
    """Subscription records for paid users with MRR and churn."""
    logger.info("Generating subscriptions table...")

    mrr_map = {"basic": 29, "pro": 79, "enterprise": 249}
    payment_methods = ["credit_card", "paypal", "bank_transfer"]
    payment_weights = [0.65, 0.25, 0.10]

    subs = []
    for _, user in users.iterrows():
        plan = user["plan_type"]
        if plan == "free":
            continue

        start = user["signup_date"]
        end = user["churn_date"] if user["is_churned"] else None
        mrr = mrr_map[plan]
        # Add some pricing variation (annual discount, promo codes)
        mrr = mrr * np.random.choice([1.0, 0.8, 0.9], p=[0.6, 0.2, 0.2])

        subs.append({
            "subscription_id": f"sub_{len(subs):05d}",
            "user_id": user["user_id"],
            "plan": plan,
            "start_date": start,
            "end_date": end,
            "mrr": round(mrr, 2),
            "payment_method": np.random.choice(payment_methods, p=payment_weights),
        })

    subscriptions = pd.DataFrame(subs)
    logger.info(f"  Subscriptions: {len(subscriptions):,} "
                f"(active: {subscriptions['end_date'].isna().sum():,})")
    return subscriptions


# ================================================================
# TABLE 5: AB TESTS
# ================================================================
def generate_ab_tests(users):
    """
    2 experiments with realistic effect sizes:
    1. 'new_onboarding_flow' — ~12% improvement in onboarding completion
    2. 'pricing_page_redesign' — ~15% improvement in upgrade conversion

    Treatment effect is NOT perfectly clean — there's noise, just like
    a real A/B test. This makes the statistical analysis in Sprint 3C
    properly challenging.
    """
    logger.info("Generating A/B test assignments...")

    ab_records = []

    # Experiment 1: New Onboarding Flow
    # Assign 40% of users who signed up after Oct 2025
    exp1_eligible = users[users["signup_date"] >= datetime(2025, 10, 1)].copy()
    exp1_sample = exp1_eligible.sample(frac=0.40, random_state=SEED)
    for _, user in exp1_sample.iterrows():
        variant = np.random.choice(["control", "treatment"], p=[0.5, 0.5])
        ab_records.append({
            "user_id": user["user_id"],
            "experiment_name": "new_onboarding_flow",
            "variant": variant,
            "assigned_date": user["signup_date"],
        })

    # Experiment 2: Pricing Page Redesign
    # Assign 35% of free users who signed up after Dec 2025
    exp2_eligible = users[
        (users["signup_date"] >= datetime(2025, 12, 1)) &
        (users["plan_type"] == "free")
    ].copy()
    exp2_sample = exp2_eligible.sample(frac=0.35, random_state=SEED + 1)
    for _, user in exp2_sample.iterrows():
        variant = np.random.choice(["control", "treatment"], p=[0.5, 0.5])
        ab_records.append({
            "user_id": user["user_id"],
            "experiment_name": "pricing_page_redesign",
            "variant": variant,
            "assigned_date": user["signup_date"],
        })

    ab_tests = pd.DataFrame(ab_records)

    # Now inject the treatment effect into events:
    # We'll track this and generate outcome metrics in Sprint 3C
    # For now, store the assignment and let downstream analysis
    # correlate with actual behavior in the events table.
    logger.info(f"  A/B test records: {len(ab_tests):,}")
    logger.info(f"    Exp 1 (onboarding): {len(ab_tests[ab_tests['experiment_name']=='new_onboarding_flow']):,} users")
    logger.info(f"    Exp 2 (pricing):    {len(ab_tests[ab_tests['experiment_name']=='pricing_page_redesign']):,} users")
    return ab_tests


# ================================================================
# TABLE 6: FEATURE ADOPTION
# ================================================================
def generate_features(users, events):
    """Track which product features each user adopted and how much they use them."""
    logger.info("Generating feature adoption table...")

    feature_names = ["dashboard", "reports", "integrations", "automations", "api_access"]
    # Adoption probability by plan (enterprise uses everything, free uses basics)
    adoption_probs = {
        "free":       [0.80, 0.30, 0.05, 0.02, 0.01],
        "basic":      [0.90, 0.60, 0.25, 0.10, 0.05],
        "pro":        [0.95, 0.80, 0.55, 0.40, 0.20],
        "enterprise": [0.98, 0.90, 0.75, 0.65, 0.50],
    }

    feature_records = []
    for _, user in users.iterrows():
        plan = user["plan_type"]
        probs = adoption_probs[plan]
        signup = user["signup_date"]

        for fname, prob in zip(feature_names, probs):
            if np.random.random() < prob:
                # First use: 0-30 days after signup
                first_use_offset = np.random.randint(0, 31)
                first_used = signup + timedelta(days=first_use_offset)
                if first_used > DATE_END:
                    continue

                # Usage intensity: power-law (few power users, many light users)
                if user["is_churned"]:
                    times_30d = max(1, int(np.random.exponential(3)))
                else:
                    times_30d = max(1, int(np.random.exponential(15)))
                times_30d = min(times_30d, 200)

                feature_records.append({
                    "user_id": user["user_id"],
                    "feature_name": fname,
                    "first_used_date": first_used,
                    "times_used_30d": times_30d,
                })

    features = pd.DataFrame(feature_records)
    logger.info(f"  Feature records: {len(features):,}")
    return features


# ================================================================
# INJECT A/B TEST EFFECTS INTO EVENTS
# ================================================================
def inject_ab_effects(events, ab_tests, users):
    """
    Make the A/B test treatment groups show realistic effects:
    1. Onboarding: treatment users 12% more likely to have onboarding_complete
    2. Pricing: treatment users 15% more likely to have upgrade_click

    Done by adding extra events for treatment users (simulating better conversion).
    Effect has noise — not a clean 12%, more like 8-16% to make stats interesting.
    """
    logger.info("Injecting A/B test treatment effects...")

    extra_events = []
    event_counter = len(events)

    # Experiment 1: onboarding improvement
    exp1_treatment = ab_tests[
        (ab_tests["experiment_name"] == "new_onboarding_flow") &
        (ab_tests["variant"] == "treatment")
    ]["user_id"].values

    for uid in exp1_treatment:
        if np.random.random() < 0.12:  # 12% of treatment users get extra onboarding_complete
            user_events = events[events["user_id"] == uid]
            if len(user_events) > 0 and "onboarding_complete" not in user_events["event_type"].values:
                ts = user_events["event_timestamp"].min() + timedelta(hours=np.random.randint(1, 48))
                extra_events.append({
                    "event_id": f"e_ab_{event_counter:07d}",
                    "user_id": uid,
                    "event_type": "onboarding_complete",
                    "event_timestamp": ts,
                    "session_id": user_events["session_id"].iloc[0],
                    "platform": user_events["platform"].iloc[0],
                })
                event_counter += 1

    # Experiment 2: pricing page improvement
    exp2_treatment = ab_tests[
        (ab_tests["experiment_name"] == "pricing_page_redesign") &
        (ab_tests["variant"] == "treatment")
    ]["user_id"].values

    for uid in exp2_treatment:
        if np.random.random() < 0.15:  # 15% of treatment get extra upgrade_click
            user_events = events[events["user_id"] == uid]
            if len(user_events) > 0 and "upgrade_click" not in user_events["event_type"].values:
                ts = user_events["event_timestamp"].min() + timedelta(days=np.random.randint(3, 20))
                extra_events.append({
                    "event_id": f"e_ab_{event_counter:07d}",
                    "user_id": uid,
                    "event_type": "upgrade_click",
                    "event_timestamp": ts,
                    "session_id": user_events["session_id"].iloc[0],
                    "platform": user_events["platform"].iloc[0],
                })
                event_counter += 1

    if extra_events:
        extra_df = pd.DataFrame(extra_events)
        events = pd.concat([events, extra_df], ignore_index=True)
        events = events.sort_values("event_timestamp").reset_index(drop=True)
        logger.info(f"  Added {len(extra_events)} treatment-effect events")

    return events


# ================================================================
# SAVE TO CSV + MySQL
# ================================================================
def save_csvs(users, events, sessions, subscriptions, ab_tests, features):
    """Save all tables as CSVs (for Streamlit deployment)."""
    users.to_csv(DATA_DIR / "users.csv", index=False)
    events.to_csv(DATA_DIR / "events.csv", index=False)
    sessions.to_csv(DATA_DIR / "sessions.csv", index=False)
    subscriptions.to_csv(DATA_DIR / "subscriptions.csv", index=False)
    ab_tests.to_csv(DATA_DIR / "ab_tests.csv", index=False)
    features.to_csv(DATA_DIR / "features.csv", index=False)
    logger.info(f"All 6 CSVs saved to {DATA_DIR}/")


def load_to_mysql(users, events, sessions, subscriptions, ab_tests, features):
    """Load into MySQL for SQL analysis in Sprint 3B."""
    try:
        conn_str = f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        engine = create_engine(conn_str)

        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

        users.to_sql("users", engine, if_exists="replace", index=False, chunksize=5000)
        logger.info(f"  MySQL: loaded users ({len(users):,} rows)")
        events.to_sql("events", engine, if_exists="replace", index=False, chunksize=10000)
        logger.info(f"  MySQL: loaded events ({len(events):,} rows)")
        sessions.to_sql("sessions", engine, if_exists="replace", index=False, chunksize=10000)
        logger.info(f"  MySQL: loaded sessions ({len(sessions):,} rows)")
        subscriptions.to_sql("subscriptions", engine, if_exists="replace", index=False, chunksize=5000)
        logger.info(f"  MySQL: loaded subscriptions ({len(subscriptions):,} rows)")
        ab_tests.to_sql("ab_tests", engine, if_exists="replace", index=False, chunksize=5000)
        logger.info(f"  MySQL: loaded ab_tests ({len(ab_tests):,} rows)")
        features.to_sql("features", engine, if_exists="replace", index=False, chunksize=5000)
        logger.info(f"  MySQL: loaded features ({len(features):,} rows)")

    except Exception as e:
        logger.warning(f"  MySQL load skipped (not critical — CSVs are saved): {e}")
        logger.warning("  Create the database first: mysql -u root -e 'CREATE DATABASE saas_product_analytics;'")


# ================================================================
# DATA SUMMARY
# ================================================================
def print_summary(users, events, sessions, subscriptions, ab_tests, features):
    """Print a comprehensive data summary for validation."""
    print("\n" + "=" * 70)
    print("DATASET SUMMARY — SaaS Product Analytics")
    print("=" * 70)

    print(f"\n  Date range: {DATE_START.date()} → {DATE_END.date()} (12 months)")
    print(f"\n  TABLE ROW COUNTS:")
    print(f"    Users:          {len(users):>10,}")
    print(f"    Events:         {len(events):>10,}")
    print(f"    Sessions:       {len(sessions):>10,}")
    print(f"    Subscriptions:  {len(subscriptions):>10,}")
    print(f"    A/B Tests:      {len(ab_tests):>10,}")
    print(f"    Features:       {len(features):>10,}")

    print(f"\n  PLAN DISTRIBUTION:")
    for plan, count in users["plan_type"].value_counts().items():
        print(f"    {plan:15s} {count:>6,} ({count/len(users)*100:.1f}%)")

    print(f"\n  CHURN:")
    print(f"    Overall churn rate:   {users['is_churned'].mean()*100:.1f}%")
    for plan in ["free", "basic", "pro", "enterprise"]:
        plan_users = users[users["plan_type"] == plan]
        print(f"    {plan:15s} churn: {plan_users['is_churned'].mean()*100:.1f}%")

    print(f"\n  FUNNEL (event type counts):")
    funnel_order = ["signup_complete", "onboarding_start", "onboarding_complete",
                    "feature_use", "invite_sent", "upgrade_click", "payment_success"]
    for etype in funnel_order:
        users_with = events[events["event_type"] == etype]["user_id"].nunique()
        pct = users_with / len(users) * 100
        print(f"    {etype:25s} {users_with:>6,} users ({pct:.1f}%)")

    print(f"\n  SIGNUP SOURCE:")
    for src, count in users["signup_source"].value_counts().items():
        print(f"    {src:20s} {count:>6,} ({count/len(users)*100:.1f}%)")

    print(f"\n  A/B TESTS:")
    for exp in ab_tests["experiment_name"].unique():
        exp_data = ab_tests[ab_tests["experiment_name"] == exp]
        ctrl = (exp_data["variant"] == "control").sum()
        treat = (exp_data["variant"] == "treatment").sum()
        print(f"    {exp}: control={ctrl}, treatment={treat}")

    print(f"\n  SUBSCRIPTION REVENUE:")
    active_subs = subscriptions[subscriptions["end_date"].isna()]
    print(f"    Active subscriptions: {len(active_subs):,}")
    print(f"    Current MRR: ${active_subs['mrr'].sum():,.2f}")
    print(f"    Avg MRR per subscriber: ${active_subs['mrr'].mean():,.2f}")

    print(f"\n  FEATURE ADOPTION (% of users who used each feature):")
    for fname in features["feature_name"].unique():
        users_adopted = features[features["feature_name"] == fname]["user_id"].nunique()
        print(f"    {fname:20s} {users_adopted:>6,} ({users_adopted/len(users)*100:.1f}%)")

    print("\n" + "=" * 70)


# ================================================================
# MAIN
# ================================================================
def main():
    logger.info("Starting SaaS dataset generation (seed=42)...")

    users = generate_users()
    events = generate_events(users)
    sessions = generate_sessions(events)
    subscriptions = generate_subscriptions(users)
    ab_tests = generate_ab_tests(users)
    features = generate_features(users, events)

    # Inject A/B treatment effects
    events = inject_ab_effects(events, ab_tests, users)

    # Save
    save_csvs(users, events, sessions, subscriptions, ab_tests, features)
    load_to_mysql(users, events, sessions, subscriptions, ab_tests, features)

    # Summary
    print_summary(users, events, sessions, subscriptions, ab_tests, features)

    logger.info("Sprint 3A complete. Dataset ready for SQL analysis + Streamlit app.")


if __name__ == "__main__":
    main()
