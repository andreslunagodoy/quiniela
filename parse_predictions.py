"""
Parses the family quiniela predictions CSV and merges with ESPN results.
Outputs quiniela.json - the single source of truth for the app.
"""

import csv
import json
import re
import unicodedata
from datetime import datetime, timezone

CSV_PATH = "Quiniela 2026.xlsx - Hoja1.csv"
RESULTS_PATH = "results.json"
OUTPUT_PATH = "quiniela.json"

# Participant name → column index (0-based)
PARTICIPANTS = [
    (4,  "ivan"),
    (5,  "raquel"),
    (7,  "adrián"),
    (9,  "soni"),
    (11, "ale"),
    (13, "arturo"),
    (15, "andrés"),
    (17, "nati"),
    (19, "ame"),
    (21, "mariana"),
    (23, "janet"),
    (25, "juan"),
    (27, "tony"),
    (28, "luis adrián"),
]

# Spanish (normalized) → English canonical team name
ES_TO_EN = {
    "mexico": "Mexico",
    "sudafrica": "South Africa",
    "corea del sur": "South Korea",
    "corea": "South Korea",
    "chequia": "Czechia",
    "canada": "Canada",
    "b&h": "Bosnia-Herzegovina",
    "bosnia-herzegovina": "Bosnia-Herzegovina",
    "estados unidos": "United States",
    "paraguay": "Paraguay",
    "catar": "Qatar",
    "suiza": "Switzerland",
    "brasil": "Brazil",
    "marruecos": "Morocco",
    "haiti": "Haiti",
    "escocia": "Scotland",
    "australia": "Australia",
    "turquia": "Türkiye",
    "alemania": "Germany",
    "curazao": "Curaçao",
    "paises bajos": "Netherlands",
    "japon": "Japan",
    "costa de marfil": "Ivory Coast",
    "ecuador": "Ecuador",
    "suecia": "Sweden",
    "tunez": "Tunisia",
    "espana": "Spain",
    "cabo verde": "Cape Verde",
    "belgica": "Belgium",
    "egipto": "Egypt",
    "arabia saudi": "Saudi Arabia",
    "uruguay": "Uruguay",
    "iran": "Iran",
    "nueva zelanda": "New Zealand",
    "francia": "France",
    "senegal": "Senegal",
    "irak": "Iraq",
    "noruega": "Norway",
    "argentina": "Argentina",
    "argelia": "Algeria",
    "austria": "Austria",
    "jordania": "Jordan",
    "portugal": "Portugal",
    "congo": "Congo DR",
    "inglaterra": "England",
    "croacia": "Croatia",
    "ghana": "Ghana",
    "panama": "Panama",
    "uzbekistan": "Uzbekistan",
    "colombia": "Colombia",
}

