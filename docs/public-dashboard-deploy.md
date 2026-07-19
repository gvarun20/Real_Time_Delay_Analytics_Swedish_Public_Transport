# Deploy the dashboard publicly (Streamlit Community Cloud)

Your full pipeline (Airflow + PySpark + Postgres) stays local in Docker.  
The **public website** is the Streamlit dashboard, fed by a **sample CSV export**
so you never put Trafiklab API keys or your home database on the internet.

## Why sample data?

| Local Docker | Public Streamlit Cloud |
|---|---|
| Real Postgres `transit_dw` | Cannot reach your laptop |
| Live pipeline updates | Fixed demo snapshot in git |
| Needs API keys | **No secrets required** |

## Steps

### 1. Export sample data (on your machine, Postgres must have facts)

```powershell
cd E:\SUMMER_3RD_PROJECT
py scripts/export_dashboard_sample.py
```

This creates `dashboard/sample_data/delay_facts.csv.gz`.

### 2. Commit and push (you run git — not the agent)

```powershell
git add dashboard/ scripts/export_dashboard_sample.py .streamlit/ .gitignore docs/public-dashboard-deploy.md README.md
git status
git commit -m "Add public Streamlit Cloud deploy path with sample delay dataset"
git push
```

### 3. Deploy on Streamlit Community Cloud

1. Go to [https://share.streamlit.io](https://share.streamlit.io) (sign in with GitHub).
2. Click **New app**.
3. Choose your repo (the new one you created).
4. Set:
   - **Branch:** `main`
   - **Main file path:** `dashboard/app.py`
   - **Python requirements file:** `dashboard/requirements.txt`  
     (Important: do **not** use the repo-root `requirements.txt` — it includes PySpark.)
5. Optional Advanced → Secrets: you can leave empty.  
   Optional env: `DASHBOARD_DATA_SOURCE=sample` (forces sample mode).
6. Click **Deploy**.

### 4. Share the URL

You get a public link like:

`https://YOUR-APP-NAME.streamlit.app`

Put that link in the README under **Live demo**.

## How to use the public site

Same UI as local:

1. Pick a **date range** in the sidebar  
2. Optionally filter **route** / **vehicle type**  
3. Read **KPIs**, charts, **map**, and **worst stops**

See README → “How to read the dashboard”.

## Refresh the public demo later

Re-run the export after you load more days, commit the new CSV, push — Streamlit Cloud redeploys automatically.
