# Quiniela Luna Campos 2026

Family World Cup prediction tracker for the 2026 FIFA World Cup.

## What it does

A Streamlit web app where 14 family members each predicted the winner of every group-stage match. The app tracks scores, shows standings, and visualises how the race evolves over time.

**Tabs:**
- **🏆 Clasificación** — live scoreboard with podium, filterable by match or date
- **🔴 En vivo** — live score and hypothetical standings during an in-progress game
- **📋 Predicciones** — full predictions table with correctness colour-coding
- **📈 Evolución** — interactive chart of each participant's points over time
- **👤 Perfiles** — per-person stats, rank evolution chart, best/worst predictions
- **🔍 Análisis** — consensus games, similarity rankings, and pairwise comparisons

## Data flow

- `Quiniela 2026.xlsx - Hoja1.csv` — original predictions spreadsheet (source of truth for picks)
- `scrape_results.py` — fetches match results from the ESPN public API → `results.json`
- `parse_predictions.py` — merges predictions CSV with ESPN results → `quiniela.json`
- `app.py` — reads `quiniela.json` directly (all group-stage matches are final, so no live overlay is needed anymore)

The group stage concluded in June 2026 and results are final, so the results-update workflow (`.github/workflows/update-results.yml`) is no longer scheduled — it's kept around as a manual (`workflow_dispatch`) tool in case results ever need reprocessing. The **🔴 En vivo** tab is likewise inert now, since there are no more live matches; it's kept in case the app is reused for a future tournament.

## Running locally

```bash
conda create -n quiniela python=3.11
conda activate quiniela
pip install -r requirements.txt
streamlit run app.py
```

To refresh results manually:

```bash
python scrape_results.py
python parse_predictions.py
```

## Deployment

Deployed on [Streamlit Community Cloud](https://quiniela-luna-campos.streamlit.app) from the `main` branch.
