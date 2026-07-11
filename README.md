# 📊 SaaS Product Analytics — Interactive Dashboard
### Funnel Analysis · Cohort Retention · A/B Testing · Metrics Framework

[![Live App](https://img.shields.io/badge/🚀_Live_App-Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://saas-analytics-dheeraj-sharma.streamlit.app/)
[![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-Deployed-FF4B4B?style=flat&logo=streamlit&logoColor=white)](https://saas-analytics-dheeraj-sharma.streamlit.app/)
[![MySQL](https://img.shields.io/badge/MySQL-8.0-4479A1?style=flat&logo=mysql&logoColor=white)](https://mysql.com)
[![Plotly](https://img.shields.io/badge/Plotly-Interactive-3F4F75?style=flat&logo=plotly&logoColor=white)](https://plotly.com)
[![SciPy](https://img.shields.io/badge/SciPy-Statistics-8CAAE6?style=flat&logo=scipy&logoColor=white)](https://scipy.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

### 🔗 [**Launch Live Dashboard →**](https://saas-analytics-dheeraj-sharma.streamlit.app/)

---

## 📌 Business Problem

A SaaS project management platform (modeled after Asana/Notion) with **10,000 users** and **500,000+ behavioral events** needs answers to four critical product questions:

1. **Where are users dropping off?** — The conversion funnel leaks users between onboarding start and onboarding completion. Without quantifying each stage's drop-off, product investment is guesswork.

2. **Which cohorts retain and which churn?** — Monthly retention curves reveal whether product improvements are working and which user segments are silently leaving.

3. **Do our experiments actually work?** — Two A/B tests (onboarding flow redesign + pricing page) need rigorous statistical evaluation — not just "treatment looks higher," but p-values, confidence intervals, power analysis, and novelty checks.

4. **Is the business healthy?** — Across the AARRR framework (Acquisition → Activation → Retention → Revenue → Referral), which metrics are green, which are yellow, and which are red?

This project builds the complete analytics stack — from synthetic data generation through SQL analysis to a **deployed interactive dashboard** — to answer all four questions.

---

## 🎯 Key Results

| Finding | Impact |
|---|---|
| **Onboarding A/B test: +19.3% lift (p=0.0013)** | Statistically significant improvement → **SHIP** recommendation |
| **Revenue impact: ~$41K additional MRR/year** | From onboarding improvement alone |
| **Biggest funnel drop-off: Onboarding Start → Complete** | Confirms the A/B test was targeting the right bottleneck |
| **Paid user churn < 10%** | Healthy retention for paid tiers; free tier churn (~30%) is expected |
| **DAU/MAU stickiness benchmarked against industry** | Tracked and displayed in real-time on the metrics dashboard |

---

## 🖥️ Live Dashboard

**→ [saas-analytics-dheeraj-sharma.streamlit.app](https://saas-analytics-dheeraj-sharma.streamlit.app/)**

| Page | What It Shows |
|---|---|
| **Executive Dashboard** | 5 KPI cards (MAU, MRR, Churn, Stickiness) + user growth + MRR trend + plan distribution |
| **Funnel Analysis** | Interactive Plotly funnel with drop-off % + funnel comparison by signup source + sidebar filters |
| **Cohort Retention** | Interactive retention heatmap + average retention curve + retention by plan type table |
| **A/B Test Results** | Experiment selector + conversion bars with error bars + CI visualization + Ship/Iterate/Kill decision + segmented analysis |
| **Metrics Health** | AARRR traffic-light dashboard (green/yellow/red) + DAU sparklines + feature adoption dual-axis chart |

---

## 📂 Repository Structure

```
saas_analytics/
│
├── app/                               # Streamlit application
│   ├── app.py                         # Main dashboard (entry point)
│   ├── data_loader.py                 # Cached data loading module
│   ├── requirements.txt               # Deployment dependencies
│   ├── .streamlit/config.toml         # Custom theme (navy/white)
│   └── pages/
│       ├── 1_Funnel_Analysis.py       # Interactive funnel + source comparison
│       ├── 2_Cohort_Retention.py      # Retention heatmap + curves
│       ├── 3_AB_Test_Results.py       # Full A/B test statistical analysis
│       └── 4_Metrics_Health.py        # AARRR metrics traffic-light dashboard
│
├── scripts/
│   └── 01_generate_dataset.py         # Synthetic data generator (10K users, 500K+ events)
│
├── sql/
│   └── 02_product_analysis.sql        # 13 product analytics SQL queries
│
├── notebooks/
│   ├── 02_funnel_retention_analysis.py # EDA: funnel, cohort, engagement, MRR (7 charts)
│   └── 03_ab_testing_metrics.py       # A/B testing + AARRR metrics framework (3 charts)
│
├── charts/                            # 10 generated static visualizations
├── data/                              # Generated CSVs (6 tables + metrics framework)
├── docs/
│   └── DEPLOYMENT.md                  # Streamlit Cloud deployment guide
│
├── .gitignore
├── requirements.txt
└── README.md
```

---

## 🗄️ Dataset (Synthetic)

**Why synthetic?** No SaaS company publishes their product analytics data — it's their competitive advantage. Generating realistic synthetic data demonstrates understanding of the data shapes, distributions, and relationships that product analysts work with daily.

**Generated tables:**

| Table | Rows | Key Characteristics |
|---|---|---|
| **users** | 10,000 | 60/25/10/5 plan split, exponential signup growth, built-in churn (~30% free, ~10% paid) |
| **events** | 500,000+ | Funnel-ordered event types, weekday/business-hours bias, power-law usage |
| **sessions** | 100,000+ | Aggregated from events, variable durations |
| **subscriptions** | ~4,000 | Paid user records with MRR, pricing variation |
| **ab_tests** | ~2,500 | 2 experiments with realistic noisy treatment effects |
| **features** | ~25,000 | Feature adoption with plan-dependent probability |

**Intentional messiness:** 0.5% duplicate events, users with zero activity, timezone inconsistencies, noisy A/B effects — because real data is never clean.

---

## 🛠️ Technical Architecture

```
┌─────────────────────────────────────────────────┐
│            Streamlit Cloud (Free)                │
│  ┌─────────────┐  ┌──────────────────────────┐  │
│  │   app.py     │  │  pages/                  │  │
│  │  (Executive  │  │  1_Funnel_Analysis.py    │  │
│  │   Dashboard) │  │  2_Cohort_Retention.py   │  │
│  │              │  │  3_AB_Test_Results.py     │  │
│  │              │  │  4_Metrics_Health.py      │  │
│  └──────┬───────┘  └────────────┬─────────────┘  │
│         │    data_loader.py     │                 │
│         └──────────┬────────────┘                 │
│                    │ @st.cache_data               │
│              ┌─────▼─────┐                        │
│              │  data/*.csv│  (no DB dependency)    │
│              └───────────┘                        │
└─────────────────────────────────────────────────┘
```

**Design decisions:**
- **CSV over MySQL for deployment** — Streamlit Cloud has no database; all data loads from committed CSVs
- **`@st.cache_data`** — data loads once and caches for 1 hour, keeping the app fast
- **Modular pages** — each page is a standalone file, making the codebase maintainable
- **Plotly over Matplotlib** — interactive charts (hover, zoom, pan) for the web app
- **Custom CSS** — professional card styling, not default Streamlit aesthetics

---

## 🧪 A/B Testing Methodology

Each experiment goes through a **10-step analysis framework:**

1. Hypothesis definition (H₀ / H₁)
2. Conversion rate calculation (control vs treatment)
3. Chi-squared test for statistical significance
4. 95% confidence interval for absolute effect (percentage points)
5. Cohen's h effect size (small / medium / large)
6. Statistical power analysis (adequate ≥ 80%?)
7. Novelty effect check (early vs late lift comparison)
8. Segmented analysis (by signup source, platform)
9. Secondary metrics evaluation
10. Ship / Iterate / Kill decision with revenue impact estimation

**Experiment 1 — New Onboarding Flow:**
- Primary metric: onboarding completion rate
- Result: **+19.3% relative lift** (p=0.0013, 95% CI entirely positive)
- Decision: **SHIP** — estimated **~$41K additional MRR/year**

**Experiment 2 — Pricing Page Redesign:**
- Primary metric: upgrade click rate
- Evaluated with identical statistical rigor
- Decision based on significance, practical effect size, and revenue impact

---

## 📋 AARRR Metrics Framework

| Category | Metric | Definition | Status |
|---|---|---|---|
| **Acquisition** | Monthly Signups | New registrations per month | Tracked |
| **Activation** | Onboarding Rate | % completing onboarding flow | Monitored |
| **Activation** | Feature Adoption | % using ≥1 core feature | Monitored |
| **Engagement** | DAU/MAU Stickiness | Daily-to-monthly active ratio | Benchmarked (>25%) |
| **Retention** | Paid Churn Rate | Paid user monthly churn | Target: <10% |
| **Revenue** | MRR | Monthly Recurring Revenue | Growing |
| **Revenue** | Free-to-Paid % | Conversion from free to paid | Target: 3-7% |
| **Referral** | Invite Rate | % of users sending invites | Tracked |

Each metric is displayed with a **traffic-light status** (green/yellow/red) on the live dashboard.

---

## 🚀 How to Reproduce

```bash
git clone https://github.com/dheeraj5988/saas_analytics.git
cd saas_analytics

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Generate the synthetic dataset
python scripts/01_generate_dataset.py

# Run SQL analysis (optional — requires MySQL)
mysql -u root -e "CREATE DATABASE saas_product_analytics;"
mysql -u root saas_product_analytics < sql/02_product_analysis.sql

# Run analysis notebooks
python notebooks/02_funnel_retention_analysis.py
python notebooks/03_ab_testing_metrics.py

# Launch the Streamlit app locally
streamlit run app/app.py
```

---

## 🔮 Future Improvements

- [ ] **Predictive churn model** — logistic regression on engagement features to flag at-risk users before they leave
- [ ] **Revenue forecasting** — time-series MRR projection with confidence bands
- [ ] **Real-time event streaming** — connect to a message queue (Kafka/Redis) for live dashboard updates
- [ ] **Multi-variate testing** — extend A/B framework to support experiments with 3+ variants
- [ ] **User journey mapping** — sequence analysis to identify optimal activation paths

---

## 📋 Skills Demonstrated

`Python` `SQL` `Streamlit` `Plotly` `Pandas` `NumPy` `SciPy` `MySQL` `Seaborn` `Matplotlib`
`Product Analytics` `SaaS Metrics` `Funnel Analysis` `Cohort Retention` `A/B Testing`
`Chi-Squared Test` `Confidence Intervals` `Statistical Power` `Effect Size`
`DAU/MAU` `MRR` `ARPU` `NRR` `AARRR Framework` `Feature Adoption`
`Data Visualization` `Dashboard Design` `Streamlit Deployment` `Synthetic Data Generation`

---

## 👤 Author

**Dheeraj Sharma**
B.Tech in Computer Science (Big Data Analytics) · SRM Institute of Science and Technology

[![Portfolio](https://img.shields.io/badge/🚀_Live_Dashboard-View_App-FF4B4B?style=for-the-badge)](https://saas-analytics-dheeraj-sharma.streamlit.app/)

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-0A66C2?style=flat&logo=linkedin)](https://www.linkedin.com/in/dheeraj-sharma-97251120b/)
[![GitHub](https://img.shields.io/badge/GitHub-dheeraj5988-181717?style=flat&logo=github)](https://github.com/dheeraj5988)
[![Email](https://img.shields.io/badge/Email-dsharma259889%40gmail.com-D14836?style=flat&logo=gmail&logoColor=white)](mailto:dsharma259889@gmail.com)

---

*This project uses synthetic data that models realistic SaaS product behavior patterns. No real user data was used.*
