SET SESSION sql_mode=(SELECT REPLACE(@@sql_mode,'ONLY_FULL_GROUP_BY',''));
-- ================================================================
-- SaaS Product Analytics — SQL Analysis
-- Sprint 3B: Funnel + Cohort + Retention + Engagement + Revenue
-- Author: Dheeraj Sharma
-- Database: saas_product_analytics (MySQL)
-- ================================================================
--
-- HOW TO RUN:
--   mysql -u root saas_product_analytics < sql/02_product_analysis.sql
-- ================================================================


-- ================================================================
-- SECTION 1: FUNNEL ANALYSIS
-- ================================================================

-- Q1: Full Conversion Funnel (counts + drop-off %)
-- ─────────────────────────────────────────────────
-- [BUSINESS QUESTION] Of all users who signed up, what % complete
-- each funnel stage? Where is the biggest drop-off?

WITH funnel AS (
    SELECT
        'a. Signup Complete' AS stage,
        COUNT(DISTINCT user_id) AS users
    FROM events WHERE event_type = 'signup_complete'
    UNION ALL
    SELECT 'b. Onboarding Start', COUNT(DISTINCT user_id)
    FROM events WHERE event_type = 'onboarding_start'
    UNION ALL
    SELECT 'c. Onboarding Complete', COUNT(DISTINCT user_id)
    FROM events WHERE event_type = 'onboarding_complete'
    UNION ALL
    SELECT 'd. Feature Use', COUNT(DISTINCT user_id)
    FROM events WHERE event_type = 'feature_use'
    UNION ALL
    SELECT 'e. Invite Sent', COUNT(DISTINCT user_id)
    FROM events WHERE event_type = 'invite_sent'
    UNION ALL
    SELECT 'f. Upgrade Click', COUNT(DISTINCT user_id)
    FROM events WHERE event_type = 'upgrade_click'
    UNION ALL
    SELECT 'g. Payment Success', COUNT(DISTINCT user_id)
    FROM events WHERE event_type = 'payment_success'
)
SELECT
    stage,
    users,
    ROUND(users * 100.0 / FIRST_VALUE(users) OVER (ORDER BY stage), 2) AS pct_of_signups,
    ROUND(
        (users - LAG(users) OVER (ORDER BY stage)) * 100.0
        / LAG(users) OVER (ORDER BY stage),
        2
    ) AS stage_drop_off_pct
FROM funnel
ORDER BY stage;

-- [INTERPRETATION] The biggest single drop-off reveals the product's
-- activation bottleneck. If onboarding_start → onboarding_complete
-- loses 30%+, the onboarding flow needs redesigning (exactly what
-- A/B test 1 is testing).


-- Q2: Funnel by Signup Source
-- ───────────────────────────
-- [BUSINESS QUESTION] Which acquisition channel produces users who
-- actually activate? (Not just sign up but complete onboarding)

SELECT
    u.signup_source,
    COUNT(DISTINCT u.user_id) AS total_signups,
    COUNT(DISTINCT CASE WHEN e1.user_id IS NOT NULL THEN u.user_id END) AS onboarded,
    COUNT(DISTINCT CASE WHEN e2.user_id IS NOT NULL THEN u.user_id END) AS used_feature,
    COUNT(DISTINCT CASE WHEN e3.user_id IS NOT NULL THEN u.user_id END) AS upgraded,
    ROUND(COUNT(DISTINCT CASE WHEN e1.user_id IS NOT NULL THEN u.user_id END)
          * 100.0 / COUNT(DISTINCT u.user_id), 2) AS onboarding_rate,
    ROUND(COUNT(DISTINCT CASE WHEN e3.user_id IS NOT NULL THEN u.user_id END)
          * 100.0 / COUNT(DISTINCT u.user_id), 2) AS upgrade_rate
FROM users u
LEFT JOIN (SELECT DISTINCT user_id FROM events WHERE event_type = 'onboarding_complete') e1
    ON u.user_id = e1.user_id
LEFT JOIN (SELECT DISTINCT user_id FROM events WHERE event_type = 'feature_use') e2
    ON u.user_id = e2.user_id
