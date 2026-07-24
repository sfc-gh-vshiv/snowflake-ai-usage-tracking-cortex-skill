import streamlit as st
import pandas as pd
from snowflake.snowpark.context import get_active_session

st.set_page_config(
    page_title="Cortex AI Spend Tracker",
    page_icon=":material/bolt:",
    layout="wide",
    initial_sidebar_state="expanded",
)

session = get_active_session()

# --- Design system ---
from modules.styles import (
    apply_styles, metric_card, alert_card, badge,
    cta_banner, insight_item, section_header, SNOWFLAKE_LOGO,
)


apply_styles()


def query(sql: str) -> pd.DataFrame:
    return session.sql(sql).to_pandas()


# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.image(SNOWFLAKE_LOGO, width=140)
    st.markdown("### Settings")
    days = st.slider("Lookback (days)", 7, 90, 30)

    st.markdown("---")
    st.markdown("**Data Sources**")
    st.caption(
        "SNOWFLAKE.ACCOUNT_USAGE:\n"
        "- CORTEX_AI_FUNCTIONS_USAGE_HISTORY\n"
        "- CORTEX_AGENT_USAGE_HISTORY\n"
        "- CORTEX_REST_API_USAGE_HISTORY\n"
        "- WAREHOUSE_METERING_HISTORY\n"
        "- RATE_SHEET_DAILY (Org Usage)"
    )

# ============================================================
# RATE LOOKUP
# ============================================================
rate_df = query("""
    SELECT EFFECTIVE_RATE
    FROM SNOWFLAKE.ORGANIZATION_USAGE.RATE_SHEET_DAILY
    WHERE DATE = (SELECT MAX(DATE) FROM SNOWFLAKE.ORGANIZATION_USAGE.RATE_SHEET_DAILY)
      AND ACCOUNT_LOCATOR = CURRENT_ACCOUNT()
      AND SERVICE_TYPE IN ('AI_FUNCTIONS', 'AI_INFERENCE', 'CORTEX_AGENTS')
    LIMIT 1
""")
if len(rate_df) > 0:
    rate = float(rate_df.iloc[0, 0])
    rate_source = "RATE_SHEET_DAILY (includes discounts)"
else:
    rate = 2.00
    rate_source = "Default $2.00/credit"

with st.sidebar:
    st.markdown("---")
    st.metric("Rate per AI Credit", f"${rate:.2f}")
    st.caption(rate_source)

# ============================================================
# HEADER
# ============================================================
acct = query("SELECT CURRENT_ACCOUNT()").iloc[0, 0]
st.markdown("<h1>Cortex AI Spend Tracker</h1>", unsafe_allow_html=True)
st.markdown(f"**Track, attribute, and optimize your Snowflake Cortex AI spend** | Account: `{acct}` | Last {days} days")

# ============================================================
# KPI ROW
# ============================================================
kpi = query(f"""
    SELECT
        COALESCE(SUM(CREDITS), 0) AS total_credits,
        COUNT(DISTINCT MODEL_NAME) AS models_used,
        COUNT(DISTINCT USER_ID) AS active_users,
        COUNT(*) AS total_calls
    FROM SNOWFLAKE.ACCOUNT_USAGE.CORTEX_AI_FUNCTIONS_USAGE_HISTORY
    WHERE START_TIME >= DATEADD('day', -{days}, CURRENT_TIMESTAMP())
      AND IS_COMPLETED = TRUE
""")
agent_kpi = query(f"""
    SELECT COALESCE(SUM(TOKEN_CREDITS), 0) AS agent_credits,
           COUNT(DISTINCT AGENT_NAME) AS agent_count
    FROM SNOWFLAKE.ACCOUNT_USAGE.CORTEX_AGENT_USAGE_HISTORY
    WHERE START_TIME >= DATEADD('day', -{days}, CURRENT_TIMESTAMP())
""")

total_credits = float(kpi["TOTAL_CREDITS"].iloc[0]) + float(agent_kpi["AGENT_CREDITS"].iloc[0])
total_usd = total_credits * rate

c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    st.markdown(metric_card("Total AI Credits", f"{total_credits:.2f}", f"${total_usd:.2f} USD"), unsafe_allow_html=True)
with c2:
    st.markdown(metric_card("AI Function Calls", f"{int(kpi['TOTAL_CALLS'].iloc[0]):,}", f"Last {days} days", "green"), unsafe_allow_html=True)
