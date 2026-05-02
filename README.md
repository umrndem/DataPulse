# 📊 DataPulse: Business Analytics Control Center

DataPulse is a business dashboard that turns raw sales and transaction data into clear charts, forecasts, and reports. It is designed to be used as a product, not as a technical project, so a business owner or examiner can understand it without reading code.

---

## What DataPulse Does

### Login Gateway
DataPulse uses role-based access control so different people see different parts of the system.

- **Admins** can manage users, update business goals, run forecasts, and use the data pipeline.
- **Viewers** can see the dashboard and reports, but cannot access sensitive admin-only features.

> **Info:** This keeps important actions like deleting data or changing users limited to the right people.

### Analytics Hub
The Analytics Hub is the control center of the app. It is the starting point for moving between the main business areas.

### Business Insights
This is the main dashboard. It takes raw numbers and turns them into useful visuals such as:

- Revenue charts
- Order counts
- Average order value
- Trend charts over time
- Forecast charts

The dashboard also responds to the **Date Range** filter, so you can focus on a week, a month, or a custom period.

### AI Forecast
The AI Forecast uses a forecasting engine called **Prophet**. It looks at past sales history and predicts future sales.

This helps with:
- Inventory planning
- Revenue planning
- Staffing decisions
- Business forecasting

> **Info:** The forecast is based on historical patterns, so it becomes more useful as more data is added.

### Settings & User Management
This section is for the owner or Admin. It is where you:

- Manage team access
- Add or remove users
- Set target goals
- Review system logs
- Clean or reset data when needed

---

## What Kind of Data You Can Use

DataPulse is business-agnostic. That means it can work with many different kinds of sales or transaction datasets, not just one specific company.

### Supported Format
- CSV files only

### Mandatory Columns
To work correctly, the data should include these fields:

- **A date column**: tells the app when the transaction happened
- **A value column**: tells the app the amount, price, or revenue
- **A unique ID column**: identifies each record, such as an order number

### Optional Column
- **A customer or user column**: identifies who made the purchase

> **Warning:** If the column names in your CSV are different, you must map them correctly before the dashboard will read them properly.

---

## How to Map Your File Headers

You do not need to change Python logic to use a different dataset. Instead, update the column mapping settings.

### Option 1: Edit the configuration file
Open:

- [src/config/column_mapping.py](src/config/column_mapping.py)

Update the values for:

- `DATE_COL`
- `VALUE_COL`
- `ID_COL`
- `USER_COL`

Example:

```python
date_col = "order_purchase_timestamp"
value_col = "price"
id_col = "order_id"
user_col = "customer_unique_id"
```

### Option 2: If your setup uses YAML mapping
If your version of the project uses a YAML-based mapping file, update the same column names there instead.

The goal is the same: match the names in the system to the names in your CSV file.

> **Info:** You only change the mapping values. You do not need to rewrite the application logic.

---

## How to Onboard a New Business

### Step 1: Prepare the CSV files
Make sure your CSV file contains the required columns:

- a date field
- a value field
- a unique record ID

If possible, keep the file clean and simple:

- one header row
- one record per row
- no merged cells
- CSV format only

### Step 2: Update the column mapping
Open [src/config/column_mapping.py](src/config/column_mapping.py) and change the mapping values so they match the headers in your CSV file.

For example, if your file uses `sale_date` instead of `order_purchase_timestamp`, update the date mapping to `sale_date`.

If your dataset uses different names, change only the mapping values, not the rest of the application.

### Step 3: Use the Data Pipeline page
Log in as an Admin and go to **Data Pipeline**.

From there you can:
- Upload or sync the data
- Load the raw files into the system
- Refresh the dashboard data
- Run the forecast

### Step 4: View the results
Go to **Business Insights** to see:

- Charts
- KPI cards
- Forecasts
- Exportable reports

---

## Project Structure

This is a simple guide to the folders and files in the project.

### Main Files

- [app.py](app.py) - the main Streamlit app that opens the product and routes between pages
- [README.md](README.md) - this guide
- [requirements.txt](requirements.txt) - the Python packages needed to run the app
- [.env](.env) - private environment settings such as the database connection

### Data Folder

- [data/raw/](data/raw/) - place incoming CSV files here before loading them into the system
- [data/processed/](data/processed/) - stores prepared or cleaned data if needed

### Source Code Folder

- [src/config/](src/config/) - dataset mapping and business configuration
- [src/services/](src/services/) - business logic such as login, forecasts, KPI calculations, and data loading
- [src/components/](src/components/) - pipeline tools such as ingestion and transformation
- [src/pages/](src/pages/) - the Streamlit pages for login, hub, insights, pipeline, and settings
- [src/ui/](src/ui/) - shared styling and reusable interface helpers
- [src/utils.py](src/utils.py) - database helpers and utility functions

### Tests and Supporting Files

- [tests/](tests/) - automated checks that confirm the system still works
- [notebooks/](notebooks/) - optional analysis notebooks
- [deliverables/](deliverables/) - project materials and submission assets

> **Info:** You do not need to open every file to use the product. Most users only need the app, the data folder, and the column mapping settings.

---

## Quality of Life Features

### CSV Export
You can download filtered dashboard data as a CSV file.

This is useful for:
- meetings
- reporting
- sharing results with stakeholders

### Target Goal
The target goal feature lets you compare actual performance against a business target.

This helps you quickly see whether sales are tracking above or below your goal.

---

## System Integrity

- Data is stored securely in the cloud using Supabase.
- The app is responsive and works on mobile browsers as well as desktop.

---

## Typical Daily Use

