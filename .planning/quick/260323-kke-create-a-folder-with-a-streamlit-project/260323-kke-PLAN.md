---
phase: quick
plan: 260323-kke
type: execute
wave: 1
depends_on: []
files_modified:
  - reports/app.py
  - reports/pages/opportunities.py
  - reports/pages/activity.py
  - reports/requirements.txt
  - reports/README.md
autonomous: true
requirements: [QUICK-01]

must_haves:
  truths:
    - "User can run `streamlit run reports/app.py` and see a dashboard"
    - "Dashboard shows Opportunity pipeline metrics from PostgreSQL"
    - "Dashboard shows activity metrics (events, tasks) from PostgreSQL"
  artifacts:
    - path: "reports/app.py"
      provides: "Streamlit main entry point with navigation"
    - path: "reports/pages/opportunities.py"
      provides: "Opportunity reporting page"
    - path: "reports/pages/activity.py"
      provides: "Activity (events/tasks) reporting page"
    - path: "reports/requirements.txt"
      provides: "Streamlit dependencies"
  key_links:
    - from: "reports/app.py"
      to: "PostgreSQL"
      via: "psycopg2 connection"
---

<objective>
Create a Streamlit reporting dashboard that showcases the Salesforce data ingested by the Dagster pipeline.

Purpose: Provide immediate visibility into the synced Salesforce data (Opportunities, Events, Tasks, OpportunityHistory) with basic KPIs and visualizations.

Output: A `reports/` folder containing a runnable Streamlit application with multi-page navigation.
</objective>

<context>
**Database Schema (from Dagster assets):**
- `salesforce_opportunities`: salesforce_id, connection_id, data (JSONB), synced_at
- `salesforce_opportunity_history`: salesforce_id, connection_id, data (JSONB), synced_at
- `salesforce_events`: salesforce_id, connection_id, data (JSONB), synced_at
- `salesforce_tasks`: salesforce_id, connection_id, data (JSONB), synced_at

All JSONB `data` columns contain the full Salesforce record. Key fields to extract:
- Opportunity: Name, Amount, StageName, CloseDate, IsClosed, IsWon
- Event: Subject, StartDateTime, EndDateTime, WhoId, WhatId
- Task: Subject, Status, Priority, ActivityDate
- OpportunityHistory: StageName, Amount, CreatedDate (for stage progression)

**Environment:** Uses same DATABASE_URL from .env as Dagster pipeline.
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create Streamlit project structure and main app</name>
  <files>reports/app.py, reports/requirements.txt, reports/__init__.py, reports/pages/__init__.py, reports/db.py</files>
  <action>
    1. Create `reports/` directory structure:
       - reports/__init__.py (empty)
       - reports/pages/__init__.py (empty)

    2. Create `reports/requirements.txt`:
       ```
       streamlit>=1.45.0
       psycopg2-binary>=2.9.9
       pandas>=2.2.0
       plotly>=5.24.0
       python-dotenv>=1.0.0
       ```

    3. Create `reports/db.py` - Database connection helper:
       - Load DATABASE_URL from environment (using python-dotenv to read from .env)
       - Provide `get_connection()` context manager
       - Provide `query_to_df(sql, params)` helper that returns pandas DataFrame
       - Use psycopg2 directly (this is a separate app, not a Dagster asset)

    4. Create `reports/app.py` - Main Streamlit entry point:
       - Set page config with title "Salesforce Data Hub Reports"
       - Create sidebar navigation with st.page_link for multi-page app
       - Show a simple home page with:
         - Title and description
         - Quick stats: count of records in each table (query each table for COUNT(*))
         - Last sync time (MAX(synced_at) from any table)
       - Use Streamlit's native multi-page app structure (pages in pages/ folder)
  </action>
  <verify>
    <automated>cd /Users/renanfonseca/Workspace/defensepoint/staq/data-hub && python -c "import reports.app; import reports.db"</automated>
  </verify>
  <done>
    - reports/ folder exists with proper structure
    - requirements.txt lists all dependencies
    - app.py is valid Python that imports without error
    - db.py provides connection and query helpers
  </done>
</task>