with c3:
    st.markdown(metric_card("Models Used", str(int(kpi["MODELS_USED"].iloc[0])), "Distinct models"), unsafe_allow_html=True)
with c4:
    st.markdown(metric_card("Active Users", str(int(kpi["ACTIVE_USERS"].iloc[0] or 0)), "Distinct user IDs", "purple"), unsafe_allow_html=True)
with c5:
    st.markdown(metric_card("Agents Active", str(int(agent_kpi["AGENT_COUNT"].iloc[0])), f"{float(agent_kpi['AGENT_CREDITS'].iloc[0]):.2f} credits", "orange"), unsafe_allow_html=True)

# Store context for Ask
st.session_state["ask_context"] = (
    f"Total AI Credits (last {days} days): {total_credits:.2f} (${total_usd:.2f}). "
    f"Models used: {int(kpi['MODELS_USED'].iloc[0])}. "
    f"Calls: {int(kpi['TOTAL_CALLS'].iloc[0])}. "
    f"Agents: {int(agent_kpi['AGENT_COUNT'].iloc[0])} ({float(agent_kpi['AGENT_CREDITS'].iloc[0]):.2f} credits). "
    f"Rate: ${rate:.2f}/credit ({rate_source})."
)

# ============================================================
# TABS
# ============================================================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Overview",
    "By Model",
    "By Warehouse",
    "Agents",
    "REST API & CoCo",
])

# ============================================================
# TAB 1: OVERVIEW
# ============================================================
with tab1:
    with st.spinner("Loading overview..."):
        st.markdown(section_header("DAILY SPEND TREND"), unsafe_allow_html=True)
        daily = query(f"""
        SELECT DATE_TRUNC('day', START_TIME)::DATE AS day,
               SUM(CREDITS) AS credits
        FROM SNOWFLAKE.ACCOUNT_USAGE.CORTEX_AI_FUNCTIONS_USAGE_HISTORY
        WHERE START_TIME >= DATEADD('day', -{days}, CURRENT_TIMESTAMP())
          AND IS_COMPLETED = TRUE
        GROUP BY 1 ORDER BY 1
    """)
        if len(daily) > 0:
            daily["USD"] = daily["CREDITS"].astype(float) * rate
            st.line_chart(daily.set_index("DAY")[["CREDITS", "USD"]])
        else:
            st.markdown(cta_banner("No AI function usage found in this period. Try increasing the lookback.", kind="blue"), unsafe_allow_html=True)

        # Spend by function
        st.markdown(section_header("SPEND BY FUNCTION TYPE"), unsafe_allow_html=True)
        by_func = query(f"""
            SELECT FUNCTION_NAME, SUM(CREDITS) AS credits, COUNT(*) AS calls
            FROM SNOWFLAKE.ACCOUNT_USAGE.CORTEX_AI_FUNCTIONS_USAGE_HISTORY
            WHERE START_TIME >= DATEADD('day', -{days}, CURRENT_TIMESTAMP())
              AND IS_COMPLETED = TRUE
            GROUP BY 1 ORDER BY credits DESC
        """)
        if len(by_func) > 0:
            by_func["USD"] = by_func["CREDITS"].astype(float) * rate
            col_a, col_b = st.columns([1, 2])
            with col_a:
                st.dataframe(by_func, use_container_width=True)
            with col_b:
                st.bar_chart(by_func.set_index("FUNCTION_NAME")["USD"])

    # AI Insights
    with st.spinner("Generating AI insights..."):
        st.markdown(section_header("AI-GENERATED INSIGHTS"), unsafe_allow_html=True)
        if total_credits > 0:
            model_summary = query(f"""
                SELECT COALESCE(NULLIF(MODEL_NAME,''), '(default)') AS model,
                       FUNCTION_NAME, COUNT(*) AS calls, SUM(CREDITS) AS credits,
                       AVG(CREDITS) AS avg_per_call
                FROM SNOWFLAKE.ACCOUNT_USAGE.CORTEX_AI_FUNCTIONS_USAGE_HISTORY
                WHERE START_TIME >= DATEADD('day', -{days}, CURRENT_TIMESTAMP()) AND IS_COMPLETED = TRUE
                GROUP BY 1, 2 ORDER BY credits DESC LIMIT 10
            """)
            summary_text = model_summary.to_string(index=False)

            try:
                prompt = f"""You are a FinOps advisor for Snowflake Cortex AI. Given this spend data, provide exactly 4 bullet-point recommendations. Be specific about model names and estimated savings. Keep each bullet under 30 words.

Spend data (last {days} days, rate ${rate:.2f}/credit):
{summary_text}

Total: {total_credits:.2f} credits (${total_usd:.2f})

Recommendations:"""
                insights_result = session.sql(f"""
                    SELECT SNOWFLAKE.CORTEX.COMPLETE('claude-sonnet-4-5', $${prompt}$$)
                """).collect()
                insights_text = insights_result[0][0]
                for line in insights_text.strip().split("\n"):
                    line = line.strip()
                    if line and (line.startswith("-") or line.startswith("*") or line[0].isdigit()):
                        clean = line.lstrip("-*0123456789. ")
                        st.markdown(insight_item(clean), unsafe_allow_html=True)
            except Exception as e:
                st.markdown(alert_card(f"Could not generate insights: {str(e)[:100]}", kind="warning"), unsafe_allow_html=True)
        else:
            st.markdown(cta_banner("No spend data available to generate insights.", kind="blue"), unsafe_allow_html=True)