LEFT JOIN (SELECT DISTINCT user_id FROM events WHERE event_type = 'payment_success') e3
    ON u.user_id = e3.user_id
GROUP BY u.signup_source
ORDER BY upgrade_rate DESC;

-- [INTERPRETATION] Referral users typically show the highest
-- activation rates (they were told what to expect). Paid channels
-- bring volume but may have lower activation — worth checking
-- if CAC is justified by lower conversion.


-- Q3: Funnel by Platform
-- ──────────────────────
-- [BUSINESS QUESTION] Do mobile users activate differently than
-- web users?

SELECT
    u.primary_platform,
    COUNT(DISTINCT u.user_id) AS total_signups,
    ROUND(COUNT(DISTINCT CASE WHEN e1.user_id IS NOT NULL THEN u.user_id END)
          * 100.0 / COUNT(DISTINCT u.user_id), 2) AS onboarding_rate,
    ROUND(COUNT(DISTINCT CASE WHEN e2.user_id IS NOT NULL THEN u.user_id END)
          * 100.0 / COUNT(DISTINCT u.user_id), 2) AS feature_use_rate,
    ROUND(COUNT(DISTINCT CASE WHEN e3.user_id IS NOT NULL THEN u.user_id END)
          * 100.0 / COUNT(DISTINCT u.user_id), 2) AS upgrade_rate
FROM users u
LEFT JOIN (SELECT DISTINCT user_id FROM events WHERE event_type = 'onboarding_complete') e1
    ON u.user_id = e1.user_id
LEFT JOIN (SELECT DISTINCT user_id FROM events WHERE event_type = 'feature_use') e2
    ON u.user_id = e2.user_id
LEFT JOIN (SELECT DISTINCT user_id FROM events WHERE event_type = 'payment_success') e3
    ON u.user_id = e3.user_id
GROUP BY u.primary_platform
ORDER BY upgrade_rate DESC;


-- Q4: Time-to-Convert (Median Days from Signup to First Payment)
-- ──────────────────────────────────────────────────────────────
-- [BUSINESS QUESTION] How long does it take for a free user to
-- become a paying customer?

WITH time_to_pay AS (
    SELECT
        u.user_id,
        DATEDIFF(MIN(e.event_timestamp), u.signup_date) AS days_to_convert
    FROM users u
    JOIN events e ON u.user_id = e.user_id
    WHERE e.event_type = 'payment_success'
    GROUP BY u.user_id
)
SELECT
    COUNT(*) AS converters,
    ROUND(AVG(days_to_convert), 1) AS avg_days_to_convert,
    ROUND(MIN(days_to_convert), 0) AS fastest,
    ROUND(MAX(days_to_convert), 0) AS slowest
FROM time_to_pay;

-- [INTERPRETATION] If average time-to-convert is 15+ days, the
-- free trial / freemium experience needs an urgency mechanism
-- (trial expiry, feature limits, or drip campaigns).


-- ================================================================
-- SECTION 2: COHORT RETENTION
-- ================================================================

-- Q5: Monthly Signup Cohort Retention Matrix
-- ──────────────────────────────────────────
-- [BUSINESS QUESTION] For each signup cohort, what % of users are
-- still active in month 1, 2, 3... after signup?
-- (We define "active" = triggered at least 1 event in that month)

WITH cohort AS (
    SELECT
        user_id,
        DATE_FORMAT(signup_date, '%Y-%m') AS cohort_month
    FROM users
),
user_activity AS (
    SELECT
        e.user_id,
        DATE_FORMAT(e.event_timestamp, '%Y-%m') AS activity_month
    FROM events e
    GROUP BY e.user_id, activity_month
),
cohort_activity AS (
    SELECT
        c.cohort_month,
        PERIOD_DIFF(
            EXTRACT(YEAR_MONTH FROM STR_TO_DATE(CONCAT(ua.activity_month, '-01'), '%Y-%m-%d')),
            EXTRACT(YEAR_MONTH FROM STR_TO_DATE(CONCAT(c.cohort_month, '-01'), '%Y-%m-%d'))
        ) AS months_since_signup,
        COUNT(DISTINCT c.user_id) AS active_users
    FROM cohort c
    JOIN user_activity ua ON c.user_id = ua.user_id
    GROUP BY c.cohort_month, months_since_signup
)
SELECT
    cohort_month,
    months_since_signup,
    active_users
