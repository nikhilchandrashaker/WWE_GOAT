"""
Phase 3: rivalry network (singles head-to-head pairs)
Phase 4: title reign history (all belts, chronological, singles + tag)
"""
import sqlite3, datetime, json
from collections import defaultdict

CLEAN = "wwe_clean.sqlite"
SRC = "wwe_db_2026-01-18.sqlite"

clean = sqlite3.connect(CLEAN)
clean.row_factory = sqlite3.Row
src = sqlite3.connect(SRC)

card_meta = {cid: (date, promo_id, event_id) for cid, date, promo_id, event_id in
             src.execute("SELECT id, event_date, promotion_id, event_id FROM Cards")}
match_card = {mid: cid for mid, cid in src.execute("SELECT id, card_id FROM Matches")}

def meta(mid):
    cid = match_card.get(mid)
    return card_meta.get(cid, (None, None, None)) if cid else (None, None, None)

names = {row[0]: row[1] for row in clean.execute("SELECT id, name FROM wrestlers_individual")}
promo_names = {pid: name for pid, name in src.execute("SELECT id, name FROM Promotions")}

# ---------------------------------------------------------------------------
# Phase 3: rivalries (singles only, per project scope)
# ---------------------------------------------------------------------------
clean.executescript("""
DROP TABLE IF EXISTS rivalries;
CREATE TABLE rivalries (
    wrestler_a INTEGER,
    wrestler_b INTEGER,
    a_wins INTEGER,
    b_wins INTEGER,
    total_matches INTEGER,
    closeness REAL,     -- 1.0 = perfectly even split, 0 = one-sided
    first_date TEXT,
    last_date TEXT
);
""")

pair_stats = defaultdict(lambda: {"a_wins":0,"b_wins":0,"dates":[]})

for row in clean.execute("SELECT match_id, winner_id, loser_id FROM matches_singles"):
    w, l = row["winner_id"], row["loser_id"]
    key = tuple(sorted((w,l)))
    d,_,_ = meta(row["match_id"])
    ps = pair_stats[key]
    if d: ps["dates"].append(d)
    if w == key[0]:
        ps["a_wins"] += 1
    else:
        ps["b_wins"] += 1

riv_rows = []
for (a,b), s in pair_stats.items():
    total = s["a_wins"] + s["b_wins"]
    if total < 3:
        continue  # skip one-off matches, not a "rivalry"
    closeness = 1 - abs(s["a_wins"]-s["b_wins"])/total
    dates = sorted(s["dates"])
    riv_rows.append((a, b, s["a_wins"], s["b_wins"], total, round(closeness,3),
                      dates[0] if dates else None, dates[-1] if dates else None))

clean.executemany("INSERT INTO rivalries VALUES (?,?,?,?,?,?,?,?)", riv_rows)
clean.commit()
print(f"rivalries rows (>=3 matches): {len(riv_rows)}")

# ---------------------------------------------------------------------------
# Phase 4: title_reigns (unified singles + tag, chronological per belt)
# ---------------------------------------------------------------------------
clean.executescript("""
DROP TABLE IF EXISTS title_reigns;
CREATE TABLE title_reigns (
    belt_id INTEGER,
    belt_name TEXT,
    reign_order INTEGER,
    kind TEXT,               -- 'singles' or 'tag'
    champion_id INTEGER,      -- wrestlers_individual.id (singles) or wrestlers_teams.id (tag)
    champion_name TEXT,
    start_date TEXT,
    end_date TEXT,
    reign_days INTEGER,
    won_by_match_id INTEGER
);
""")

belt_names = {row[0]: row[1] for row in clean.execute("SELECT id, name FROM belts_clean")}

belt_events = defaultdict(list)
for row in clean.execute("SELECT match_id, winner_id, title_id FROM matches_singles WHERE title_change=1 AND title_id IS NOT NULL"):
    d,_,_ = meta(row["match_id"])
    if d:
        belt_events[row["title_id"]].append((d, row["match_id"], "singles", row["winner_id"], names.get(row["winner_id"],"?")))
for row in clean.execute("SELECT match_id, winner_team_raw_id, title_id FROM matches_tag WHERE title_change=1 AND title_id IS NOT NULL"):
    d,_,_ = meta(row["match_id"])
    if d:
        tname = clean.execute("SELECT name FROM wrestlers_teams WHERE id=?", (row["winner_team_raw_id"],)).fetchone()
        belt_events[row["title_id"]].append((d, row["match_id"], "tag", row["winner_team_raw_id"], tname[0] if tname else "?"))

reign_rows = []
DATASET_END = "2026-01-16"
for belt_id, events in belt_events.items():
    events.sort(key=lambda e: e[0])
    for i, (d, mid, kind, champ_id, champ_name) in enumerate(events):
        start = datetime.datetime.strptime(d[:10], "%Y-%m-%d")
        end_d = events[i+1][0] if i+1 < len(events) else DATASET_END
        end = datetime.datetime.strptime(end_d[:10], "%Y-%m-%d")
        days = max((end-start).days, 0)
        reign_rows.append((belt_id, belt_names.get(belt_id, f"Belt {belt_id}"), i+1, kind,
                            champ_id, champ_name, d, end_d if i+1 < len(events) else None, days, mid))

clean.executemany("INSERT INTO title_reigns VALUES (?,?,?,?,?,?,?,?,?,?)", reign_rows)
clean.commit()
print(f"title_reigns rows: {len(reign_rows)}")

# sanity: top 10 longest reigns
top_reigns = clean.execute("""
    SELECT belt_name, champion_name, kind, start_date, reign_days
    FROM title_reigns ORDER BY reign_days DESC LIMIT 10
""").fetchall()
print("\nTop 10 longest reigns:")
for r in top_reigns:
    print(dict(r))

clean.close()
src.close()
