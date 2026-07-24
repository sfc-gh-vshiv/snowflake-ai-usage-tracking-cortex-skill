---
name: track-cortex-ai-spend
description: "Track and attribute Snowflake Cortex AI spend by model, user, warehouse, role, or query tag. Help decide which AI model works best for which tasks using cost data and AI Observability quality metrics. Use when: AI cost attribution, Cortex AI chargeback, model cost comparison, AI spend by team, AI budget, token usage, model cost vs quality, AI FinOps, showback, credit optimization, AI Observability, model evaluation, model benchmarking. Triggers: AI spend, Cortex AI cost, which model, model cost, AI attribution, chargeback AI, token cost, AI credits, which AI model is cheapest, model selection Cortex, AI governance cost, cortex functions cost, how much am I spending on AI, evaluate model quality, compare models, AI observability."
---

# Track Cortex AI Spend

## When to Use

- A customer or team wants to understand where their Cortex AI credits are going
- Finance/FinOps needs a chargeback or showback report for AI usage
- An engineer wants to know which AI model is cheapest or best for a given task
- Comparing model quality vs cost to pick the right model for a workload
- Setting budgets, quotas, or resource monitors on AI consumption
- Preparing for a governance conversation about uncontrolled AI spend growth

## Pricing Context

Snowflake uses **AI Credits** for AI services — separate from Platform Credits.

### How cost is reported

Views report **tokens** and/or **credits** — never dollars directly:

```
TOKENS (raw usage) → CREDITS (fractional AI Credits) → DOLLARS (credits × account effective rate)
```

| View | Tokens | Credits | Notes |
|------|:------:|:-------:|-------|
| `CORTEX_AI_FUNCTIONS_USAGE_HISTORY` | METRICS array (input/output) | `CREDITS` | Richest view |
| `CORTEX_FUNCTIONS_QUERY_USAGE_HISTORY` | `TOKENS` | `TOKEN_CREDITS` | No timestamp — join QUERY_HISTORY |
| `CORTEX_AGENT_USAGE_HISTORY` | `TOKENS` + `TOKENS_GRANULAR` (per-model) | `TOKEN_CREDITS` + `CREDITS_GRANULAR` (per-model) | Best for agent breakdown |
| `CORTEX_REST_API_USAGE_HISTORY` | `TOKENS` + `TOKENS_GRANULAR` (input/output/cache) | **Not available** | Tokens only — estimate via rate sheet |

### Getting the account's actual dollar cost (with discounts)

Use `SNOWFLAKE.ORGANIZATION_USAGE.RATE_SHEET_DAILY` for the **exact negotiated effective rate** per account per service type. This includes all contract discounts and varies by account.

```sql
-- Get this account's current AI credit rate (requires ORGADMIN or imported privileges)
SELECT DISTINCT
    ACCOUNT_NAME, SERVICE_TYPE, USAGE_TYPE, EFFECTIVE_RATE, CURRENCY, RATING_TYPE
FROM SNOWFLAKE.ORGANIZATION_USAGE.RATE_SHEET_DAILY
WHERE DATE = (SELECT MAX(DATE) FROM SNOWFLAKE.ORGANIZATION_USAGE.RATE_SHEET_DAILY)
  AND ACCOUNT_LOCATOR = CURRENT_ACCOUNT()
  AND (SERVICE_TYPE ILIKE '%AI%' OR SERVICE_TYPE ILIKE '%CORTEX%')
ORDER BY SERVICE_TYPE;
```

Service types that appear in the rate sheet:

| SERVICE_TYPE | RATING_TYPE | Typical range |
|-------------|-------------|---------------|
| `AI_FUNCTIONS` | AI_COMPUTE | $2.00 – $2.20 |
| `AI_INFERENCE` | AI_COMPUTE | $2.00 – $2.20 (per-model rates vary) |
| `CORTEX_AGENTS` | AI_COMPUTE | $2.00 – $2.20 |
| `CORTEX_AI_GUARDRAILS` | AI_COMPUTE | $2.00 – $2.20 |
| `CORTEX_SEARCH` | AI_COMPUTE | $2.20 |
| `BATCH_CORTEX_SEARCH` | AI_COMPUTE | $2.20 |
| `AI_SERVICES` (legacy) | COMPUTE | $2.00 – $6.20 (varies by edition) |

