"""
Phase 1-4: build wrestler_stats, rivalries, title_reigns tables on top of wwe_clean.sqlite
"""
import sqlite3, datetime
from collections import defaultdict

SRC = "wwe_db_2026-01-18.sqlite"
CLEAN = "wwe_clean.sqlite"

src = sqlite3.connect(SRC)
clean = sqlite3.connect(CLEAN)
clean.row_factory = sqlite3.Row

# ---------------------------------------------------------------------------
# Load supporting maps: match_id -> (date, promotion_id, event_id)
# ---------------------------------------------------------------------------
card_meta = {}
for cid, date, promo_id, event_id in src.execute("SELECT id, event_date, promotion_id, event_id FROM Cards"):
    card_meta[cid] = (date, promo_id, event_id)

match_card = {mid: card_id for mid, card_id in src.execute("SELECT id, card_id FROM Matches")}

def meta_for_match(mid):
    cid = match_card.get(mid)
    if cid is None:
        return (None, None, None)
    return card_meta.get(cid, (None, None, None))

promo_names = {pid: name for pid, name in src.execute("SELECT id, name FROM Promotions")}

# ---------------------------------------------------------------------------
# Phase 1: wrestler_stats (singles-only for GOAT, tag/multiman tracked separately)
# ---------------------------------------------------------------------------
clean.executescript("""
DROP TABLE IF EXISTS wrestler_stats;
CREATE TABLE wrestler_stats (
    wrestler_id INTEGER PRIMARY KEY,
    name TEXT,
    possible_collision INTEGER,
    singles_wins INTEGER,
    singles_losses INTEGER,
    singles_matches INTEGER,
    singles_win_rate REAL,
    tag_wins INTEGER,
    tag_losses INTEGER,
    tag_matches INTEGER,
    multiman_wins INTEGER,
    multiman_matches INTEGER,
    first_match_date TEXT,
    last_match_date TEXT,
    years_active REAL,
    singles_title_reigns INTEGER,
    singles_title_days INTEGER,
    sos REAL,              -- strength of schedule: avg opponent singles win rate
    goat_score REAL
);
""")

# gather singles participation with dates
singles_part = []  # (wrestler_id, match_id, side, date)
for row in clean.execute("SELECT match_id, wrestler_id, side FROM participation WHERE context='singles'"):
    date, promo, event = meta_for_match(row["match_id"])
    singles_part.append((row["wrestler_id"], row["match_id"], row["side"], date))

by_wrestler_singles = defaultdict(list)
for wid, mid, side, date in singles_part:
    by_wrestler_singles[wid].append((mid, side, date))

# tag / multiman aggregates
tag_stats = defaultdict(lambda: [0,0,0])   # wins, losses, matches
for row in clean.execute("SELECT wrestler_id, side FROM participation WHERE context='tag'"):
    s = tag_stats[row["wrestler_id"]]
    s[2]+=1
    if row["side"]=="winner": s[0]+=1
    else: s[1]+=1

mm_stats = defaultdict(lambda: [0,0])  # wins, matches
for row in clean.execute("SELECT wrestler_id, side FROM participation WHERE context='multiman'"):
    s = mm_stats[row["wrestler_id"]]
    s[1]+=1
    if row["side"]=="winner": s[0]+=1

# singles win rate per wrestler (needed for SOS calc) - first pass
win_rate = {}
for wid, matches in by_wrestler_singles.items():
    wins = sum(1 for _,side,_ in matches if side=="winner")
    win_rate[wid] = wins/len(matches) if matches else 0.0

# opponent map for singles matches: match_id -> (winner_id, loser_id)
singles_match_pair = {}
for row in clean.execute("SELECT match_id, winner_id, loser_id FROM matches_singles"):
    singles_match_pair[row["match_id"]] = (row["winner_id"], row["loser_id"])

# title reigns per wrestler (singles title matches only, title_change=1)
title_matches = list(clean.execute("""
    SELECT match_id, winner_id, loser_id, title_id FROM matches_singles WHERE title_change=1
"""))

# build reign length per belt using chronological order across ALL match types (singles+tag) is more correct,
# but for individual attribution we only score singles title reigns. Compute reign end dates using a
# unified per-belt timeline (any match with that title_id and title_change=1, singles or tag).
belt_events = defaultdict(list)  # belt_id -> [(date, match_id, kind, winner_repr)]
for row in clean.execute("SELECT match_id, winner_id, title_id FROM matches_singles WHERE title_change=1 AND title_id IS NOT NULL"):
    d,_,_ = meta_for_match(row["match_id"])
    belt_events[row["title_id"]].append((d, row["match_id"], "singles", row["winner_id"]))
for row in clean.execute("SELECT match_id, winner_team_raw_id, title_id FROM matches_tag WHERE title_change=1 AND title_id IS NOT NULL"):
    d,_,_ = meta_for_match(row["match_id"])
    belt_events[row["title_id"]].append((d, row["match_id"], "tag", row["winner_team_raw_id"]))

