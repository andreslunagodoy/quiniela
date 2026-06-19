import json
import os
from datetime import datetime
from itertools import combinations

import altair as alt
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="Quiniela 2026", page_icon="⚽", layout="wide")

st.markdown("""
<style>
[data-testid="stSidebar"] { min-width: 200px; max-width: 200px; }
[data-testid="stSelectbox"] { max-width: 280px; }
</style>
""", unsafe_allow_html=True)

# ── Display overrides ─────────────────────────────────────────────────────────

PARTICIPANT_DISPLAY = {
    "mariana":      "Mari",
    "luis adrián":  "Luis",
}

TEAM_DISPLAY = {
    "Bosnia-Herzegovina": "Bos-Her",
}

TEAM_FLAGS = {
    "Mexico":             "🇲🇽",
    "South Africa":       "🇿🇦",
    "South Korea":        "🇰🇷",
    "Czechia":            "🇨🇿",
    "Canada":             "🇨🇦",
    "Bosnia-Herzegovina": "🇧🇦",
    "United States":      "🇺🇸",
    "Qatar":              "🇶🇦",
    "Switzerland":        "🇨🇭",
    "Brazil":             "🇧🇷",
    "Morocco":            "🇲🇦",
    "Haiti":              "🇭🇹",
    "Scotland":           "🏴󠁧󠁢󠁳󠁣󠁴󠁿",
    "Paraguay":           "🇵🇾",
    "Australia":          "🇦🇺",
    "Türkiye":            "🇹🇷",
    "Germany":            "🇩🇪",
    "Curaçao":            "🇨🇼",
    "Ivory Coast":        "🇨🇮",
    "Ecuador":            "🇪🇨",
    "Netherlands":        "🇳🇱",
    "Japan":              "🇯🇵",
    "Sweden":             "🇸🇪",
    "Tunisia":            "🇹🇳",
    "Belgium":            "🇧🇪",
    "Egypt":              "🇪🇬",
    "Iran":               "🇮🇷",
    "New Zealand":        "🇳🇿",
    "Spain":              "🇪🇸",
    "Cape Verde":         "🇨🇻",
    "Saudi Arabia":       "🇸🇦",
    "Uruguay":            "🇺🇾",
    "France":             "🇫🇷",
    "Senegal":            "🇸🇳",
    "Iraq":               "🇮🇶",
    "Norway":             "🇳🇴",
    "Argentina":          "🇦🇷",
    "Algeria":            "🇩🇿",
    "Austria":            "🇦🇹",
    "Jordan":             "🇯🇴",
    "Portugal":           "🇵🇹",
    "Congo DR":           "🇨🇩",
    "Uzbekistan":         "🇺🇿",
    "Colombia":           "🇨🇴",
    "England":            "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
    "Croatia":            "🇭🇷",
    "Ghana":              "🇬🇭",
    "Panama":             "🇵🇦",
}

MONTHS_ES = {6: "Jun", 7: "Jul", 8: "Ago"}

COLORS = {
    "correct": "background-color: #d4edda; color: #155724",
    "wrong":   "background-color: #f8d7da; color: #721c24",
    "pending": "",
    "missing": "color: #aaa",
}

MEDALS = {1: "🥇", 2: "🥈", 3: "🥉"}

PALETTE = [
    "#e41a1c", "#377eb8", "#4daf4a", "#984ea3",
    "#ff7f00", "#a65628", "#f781bf", "#008080",
    "#66c2a5", "#e6ab02", "#7570b3", "#d95f02",
    "#1b9e77", "#e7298a",
]

def participant_col(p):
    return PARTICIPANT_DISPLAY.get(p, p.title())

def team_display(t):
    name = TEAM_DISPLAY.get(t, t)
    flag = TEAM_FLAGS.get(t, "")
    return f"{flag} {name}" if flag else name

def format_date(date_utc):
    try:
        dt = datetime.fromisoformat(date_utc.replace("Z", "+00:00"))
        return f"{dt.day} {MONTHS_ES.get(dt.month, dt.strftime('%b'))}"
    except Exception:
        return date_utc[:10]

# ── Data loading ──────────────────────────────────────────────────────────────

ESPN_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"

_ESPN_HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"}

@st.cache_data(ttl=60)
def _espn_events():
    r = requests.get(ESPN_URL, params={"dates": "20260611-20260726", "limit": 200},
                     headers=_ESPN_HEADERS, timeout=10)
    r.raise_for_status()
    return r.json().get("events", [])