### Dollar cost query with rate sheet join

```sql
-- Accurate dollar cost using account's actual negotiated rate
-- Falls back to $2.00 (global) if rate sheet has no entry for this service
WITH rates AS (
    SELECT EFFECTIVE_RATE
    FROM SNOWFLAKE.ORGANIZATION_USAGE.RATE_SHEET_DAILY
    WHERE DATE = (SELECT MAX(DATE) FROM SNOWFLAKE.ORGANIZATION_USAGE.RATE_SHEET_DAILY)
      AND ACCOUNT_LOCATOR = CURRENT_ACCOUNT()
      AND SERVICE_TYPE IN ('AI_FUNCTIONS', 'AI_INFERENCE', 'CORTEX_AGENTS')
    LIMIT 1
)
SELECT
    u.FUNCTION_NAME,
    u.MODEL_NAME,
    SUM(u.CREDITS)                                         AS total_credits,
    SUM(u.CREDITS) * COALESCE(MAX(r.EFFECTIVE_RATE), 2.00) AS total_cost_usd,
    COALESCE(MAX(r.EFFECTIVE_RATE), 2.00)                  AS rate_per_credit_usd,
    CASE WHEN MAX(r.EFFECTIVE_RATE) IS NULL
         THEN '⚠️ Rate not in rate sheet — using $2.00 default'
         ELSE 'From RATE_SHEET_DAILY (includes discounts)'
    END AS rate_source
FROM SNOWFLAKE.ACCOUNT_USAGE.CORTEX_AI_FUNCTIONS_USAGE_HISTORY u
LEFT JOIN rates r ON TRUE
WHERE u.START_TIME >= DATEADD('day', -30, CURRENT_TIMESTAMP())
  AND u.IS_COMPLETED = TRUE
GROUP BY 1, 2
ORDER BY total_cost_usd DESC;
```

**For org-level reporting across all accounts:**

```sql
-- Dollar cost per account across the entire org (requires ORGADMIN)
SELECT
    r.ACCOUNT_NAME,
    r.SERVICE_TYPE,
    r.EFFECTIVE_RATE AS rate_usd,
    r.DATE
FROM SNOWFLAKE.ORGANIZATION_USAGE.RATE_SHEET_DAILY r
WHERE r.DATE = (SELECT MAX(DATE) FROM SNOWFLAKE.ORGANIZATION_USAGE.RATE_SHEET_DAILY)
  AND r.SERVICE_TYPE IN ('AI_FUNCTIONS', 'AI_INFERENCE', 'CORTEX_AGENTS',
                         'CORTEX_AI_GUARDRAILS', 'CORTEX_SEARCH', 'BATCH_CORTEX_SEARCH')
ORDER BY r.ACCOUNT_NAME, r.SERVICE_TYPE;
```

**Fallback (if ORGADMIN not available):** Check the routing parameter to estimate the rate:
```sql
SHOW PARAMETERS LIKE 'CORTEX_ENABLED_CROSS_REGION' IN ACCOUNT;
-- ANY_REGION / *_GLOBAL → $2.00 per AI Credit
-- DISABLED / regional  → $2.20 per AI Credit
```

---

## Data Sources

All views are in `SNOWFLAKE.ACCOUNT_USAGE` (45-min to 3-hour latency). For real-time, use `SNOWFLAKE.INFORMATION_SCHEMA` equivalents (7-day history only).

### Primary attribution views