# English canonical → set of normalized aliases
TEAM_ALIASES: dict[str, set] = {
    "Mexico":              {"mexico", "mex", "mex"},
    "South Africa":        {"south africa", "sudafrica", "rsa", "sa", "sud"},
    "South Korea":         {"south korea", "corea del sur", "cor", "core", "corea", "kor"},
    "Czechia":             {"czechia", "chequia", "che", "cze"},
    "Canada":              {"canada", "canadá", "can"},
    "Bosnia-Herzegovina":  {"bosnia-herzegovina", "b&h", "boz", "bih", "bos", "bosn", "bosnia"},
    "United States":       {"united states", "estados unidos", "usa", "us", "eeuu"},
    "Paraguay":            {"paraguay", "par"},
    "Qatar":               {"qatar", "catar", "cat", "qat"},
    "Switzerland":         {"switzerland", "suiza", "sui", "suiz"},
    "Brazil":              {"brazil", "brasil", "bra"},
    "Morocco":             {"morocco", "marruecos", "mar", "marr"},
    "Haiti":               {"haiti", "haití", "hai"},
    "Scotland":            {"scotland", "escocia", "esc", "sco"},
    "Australia":           {"australia", "aus"},
    "Türkiye":             {"türkiye", "turquia", "turquía", "tur", "turq", "turkey"},
    "Germany":             {"germany", "alemania", "ale", "ger"},
    "Curaçao":             {"curaçao", "curazao", "cur", "crz"},
    "Netherlands":         {"netherlands", "paises bajos", "países bajos", "pb", "hol", "ned", "holanda"},
    "Japan":               {"japan", "japon", "japón", "jap", "jpn"},
    "Ivory Coast":         {"ivory coast", "costa de marfil", "cdm", "civ"},
    "Ecuador":             {"ecuador", "ecu"},
    "Sweden":              {"sweden", "suecia", "sue", "swe"},
    "Tunisia":             {"tunisia", "tunez", "túnez", "tun"},
    "Spain":               {"spain", "espana", "españa", "esp"},
    "Cape Verde":          {"cape verde", "cabo verde", "cabo", "cv"},
    "Belgium":             {"belgium", "belgica", "bélgica", "bel", "belg"},
    "Egypt":               {"egypt", "egipto", "egi", "egip", "egy"},
    "Saudi Arabia":        {"saudi arabia", "arabia saudi", "arabia saudí", "saud", "ksa", "arabia saudiata"},
    "Uruguay":             {"uruguay", "uru"},
    "Iran":                {"iran", "irán", "ira"},
    "New Zealand":         {"new zealand", "nueva zelanda", "nz", "nzl"},
    "France":              {"france", "francia", "fra", "fran"},
    "Senegal":             {"senegal", "sen"},
    "Iraq":                {"iraq", "irak"},
    "Norway":              {"norway", "noruega", "nor"},
    "Argentina":           {"argentina", "arg", "argt"},
    "Algeria":             {"algeria", "argelia", "alg"},
    "Austria":             {"austria", "aus"},
    "Jordan":              {"jordan", "jordania", "jor"},
    "Portugal":            {"portugal", "por", "port"},
    "Congo DR":            {"congo dr", "congo", "drc", "con", "cong"},
    "England":             {"england", "inglaterra", "ing", "ingl", "eng"},
    "Croatia":             {"croatia", "croacia", "cro", "croa"},
    "Ghana":               {"ghana", "gha", "gahana", "gan"},
    "Panama":              {"panama", "panamá", "pan"},
    "Uzbekistan":          {"uzbekistan", "uzbekistán", "uzb"},
    "Colombia":            {"colombia", "col"},
}

DRAW_TOKENS = {"emp", "empate", "draw", "tie", "empt"}


def norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower().strip())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.replace(".", "").strip()
    return re.sub(r"\s+", " ", s).strip()


def es_to_en(spanish_name: str) -> str:
    key = norm(spanish_name)
    if key in ES_TO_EN:
        return ES_TO_EN[key]
    # Fallback: try stripping trailing spaces and re-normalize
    raise ValueError(f"Unknown team: '{spanish_name}' (normalized: '{key}')")


def resolve_prediction(pred: str, t1_en: str, t2_en: str):
    """Resolve a prediction string to a canonical team name, 'draw', or None."""
    pred_n = norm(pred)
    if not pred_n:
        return None
    if pred_n in DRAW_TOKENS:
        return "draw"

    t1_aliases = TEAM_ALIASES.get(t1_en, set())
    t2_aliases = TEAM_ALIASES.get(t2_en, set())

    m1 = pred_n in t1_aliases
    m2 = pred_n in t2_aliases

    if m1 and not m2:
        return t1_en
    if m2 and not m1:
        return t2_en
    if m1 and m2:
        # Ambiguous alias — prefer team1 (home) as tiebreaker
        # (only happens with "arg" in Argentina vs Algeria, "aus" never co-occurs)
        return t1_en

    # Fallback: prefix match against Spanish-ish name (handles typos like "suiz")
    t1_key = norm(next((k for k, v in ES_TO_EN.items() if v == t1_en), t1_en))
    t2_key = norm(next((k for k, v in ES_TO_EN.items() if v == t2_en), t2_en))

    if t1_key.startswith(pred_n) and not t2_key.startswith(pred_n):
        return t1_en
    if t2_key.startswith(pred_n) and not t1_key.startswith(pred_n):
        return t2_en

    # Word-level prefix (e.g. "ira" → "irak" for Iraq)
    for word in t1_key.split():
        if word.startswith(pred_n):
            return t1_en
    for word in t2_key.split():
        if word.startswith(pred_n):
            return t2_en

    print(f"  UNRESOLVED: '{pred}' → '{pred_n}' in {t1_en} vs {t2_en}")
    return None