def _parse_espn_events(events):
    index, abbrevs = {}, {}
    for event in events:
        comp = event["competitions"][0]
        status = comp["status"]["type"]
        competitors = {c["homeAway"]: c for c in comp.get("competitors", [])}
        home = competitors.get("home", {})
        away = competitors.get("away", {})
        home_name = home.get("team", {}).get("displayName")
        away_name = away.get("team", {}).get("displayName")
        if not home_name or not away_name:
            continue
        home_score = int(home["score"]) if home.get("score") not in (None, "") else None
        away_score = int(away["score"]) if away.get("score") not in (None, "") else None
        completed = status.get("completed", False)
        if completed and home_score is not None and away_score is not None:
            result = "home" if home_score > away_score else ("away" if away_score > home_score else "draw")
        else:
            result = None
        key = frozenset({home_name, away_name})
        index[key] = {
            "home_score": home_score, "away_score": away_score,
            "completed": completed, "result": result,
            "date_utc": event["date"],
            "venue": comp.get("venue", {}).get("fullName"),
            "city": comp.get("venue", {}).get("address", {}).get("city"),
        }
        abbrevs[home_name] = home.get("team", {}).get("abbreviation", "")
        abbrevs[away_name] = away.get("team", {}).get("abbreviation", "")
    return index, abbrevs

@st.cache_data(ttl=60)
def _espn_live():
    r = requests.get(ESPN_URL, headers=_ESPN_HEADERS, timeout=10)
    r.raise_for_status()
    return r.json().get("events", [])

def get_live_games():
    try:
        events = _espn_live()
    except Exception:
        return []
    live = []
    for event in events:
        comp = event["competitions"][0]
        status = comp["status"]["type"]
        if status.get("state") != "in":
            continue
        competitors = {c["homeAway"]: c for c in comp.get("competitors", [])}
        home = competitors.get("home", {})
        away = competitors.get("away", {})
        raw_hs = home.get("score", "")
        raw_as = away.get("score", "")
        live.append({
            "home_team": home.get("team", {}).get("displayName"),
            "away_team": away.get("team", {}).get("displayName"),
            "home_score": int(raw_hs) if raw_hs not in (None, "") else 0,
            "away_score": int(raw_as) if raw_as not in (None, "") else 0,
            "clock":  status.get("detail", ""),
            "period": status.get("description", ""),
        })
    return live

def load_quiniela():
    with open("quiniela.json", encoding="utf-8") as f:
        data = json.load(f)
    espn_error = None
    try:
        espn_index, _ = _parse_espn_events(_espn_events())
        for m in data["matches"]:
            live = espn_index.get(frozenset({m["home_team"], m["away_team"]}))
            if live:
                m.update({k: v for k, v in live.items() if v is not None})
    except Exception as e:
        espn_error = str(e)
    data["_espn_error"] = espn_error
    return data

def load_abbrevs():
    try:
        _, abbrevs = _parse_espn_events(_espn_events())
        if abbrevs:
            return abbrevs
    except Exception:
        pass
    try:
        with open("results.json", encoding="utf-8") as f:
            results = json.load(f)
        return {m["home_team"]: m["home_abbreviation"] for m in results["matches"]} | \
               {m["away_team"]: m["away_abbreviation"] for m in results["matches"]}
    except Exception:
        return {}

# ── Helpers ───────────────────────────────────────────────────────────────────

def get_winner(match):
    if not match["completed"]:
        return None
    r = match["result"]
    if r == "home":
        return match["home_team"]
    if r == "away":
        return match["away_team"]
    return "draw"

def pred_label(pred, abbrev_map):
    if pred is None:
        return "—"
    if pred == "draw":
        return "EMP"
    return abbrev_map.get(pred, pred[:3].upper())

def tally_style(n):
    if n is None:
        return ""
    frac = n / 14
    if frac >= 0.65:
        return "background-color: #d4edda; color: #155724"
    if frac >= 0.35:
        return "background-color: #fff3cd; color: #856404"
    return "background-color: #f8d7da; color: #721c24"

def match_row_display(m):
    return {
        "#":        m["match_number"],
        "Local":    team_display(m["home_team"]),
        "Marcador": f"{m['home_score']}–{m['away_score']}",
        "Visitante": team_display(m["away_team"]),
    }

# ── Load ──────────────────────────────────────────────────────────────────────

data         = load_quiniela()
abbrev_map   = load_abbrevs()
matches      = data["matches"]
participants = data["participants"]
completed    = sorted([m for m in matches if m["completed"]], key=lambda m: m["match_number"])
n_played     = len(completed)
n_parts      = len(participants)

# Per-match consensus (used in Análisis and Perfiles tabs)
consensus = []
for _m in completed:
    _winner  = get_winner(_m)
    _scorers = [p for p in participants if _m["predictions"].get(p) == _winner]
    _missers = [p for p in participants if p not in _scorers]
    consensus.append({
        **match_row_display(_m),
        "n_correct": len(_scorers),
        "scorers":   _scorers,
        "missers":   _missers,
    })

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("⚽ Quiniela Luna Campos 2026")
    st.caption(f"{n_played}/{len(matches)} partidos jugados")
    if data.get("_espn_error"):
        st.caption(f"⚠️ ESPN: {data['_espn_error']}")
    else:
        st.caption("🟢 Datos en vivo")
    st.caption("Hecho con ❤️ para la familia")

# ── Tabs ──────────────────────────────────────────────────────────────────────