| View | Covers | Key columns |
|------|--------|-------------|
| `CORTEX_AI_FUNCTIONS_USAGE_HISTORY` | AI_COMPLETE, AI_CLASSIFY, AI_EXTRACT, AI_SUMMARIZE, AI_TRANSLATE, AI_EMBED, AI_AGG, AI_SENTIMENT (per-query, richest metadata) | USER_ID, MODEL_NAME, WAREHOUSE_ID, ROLE_NAMES, QUERY_TAG, CREDITS, METRICS (ARRAY) |
| `CORTEX_FUNCTIONS_QUERY_USAGE_HISTORY` | Same functions (per-query, simpler — **no timestamp**, join to QUERY_HISTORY for time filtering) | QUERY_ID, WAREHOUSE_ID, MODEL_NAME, FUNCTION_NAME, TOKENS, TOKEN_CREDITS |
| `CORTEX_FUNCTIONS_USAGE_HISTORY` | Same functions (hourly rollup — use for long-range trends) | FUNCTION_NAME, MODEL_NAME, WAREHOUSE_ID, TOKEN_CREDITS, TOKENS |
| `CORTEX_REST_API_USAGE_HISTORY` | Direct REST API, Cortex Code, external app calls | USER_ID, MODEL_NAME, QUERY_TAG, TOKENS, TOKENS_GRANULAR |
| `CORTEX_AGENT_USAGE_HISTORY` | Cortex Agents (Snowflake Intelligence, custom agents) | USER_NAME, AGENT_NAME, TOKEN_CREDITS, TOKENS_GRANULAR, CREDITS_GRANULAR |
| `CORTEX_ANALYST_USAGE_HISTORY` | Cortex Analyst (text-to-SQL) | USER_ID, MODEL_NAME, CREDITS |

### Additional Cortex views

| View | Covers |
|------|--------|
| `CORTEX_CODE_CLI_USAGE_HISTORY` | Cortex Code CLI sessions |
| `CORTEX_CODE_DESKTOP_USAGE_HISTORY` | Cortex Code Desktop sessions |
| `CORTEX_CODE_SNOWSIGHT_USAGE_HISTORY` | Cortex Code in Snowsight |
| `CORTEX_AI_GUARDRAILS_USAGE_HISTORY` | Cortex Guard / AI Guardrails (includes AGENTIC_SOURCE) |
| `CORTEX_AISQL_USAGE_HISTORY` | Analytical SQL (AI-assisted SQL generation) |
| `CORTEX_DOCUMENT_PROCESSING_USAGE_HISTORY` | AI_PARSE_DOCUMENT (OCR/doc processing) |
| `CORTEX_FINE_TUNING_USAGE_HISTORY` | Cortex Fine-tuning jobs |
| `CORTEX_PROVISIONED_THROUGHPUT_USAGE_HISTORY` | Provisioned throughput reservations |
| `CORTEX_SEARCH_SERVING_USAGE_HISTORY` | Cortex Search serving credits |
| `CORTEX_SEARCH_DAILY_USAGE_HISTORY` | Cortex Search daily usage |
| `CORTEX_SEARCH_BATCH_QUERY_USAGE_HISTORY` | Cortex Batch Search |
| `CORTEX_REST_API_RATE_LIMIT_POLICIES` | Rate limit policy config (not usage) |

**Required privilege:** `ACCOUNTADMIN` or a role granted `IMPORTED PRIVILEGES` on the `SNOWFLAKE` database.

---

## Workflow

### Step 1: Confirm Scope with the User

✋ **STOP** — ask the user:
1. Time window (last 7 days / 30 days / custom range)?
2. Primary attribution dimension: by user, team/role, model, warehouse, or query tag?
3. Goal: spend visibility, chargeback allocation, budget setting, or model selection?

---

### Step 2: Run the Right Attribution Query

Pick the query matching the user's attribution goal.

#### A. Total AI spend by function and model

```sql
SELECT
    FUNCTION_NAME,
    MODEL_NAME,
    COUNT(*)       AS call_count,
    SUM(CREDITS)   AS total_credits
FROM SNOWFLAKE.ACCOUNT_USAGE.CORTEX_AI_FUNCTIONS_USAGE_HISTORY
WHERE START_TIME >= DATEADD('day', -30, CURRENT_TIMESTAMP())
  AND IS_COMPLETED = TRUE
GROUP BY 1, 2
ORDER BY total_credits DESC;
```

#### B. Per-query AI spend by user and query tag (for chargeback)

```sql
SELECT
    DATE_TRUNC('day', START_TIME) AS usage_day,
    USER_ID,
    MODEL_NAME,
    FUNCTION_NAME,
    QUERY_TAG,
    SUM(CREDITS)                  AS total_credits,
    COUNT(*)                      AS call_count
FROM SNOWFLAKE.ACCOUNT_USAGE.CORTEX_AI_FUNCTIONS_USAGE_HISTORY
WHERE START_TIME >= DATEADD('day', -30, CURRENT_TIMESTAMP())
  AND IS_COMPLETED = TRUE
GROUP BY 1, 2, 3, 4, 5
ORDER BY usage_day DESC, total_credits DESC;
```