def parse_csv() -> list[dict]:
    """Parse the quiniela CSV into a list of match prediction dicts."""
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))

    matches = []
    current_date = None
    match_number = 0

    for row in rows[3:]:  # skip rows 1-3 (blank, names, blank)
        if not any(row):
            continue

        raw_date = row[0].strip()
        if raw_date:
            current_date = raw_date

        group = row[1].strip().upper() if len(row) > 1 else None
        team1_raw = row[2].strip() if len(row) > 2 else ""
        team2_raw = row[3].strip() if len(row) > 3 else ""

        if not team1_raw or not team2_raw:
            continue

        t1_en = es_to_en(team1_raw)
        t2_en = es_to_en(team2_raw)

        preds = {}
        for col, name in PARTICIPANTS:
            raw = row[col].strip() if col < len(row) else ""
            preds[name] = resolve_prediction(raw, t1_en, t2_en)

        match_number += 1
        matches.append({
            "csv_match_number": match_number,
            "csv_date": current_date,
            "group": group,
            "team1": t1_en,
            "team2": t2_en,
            "predictions": preds,
        })

    return matches


# Manual corrections for cells left blank in the original spreadsheet
CORRECTIONS: dict[frozenset, dict] = {
    frozenset({"Argentina", "Algeria"}): {"nati": "Argentina"},
}


def apply_corrections(matches: list[dict]) -> list[dict]:
    for m in matches:
        key = frozenset({m["team1"], m["team2"]})
        if key in CORRECTIONS:
            for participant, value in CORRECTIONS[key].items():
                if m["predictions"].get(participant) is None:
                    m["predictions"][participant] = value
    return matches


def load_results() -> dict:
    """Load ESPN results indexed by frozenset of team names."""
    with open(RESULTS_PATH, encoding="utf-8") as f:
        data = json.load(f)
    index = {}
    for m in data["matches"]:
        key = frozenset({m["home_team"], m["away_team"]})
        index[key] = m
    return index


def merge(csv_matches: list[dict], results_index: dict) -> list[dict]:
    merged = []
    unmatched = []

    for cm in csv_matches:
        key = frozenset({cm["team1"], cm["team2"]})
        espn = results_index.get(key)

        if espn is None:
            unmatched.append(cm)
            merged.append({
                "match_number": cm["csv_match_number"],
                "csv_date": cm["csv_date"],
                "group": cm["group"],
                "home_team": cm["team1"],
                "away_team": cm["team2"],
                "home_score": None,
                "away_score": None,
                "completed": False,
                "result": None,
                "date_utc": None,
                "venue": None,
                "city": None,
                "predictions": cm["predictions"],
            })
        else:
            merged.append({
                "match_number": espn["match_number"],
                "csv_date": cm["csv_date"],
                "group": cm["group"],
                "home_team": espn["home_team"],
                "away_team": espn["away_team"],
                "home_score": espn["home_score"],
                "away_score": espn["away_score"],
                "completed": espn["completed"],
                "result": espn["result"],
                "date_utc": espn["date_utc"],
                "venue": espn["venue"],
                "city": espn["city"],
                "predictions": cm["predictions"],
            })

    if unmatched:
        print(f"\nWARNING: {len(unmatched)} CSV matches not found in ESPN results:")
        for m in unmatched:
            print(f"  - {m['team1']} vs {m['team2']}")

    return sorted(merged, key=lambda m: m["match_number"])


def main():
    print("Parsing predictions CSV...")
    csv_matches = parse_csv()
    csv_matches = apply_corrections(csv_matches)
    print(f"  → {len(csv_matches)} matches parsed")

    print("Loading ESPN results...")
    results_index = load_results()
    print(f"  → {len(results_index)} matches indexed")

    print("Merging...")
    merged = merge(csv_matches, results_index)

    participants = [name for _, name in PARTICIPANTS]

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "participants": participants,
        "matches": merged,
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"  → Saved to {OUTPUT_PATH}")

    # Quick sanity check
    print("\nSample (match 1):")
    m = merged[0]
    print(f"  {m['home_team']} {m['home_score']}-{m['away_score']} {m['away_team']}")
    for p, pred in m["predictions"].items():
        correct = "✓" if pred == m["home_team"] else ("~" if pred == "draw" else "✗") if m["completed"] else " "
        print(f"    {p:<15} → {str(pred):<20} {correct}")


if __name__ == "__main__":
    main()