<task type="auto">
  <name>Task 2: Create Opportunities reporting page</name>
  <files>reports/pages/1_opportunities.py</files>
  <action>
    Create `reports/pages/1_opportunities.py` (prefix number controls page order):

    1. Page header: "Opportunity Pipeline"

    2. KPI row using st.columns (4 columns):
       - Total Pipeline Value: SUM of Amount where IsClosed = false
       - Closed Won Value: SUM of Amount where IsWon = true
       - Win Rate: COUNT(IsWon=true) / COUNT(IsClosed=true) as percentage
       - Open Opportunities: COUNT where IsClosed = false

    3. Charts section:
       a. Pipeline by Stage (bar chart):
          - Query: Group by data->>'StageName', SUM Amount
          - Use plotly express bar chart

       b. Opportunities Closing This Month (table):
          - Query: WHERE data->>'CloseDate' is within current month and IsClosed = false
          - Show: Name, Amount, StageName, CloseDate
          - Use st.dataframe with column_config for currency formatting

    4. SQL queries should extract JSONB fields:
       ```sql
       SELECT
         data->>'Name' as name,
         (data->>'Amount')::numeric as amount,
         data->>'StageName' as stage,
         (data->>'IsClosed')::boolean as is_closed,
         (data->>'IsWon')::boolean as is_won
       FROM salesforce_opportunities
       ```

    5. Handle empty data gracefully with st.info messages
  </action>
  <verify>
    <automated>cd /Users/renanfonseca/Workspace/defensepoint/staq/data-hub && python -c "import reports.pages" && test -f reports/pages/1_opportunities.py</automated>
  </verify>
  <done>
    - Opportunities page renders without error
    - Shows 4 KPIs in a row
    - Shows pipeline by stage bar chart
    - Shows closing this month table
    - Handles empty data state
  </done>
</task>

<task type="auto">
  <name>Task 3: Create Activity reporting page</name>
  <files>reports/pages/2_activity.py</files>
  <action>
    Create `reports/pages/2_activity.py`:

    1. Page header: "Sales Activity"

    2. KPI row using st.columns (4 columns):
       - Total Events: COUNT from salesforce_events
       - Total Tasks: COUNT from salesforce_tasks
       - Completed Tasks: COUNT where data->>'Status' = 'Completed'
       - Events This Week: COUNT where StartDateTime is within current week

    3. Activity breakdown section with tabs (st.tabs):

       Tab 1 - Events:
       - Recent events table (last 20, ordered by StartDateTime desc)
       - Columns: Subject, StartDateTime, synced_at

       Tab 2 - Tasks:
       - Tasks by status (pie chart using plotly)
       - Tasks by priority (bar chart)
       - Recent tasks table (last 20)

    4. SQL for events:
       ```sql
       SELECT
         data->>'Subject' as subject,
         data->>'StartDateTime' as start_time,
         synced_at
       FROM salesforce_events
       ORDER BY data->>'StartDateTime' DESC
       LIMIT 20
       ```

    5. SQL for tasks:
       ```sql
       SELECT
         data->>'Subject' as subject,
         data->>'Status' as status,
         data->>'Priority' as priority,
         data->>'ActivityDate' as activity_date
       FROM salesforce_tasks
       ```

    6. Handle empty data gracefully
  </action>
  <verify>
    <automated>cd /Users/renanfonseca/Workspace/defensepoint/staq/data-hub && python -c "from reports.pages import *" && test -f reports/pages/2_activity.py</automated>
  </verify>
  <done>
    - Activity page renders without error
    - Shows 4 KPIs for events and tasks
    - Events tab shows recent events table
    - Tasks tab shows status pie chart, priority bar chart, and recent tasks
    - Handles empty data state
  </done>
</task>

</tasks>

<verification>
After all tasks complete:
1. All files exist in reports/ folder
2. `cd reports && pip install -r requirements.txt` succeeds
3. `source .env && streamlit run reports/app.py --server.headless true` starts without error
</verification>

<success_criteria>
- Streamlit app starts and displays home page with record counts
- Opportunities page shows pipeline KPIs and charts
- Activity page shows events/tasks metrics
- All queries execute against the existing Salesforce tables
- Empty state handling works (no crashes on empty tables)
</success_criteria>

<output>
After completion, the executor should:
1. Verify the app runs with `source .env && streamlit run reports/app.py`
2. Confirm pages load without database errors
</output>