# ============================================================
# TAB 2: BY MODEL
# ============================================================
with tab2:
    with st.spinner("Loading model data..."):
        st.markdown(section_header("COST BY MODEL"), unsafe_allow_html=True)
        by_model = query(f"""
        SELECT
            COALESCE(NULLIF(MODEL_NAME, ''), '(default)') AS model,
            FUNCTION_NAME,
            COUNT(*) AS calls,
            SUM(CREDITS) AS credits,
            AVG(CREDITS) AS avg_per_call
        FROM SNOWFLAKE.ACCOUNT_USAGE.CORTEX_AI_FUNCTIONS_USAGE_HISTORY
        WHERE START_TIME >= DATEADD('day', -{days}, CURRENT_TIMESTAMP())
          AND IS_COMPLETED = TRUE
        GROUP BY 1, 2 ORDER BY credits DESC
    """)
        if len(by_model) > 0:
            by_model["USD"] = by_model["CREDITS"].astype(float) * rate
            by_model["USD_PER_CALL"] = by_model["AVG_PER_CALL"].astype(float) * rate
            st.bar_chart(by_model.groupby("MODEL")["USD"].sum())
            st.dataframe(by_model[["MODEL", "FUNCTION_NAME", "CALLS", "CREDITS", "USD", "USD_PER_CALL"]], use_container_width=True)

        # Token breakdown
        st.markdown(section_header("INPUT vs OUTPUT TOKENS"), unsafe_allow_html=True)
        tokens = query(f"""
            SELECT
                COALESCE(NULLIF(MODEL_NAME, ''), '(default)') AS model,
                FUNCTION_NAME,
                SUM(CASE WHEN m.value:key:metric::STRING = 'input' THEN m.value:value::NUMBER ELSE 0 END) AS input_tokens,
                SUM(CASE WHEN m.value:key:metric::STRING = 'output' THEN m.value:value::NUMBER ELSE 0 END) AS output_tokens,
                SUM(CREDITS) AS credits
            FROM SNOWFLAKE.ACCOUNT_USAGE.CORTEX_AI_FUNCTIONS_USAGE_HISTORY,
                LATERAL FLATTEN(input => METRICS) m
            WHERE START_TIME >= DATEADD('day', -{days}, CURRENT_TIMESTAMP()) AND IS_COMPLETED = TRUE
            GROUP BY 1, 2 ORDER BY credits DESC
        """)
        if len(tokens) > 0:
            st.dataframe(tokens, use_container_width=True)

        # Model selection guide
        st.markdown(section_header("MODEL SELECTION GUIDE"), unsafe_allow_html=True)
        st.markdown("""
| Task Type | Recommended | Why |
|-----------|------------|-----|
| High-volume extraction / classification | `snowflake-arctic`, `llama3.1-8b` | Lowest cost per token |
| Summarization / generation | `mistral-large`, `llama3.1-70b` | Mid-tier cost, strong quality |
| Complex reasoning / agentic | `claude-sonnet-4-5`, `claude-sonnet-4-6` | Highest reasoning quality |
| Code / SQL generation | `claude-sonnet-4-5`, `llama3.1-70b` | Strong structured output |
| Embeddings | `snowflake-arctic-embed-l-v2.0` | Native Cortex Search integration |
| Document OCR | `AI_PARSE_DOCUMENT` | Dedicated pipeline, per-page pricing |
        """)

