# Enable the GitHub Pages landing page

This repo includes a static project website at [`docs/index.html`](index.html).

It explains the problem, goals, architecture, 4-week plan, and links to:

- the **GitHub repository** (code)
- the **live Streamlit dashboard** (interactive filters → KPIs / map / stops)

GitHub Pages only hosts this **landing page**. The interactive dashboard still runs on Streamlit Cloud.

## Turn on GitHub Pages

1. Open your repo on GitHub → **Settings** → **Pages**
2. Under **Build and deployment**:
   - **Source:** Deploy from a branch
   - **Branch:** `main`
   - **Folder:** `/docs`
3. Save

After 1–2 minutes your site will be at:

`https://gvarun20.github.io/Real_Time_Delay_Analytics_Swedish_Public_Transport/`

(Replace with your exact GitHub username/repo if different.)

## Add the Streamlit link to the landing page

1. Deploy the dashboard on [share.streamlit.io](https://share.streamlit.io) (see [public-dashboard-deploy.md](public-dashboard-deploy.md)).
2. Edit `docs/index.html` and set:

```js
window.LIVE_DASHBOARD_URL = "https://YOUR-APP.streamlit.app";
```

3. Commit and push — Pages updates automatically.

## Optional screenshots

Drop PNG files into `docs/demo/`:

| File | Suggested content |
|---|---|
| `kpis.png` | Top KPI row of the Streamlit app |
| `map-stops.png` | Map + worst stops |
| `routes.png` | Route bar chart or heatmap |
| `airflow.png` | Airflow DAG success view |

The landing page shows them when present; until then it shows text placeholders.