If you are using DataPulse as a business owner, your normal workflow is:

1. Log in
2. Open the Analytics Hub
3. Review Business Insights
4. Adjust the Date Range if needed
5. Download a report for meetings
6. Check the forecast before making planning decisions

> **Info:** Viewers can safely use the dashboard, while Admins handle team management and operational settings.

---

## Advanced: Technical Setup

This section is for developers or technical examiners.

### Directory Structure

```text
DataPulse/
├── app.py
├── README.md
├── requirements.txt
├── .env
├── data/
│   ├── raw/
│   └── processed/
├── deliverables/
├── notebooks/
├── src/
│   ├── config/
│   │   ├── __init__.py
│   │   └── column_mapping.py
│   ├── components/
│   │   ├── __init__.py
│   │   ├── data_ingestion.py
│   │   ├── data_transformation.py
│   │   └── prediction_pipeline.py
│   ├── pages/
│   │   ├── __init__.py
│   │   ├── login.py
│   │   ├── home.py
│   │   ├── insights.py
│   │   ├── pipeline.py
│   │   └── settings.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── data_service.py
│   │   ├── forecast_service.py
│   │   └── kpi_service.py
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── components.py
│   │   ├── helpers.py
│   │   └── styles.py
│   └── utils.py
└── tests/
	├── test_kpis.py
	└── test_streamlit_supabase_integration.py
```

### What Each File and Folder Does

- [app.py](app.py) is the main entry point. It loads the app, checks whether the user is logged in, routes to the correct page, and connects all page modules together.
- [README.md](README.md) explains how to use the product and how the project is organized.
- [requirements.txt](requirements.txt) lists the Python libraries required to run the app.
- [.env](.env) stores private environment values such as the Supabase database URL and column mapping settings.

#### Data Folders

- [data/raw/](data/raw/) is where you place the original CSV files before uploading them into the system.
- [data/processed/](data/processed/) is for cleaned or prepared data outputs when needed.

#### Configuration Folder

- [src/config/](src/config/) contains the business mapping and dataset configuration.
- [src/config/column_mapping.py](src/config/column_mapping.py) defines which CSV columns represent dates, values, IDs, and optional customer fields.
- [src/config/__init__.py](src/config/__init__.py) exposes the configuration objects for easy import elsewhere in the app.

#### Components Folder

- [src/components/data_ingestion.py](src/components/data_ingestion.py) reads CSV files from `data/raw/`, cleans column names, and uploads them to Supabase.
- [src/components/data_transformation.py](src/components/data_transformation.py) combines raw tables into a business-ready analytics table.
- [src/components/prediction_pipeline.py](src/components/prediction_pipeline.py) runs the forecasting pipeline as a standalone process.
- [src/components/__init__.py](src/components/__init__.py) marks the directory as a Python package.

#### Pages Folder

- [src/pages/login.py](src/pages/login.py) renders the login form and authenticates users.
- [src/pages/home.py](src/pages/home.py) renders the Analytics Hub / control center.
- [src/pages/insights.py](src/pages/insights.py) renders the Business Insights dashboard, charts, and data table.
- [src/pages/pipeline.py](src/pages/pipeline.py) renders the data pipeline and forecast controls for Admins.
- [src/pages/settings.py](src/pages/settings.py) renders user management, goals, logs, and reset tools.
- [src/pages/__init__.py](src/pages/__init__.py) marks the directory as a Python package.

#### Services Folder

- [src/services/auth_service.py](src/services/auth_service.py) handles authentication, password hashing, and user management.
- [src/services/data_service.py](src/services/data_service.py) loads dashboard data from the database.
- [src/services/forecast_service.py](src/services/forecast_service.py) prepares data, trains Prophet, and saves forecast results.
- [src/services/kpi_service.py](src/services/kpi_service.py) calculates metrics such as revenue, order count, and average order value.
- [src/services/__init__.py](src/services/__init__.py) marks the directory as a Python package.

#### UI Folder

- [src/ui/styles.py](src/ui/styles.py) contains the shared page styling and layout setup.
- [src/ui/components.py](src/ui/components.py) contains shared navigation and sidebar rendering.
- [src/ui/helpers.py](src/ui/helpers.py) contains reusable chart and formatting helpers.
- [src/ui/__init__.py](src/ui/__init__.py) marks the directory as a Python package.

#### Utilities and Tests

- [src/utils.py](src/utils.py) contains shared database helpers, logging, and low-level data access functions.
- [tests/test_kpis.py](tests/test_kpis.py) checks KPI calculations.
- [tests/test_streamlit_supabase_integration.py](tests/test_streamlit_supabase_integration.py) checks that the app can load data from the database correctly.

> **Info:** The app is intentionally split this way so each file has one clear job and can be maintained without touching the whole system.

### Setup

```bash
cd DataPulse
python -m venv venv
source venv/Scripts/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Database Connection
Create a `.env` file in the project root and add your Supabase connection string:

```env
DATABASE_URL="postgresql://user:password@host:port/database"
```

### Run the App

```bash
streamlit run app.py
```

### Source Code Overview

- `app.py` - main Streamlit router and page launcher
- `src/pages/` - page modules for login, hub, insights, pipeline, and settings
- `src/ui/` - shared styling and UI helpers
- `src/services/` - business logic for authentication, KPI calculations, and forecasting
- `src/components/` - ingestion, transformation, and pipeline execution utilities
- `src/config/` - dataset mapping and environment-driven settings
- `src/utils.py` - database helpers, logging, and CRUD support

### Testing

```bash
pytest -v
```