# ============================================================
# TAB 3: BY WAREHOUSE
# ============================================================
with tab3:
    with st.spinner("Loading warehouse data..."):
        st.markdown(section_header("AI SPEND BY WAREHOUSE"), unsafe_allow_html=True)
        by_wh = query(f"""
        SELECT
            COALESCE(wh.WAREHOUSE_NAME, h.WAREHOUSE_ID::STRING) AS warehouse_name,
            COALESCE(NULLIF(h.MODEL_NAME, ''), '(default)') AS model,
            SUM(h.CREDITS) AS credits, COUNT(*) AS calls
        FROM SNOWFLAKE.ACCOUNT_USAGE.CORTEX_AI_FUNCTIONS_USAGE_HISTORY h
        LEFT JOIN (SELECT DISTINCT WAREHOUSE_ID, WAREHOUSE_NAME FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY) wh
          ON h.WAREHOUSE_ID = wh.WAREHOUSE_ID
        WHERE h.START_TIME >= DATEADD('day', -{days}, CURRENT_TIMESTAMP()) AND h.IS_COMPLETED = TRUE
        GROUP BY 1, 2 ORDER BY credits DESC
    """)
        if len(by_wh) > 0:
            by_wh["USD"] = by_wh["CREDITS"].astype(float) * rate
            st.bar_chart(by_wh.groupby("WAREHOUSE_NAME")["USD"].sum())
            st.dataframe(by_wh, use_container_width=True)

        # Chargeback
        st.markdown(section_header("CHARGEBACK BY TEAM (QUERY_TAG)"), unsafe_allow_html=True)
        by_tag = query(f"""
            SELECT
                COALESCE(TRY_PARSE_JSON(QUERY_TAG):team::STRING, 'untagged') AS team,
                COALESCE(TRY_PARSE_JSON(QUERY_TAG):project::STRING, 'untagged') AS project,
                COALESCE(NULLIF(MODEL_NAME, ''), '(default)') AS model,
                SUM(CREDITS) AS credits, COUNT(*) AS calls
            FROM SNOWFLAKE.ACCOUNT_USAGE.CORTEX_AI_FUNCTIONS_USAGE_HISTORY
            WHERE START_TIME >= DATEADD('day', -{days}, CURRENT_TIMESTAMP()) AND IS_COMPLETED = TRUE
            GROUP BY 1, 2, 3 ORDER BY credits DESC
        """)
        if len(by_tag) > 0:
            by_tag["USD"] = by_tag["CREDITS"].astype(float) * rate
            total_spend = by_tag["CREDITS"].astype(float).sum()
            untagged = by_tag[by_tag["TEAM"] == "untagged"]["CREDITS"].astype(float).sum()
            tagged_pct = (1 - untagged / total_spend) * 100 if total_spend > 0 else 0
            if tagged_pct < 50:
                st.markdown(alert_card(
                    f"Only <b>{tagged_pct:.0f}%</b> of spend is tagged. Use <code>ALTER SESSION SET QUERY_TAG = "
                    "'{\"team\":\"...\",\"project\":\"...\"}';</code> before AI calls to enable chargeback.",
                    kind="warning"
                ), unsafe_allow_html=True)
            else:
                st.markdown(alert_card(f"{tagged_pct:.0f}% of spend is tagged for chargeback.", kind="success"), unsafe_allow_html=True)
            st.dataframe(by_tag, use_container_width=True)