tab_score, tab_live, tab_preds, tab_profile, tab_evo, tab_analisis = st.tabs([
    "🏆 Clasificación", "🔴 En vivo", "📋 Predicciones", "👤 Perfiles", "📈 Evolución", "🔍 Análisis",
])

# ── Tab 1: Clasificación ──────────────────────────────────────────────────────

with tab_score:

    # Read filter values from session state so the scoreboard renders first
    # and the filter widgets appear below. On first load defaults apply (all matches).
    sel_match = st.session_state.get("filter_match", 0)
    sel_date  = st.session_state.get("filter_date",  "Todas")

    filter_matches = [
        m for m in completed
        if (sel_match == 0 or m["match_number"] <= sel_match)
        and (sel_date == "Todas" or m["date_utc"][:10] <= sel_date)
    ]
    n_filter = len(filter_matches)

    # ── Compute scores ────────────────────────────────────────────────────────
    rows = []
    for p in participants:
        pts = sum(
            1 for m in filter_matches
            if m["predictions"].get(p) is not None
            and m["predictions"][p] == get_winner(m)
        )
        rows.append({"name": p, "points": pts})

    rows.sort(key=lambda r: -r["points"])
    rank = 1
    for i, r in enumerate(rows):
        if i > 0 and r["points"] < rows[i - 1]["points"]:
            rank = i + 1
        r["rank"] = rank

    # ── Tables ────────────────────────────────────────────────────────────────
    col_board, col_recent = st.columns([1, 1.5])

    with col_board:
        st.subheader("Clasificación")
        df_score = pd.DataFrame([{
            "Pos.":         MEDALS.get(r["rank"], str(r["rank"])),
            "Participante": participant_col(r["name"]),
            "Pts.":         r["points"],
            "%":            f"{r['points'] / n_filter * 100:.0f}%" if n_filter else "—",
        } for r in rows])

        st.dataframe(df_score, hide_index=True, use_container_width=False,
                     height=35 * (len(rows) + 1) + 3)
        st.caption(f"Puntos = predicciones correctas de {n_filter}/{len(matches)} partidos.")

    with col_recent:
        st.subheader("Últimos resultados")
        recent = sorted(filter_matches, key=lambda m: -m["match_number"])[:10]
        if recent:
            consensus_by_num = {g["#"]: g["n_correct"] for g in consensus}
            recent_rows = []
            tally_ints = []
            for m in recent:
                row = match_row_display(m)
                n = consensus_by_num.get(m["match_number"])
                row["Aciertos"] = f"{n}/14" if n is not None else ""
                tally_ints.append(n)
                recent_rows.append(row)
            df_recent = pd.DataFrame(recent_rows)

            def style_recent(df):
                out = pd.DataFrame("", index=df.index, columns=df.columns)
                for i in df.index:
                    out.loc[i, "Aciertos"] = tally_style(tally_ints[i])
                return out

            st.dataframe(
                df_recent.style.apply(style_recent, axis=None),
                hide_index=True,
                use_container_width=False,
                column_config={
                    "#":         st.column_config.NumberColumn(width="small"),
                    "Marcador":  st.column_config.TextColumn(width="small"),
                    "Aciertos":  st.column_config.TextColumn(width="small"),
                },
                height=35 * (len(recent) + 1) + 3,
            )
        else:
            st.info("No hay partidos en el rango seleccionado.")

        match_nums_desc = list(reversed([m["match_number"] for m in completed]))
        st.selectbox(
            "Clasificación hasta partido:",
            options=[0] + match_nums_desc,
            format_func=lambda n: "Todos" if n == 0
                else f"#{n} — {format_date(next(m['date_utc'] for m in completed if m['match_number'] == n))}",
            index=0,
            key="filter_match",
        )
        unique_dates_desc = sorted(set(m["date_utc"][:10] for m in completed), reverse=True)
        st.selectbox(
            "Clasificación hasta fecha:",
            options=["Todas"] + unique_dates_desc,
            format_func=lambda d: "Todas" if d == "Todas" else format_date(d + "T00:00Z"),
            index=0,
            key="filter_date",
        )

    # ── Podium ────────────────────────────────────────────────────────────────
    if len(rows) >= 3 and n_filter > 0:
        st.markdown("### 🏆 Líderes")
        # Classic podium order: 2nd | 1st | 3rd
        podium = [rows[1], rows[0], rows[2]]
        sizes  = [3, 3, 3]
        pod_cols = st.columns(3)
        for col, r, rel in zip(pod_cols, podium, sizes):
            with col:
                medal  = MEDALS.get(r["rank"], f"#{r['rank']}")
                name   = participant_col(r["name"])
                pts    = r["points"]
                st.markdown(
                    f"<div style='text-align:center;padding:6px 0 4px'>"
                    f"<span style='font-size:1.5em;font-weight:800'>{medal} {name}</span><br>"
                    f"<span style='font-size:1.25em;font-weight:600'>{pts} pts</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
                avatar = f"assets/{r['name']}.png"
                if os.path.exists(avatar):
                    _, ic, _ = st.columns([1, rel, 1])
                    with ic:
                        st.image(avatar, use_container_width=True)


# ── Tab 2: En vivo ────────────────────────────────────────────────────────────

with tab_live:
    live_games = get_live_games()

    col_live_refresh, _ = st.columns([1, 4])
    with col_live_refresh:
        if st.button("🔄 Actualizar", key="live_refresh"):
            _espn_live.clear()
            st.rerun()

    if not live_games:
        st.info("No hay partidos en curso en este momento.")
    else:
        for live in live_games:
            home = live["home_team"]
            away = live["away_team"]
            hs   = live["home_score"]
            as_  = live["away_score"]

            if hs > as_:   hyp_winner = home
            elif as_ > hs: hyp_winner = away
            else:          hyp_winner = "draw"

            match_data = next(
                (m for m in matches
                 if frozenset({m["home_team"], m["away_team"]}) == frozenset({home, away})),
                None,
            )

            st.markdown(f"""
            <div style='text-align:center;padding:20px 0 16px;'>
              <div style='font-size:0.95em;color:#888;margin-bottom:6px'>
                {live["clock"]} &nbsp;·&nbsp; {live["period"]}
              </div>
              <div style='font-size:2.2em;font-weight:800;'>
                {team_display(home)} &nbsp;&nbsp; {hs} – {as_} &nbsp;&nbsp; {team_display(away)}
              </div>
            </div>
            """, unsafe_allow_html=True)

            col_lp, col_lb = st.columns(2)

            with col_lp:
                st.subheader("Predicciones")
                if match_data:
                    pred_rows, correct_flags, has_pred = [], [], []
                    for p in participants:
                        pred = match_data["predictions"].get(p)
                        if pred == home:    plabel = team_display(home)
                        elif pred == away:  plabel = team_display(away)
                        elif pred == "draw": plabel = "Empate"
                        else:               plabel = "—"
                        correct_flags.append(pred == hyp_winner if pred is not None else False)
                        has_pred.append(pred is not None)
                        pred_rows.append({"Participante": participant_col(p), "Predicción": plabel})

                    df_lp = pd.DataFrame(pred_rows)

                    def _style_lp(df):
                        out = pd.DataFrame("", index=df.index, columns=df.columns)
                        for i in df.index:
                            if has_pred[i]:
                                out.loc[i] = COLORS["correct"] if correct_flags[i] else COLORS["wrong"]
                        return out

                    st.dataframe(df_lp.style.apply(_style_lp, axis=None),
                                 hide_index=True, use_container_width=False,
                                 height=35*(len(participants)+1)+3)

            with col_lb:
                st.subheader("Tabla si así termina")

                curr_pts = {p: sum(1 for m in completed
                                   if m["predictions"].get(p) == get_winner(m))
                            for p in participants}
                curr_sorted = sorted(participants, key=lambda p: -curr_pts[p])
                curr_rank = {}
                _r = 1
                for _i, _p in enumerate(curr_sorted):
                    if _i > 0 and curr_pts[_p] < curr_pts[curr_sorted[_i-1]]:
                        _r = _i + 1
                    curr_rank[_p] = _r

                hyp_rows = []
                for p in participants:
                    pts = curr_pts[p]
                    if match_data and match_data["predictions"].get(p) == hyp_winner:
                        pts += 1
                    hyp_rows.append({"name": p, "points": pts})
                hyp_rows.sort(key=lambda x: -x["points"])
                _r = 1
                for _i, _row in enumerate(hyp_rows):
                    if _i > 0 and _row["points"] < hyp_rows[_i-1]["points"]:
                        _r = _i + 1
                    _row["rank"] = _r

                delta_styles = []
                df_hyp_rows = []
                for _row in hyp_rows:
                    d = curr_rank[_row["name"]] - _row["rank"]
                    if d > 0:   ds, dc = f"↑{d}", "color:#155724;font-weight:600"
                    elif d < 0: ds, dc = f"↓{abs(d)}", "color:#721c24;font-weight:600"
                    else:       ds, dc = "—", ""
                    delta_styles.append(dc)
                    df_hyp_rows.append({
                        "Pos.": MEDALS.get(_row["rank"], str(_row["rank"])),
                        "Participante": participant_col(_row["name"]),
                        "Pts.": _row["points"],
                        "Δ": ds,
                    })

                df_hyp = pd.DataFrame(df_hyp_rows)

                def _style_hyp(df):
                    out = pd.DataFrame("", index=df.index, columns=df.columns)
                    for i in df.index:
                        out.loc[i, "Δ"] = delta_styles[i]
                    return out

                st.dataframe(df_hyp.style.apply(_style_hyp, axis=None),
                             hide_index=True, use_container_width=False,
                             height=35*(len(hyp_rows)+1)+3)

            st.divider()

# ── Tab 3: Predicciones ───────────────────────────────────────────────────────

with tab_preds:
    st.header("Predicciones")

    p_cols = {p: participant_col(p) for p in participants}
    rows, correctness = [], []

    for m in matches:
        winner    = get_winner(m)
        score_str = f"{m['home_score']}–{m['away_score']}" if m["completed"] else "vs"

        row = {
            "#":         m["match_number"],
            "Grupo":     m["group"],
            "Local":     team_display(m["home_team"]),
            "Marcador":  score_str,
            "Visitante": team_display(m["away_team"]),
        }
        corr = {}
        n_correct = 0
        for p in participants:
            pred = m["predictions"].get(p)
            col  = p_cols[p]
            row[col] = pred_label(pred, abbrev_map)
            if not m["completed"]:
                corr[col] = "pending"
            elif pred is None:
                corr[col] = "missing"
            elif pred == winner:
                corr[col] = "correct"
                n_correct += 1
            else:
                corr[col] = "wrong"

        row["Aciertos"] = f"{n_correct}/14" if m["completed"] else ""
        rows.append(row)
        correctness.append(corr)

    df_preds       = pd.DataFrame(rows)
    corr_df        = pd.DataFrame(correctness)
    display_p_cols = list(p_cols.values())
    _cons_lookup   = {g["#"]: g["n_correct"] for g in consensus}
    tally_pred     = [_cons_lookup.get(m["match_number"]) for m in matches]

    def style_preds(df):
        styles = pd.DataFrame("", index=df.index, columns=df.columns)
        for col in display_p_cols:
            if col in df.columns:
                for i in df.index:
                    styles.loc[i, col] = COLORS.get(corr_df.loc[i, col], "")
        for i in df.index:
            styles.loc[i, "Aciertos"] = tally_style(tally_pred[i])
        return styles

    styled = df_preds.style.apply(style_preds, axis=None)
    st.dataframe(styled, hide_index=True, use_container_width=False,
                 height=35 * (len(matches) + 1) + 3)

# ── Tab 3: Evolución ──────────────────────────────────────────────────────────

with tab_evo:
    st.header("Evolución de puntos")

    evo_rows  = [{"match": 0, "participant": participant_col(p), "puntos": 0} for p in participants]
    running   = {p: 0 for p in participants}
    last_match = 0

    for m in completed:
        winner     = get_winner(m)
        last_match = m["match_number"]
        for p in participants:
            pred = m["predictions"].get(p)
            if pred is not None and pred == winner:
                running[p] += 1
            evo_rows.append({
                "match":       last_match,
                "participant": participant_col(p),
                "puntos":      running[p],
            })

    # Phantom trailing point so step-after always ends with a horizontal line
    for p in participants:
        evo_rows.append({"match": last_match + 0.5, "participant": participant_col(p), "puntos": running[p]})

    # Sort legend by current points descending
    sorted_parts  = sorted(participants, key=lambda p: -running[p])
    sorted_p_names = [participant_col(p) for p in sorted_parts]

    df_evo = pd.DataFrame(evo_rows)

    # Real data only (no phantom trailing points) for tooltip layer
    df_real = df_evo[df_evo["match"] % 1 == 0].copy()

    color_scale = alt.Scale(domain=sorted_p_names, range=PALETTE)
    sel = alt.selection_point(fields=["participant"], bind="legend", empty=True)

    x_enc = alt.X("match:Q", title="Partido #",
                   axis=alt.Axis(tickMinStep=1),
                   scale=alt.Scale(domain=[0, last_match + 0.5]))
    y_enc = alt.Y("puntos:Q", title="Pts. acumulados")
    color_enc = alt.Color("participant:N",
                           sort=sorted_p_names,
                           scale=color_scale,
                           legend=alt.Legend(title="Participante", values=sorted_p_names))

    lines = (
        alt.Chart(df_evo)
        .mark_line(interpolate="step-after")
        .encode(
            x=x_enc, y=y_enc, color=color_enc,
            opacity=alt.condition(sel, alt.value(0.85), alt.value(0.05)),
            strokeWidth=alt.condition(sel, alt.value(3.0), alt.value(1.5)),
        )
        .add_params(sel)
    )

    # Invisible points on real data only — give hover tooltip a clean hit target
    hover_pts = (
        alt.Chart(df_real)
        .mark_point(size=120, opacity=0, filled=True)
        .encode(
            x=x_enc, y=y_enc, color=color_enc,
            tooltip=[
                alt.Tooltip("participant:N", title="Participante"),
                alt.Tooltip("match:Q",       title="Partido",  format="d"),
                alt.Tooltip("puntos:Q",      title="Puntos"),
            ],
        )
    )

    chart = (lines + hover_pts).properties(height=450)

    st.caption("Haz clic en un nombre de la leyenda para resaltarlo. Clic de nuevo para quitar.")
    st.altair_chart(chart, use_container_width=True)

# ── Tab 4: Análisis ───────────────────────────────────────────────────────────

with tab_analisis:
    if not completed:
        st.info("Aún no hay partidos jugados.")
        st.stop()

    top3    = sorted(consensus, key=lambda x: -x["n_correct"])[:3]
    bottom3 = sorted(consensus, key=lambda x:  x["n_correct"])[:3]

    def game_card(g, show_missers=True):
        pct   = g["n_correct"] / n_parts
        names = g["missers"] if show_missers else g["scorers"]
        label = "Fallaron" if show_missers else "Acertaron"
        icon  = "❌" if show_missers else "✅"
        with st.container(border=True):
            st.markdown(f"**#{g['#']}** {g['Local']} **{g['Marcador']}** {g['Visitante']}")
            st.progress(pct, text=f"{g['n_correct']}/{n_parts} ({pct:.0%})")
            if names:
                st.caption(f"{icon} {label}: " + ", ".join(participant_col(p) for p in names))

    col_top, col_bot = st.columns(2)
    with col_top:
        st.subheader("Partidos más acertados")
        for g in top3:
            game_card(g, show_missers=True)

    with col_bot:
        st.subheader("Partidos más difíciles")
        for g in bottom3:
            game_card(g, show_missers=False)

    st.divider()
    st.header("Similitudes")

    # ── Similarity matrix (over all 72 matches) ───────────────────────────────
    sims = {}
    for p1, p2 in combinations(participants, 2):
        agree = total = 0
        for m in matches:
            v1, v2 = m["predictions"].get(p1), m["predictions"].get(p2)
            if v1 is not None and v2 is not None:
                total += 1
                if v1 == v2:
                    agree += 1
        pct = agree / total if total else 0.0
        sims[frozenset({p1, p2})] = (agree, total, pct)

    # ── Most similar pairs (global) ───────────────────────────────────────────
    all_pairs = sorted(
        [(p1, p2, *sims[frozenset({p1, p2})]) for p1, p2 in combinations(participants, 2)],
        key=lambda x: -x[4],
    )

    def pairs_df(pairs_data):
        return pd.DataFrame([{
            "Participante 1": participant_col(p1),
            "Participante 2": participant_col(p2),
            "Similitud":      f"{pct:.0%}",
            "Coincidencias":  f"{agree}/{total}",
        } for p1, p2, agree, total, pct in pairs_data])

    def pair_card(title, p1, p2, agree, total, pct, table_data):
        st.subheader(title)
        c_l, c_r, c_m = st.columns([2, 2, 3])
        with c_l:
            av = f"assets/{p1}.png"
            if os.path.exists(av):
                st.image(av, width=113)
            st.markdown(f"**{participant_col(p1)}**")
        with c_r:
            av = f"assets/{p2}.png"
            if os.path.exists(av):
                st.image(av, width=113)
            st.markdown(f"**{participant_col(p2)}**")
        with c_m:
            st.metric("Similitud", f"{pct:.0%}", f"{agree} de {total} coinciden")
        st.markdown(f"**{title}**")
        st.dataframe(pairs_df(table_data), hide_index=True, use_container_width=True)

    col_top_p, col_bot_p = st.columns(2)
    with col_top_p:
        p1s, p2s, agree_s, total_s, pct_s = all_pairs[0]
        pair_card("Los más similares", p1s, p2s, agree_s, total_s, pct_s, all_pairs[:3])
    with col_bot_p:
        p1d, p2d, agree_d, total_d, pct_d = all_pairs[-1]
        pair_card("Los más diferentes", p1d, p2d, agree_d, total_d, pct_d, list(reversed(all_pairs[-3:])))

    st.divider()

    # ── Similarity per person ─────────────────────────────────────────────────
    st.subheader("Similitud por participante")

    sel_person = st.selectbox(
        "Selecciona un participante:",
        options=participants,
        format_func=participant_col,
        index=participants.index("ame"),
    )
    _av = f"assets/{sel_person}.png"
    if os.path.exists(_av):
        st.image(_av, width=113)

    others = sorted(
        [(p, *sims[frozenset({sel_person, p})]) for p in participants if p != sel_person],
        key=lambda x: -x[3],
    )

    def sim_table(rows_data):
        return pd.DataFrame([{
            "Participante":  participant_col(p),
            "Similitud":     f"{pct:.0%}",
            "Coincidencias": f"{agree}/{total}",
        } for p, agree, total, pct in rows_data])

    col_sim1, col_sim2 = st.columns(2)
    with col_sim1:
        best_p, best_agree, best_total, best_pct = others[0]
        c_pic, c_met = st.columns([2, 3])
        with c_pic:
            av = f"assets/{best_p}.png"
            if os.path.exists(av):
                st.image(av, width=113)
            st.markdown(f"**{participant_col(best_p)}**")
        with c_met:
            st.metric("Similitud", f"{best_pct:.0%}", f"{best_agree} de {best_total} coinciden")
        st.markdown("**Top 3 más similares**")
        st.dataframe(sim_table(others[:3]), hide_index=True, use_container_width=True)
    with col_sim2:
        worst_p, worst_agree, worst_total, worst_pct = others[-1]
        c_pic, c_met = st.columns([2, 3])
        with c_pic:
            av = f"assets/{worst_p}.png"
            if os.path.exists(av):
                st.image(av, width=113)
            st.markdown(f"**{participant_col(worst_p)}**")
        with c_met:
            st.metric("Similitud", f"{worst_pct:.0%}", f"{worst_agree} de {worst_total} coinciden")
        st.markdown("**Top 3 más diferentes**")
        st.dataframe(sim_table(list(reversed(others[-3:]))), hide_index=True, use_container_width=True)

    st.divider()

    # ── Pair comparison ───────────────────────────────────────────────────────
    st.subheader("Similitud entre dos participantes")

    col_p1, col_p2 = st.columns(2)
    with col_p1:
        pair1 = st.selectbox("Participante 1:", participants,
                             format_func=participant_col, key="pair1")
    with col_p2:
        pair2 = st.selectbox("Participante 2:",
                             [p for p in participants if p != pair1],
                             format_func=participant_col, key="pair2")

    # VS banner
    _av1, _av2 = f"assets/{pair1}.png", f"assets/{pair2}.png"
    c_l, c_vs, c_r = st.columns([2, 1, 2])
    with c_l:
        if os.path.exists(_av1):
            st.image(_av1, width=100)
        st.caption(participant_col(pair1))
    with c_vs:
        st.markdown("<div style='text-align:center;font-size:1.6em;padding-top:28px'>vs</div>",
                    unsafe_allow_html=True)
    with c_r:
        if os.path.exists(_av2):
            st.image(_av2, width=100)
        st.caption(participant_col(pair2))

    agree_n, total_n, pct_n = sims[frozenset({pair1, pair2})]
    st.metric(
        f"Similitud — {participant_col(pair1)} vs {participant_col(pair2)}",
        f"{pct_n:.0%}",
        f"{agree_n} de {total_n} predicciones coinciden",
    )

    p1_col = participant_col(pair1)
    p2_col = participant_col(pair2)

    agree_rows, agree_corr_rows = [], []
    diff_rows,  diff_corr_rows  = [], []

    for m in matches:
        v1, v2 = m["predictions"].get(pair1), m["predictions"].get(pair2)
        if v1 is None or v2 is None:
            continue
        winner    = get_winner(m)
        score_str = f"{m['home_score']}–{m['away_score']}" if m["completed"] else "vs"
        row = {
            "#":        m["match_number"],
            "Local":    team_display(m["home_team"]),
            "Marcador": score_str,
            "Visitante": team_display(m["away_team"]),
            p1_col:     pred_label(v1, abbrev_map),
            p2_col:     pred_label(v2, abbrev_map),
        }
        if m["completed"]:
            c1 = "correct" if v1 == winner else "wrong"
            c2 = "correct" if v2 == winner else "wrong"
        else:
            c1 = c2 = "pending"

        if v1 == v2:
            agree_rows.append(row)
            agree_corr_rows.append({p1_col: c1, p2_col: c2})
        else:
            diff_rows.append(row)
            diff_corr_rows.append({p1_col: c1, p2_col: c2})

    def style_pair(corr_list, pcols):
        corr_df_local = pd.DataFrame(corr_list)
        def fn(df):
            out = pd.DataFrame("", index=df.index, columns=df.columns)
            for col in pcols:
                if col in df.columns and col in corr_df_local.columns:
                    out[col] = corr_df_local[col].map(lambda v: COLORS.get(v, ""))
            return out
        return fn

    col_ag, col_dif = st.columns(2)

    with col_ag:
        st.markdown(f"**✅ Coinciden ({len(agree_rows)})**")
        if agree_rows:
            df_ag = pd.DataFrame(agree_rows)
            styled_ag = df_ag.style.apply(style_pair(agree_corr_rows, [p1_col, p2_col]), axis=None)
            st.dataframe(styled_ag, hide_index=True, use_container_width=True,
                         height=min(35 * len(agree_rows) + 38, 420))
        else:
            st.info("No coinciden en ninguna predicción.")

    with col_dif:
        n_diff_played = sum(1 for c in diff_corr_rows if c.get(p1_col) != "pending")
        p1_diff_pts   = sum(1 for c in diff_corr_rows if c.get(p1_col) == "correct")
        p2_diff_pts   = sum(1 for c in diff_corr_rows if c.get(p2_col) == "correct")

        st.markdown(f"**❌ Difieren ({len(diff_rows)})**")
        if diff_rows:
            df_dif = pd.DataFrame(diff_rows)
            styled_dif = df_dif.style.apply(style_pair(diff_corr_rows, [p1_col, p2_col]), axis=None)
            st.dataframe(styled_dif, hide_index=True, use_container_width=True,
                         height=min(35 * len(diff_rows) + 38, 420))
            if n_diff_played:
                mc1, mc2 = st.columns(2)
                mc1.metric(p1_col, f"{p1_diff_pts} pts", f"de {n_diff_played} jugados")
                mc2.metric(p2_col, f"{p2_diff_pts} pts", f"de {n_diff_played} jugados")
        else:
            st.info("Coinciden en todas las predicciones.")

# ── Tab 5: Perfiles ───────────────────────────────────────────────────────────

with tab_profile:
    sel_p = st.selectbox("Participante:", participants, format_func=participant_col,
                         key="profile_person", index=participants.index("ame"))

    # ── Stats ─────────────────────────────────────────────────────────────────
    total_pts = sum(
        1 for m in completed
        if m["predictions"].get(sel_p) is not None
        and m["predictions"][sel_p] == get_winner(m)
    )
    n_pred = sum(1 for m in completed if m["predictions"].get(sel_p) is not None)
    accuracy = total_pts / n_pred if n_pred else 0.0

    # Competition rank (people with strictly more points come before)
    all_pts = {
        p: sum(1 for m in completed
               if m["predictions"].get(p) is not None
               and m["predictions"][p] == get_winner(m))
        for p in participants
    }
    rank = sum(1 for p in participants if all_pts[p] > all_pts[sel_p]) + 1

    # ── Header row: avatar + stats ────────────────────────────────────────────
    col_pic, col_stats = st.columns([1, 3])

    with col_pic:
        avatar = f"assets/{sel_p}.png"
        if os.path.exists(avatar):
            st.image(avatar, width=160)

    with col_stats:
        st.subheader(participant_col(sel_p))
        c1, c2, c3 = st.columns(3)
        c1.metric("Puntos", total_pts)
        c2.metric("Posición", MEDALS.get(rank, f"#{rank}"))
        c3.metric("Aciertos", f"{accuracy:.0%}" if n_pred else "—")

    st.divider()

    # ── Rank evolution chart ──────────────────────────────────────────────────
    if completed:
        rank_rows = []
        running_r = {p: 0 for p in participants}
        last_m = 0
        for m in completed:
            winner = get_winner(m)
            for p in participants:
                if m["predictions"].get(p) is not None and m["predictions"][p] == winner:
                    running_r[p] += 1
            sel_pts = running_r[sel_p]
            rank_now = sum(1 for p in participants if running_r[p] > sel_pts) + 1
            rank_rows.append({"match": m["match_number"], "posición": rank_now})
            last_m = m["match_number"]
        # Phantom trailing point for horizontal line ending
        rank_rows.append({"match": last_m + 0.5, "posición": rank_rows[-1]["posición"]})

        df_rank = pd.DataFrame(rank_rows)
        p_color = PALETTE[participants.index(sel_p)]

        rank_chart = (
            alt.Chart(df_rank)
            .mark_line(interpolate="step-after", color=p_color, strokeWidth=2.5)
            .encode(
                x=alt.X("match:Q", title="Partido #",
                         axis=alt.Axis(tickMinStep=1),
                         scale=alt.Scale(domain=[1, last_m + 0.5])),
                y=alt.Y("posición:Q", title="Posición",
                         scale=alt.Scale(reverse=True, domain=[1, n_parts]),
                         axis=alt.Axis(tickMinStep=1, values=list(range(1, n_parts + 1)))),
                tooltip=[
                    alt.Tooltip("match:Q",    title="Partido",  format="d"),
                    alt.Tooltip("posición:Q", title="Posición"),
                ],
            )
            .properties(height=250, title="Evolución de posición en el torneo")
        )
        st.altair_chart(rank_chart, use_container_width=True)

        real_ranks = [r["posición"] for r in rank_rows if r["match"] % 1 == 0 and r["match"] > 0]
        if real_ranks:
            rb1, rb2 = st.columns(2)
            rb1.metric("🏆 Mejor posición", MEDALS.get(min(real_ranks), f"#{min(real_ranks)}"))
            rb2.metric("📉 Peor posición", f"#{max(real_ranks)}")

    st.divider()

    # ── Best / worst game ─────────────────────────────────────────────────────
    their_good = [g for g in consensus if sel_p in g["scorers"]]
    their_bad  = [g for g in consensus if sel_p in g["missers"]]

    # Best: scored in the game where fewest others did (rarest correct call)
    best  = min(their_good, key=lambda g: g["n_correct"]) if their_good else None
    # Worst: missed in the game where most others scored (most obvious miss)
    worst = max(their_bad,  key=lambda g: g["n_correct"]) if their_bad  else None

    col_best, col_worst = st.columns(2)

    with col_best:
        st.subheader("🌟 Mejor predicción")
        if best:
            pct = best["n_correct"] / n_parts
            with st.container(border=True):
                st.markdown(f"**#{best['#']}** {best['Local']} **{best['Marcador']}** {best['Visitante']}")
                st.progress(pct, text=f"Solo {best['n_correct']} de {n_parts} lo acertaron ({pct:.0%})")
        else:
            st.info("Aún no ha acertado ningún partido.")

    with col_worst:
        st.subheader("💔 Peor predicción")
        if worst:
            pct = worst["n_correct"] / n_parts
            with st.container(border=True):
                st.markdown(f"**#{worst['#']}** {worst['Local']} **{worst['Marcador']}** {worst['Visitante']}")
                st.progress(pct, text=f"{worst['n_correct']} de {n_parts} lo acertaron ({pct:.0%})")
        else:
            st.info("¡Ha acertado todos los partidos!")