FROM cohort_activity
WHERE months_since_signup >= 0
  AND months_since_signup <= 6
ORDER BY cohort_month, months_since_signup;

-- [INTERPRETATION] Look for the "retention cliff" — the month where
-- the biggest drop happens. Also compare cohorts: are newer cohorts
-- retaining better? That suggests product improvements are working.


-- Q6: Retention by Plan Type
-- ──────────────────────────
-- [BUSINESS QUESTION] Do paid users retain better than free users?
-- (Validates the freemium model)

SELECT
    u.plan_type,
    COUNT(DISTINCT u.user_id) AS total_users,
    COUNT(DISTINCT CASE WHEN u.is_churned = 0 THEN u.user_id END) AS active_users,
    ROUND(COUNT(DISTINCT CASE WHEN u.is_churned = 0 THEN u.user_id END)
          * 100.0 / COUNT(DISTINCT u.user_id), 2) AS retention_rate_pct,
    ROUND(AVG(CASE WHEN u.is_churned = 1
              THEN DATEDIFF(u.churn_date, u.signup_date) END), 1) AS avg_days_before_churn
FROM users u
GROUP BY u.plan_type
ORDER BY retention_rate_pct DESC;


-- Q7: Retention by Signup Source
-- ─────────────────────────────
-- [BUSINESS QUESTION] Which acquisition channels bring users who
-- stick around vs. users who churn quickly?

SELECT
    u.signup_source,
    COUNT(DISTINCT u.user_id) AS total_users,
    ROUND(SUM(u.is_churned) * 100.0 / COUNT(*), 2) AS churn_rate_pct,
    ROUND(AVG(CASE WHEN u.is_churned = 1
              THEN DATEDIFF(u.churn_date, u.signup_date) END), 1) AS avg_days_before_churn
FROM users u
GROUP BY u.signup_source
ORDER BY churn_rate_pct ASC;


-- ================================================================
-- SECTION 3: ENGAGEMENT METRICS
-- ================================================================

-- Q8: DAU, WAU, MAU + Stickiness (DAU/MAU Ratio)
-- ────────────────────────────────────────────────
-- [BUSINESS QUESTION] How "sticky" is the product?
-- DAU/MAU > 25% = excellent. <10% = engagement problem.

WITH daily_active AS (
    SELECT
        DATE(event_timestamp) AS activity_date,
        COUNT(DISTINCT user_id) AS dau
    FROM events
    GROUP BY activity_date
),
monthly_active AS (
    SELECT
        DATE_FORMAT(event_timestamp, '%Y-%m') AS activity_month,
        COUNT(DISTINCT user_id) AS mau
    FROM events
    GROUP BY activity_month
)
SELECT
    m.activity_month,
    m.mau,
    ROUND(AVG(d.dau), 0) AS avg_dau,
    ROUND(AVG(d.dau) * 100.0 / m.mau, 2) AS stickiness_dau_mau_pct
FROM monthly_active m
JOIN daily_active d
    ON DATE_FORMAT(d.activity_date, '%Y-%m') = m.activity_month
GROUP BY m.activity_month, m.mau
ORDER BY m.activity_month;

-- [INTERPRETATION] Stickiness trending UP = product is getting more
-- habitual. Trending DOWN with growing MAU = you're adding users
-- faster than engaging them — a ticking retention bomb.


-- Q9: Power Users (>20 sessions/month)
-- ─────────────────────────────────────
-- [BUSINESS QUESTION] What percentage of users are "power users,"
-- and what plan are they on?

WITH monthly_sessions AS (
    SELECT
        user_id,
        DATE_FORMAT(start_time, '%Y-%m') AS month,
        COUNT(*) AS session_count
    FROM sessions
    GROUP BY user_id, month
)
SELECT
    u.plan_type,
    COUNT(DISTINCT ms.user_id) AS power_users,
    ROUND(COUNT(DISTINCT ms.user_id) * 100.0 /
          (SELECT COUNT(DISTINCT user_id) FROM monthly_sessions WHERE session_count > 20),
          2) AS pct_of_all_power_users