# ============================================================
# TAB 4: AGENTS
# ============================================================
with tab4:
    with st.spinner("Loading agent data..."):
        st.markdown(section_header("CORTEX AGENT SPEND"), unsafe_allow_html=True)
        agents = query(f"""
        SELECT USER_NAME, AGENT_NAME, DATE_TRUNC('day', START_TIME)::DATE AS usage_day,
               SUM(TOKEN_CREDITS) AS credits, SUM(TOKENS) AS tokens
        FROM SNOWFLAKE.ACCOUNT_USAGE.CORTEX_AGENT_USAGE_HISTORY
        WHERE START_TIME >= DATEADD('day', -{days}, CURRENT_TIMESTAMP())
        GROUP BY 1, 2, 3 ORDER BY usage_day DESC, credits DESC
    """)
        if len(agents) > 0:
            agents["CREDITS"] = agents["CREDITS"].astype(float)
            agents["USD"] = agents["CREDITS"] * rate
            mc1, mc2 = st.columns(2)
            with mc1:
                st.markdown(metric_card("Total Agent Credits", f"{agents['CREDITS'].sum():.2f}", f"${agents['USD'].sum():.2f}"), unsafe_allow_html=True)
            with mc2:
                st.markdown(metric_card("Agent Sessions", str(len(agents)), f"{agents['AGENT_NAME'].nunique()} distinct agents", "purple"), unsafe_allow_html=True)
            st.bar_chart(agents.groupby("AGENT_NAME")["USD"].sum())
            st.dataframe(agents, use_container_width=True)
        else:
            st.markdown(cta_banner("No Cortex Agent usage in this period.", kind="blue"), unsafe_allow_html=True)

# ============================================================
# TAB 5: REST API & COCO
# ============================================================
with tab5:
    with st.spinner("Loading REST API data..."):
        st.markdown(section_header("REST API / CORTEX CODE USAGE"), unsafe_allow_html=True)
        rest = query(f"""
        SELECT USER_ID, MODEL_NAME, DATE_TRUNC('day', START_TIME)::DATE AS usage_day,
               COALESCE(QUERY_TAG, '') AS query_tag, SUM(TOKENS) AS total_tokens
        FROM SNOWFLAKE.ACCOUNT_USAGE.CORTEX_REST_API_USAGE_HISTORY
        WHERE START_TIME >= DATEADD('day', -{days}, CURRENT_TIMESTAMP())
        GROUP BY 1, 2, 3, 4 ORDER BY usage_day DESC, total_tokens DESC
    """)
        if len(rest) > 0:
            st.markdown(metric_card("Total REST API Tokens", f"{rest['TOTAL_TOKENS'].astype(float).sum():,.0f}", "Note: tokens only (no credits column in this view)", "orange"), unsafe_allow_html=True)
            st.bar_chart(rest.groupby("MODEL_NAME")["TOTAL_TOKENS"].sum())
            st.dataframe(rest, use_container_width=True)
        else:
            st.markdown(cta_banner("No REST API usage in this period.", kind="blue"), unsafe_allow_html=True)

        # Cortex Code
        st.markdown(section_header("CORTEX CODE SESSIONS"), unsafe_allow_html=True)
        for view in ["CORTEX_CODE_CLI_USAGE_HISTORY", "CORTEX_CODE_DESKTOP_USAGE_HISTORY", "CORTEX_CODE_SNOWSIGHT_USAGE_HISTORY"]:
            try:
                coco = query(f"SELECT * FROM SNOWFLAKE.ACCOUNT_USAGE.{view} WHERE START_TIME >= DATEADD('day', -{days}, CURRENT_TIMESTAMP()) LIMIT 20")
                if len(coco) > 0:
                    st.caption(f"`{view}`")
                    st.dataframe(coco, use_container_width=True)
            except Exception:
                pass


# ============================================================
# FOOTER
# ============================================================
st.markdown("---")
st.markdown(
    f"**Rate:** ${rate:.2f}/credit ({rate_source}) | "
    f"**Period:** Last {days} days | "
    f"[AI Pricing Docs](https://docs.snowflake.com/en/user-guide/snowflake-cortex/pricing) | "
    f"[AI Observability](https://docs.snowflake.com/en/user-guide/snowflake-cortex/ai-observability)"
)

with st.expander("Export Data"):
    export_data = query(f"""
        SELECT DATE_TRUNC('day', START_TIME)::DATE AS day, FUNCTION_NAME, MODEL_NAME, USER_ID, QUERY_TAG,
               CREDITS, CREDITS * {rate} AS estimated_usd
        FROM SNOWFLAKE.ACCOUNT_USAGE.CORTEX_AI_FUNCTIONS_USAGE_HISTORY
        WHERE START_TIME >= DATEADD('day', -{days}, CURRENT_TIMESTAMP()) AND IS_COMPLETED = TRUE
        ORDER BY day DESC, CREDITS DESC
    """)
    st.download_button("Download CSV", export_data.to_csv(index=False), "cortex_ai_spend.csv", "text/csv")

st.caption("Cortex AI Spend Tracker | v2.0.0 | Built with Snowflake Design System")