singles_title_reigns = defaultdict(lambda: [0,0])  # wrestler_id -> [reign_count, total_days]
for belt_id, events in belt_events.items():
    events = [e for e in events if e[0]]
    events.sort(key=lambda e: e[0])
    for i, (d, mid, kind, winner) in enumerate(events):
        start = datetime.datetime.strptime(d[:10], "%Y-%m-%d")
        if i+1 < len(events) and events[i+1][0]:
            end = datetime.datetime.strptime(events[i+1][0][:10], "%Y-%m-%d")
        else:
            end = datetime.datetime(2026,1,16)  # dataset end
        days = max((end-start).days, 0)
        if kind == "singles":
            singles_title_reigns[winner][0] += 1
            singles_title_reigns[winner][1] += days

# SOS: average opponent's overall singles win rate
sos_sum = defaultdict(float)
sos_count = defaultdict(int)
for mid, (w, l) in singles_match_pair.items():
    sos_sum[w] += win_rate.get(l, 0.0)
    sos_count[w] += 1
    sos_sum[l] += win_rate.get(w, 0.0)
    sos_count[l] += 1

names = {row["id"]: row["name"] for row in clean.execute("SELECT id, name FROM wrestlers_individual")}
collision = {row["id"]: row["possible_collision"] for row in clean.execute("SELECT id, possible_collision FROM wrestlers_individual")}

rows = []
for wid, name in names.items():
    matches = by_wrestler_singles.get(wid, [])
    wins = sum(1 for _,side,_ in matches if side=="winner")
    losses = len(matches)-wins
    dates = sorted(d for _,_,d in matches if d)
    first_d = dates[0] if dates else None
    last_d = dates[-1] if dates else None
    years_active = 0.0
    if first_d and last_d:
        try:
            fd = datetime.datetime.strptime(first_d[:10], "%Y-%m-%d")
            ld = datetime.datetime.strptime(last_d[:10], "%Y-%m-%d")
            years_active = round((ld-fd).days/365.25, 2)
        except Exception:
            pass
    tw, tl, tm = tag_stats.get(wid, [0,0,0])
    mw, mm = mm_stats.get(wid, [0,0])
    reigns, reign_days = singles_title_reigns.get(wid, [0,0])
    sos = sos_sum[wid]/sos_count[wid] if sos_count.get(wid) else 0.0

    rows.append((
        wid, name, collision.get(wid,0),
        wins, losses, len(matches), (wins/len(matches) if matches else 0.0),
        tw, tl, tm,
        mw, mm,
        first_d, last_d, years_active,
        reigns, reign_days, sos, 0.0  # goat_score placeholder
    ))

clean.executemany("""
INSERT INTO wrestler_stats VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
""", rows)
clean.commit()

# ---------------------------------------------------------------------------
# Compute GOAT score: normalize components 0-1 among wrestlers with >=10 singles matches,
# composite = weighted sum. Default draft weights (to be tuned):
#   win_rate 30%, longevity(years_active) 15%, volume(singles_matches) 15%,
#   title_days 25%, sos 15%
# ---------------------------------------------------------------------------
qualified = [r for r in clean.execute("SELECT * FROM wrestler_stats WHERE singles_matches >= 10")]

def normalize(values):
    lo, hi = min(values), max(values)
    if hi == lo:
        return [0.5]*len(values)
    return [(v-lo)/(hi-lo) for v in values]

win_rates = [r["singles_win_rate"] for r in qualified]
years = [r["years_active"] for r in qualified]
volumes = [r["singles_matches"] for r in qualified]
title_days = [r["singles_title_days"] for r in qualified]
sos_vals = [r["sos"] for r in qualified]

n_wr = normalize(win_rates)
n_yr = normalize(years)
n_vol = normalize(volumes)
n_td = normalize(title_days)
n_sos = normalize(sos_vals)

W_WINRATE, W_LONGEVITY, W_VOLUME, W_TITLE, W_SOS = 0.30, 0.15, 0.15, 0.25, 0.15

updates = []
for i, r in enumerate(qualified):
    score = (W_WINRATE*n_wr[i] + W_LONGEVITY*n_yr[i] + W_VOLUME*n_vol[i] +
             W_TITLE*n_td[i] + W_SOS*n_sos[i]) * 100
    updates.append((round(score,2), r["wrestler_id"]))

clean.executemany("UPDATE wrestler_stats SET goat_score=? WHERE wrestler_id=?", updates)
clean.commit()

print(f"wrestler_stats rows: {clean.execute('SELECT COUNT(*) FROM wrestler_stats').fetchone()[0]}")
print(f"qualified for GOAT scoring (>=10 singles matches): {len(qualified)}")

top10 = clean.execute("""
    SELECT name, singles_wins, singles_losses, ROUND(singles_win_rate,3) wr,
           years_active, singles_title_reigns, singles_title_days, ROUND(sos,3) sos, goat_score, possible_collision
    FROM wrestler_stats ORDER BY goat_score DESC LIMIT 15
""").fetchall()
print("\nTop 15 draft GOAT leaderboard:")
for r in top10:
    print(dict(r))

clean.close()
src.close()