FROM monthly_sessions ms
JOIN users u ON ms.user_id = u.user_id
WHERE ms.session_count > 20
GROUP BY u.plan_type
ORDER BY power_users DESC;


-- Q10: Feature Adoption Rates
-- ───────────────────────────
-- [BUSINESS QUESTION] Which features are most/least adopted?
-- Low adoption on a core feature = onboarding gap.

SELECT
    f.feature_name,
    COUNT(DISTINCT f.user_id) AS users_adopted,
    ROUND(COUNT(DISTINCT f.user_id) * 100.0 / (SELECT COUNT(*) FROM users), 2) AS adoption_rate_pct,
    ROUND(AVG(f.times_used_30d), 1) AS avg_monthly_usage,
    ROUND(STDDEV(f.times_used_30d), 1) AS usage_std_dev
FROM features f
GROUP BY f.feature_name
ORDER BY adoption_rate_pct DESC;

-- [INTERPRETATION] "api_access" adoption will be low — that's
-- expected (only technical users). But if "reports" adoption is
-- low among paying users, it's a product gap worth investigating.


-- ================================================================
-- SECTION 4: REVENUE METRICS
-- ================================================================

-- Q11: Monthly Recurring Revenue (MRR) Trend
-- ───────────────────────────────────────────
-- [BUSINESS QUESTION] Is MRR growing? What's driving it?

SELECT
    DATE_FORMAT(s.start_date, '%Y-%m') AS month,
    COUNT(*) AS new_subscriptions,
    ROUND(SUM(s.mrr), 2) AS new_mrr,
    ROUND(SUM(SUM(s.mrr)) OVER (ORDER BY DATE_FORMAT(s.start_date, '%Y-%m')), 2) AS cumulative_mrr
FROM subscriptions s
GROUP BY month
ORDER BY month;

-- [INTERPRETATION] MRR growth rate matters more than absolute MRR.
-- Accelerating growth = product-market fit. Decelerating =
-- approaching market ceiling or increasing churn eating gains.


-- Q12: Churn Rate by Month
-- ────────────────────────
-- [BUSINESS QUESTION] Is churn getting better or worse over time?

SELECT
    DATE_FORMAT(churn_date, '%Y-%m') AS churn_month,
    COUNT(*) AS churned_users,
    SUM(CASE WHEN plan_type = 'free' THEN 1 ELSE 0 END) AS free_churns,
    SUM(CASE WHEN plan_type != 'free' THEN 1 ELSE 0 END) AS paid_churns
FROM users
WHERE is_churned = 1 AND churn_date IS NOT NULL
GROUP BY churn_month
ORDER BY churn_month;


-- Q13: ARPU by Plan Type
-- ──────────────────────
-- [BUSINESS QUESTION] What's the average revenue per user by plan?

SELECT
    s.plan,
    COUNT(DISTINCT s.user_id) AS subscribers,
    ROUND(AVG(s.mrr), 2) AS avg_mrr,
    ROUND(SUM(s.mrr), 2) AS total_mrr,
    ROUND(SUM(s.mrr) * 100.0 / (SELECT SUM(mrr) FROM subscriptions), 2) AS pct_of_total_mrr
FROM subscriptions s
GROUP BY s.plan
ORDER BY avg_mrr DESC;


-- ================================================================
-- END OF SPRINT 3B SQL — 13 PRODUCT QUERIES COMPLETE
-- ================================================================
--
-- PRODUCT ANALYTICS CONCEPTS COVERED:
--   1. Conversion funnel with drop-off % (Q1-Q4)
--   2. Cohort retention matrix (Q5)
--   3. Retention by segment (Q6-Q7)
--   4. DAU/MAU stickiness ratio (Q8)
--   5. Power user identification (Q9)
--   6. Feature adoption rates (Q10)
--   7. MRR trend and cumulative (Q11)
--   8. Churn analysis (Q12)
--   9. ARPU by plan (Q13)
