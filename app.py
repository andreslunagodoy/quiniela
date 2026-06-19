import json
import subprocess
from datetime import datetime
from itertools import combinations

import altair as alt
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Quiniela 2026", page_icon="⚽", layout="wide")

st.markdown("""
<style>
[data-testid="stSidebar"] { min-width: 200px; max-width: 200px; }
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

@st.cache_data(ttl=300)
def load_quiniela():
    with open("quiniela.json", encoding="utf-8") as f:
        return json.load(f)

@st.cache_data(ttl=300)
def load_abbrevs():
    with open("results.json", encoding="utf-8") as f:
        results = json.load(f)
    abbrev = {}
    for m in results["matches"]:
        abbrev[m["home_team"]] = m["home_abbreviation"]
        abbrev[m["away_team"]] = m["away_abbreviation"]
    return abbrev

def refresh_results():
    subprocess.run(["python3", "scrape_results.py"], check=True)
    subprocess.run(["python3", "parse_predictions.py"], check=True)
    load_quiniela.clear()
    load_abbrevs.clear()

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
    st.caption(f"Actualizado: {data['generated_at'][:16].replace('T', ' ')} UTC")
    st.caption(f"{n_played}/{len(matches)} partidos jugados")
    if st.button("🔄 Actualizar resultados", use_container_width=True):
        with st.spinner("Obteniendo resultados..."):
            refresh_results()
        st.rerun()
    st.caption("Hecho con ❤️ para la familia")

# ── Tabs ──────────────────────────────────────────────────────────────────────

tab_score, tab_preds, tab_evo, tab_analisis, tab_profile = st.tabs([
    "🏆 Clasificación", "📋 Predicciones", "📈 Evolución", "🔍 Análisis", "👤 Perfiles",
])

# ── Tab 1: Clasificación ──────────────────────────────────────────────────────

with tab_score:
    st.header("Clasificación")

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

    # ── Tables ────────────────────────────────────────────────────────────────
    col_board, col_recent = st.columns([1, 1.5])

    with col_board:
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

        df_score = pd.DataFrame([{
            "Pos.":         MEDALS.get(r["rank"], str(r["rank"])),
            "Participante": participant_col(r["name"]),
            "Pts.":         r["points"],
            "%":            f"{r['points'] / n_filter * 100:.0f}%" if n_filter else "—",
        } for r in rows])

        st.dataframe(df_score, hide_index=True, use_container_width=False,
                     height=35 * (len(rows) + 1) + 3)
        st.caption(f"Puntos = predicciones correctas de {n_filter} partidos.")

    with col_recent:
        st.subheader("Últimos resultados")
        recent = sorted(filter_matches, key=lambda m: -m["match_number"])[:10]
        if recent:
            df_recent = pd.DataFrame([match_row_display(m) for m in recent])
            st.dataframe(
                df_recent,
                hide_index=True,
                use_container_width=False,
                column_config={
                    "#":        st.column_config.NumberColumn(width="small"),
                    "Marcador": st.column_config.TextColumn(width="small"),
                },
                height=35 * (len(recent) + 1) + 3,
            )
        else:
            st.info("No hay partidos en el rango seleccionado.")

    # ── Filters (below tables) ────────────────────────────────────────────────
    st.divider()
    col_f, _ = st.columns([1.5, 2.5])
    with col_f:
        match_nums_desc = list(reversed([m["match_number"] for m in completed]))
        st.selectbox(
            "Hasta partido:",
            options=[0] + match_nums_desc,
            format_func=lambda n: "Todos" if n == 0
                else f"#{n} — {format_date(next(m['date_utc'] for m in completed if m['match_number'] == n))}",
            index=0,
            key="filter_match",
        )
        unique_dates_desc = sorted(set(m["date_utc"][:10] for m in completed), reverse=True)
        st.selectbox(
            "Hasta fecha:",
            options=["Todas"] + unique_dates_desc,
            format_func=lambda d: "Todas" if d == "Todas" else format_date(d + "T00:00Z"),
            index=0,
            key="filter_date",
        )

# ── Tab 2: Predicciones ───────────────────────────────────────────────────────

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
            else:
                corr[col] = "wrong"

        rows.append(row)
        correctness.append(corr)

    df_preds = pd.DataFrame(rows)
    corr_df  = pd.DataFrame(correctness)
    display_p_cols = list(p_cols.values())

    def style_preds(df):
        styles = pd.DataFrame("", index=df.index, columns=df.columns)
        for col in display_p_cols:
            if col in df.columns:
                for i in df.index:
                    styles.loc[i, col] = COLORS.get(corr_df.loc[i, col], "")
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
    st.subheader("Pares más similares")

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

    col_top_p, col_bot_p = st.columns(2)
    with col_top_p:
        st.markdown("**Top 3 pares más similares**")
        st.dataframe(pairs_df(all_pairs[:3]), hide_index=True, use_container_width=True)
    with col_bot_p:
        st.markdown("**Top 3 pares más diferentes**")
        st.dataframe(pairs_df(list(reversed(all_pairs[-3:]))), hide_index=True, use_container_width=True)

    st.divider()

    # ── Similarity per person ─────────────────────────────────────────────────
    st.subheader("Similitud por participante")

    sel_person = st.selectbox(
        "Selecciona un participante:",
        options=participants,
        format_func=participant_col,
    )

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
        st.markdown("**Top 3 más similares**")
        st.dataframe(sim_table(others[:3]), hide_index=True, use_container_width=True)
    with col_sim2:
        st.markdown("**Top 3 más diferentes**")
        st.dataframe(sim_table(list(reversed(others[-3:]))), hide_index=True, use_container_width=True)

    st.divider()

    # ── Pair comparison ───────────────────────────────────────────────────────
    st.subheader("Comparar dos participantes")

    col_p1, col_p2 = st.columns(2)
    with col_p1:
        pair1 = st.selectbox("Participante 1:", participants,
                             format_func=participant_col, key="pair1")
    with col_p2:
        pair2 = st.selectbox("Participante 2:",
                             [p for p in participants if p != pair1],
                             format_func=participant_col, key="pair2")

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
                         key="profile_person")

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
        if __import__("os").path.exists(avatar):
            st.image(avatar, width=160)

    with col_stats:
        st.subheader(participant_col(sel_p))
        c1, c2, c3 = st.columns(3)
        c1.metric("Puntos", total_pts)
        c2.metric("Posición", MEDALS.get(rank, f"#{rank}"))
        c3.metric("Aciertos", f"{accuracy:.0%}" if n_pred else "—")

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
