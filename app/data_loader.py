"""
Centralized data loading with Streamlit caching.
All pages import from here — single source of truth.
"""
import streamlit as st
import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"

@st.cache_data(ttl=3600)
def load_users():
    return pd.read_csv(DATA_DIR / "users.csv", parse_dates=["signup_date", "churn_date"])

@st.cache_data(ttl=3600)
def load_events():
    df = pd.read_csv(DATA_DIR / "events.csv", parse_dates=["event_timestamp"])
    df["event_date"] = df["event_timestamp"].dt.date
    df["event_month"] = df["event_timestamp"].dt.to_period("M").astype(str)
    return df

@st.cache_data(ttl=3600)
def load_sessions():
    return pd.read_csv(DATA_DIR / "sessions.csv", parse_dates=["start_time", "end_time"])

@st.cache_data(ttl=3600)
def load_subscriptions():
    return pd.read_csv(DATA_DIR / "subscriptions.csv", parse_dates=["start_date", "end_date"])

@st.cache_data(ttl=3600)
def load_ab_tests():
    return pd.read_csv(DATA_DIR / "ab_tests.csv", parse_dates=["assigned_date"])

@st.cache_data(ttl=3600)
def load_features():
    return pd.read_csv(DATA_DIR / "features.csv", parse_dates=["first_used_date"])

@st.cache_data(ttl=3600)
def load_metrics_framework():
    return pd.read_csv(DATA_DIR / "metrics_framework.csv")