> **Chargeback tip:** Tag application queries with `ALTER SESSION SET QUERY_TAG = '{"team":"data-science","project":"chatbot-v2"}';` before calling AI functions. The QUERY_TAG column captures this JSON and enables per-team attribution.

#### C. AI spend by warehouse

```sql
SELECT
    COALESCE(wh.WAREHOUSE_NAME, h.WAREHOUSE_ID::STRING) AS warehouse_name,
    h.MODEL_NAME,
    SUM(h.CREDITS) AS ai_credits,
    COUNT(*)       AS call_count
FROM SNOWFLAKE.ACCOUNT_USAGE.CORTEX_AI_FUNCTIONS_USAGE_HISTORY h
LEFT JOIN (
    SELECT DISTINCT WAREHOUSE_ID, WAREHOUSE_NAME
    FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
) wh ON h.WAREHOUSE_ID = wh.WAREHOUSE_ID
WHERE h.START_TIME >= DATEADD('day', -30, CURRENT_TIMESTAMP())
  AND h.IS_COMPLETED = TRUE
GROUP BY 1, 2
ORDER BY ai_credits DESC;
```

#### D. Cortex Agent spend by agent name

```sql
SELECT
    USER_NAME,
    AGENT_NAME,
    DATE_TRUNC('day', START_TIME) AS usage_day,
    SUM(TOKEN_CREDITS)            AS total_credits,
    SUM(TOKENS)                   AS total_tokens
FROM SNOWFLAKE.ACCOUNT_USAGE.CORTEX_AGENT_USAGE_HISTORY
WHERE START_TIME >= DATEADD('day', -30, CURRENT_TIMESTAMP())
GROUP BY 1, 2, 3
ORDER BY usage_day DESC, total_credits DESC;
```

#### E. REST API spend (external apps, MCP servers, CoCo)

```sql
SELECT
    USER_ID,
    MODEL_NAME,
    DATE_TRUNC('day', START_TIME) AS usage_day,
    QUERY_TAG,
    SUM(TOKENS)                   AS total_tokens
FROM SNOWFLAKE.ACCOUNT_USAGE.CORTEX_REST_API_USAGE_HISTORY
WHERE START_TIME >= DATEADD('day', -30, CURRENT_TIMESTAMP())
GROUP BY 1, 2, 3, 4
ORDER BY usage_day DESC, total_tokens DESC;
```

#### F. Input vs output token breakdown (advanced)

The `METRICS` column in `CORTEX_AI_FUNCTIONS_USAGE_HISTORY` is an ARRAY of `{"key":{"metric":"input"|"output","unit":"tokens"},"value":<N>}`:

```sql
SELECT
    MODEL_NAME,
    FUNCTION_NAME,
    SUM(CASE WHEN m.value:key:metric::STRING = 'input'
             THEN m.value:value::NUMBER ELSE 0 END)  AS input_tokens,
    SUM(CASE WHEN m.value:key:metric::STRING = 'output'
             THEN m.value:value::NUMBER ELSE 0 END)  AS output_tokens,
    SUM(CREDITS) AS total_credits
FROM SNOWFLAKE.ACCOUNT_USAGE.CORTEX_AI_FUNCTIONS_USAGE_HISTORY,
    LATERAL FLATTEN(input => METRICS) m
WHERE START_TIME >= DATEADD('day', -30, CURRENT_TIMESTAMP())
  AND IS_COMPLETED = TRUE
GROUP BY 1, 2
ORDER BY total_credits DESC;
```

---

### Step 3: Model Cost vs Quality — Which Model for Which Task?

This step addresses the "which model is best for my workload?" question using two approaches: **cost data** and **quality evaluation**.

#### A. Measure actual cost per model for your workload

