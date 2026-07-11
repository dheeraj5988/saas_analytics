# Project 3 — Sprint 3A: Synthetic SaaS Dataset

## Steps to Run

1. Create MySQL database:
   ```bash
   mysql -u root -e "CREATE DATABASE saas_product_analytics;"
   ```

2. Set up Python:
   ```bash
   cd project3_saas_analytics
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. Configure credentials:
   ```bash
   cp .env.example .env
   # Edit .env with your MySQL password
   ```

4. Generate the dataset:
   ```bash
   python scripts/01_generate_dataset.py
   ```

   Runtime: ~2-3 minutes. Generates 6 CSV files in `data/` + loads to MySQL.

## What Gets Generated

| Table | Rows | Description |
|---|---|---|
| users | 10,000 | Signups over 12 months with plan, source, churn |
| events | 500,000+ | Funnel events (pageview → signup → onboard → feature_use → upgrade) |
| sessions | 100,000+ | Aggregated from events, with duration and pages |
| subscriptions | ~4,000 | Paid user records with MRR |
| ab_tests | ~2,500 | 2 experiments: onboarding flow + pricing redesign |
| features | ~25,000 | Feature adoption tracking per user |

## Intentional Data Messiness (Realistic)
- ~0.5% duplicate events
- Users with 0 events (signed up but never returned)
- Weekday/weekend usage bias
- Power-law event distributions (few power users, many light users)
- A/B test effects have noise (not perfectly clean 12%)

## Next Sprint
Say "3A done" to proceed to Sprint 3B — Funnel + Cohort + Retention Analysis.
