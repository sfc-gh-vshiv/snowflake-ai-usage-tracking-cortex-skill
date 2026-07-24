# Snowflake AI Usage Tracking — Cortex Code Skill

A [Cortex Code](https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code) skill that helps you **track, attribute, and optimize** your Snowflake Cortex AI spend — and decide which AI model works best for which tasks.

## What This Skill Does

| Capability | How |
|-----------|-----|
| **Cost attribution** | Breaks down AI credits by model, user, warehouse, role, and query tag |
| **Dollar cost reporting** | Joins usage views with `RATE_SHEET_DAILY` for your account's actual negotiated rate (including discounts) |
| **Model selection** | Decision framework by task type + AI Observability guidance for quality benchmarking |
| **Chargeback / showback** | Team-level cost allocation via `QUERY_TAG` JSON parsing |
| **Budget & alerts** | Resource monitor DDL, daily spend alerts, Snowflake Task automation |
| **Programmatic access** | REST API, Python connector, and scheduled task examples |

## Output Formats

The skill can produce any of these (default: Streamlit app):

- **Streamlit dashboard** — deployable app with KPIs, charts, and CSV export
- **HTML report** — self-contained shareable file
- **Excel export** — multi-sheet .xlsx for finance teams
- **SQL results** — raw queries for Snowsight

## Data Sources

Queries 18 `SNOWFLAKE.ACCOUNT_USAGE.CORTEX_*` views including:

- `CORTEX_AI_FUNCTIONS_USAGE_HISTORY` — per-query, richest metadata (user, model, role, tag, credits)
- `CORTEX_AGENT_USAGE_HISTORY` — agent-level with per-model granular breakdown
- `CORTEX_REST_API_USAGE_HISTORY` — external app / MCP / CoCo calls
- `RATE_SHEET_DAILY` (Organization Usage) — account-specific discounted dollar rates

## Install in Cortex Code

### Option 1: From skill catalog (Snowflake internal)

```bash
cortex skill catalog install track-cortex-ai-spend
```

### Option 2: From this repo

```bash
# Clone and add locally
git clone https://github.com/sfc-gh-vshiv/snowflake-ai-usage-tracking-cortex-skill.git
cortex skill add ./snowflake-ai-usage-tracking-cortex-skill
```

### Option 3: Direct path (if already cloned)

```bash
cortex skill add /path/to/snowflake-ai-usage-tracking-cortex-skill
```

## Verify It's Loaded

```bash
cortex skill list
```

You should see `track-cortex-ai-spend` in the list.

## Usage

Once installed, just ask Cortex Code questions like:

- "How much am I spending on Cortex AI this month?"
- "Show me AI spend by model"
- "Which AI model should I use for bulk text classification?"
- "Build a chargeback report for AI usage by team"
- "Set up a budget alert for my Cortex AI spend"
- "Which model is cheapest for my summarization workload?"
- "Create a Streamlit dashboard for AI cost tracking"

The skill activates automatically based on these triggers.

## Prerequisites

- **Role:** `ACCOUNTADMIN` or a role with `IMPORTED PRIVILEGES` on the `SNOWFLAKE` database
- **For dollar cost reporting:** `ORGADMIN` access to `SNOWFLAKE.ORGANIZATION_USAGE.RATE_SHEET_DAILY` (falls back to $2.00/credit if unavailable)
- **For AI Observability (model quality benchmarking):** `CORTEX_USER` database role + Python packages (`trulens-core`, `trulens-connectors-snowflake`, `trulens-providers-cortex`)

## How Dollar Cost Is Calculated

```
TOKENS → CREDITS (from usage views) → DOLLARS (credits × EFFECTIVE_RATE from RATE_SHEET_DAILY)
```

The `RATE_SHEET_DAILY` view includes your account's negotiated ACV-based discounts. If not available, the skill falls back to the list price ($2.00 global / $2.20 regional) and flags it clearly.

## File Structure

```
├── SKILL.md              # The skill definition (loaded by Cortex Code)
├── skill_evidence.yaml   # Metadata for skill validation
└── README.md             # This file
```

## Related Resources

- [Snowflake AI Pricing](https://docs.snowflake.com/en/user-guide/snowflake-cortex/pricing)
- [AI Observability](https://docs.snowflake.com/en/user-guide/snowflake-cortex/ai-observability)
- [CORTEX_AGENT_USAGE_HISTORY](https://docs.snowflake.com/en/sql-reference/account-usage/cortex_agent_usage_history)
- [RATE_SHEET_DAILY](https://docs.snowflake.com/en/sql-reference/organization-usage/rate_sheet_daily)

## Contributing

This skill is also submitted to the [Snowflake-Solutions/cortex-code-skills](https://github.com/Snowflake-Solutions/cortex-code-skills) community repo as PR #367.

## License

Apache 2.0