```sql
SELECT
    MODEL_NAME,
    FUNCTION_NAME,
    COUNT(*)             AS query_count,
    SUM(CREDITS)         AS total_credits,
    AVG(CREDITS)         AS avg_credits_per_call
FROM SNOWFLAKE.ACCOUNT_USAGE.CORTEX_AI_FUNCTIONS_USAGE_HISTORY
WHERE START_TIME >= DATEADD('day', -7, CURRENT_TIMESTAMP())
  AND QUERY_TAG LIKE '%model_test%'
GROUP BY 1, 2
ORDER BY avg_credits_per_call ASC;
```

> **Test method:** Run the same prompt through multiple models with a tagged test query, then compare costs above.

#### B. Decision framework by task type

| Task Type | Recommended Model | Why |
|-----------|------------------|-----|
| **High-volume extraction / classification** (structured output, 10M+ rows) | `snowflake-arctic` or `llama3.1-8b` | Lowest cost per token; good for narrow, well-defined tasks |
| **Summarization / generation** (moderate quality, cost-sensitive) | `mistral-large` or `llama3.1-70b` | Mid-tier cost, strong quality for most enterprise tasks |
| **Complex reasoning / agentic workflows** (accuracy > cost) | `claude-sonnet-4-5`, `claude-sonnet-4-6` | Highest reasoning quality; use when errors are expensive |
| **Code generation / SQL** | `claude-sonnet-4-5` or `llama3.1-70b` | Strong code quality; Claude excels at structured output |
| **Embeddings / semantic search** | `snowflake-arctic-embed-l-v2.0` | Snowflake-native; integrates with Cortex Search |
| **Document parsing (OCR)** | via `AI_PARSE_DOCUMENT` | Dedicated document pipeline; billed per 1,000 pages |

#### C. Use AI Observability to benchmark model quality

