"""
Scrapes World Cup 2026 group stage results from the ESPN public API.
Outputs results.json with one entry per match.
"""

import json
import requests
from datetime import datetime, timezone

ESPN_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"


def fetch_matches():
    r = requests.get(
        ESPN_URL,
        params={"dates": "20260611-20260627", "limit": 200},
        timeout=15,
    )
    r.raise_for_status()
    return r.json().get("events", [])


def parse_group(event):
    note = event["competitions"][0].get("altGameNote", "")
    # e.g. "FIFA World Cup, Group A"
    if "Group" in note:
        return note.split("Group")[-1].strip()
    return None


def parse_event(idx, event):
    comp = event["competitions"][0]
    status = comp["status"]["type"]

    competitors = {c["homeAway"]: c for c in comp.get("competitors", [])}
    home = competitors.get("home", {})
    away = competitors.get("away", {})

    home_score = int(home["score"]) if home.get("score") not in (None, "") else None
    away_score = int(away["score"]) if away.get("score") not in (None, "") else None

    completed = status.get("completed", False)
    state = status.get("state", "")  # pre / in / post

    if completed:
        if home_score > away_score:
            result = "home"
        elif away_score > home_score:
            result = "away"
        else:
            result = "draw"
    else:
        result = None

    return {
        "match_number": idx + 1,
        "espn_id": event["id"],
        "date_utc": event["date"],
        "group": parse_group(event),
        "home_team": home.get("team", {}).get("displayName"),
        "home_abbreviation": home.get("team", {}).get("abbreviation"),
        "away_team": away.get("team", {}).get("displayName"),
        "away_abbreviation": away.get("team", {}).get("abbreviation"),
        "home_score": home_score,
        "away_score": away_score,
        "status": state,          # pre | in | post
        "completed": completed,
        "result": result,         # home | away | draw | null
        "venue": comp.get("venue", {}).get("fullName"),
        "city": comp.get("venue", {}).get("address", {}).get("city"),
    }


def main():
    print("Fetching matches from ESPN...")
    events = fetch_matches()
    print(f"  → {len(events)} matches found")

    matches = [parse_event(i, e) for i, e in enumerate(events)]

    completed = sum(1 for m in matches if m["completed"])
    in_progress = sum(1 for m in matches if m["status"] == "in")
    print(f"  → {completed} completed, {in_progress} in progress, {len(matches) - completed - in_progress} upcoming")

    out_path = "results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "matches": matches,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    print(f"  → Saved to {out_path}")

    # Print a quick table of completed matches
    print("\nCompleted matches:")
    print(f"{'#':>3}  {'Group':<6} {'Home':<25} {'Score':^7} {'Away':<25}")
    print("-" * 70)
    for m in matches:
        if m["completed"]:
            score = f"{m['home_score']}-{m['away_score']}"
            print(f"{m['match_number']:>3}  {m['group'] or '?':<6} {m['home_team']:<25} {score:^7} {m['away_team']:<25}")


if __name__ == "__main__":
    main()
