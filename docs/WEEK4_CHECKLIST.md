# Week 4 Completion Checklist

Week 4 = make the project **easy for outsiders** (recruiters, classmates, interviewers).

## Public demos

- [x] GitHub Pages landing from `/docs`  
  https://gvarun20.github.io/Real_Time_Delay_Analytics_Swedish_Public_Transport/
- [x] Streamlit Cloud dashboard (sample delays + sample energy)  
  https://realtime--delay--analytics--swedish--publictransport.streamlit.app/
- [x] README has live links + “how to read this project”
- [ ] Optional: 2–3 min demo video (Loom/YouTube) linked from README
- [ ] Optional: screenshots in `docs/demo/` (`kpis.png`, `map-stops.png`, …)

## CI / CD

- [x] GitHub Actions CI green on `main` (ruff + Postgres pytest)
- [x] CI badge in README
- [x] Manual `workflow_dispatch` available on the CI workflow

## Analytics polish

- [x] Relative bus **energy scores** (local + sample CSV for Cloud)
- [x] Energy runbook: [energy-score-runbook.md](energy-score-runbook.md)
- [x] Beginner docs hub: [00-START_HERE.md](00-START_HERE.md)
- [x] Plain-language guide: [05-how-to-understand-this-project.md](05-how-to-understand-this-project.md)

## Still nice-to-have (not blockers)

- [ ] ≥7 consecutive service dates of facts (history grows as Airflow runs)
- [ ] Short ADR if extreme delay outliers need a hard DQ cap
- [ ] Mini GTFS fixture tests for the Spark join path

---

**Week 4 phase gate:**  
> CI green; public links work; README explains need → build → how to read the dashboard.
