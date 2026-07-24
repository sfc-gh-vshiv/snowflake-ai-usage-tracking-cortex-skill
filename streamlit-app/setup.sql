-- ============================================================
-- Cortex AI Spend Tracker — Streamlit-in-Snowflake Setup
-- ============================================================
-- Run this in your Snowflake account to deploy the app.
-- Prerequisites: ACCOUNTADMIN or role with IMPORT SHARE + CREATE STREAMLIT privileges.

-- 1. Create a database (or use an existing one)
CREATE DATABASE IF NOT EXISTS AI_SPEND_DB;
USE DATABASE AI_SPEND_DB;
CREATE SCHEMA IF NOT EXISTS PUBLIC;
USE SCHEMA PUBLIC;

-- 2. Create stage for app files
CREATE STAGE IF NOT EXISTS AI_SPEND_TRACKER_STAGE
  DIRECTORY = (ENABLE = TRUE);

-- 3. Upload files (run from SnowSQL or Snowsight):
--    PUT file://streamlit-app/ai_spend_tracker_app.py @AI_SPEND_TRACKER_STAGE/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
--    PUT file://streamlit-app/modules/styles.py @AI_SPEND_TRACKER_STAGE/modules/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
--    PUT file://streamlit-app/modules/__init__.py @AI_SPEND_TRACKER_STAGE/modules/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE;

-- 4. Create the Streamlit app
CREATE OR REPLACE STREAMLIT AI_SPEND_TRACKER
  ROOT_LOCATION = '@AI_SPEND_TRACKER_STAGE'
  MAIN_FILE = 'ai_spend_tracker_app.py'
  QUERY_WAREHOUSE = 'COMPUTE_WH'   -- change to your warehouse
  TITLE = 'Cortex AI Spend Tracker';

-- 5. Grant access (optional)
-- GRANT USAGE ON STREAMLIT AI_SPEND_TRACKER TO ROLE <your_role>;