For a rigorous "which model is best for MY task" evaluation, use [AI Observability](https://docs.snowflake.com/en/user-guide/snowflake-cortex/ai-observability):

1. **Create a test dataset** — a table with input prompts and (optionally) expected outputs
2. **Run same inputs through multiple models** — different application "versions"
3. **Use AI Observability evaluations** to score quality metrics:
   - **Answer relevance** — is the response relevant to the question?
   - **Groundedness** — is the response grounded in retrieved context?
   - **Context relevance** — are the search results relevant?
   - **Factual correctness** — for summarization tasks
4. **Compare evaluations side-by-side** in Snowsight to see cost vs quality tradeoff

```sql
-- After running evaluations, query results
SELECT *
FROM TABLE(SNOWFLAKE.LOCAL.GET_AI_EVALUATION_DATA(
    '<database>', '<schema>', '<app_name>', 'EXTERNAL AGENT', '<run_name>'
))
ORDER BY TIMESTAMP DESC;
```

AI Observability uses `AI_COMPLETE` as an LLM judge — so there is a small credit cost for running evaluations, but this is minor compared to the insight gained.

**Prerequisites for AI Observability:**
- `CORTEX_USER` database role
- `CREATE EXTERNAL AGENT` privilege on schema
- Python packages: `trulens-core`, `trulens-connectors-snowflake`, `trulens-providers-cortex` (v2.1.2+)

✋ **STOP** — confirm whether user wants to proceed to budget setup or stop at reporting/model selection.

---

### Step 4: Set Budgets and Alerts

#### Option A: Resource monitor scoped to AI warehouse

```sql
CREATE RESOURCE MONITOR ai_budget
    WITH CREDIT_QUOTA = 500
    FREQUENCY = MONTHLY
    START_TIMESTAMP = IMMEDIATELY
    TRIGGERS
        ON 80 PERCENT DO NOTIFY
        ON 100 PERCENT DO SUSPEND;

ALTER WAREHOUSE ai_workload_wh SET RESOURCE_MONITOR = ai_budget;
```

#### Option B: Alert on daily AI spend spike

```sql
CREATE OR REPLACE ALERT ai_spend_alert
    WAREHOUSE = alert_wh
    SCHEDULE = '1440 MINUTES'
    IF (EXISTS (
        SELECT 1 FROM SNOWFLAKE.ACCOUNT_USAGE.CORTEX_AI_FUNCTIONS_USAGE_HISTORY
        WHERE START_TIME >= DATEADD('day', -1, CURRENT_TIMESTAMP())
        HAVING SUM(CREDITS) > 100
    ))
    THEN CALL SYSTEM$SEND_EMAIL(
        'your_email_integration',
        'ai-ops@yourcompany.com',
        'Cortex AI spend alert',
        'Daily AI credits exceeded threshold.'
    );
```

---

### Step 5: Build a Chargeback/Showback Report

```sql
WITH ai_tagged AS (
    SELECT
        DATE_TRUNC('month', START_TIME) AS month,
        TRY_PARSE_JSON(QUERY_TAG):team::STRING     AS team,
        TRY_PARSE_JSON(QUERY_TAG):project::STRING  AS project,
        MODEL_NAME,
        FUNCTION_NAME,
        SUM(CREDITS) AS credits
    FROM SNOWFLAKE.ACCOUNT_USAGE.CORTEX_AI_FUNCTIONS_USAGE_HISTORY
    WHERE START_TIME >= DATEADD('month', -1, DATE_TRUNC('month', CURRENT_TIMESTAMP()))
      AND START_TIME  < DATE_TRUNC('month', CURRENT_TIMESTAMP())
      AND IS_COMPLETED = TRUE
    GROUP BY 1, 2, 3, 4, 5
)
SELECT
    month,
    COALESCE(team, 'untagged') AS team,
    COALESCE(project, 'untagged') AS project,
    MODEL_NAME,
    FUNCTION_NAME,
    credits,
    ROUND(credits / SUM(credits) OVER (PARTITION BY month) * 100, 2) AS pct_of_total
FROM ai_tagged
ORDER BY month DESC, credits DESC;
```

> **If spend is mostly "untagged"**: guide the team to add `QUERY_TAG` to their application sessions. For dbt, use `query_comment`. For Python, set `session.query_tag`. For Streamlit, use `st.connection` with `query_tag` param.

---

### Step 5b: Programmatic Access via API

For automation, CI/CD, or external dashboards — access the same data and set budgets programmatically.

#### Cost attribution via REST API

```bash
# Snowflake SQL API — run any attribution query programmatically
curl -X POST "https://<account>.snowflakecomputing.com/api/v2/statements" \
  -H "Authorization: Bearer $SNOWFLAKE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "statement": "SELECT FUNCTION_NAME, MODEL_NAME, SUM(CREDITS) AS total_credits FROM SNOWFLAKE.ACCOUNT_USAGE.CORTEX_AI_FUNCTIONS_USAGE_HISTORY WHERE START_TIME >= DATEADD(day, -30, CURRENT_TIMESTAMP()) AND IS_COMPLETED = TRUE GROUP BY 1, 2 ORDER BY total_credits DESC",
    "warehouse": "COMPUTE_WH",
    "role": "ACCOUNTADMIN"
  }'
```

#### Cost attribution via Python

```python
from snowflake.connector import connect

conn = connect(connection_name="default")  # uses connections.toml
cur = conn.cursor()

# Get AI spend by model for last 30 days
cur.execute("""
    SELECT MODEL_NAME, FUNCTION_NAME, SUM(CREDITS) AS total_credits,
           SUM(CREDITS) * 2.00 AS estimated_usd
    FROM SNOWFLAKE.ACCOUNT_USAGE.CORTEX_AI_FUNCTIONS_USAGE_HISTORY
    WHERE START_TIME >= DATEADD('day', -30, CURRENT_TIMESTAMP())
      AND IS_COMPLETED = TRUE
    GROUP BY 1, 2 ORDER BY total_credits DESC
""")
for row in cur:
    print(f"{row[0]:30s} {row[1]:15s} {row[2]:.4f} credits  ${row[3]:.2f}")
```

#### Set budgets via API

```python
# Create or update a resource monitor programmatically
cur.execute("""
    CREATE OR REPLACE RESOURCE MONITOR ai_monthly_budget
        WITH CREDIT_QUOTA = 1000
        FREQUENCY = MONTHLY
        START_TIMESTAMP = IMMEDIATELY
        TRIGGERS
            ON 50 PERCENT DO NOTIFY
            ON 80 PERCENT DO NOTIFY
            ON 100 PERCENT DO SUSPEND
""")

# Attach to warehouse
cur.execute("ALTER WAREHOUSE ai_wh SET RESOURCE_MONITOR = ai_monthly_budget")

# Or use Snowflake Budgets (account-level, more granular)
cur.execute("""
    CALL SNOWFLAKE.LOCAL.ACCOUNT_ROOT_BUDGET!SET_SPENDING_LIMIT(1000)
""")
```

#### Scheduled cost report via Snowflake Task

```sql
-- Auto-send daily AI spend summary via email
CREATE OR REPLACE TASK daily_ai_cost_report
    WAREHOUSE = compute_wh
    SCHEDULE = 'USING CRON 0 8 * * * America/Los_Angeles'
AS
CALL SYSTEM$SEND_EMAIL(
    'cost_alert_integration',
    'finops@yourcompany.com',
    'Daily Cortex AI Spend Report',
    (SELECT LISTAGG(MODEL_NAME || ': ' || total_credits::STRING || ' credits', '\n')
     FROM (SELECT MODEL_NAME, SUM(CREDITS) AS total_credits
           FROM SNOWFLAKE.ACCOUNT_USAGE.CORTEX_AI_FUNCTIONS_USAGE_HISTORY
           WHERE START_TIME >= DATEADD('day', -1, CURRENT_TIMESTAMP())
             AND IS_COMPLETED = TRUE
           GROUP BY 1 ORDER BY total_credits DESC))
);
ALTER TASK daily_ai_cost_report RESUME;
```

---

---

### Step 6: Produce Deliverable

✋ **STOP** — ask the user which output format they want. Default is **Streamlit app**.

| Format | What they get |
|--------|--------------|
| **Streamlit app** (default) | Deployable multi-page dashboard with filters, charts, and export |
| **HTML report** | Self-contained file with charts, shareable via email |
| **Excel export** | .xlsx with chargeback data for finance teams |
| **SQL only** | Raw queries to run in Snowsight (steps 2-5 above) |

---

#### Default: Streamlit AI Spend Dashboard

Generate this app and deploy to the customer's account:

```python
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Cortex AI Spend Tracker", layout="wide")
conn = st.connection("snowflake")

st.title("Cortex AI Spend Tracker")

# Sidebar filters
days = st.sidebar.slider("Lookback (days)", 7, 90, 30)

# --- KPI metrics row ---
total = conn.query(f"""
    SELECT
        SUM(CREDITS) AS total_credits,
        COUNT(DISTINCT MODEL_NAME) AS models_used,
        COUNT(DISTINCT USER_ID) AS active_users,
        COUNT(*) AS total_calls
    FROM SNOWFLAKE.ACCOUNT_USAGE.CORTEX_AI_FUNCTIONS_USAGE_HISTORY
    WHERE START_TIME >= DATEADD('day', -{days}, CURRENT_TIMESTAMP())
      AND IS_COMPLETED = TRUE
""")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total AI Credits", f"{total['TOTAL_CREDITS'].iloc[0]:.2f}")
c2.metric("Models Used", total['MODELS_USED'].iloc[0])
c3.metric("Active Users", total['ACTIVE_USERS'].iloc[0])
c4.metric("Total Calls", f"{total['TOTAL_CALLS'].iloc[0]:,}")

# --- Spend by model ---
st.subheader("Credits by Model")
by_model = conn.query(f"""
    SELECT MODEL_NAME, FUNCTION_NAME, SUM(CREDITS) AS credits, COUNT(*) AS calls
    FROM SNOWFLAKE.ACCOUNT_USAGE.CORTEX_AI_FUNCTIONS_USAGE_HISTORY
    WHERE START_TIME >= DATEADD('day', -{days}, CURRENT_TIMESTAMP())
      AND IS_COMPLETED = TRUE
    GROUP BY 1, 2 ORDER BY credits DESC
""")
st.bar_chart(by_model.set_index("MODEL_NAME")["CREDITS"])
st.dataframe(by_model, use_container_width=True)

# --- Daily trend ---
st.subheader("Daily Spend Trend")
daily = conn.query(f"""
    SELECT DATE_TRUNC('day', START_TIME)::DATE AS day, SUM(CREDITS) AS credits
    FROM SNOWFLAKE.ACCOUNT_USAGE.CORTEX_AI_FUNCTIONS_USAGE_HISTORY
    WHERE START_TIME >= DATEADD('day', -{days}, CURRENT_TIMESTAMP())
      AND IS_COMPLETED = TRUE
    GROUP BY 1 ORDER BY 1
""")
st.line_chart(daily.set_index("DAY")["CREDITS"])

# --- Spend by user ---
st.subheader("Top Users by AI Spend")
by_user = conn.query(f"""
    SELECT USER_ID, SUM(CREDITS) AS credits, COUNT(*) AS calls
    FROM SNOWFLAKE.ACCOUNT_USAGE.CORTEX_AI_FUNCTIONS_USAGE_HISTORY
    WHERE START_TIME >= DATEADD('day', -{days}, CURRENT_TIMESTAMP())
      AND IS_COMPLETED = TRUE
    GROUP BY 1 ORDER BY credits DESC LIMIT 20
""")
st.dataframe(by_user, use_container_width=True)

# --- Chargeback by query tag ---
st.subheader("Chargeback by Team (QUERY_TAG)")
by_tag = conn.query(f"""
    SELECT
        COALESCE(TRY_PARSE_JSON(QUERY_TAG):team::STRING, 'untagged') AS team,
        COALESCE(TRY_PARSE_JSON(QUERY_TAG):project::STRING, 'untagged') AS project,
        MODEL_NAME,
        SUM(CREDITS) AS credits
    FROM SNOWFLAKE.ACCOUNT_USAGE.CORTEX_AI_FUNCTIONS_USAGE_HISTORY
    WHERE START_TIME >= DATEADD('day', -{days}, CURRENT_TIMESTAMP())
      AND IS_COMPLETED = TRUE
    GROUP BY 1, 2, 3 ORDER BY credits DESC
""")
st.dataframe(by_tag, use_container_width=True)

# --- Agent spend ---
st.subheader("Cortex Agent Spend")
agents = conn.query(f"""
    SELECT USER_NAME, AGENT_NAME, SUM(TOKEN_CREDITS) AS credits, SUM(TOKENS) AS tokens
    FROM SNOWFLAKE.ACCOUNT_USAGE.CORTEX_AGENT_USAGE_HISTORY
    WHERE START_TIME >= DATEADD('day', -{days}, CURRENT_TIMESTAMP())
    GROUP BY 1, 2 ORDER BY credits DESC
""")
st.dataframe(agents, use_container_width=True)

# --- Export ---
st.subheader("Export")
st.download_button("Download as CSV", by_model.to_csv(index=False), "ai_spend.csv")
```

**Deployment:**
```sql
CREATE STREAMLIT IF NOT EXISTS ai_spend_tracker
    ROOT_LOCATION = '@<stage>/ai_spend_tracker'
    MAIN_FILE = 'app.py'
    QUERY_WAREHOUSE = '<warehouse>';
```

---

#### HTML Report

Generate a self-contained HTML file with embedded charts using the data from Step 2 queries. Include:
- KPI header (total credits, models used, active users)
- Bar chart: credits by model
- Line chart: daily trend
- Table: chargeback by team

Use the `html-authoring` skill for rendering. Save as `ai_spend_report_<YYYY-MM-DD>.html`.

---

#### Excel Export

```python
import pandas as pd

# After running queries, write to Excel with multiple sheets
with pd.ExcelWriter('ai_spend_chargeback.xlsx') as writer:
    by_model_df.to_excel(writer, sheet_name='By Model', index=False)
    by_user_df.to_excel(writer, sheet_name='By User', index=False)
    by_tag_df.to_excel(writer, sheet_name='Chargeback', index=False)
    agents_df.to_excel(writer, sheet_name='Agents', index=False)
```

---

## Stopping Points

- ✋ After Step 1: Confirm scope (time window, dimension, goal)
- ✋ After Step 3: Confirm whether user wants budget setup or just reporting
- ✋ After Step 6: Confirm output format (default: Streamlit app)

## Output

- **Streamlit app** (default): deployable multi-page dashboard with KPIs, charts, chargeback table, export button
- **HTML report**: self-contained shareable file with embedded charts
- **Excel**: .xlsx with per-model, per-user, chargeback, and agent sheets
- **SQL only**: raw queries for Snowsight
- **Model selection guidance**: decision framework table + AI Observability evaluation instructions
- **Optional**: resource monitor / alert DDL for spend control
