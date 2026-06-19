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
- `app.py` — reads `quiniela.json` and overlays fresh ESPN data on every page load

Results are also updated automatically every 30 minutes via a GitHub Actions workflow.

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
