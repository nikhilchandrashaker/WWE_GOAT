"""
Phase 0: Data cleaning & wrestler splitting for WWE GOAT project.

Produces a new sqlite db (wwe_clean.sqlite) with:
  - wrestlers_individual   (id, name)              canonical individual wrestlers
  - wrestlers_teams        (id, name, member_ids)  raw multi-name entities, kept for reference
  - matches_singles        (match_id, winner_id, loser_id, ...)      1v1 only
  - matches_tag            (match_id, winner_team_id, loser_team_id, winner_members, loser_members, ...)
  - matches_multiman       (match_id, winner_side, loser_side, winner_members, loser_members, ...)
  - participation          (match_id, wrestler_id, side['winner'/'loser'], context['singles'/'tag'/'multiman'])
      -> the main table individual/team stats get built from downstream

Also filters the id=1 blank-name junk rows out of Belts / Match_Types.
"""
import sqlite3
import re

SRC = "wwe_db_2026-01-18.sqlite"
DST = "wwe_clean.sqlite"

src = sqlite3.connect(SRC)
src.row_factory = sqlite3.Row

import os
if os.path.exists(DST):
    os.remove(DST)
dst = sqlite3.connect(DST)

def split_name(name):
    """Split a Wrestlers.name on ' & ' into individual member names."""
    if name is None:
        return []
    parts = [p.strip() for p in name.split(" & ")]
    return [p for p in parts if p]

# ---------------------------------------------------------------------------
# Step 1: load all wrestlers, build canonical individual-name -> new id map
# ---------------------------------------------------------------------------
cur = src.execute("SELECT id, name FROM Wrestlers")
all_wrestlers = cur.fetchall()

raw_id_to_name = {r["id"]: r["name"] for r in all_wrestlers}
raw_id_to_members = {}  # raw wrestler id -> list of individual member names

individual_name_to_new_id = {}
next_individual_id = 1

for r in all_wrestlers:
    members = split_name(r["name"])
    raw_id_to_members[r["id"]] = members
    for m in members:
        if m not in individual_name_to_new_id:
            individual_name_to_new_id[m] = next_individual_id
            next_individual_id += 1

print(f"Total raw Wrestlers rows: {len(all_wrestlers)}")
print(f"Unique individual names resolved: {len(individual_name_to_new_id)}")

# team entities = raw rows that had 2+ members (i.e. were combos of any size)
team_rows = [r for r in all_wrestlers if len(raw_id_to_members[r["id"]]) >= 2]
print(f"Raw rows that are combos (2+ names): {len(team_rows)}")

# ---------------------------------------------------------------------------
# Step 2: classify every match by shape (singles / tag / multiman)
# ---------------------------------------------------------------------------
cur = src.execute("""
    SELECT id, card_id, winner_id, win_type, loser_id, match_type_id,
           duration, title_id, title_change
    FROM Matches
""")
matches = cur.fetchall()
print(f"Total matches: {len(matches)}")

def side_size(raw_id):
    raw_id_int = int(raw_id) if raw_id is not None and str(raw_id).strip() != "" else None
    if raw_id_int is None or raw_id_int not in raw_id_to_members:
        return 0
    return len(raw_id_to_members[raw_id_int])

classified = {"singles": [], "tag": [], "multiman": [], "unresolved": []}

for m in matches:
    w_raw = m["winner_id"]
    l_raw = m["loser_id"]
    try:
        w_size = side_size(w_raw)
        l_size = side_size(l_raw)
    except Exception:
        classified["unresolved"].append(m)
        continue

    if w_size == 0 or l_size == 0:
        classified["unresolved"].append(m)
    elif w_size == 1 and l_size == 1:
        classified["singles"].append(m)
    elif w_size >= 2 and l_size >= 2:
        classified["tag"].append(m)
    else:
        classified["multiman"].append(m)

for k, v in classified.items():
    print(f"  {k}: {len(v)}")

# ---------------------------------------------------------------------------
# Step 3: build destination schema
# ---------------------------------------------------------------------------
dst.executescript("""
CREATE TABLE wrestlers_individual (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE wrestlers_teams (
    id INTEGER PRIMARY KEY,      -- original raw Wrestlers.id, kept as-is
    name TEXT NOT NULL,
    member_count INTEGER NOT NULL,
    member_ids TEXT NOT NULL     -- comma-separated wrestlers_individual ids
);

CREATE TABLE matches_singles (
    match_id INTEGER PRIMARY KEY,
    card_id INTEGER,
    winner_id INTEGER,           -- wrestlers_individual.id
    loser_id INTEGER,            -- wrestlers_individual.id
    win_type TEXT,
    match_type_id INTEGER,
    duration TEXT,
    title_id INTEGER,
    title_change INTEGER
);

CREATE TABLE matches_tag (
    match_id INTEGER PRIMARY KEY,
    card_id INTEGER,
    winner_team_raw_id INTEGER,  -- wrestlers_teams.id
    loser_team_raw_id INTEGER,   -- wrestlers_teams.id
    winner_member_ids TEXT,
    loser_member_ids TEXT,
    win_type TEXT,
    match_type_id INTEGER,
    duration TEXT,
    title_id INTEGER,
    title_change INTEGER
);

CREATE TABLE matches_multiman (
    match_id INTEGER PRIMARY KEY,
    card_id INTEGER,
    winner_raw_id INTEGER,
    loser_raw_id INTEGER,
    winner_member_ids TEXT,      -- individual ids on winning side
    loser_member_ids TEXT,       -- individual ids on losing side
    win_type TEXT,
    match_type_id INTEGER,
    duration TEXT,
    title_id INTEGER,
    title_change INTEGER
);

-- flat table: one row per (match, wrestler) for easy aggregation later
CREATE TABLE participation (
    match_id INTEGER,
    wrestler_id INTEGER,         -- wrestlers_individual.id
    side TEXT CHECK(side IN ('winner','loser')),
    context TEXT CHECK(context IN ('singles','tag','multiman'))
);

CREATE TABLE belts_clean (id INTEGER PRIMARY KEY, name TEXT);
CREATE TABLE match_types_clean (id INTEGER PRIMARY KEY, name TEXT);
""")

# ---------------------------------------------------------------------------
# Step 4: populate wrestlers_individual + wrestlers_teams
# ---------------------------------------------------------------------------
dst.executemany(
    "INSERT INTO wrestlers_individual (id, name) VALUES (?, ?)",
    [(v, k) for k, v in individual_name_to_new_id.items()]
)

team_insert_rows = []
for r in team_rows:
    members = raw_id_to_members[r["id"]]
    member_ids = [individual_name_to_new_id[m] for m in members]
    team_insert_rows.append((r["id"], r["name"], len(members), ",".join(str(x) for x in member_ids)))
dst.executemany(
    "INSERT INTO wrestlers_teams (id, name, member_count, member_ids) VALUES (?, ?, ?, ?)",
    team_insert_rows
)

# ---------------------------------------------------------------------------
# Step 5: populate matches_singles + participation (singles)
# ---------------------------------------------------------------------------
def to_int_or_none(x):
    try:
        return int(x)
    except (TypeError, ValueError):
        return None

singles_rows = []
participation_rows = []

for m in classified["singles"]:
    w_raw = int(m["winner_id"])
    l_raw = int(m["loser_id"])
    w_name = raw_id_to_members[w_raw][0]
    l_name = raw_id_to_members[l_raw][0]
    w_id = individual_name_to_new_id[w_name]
    l_id = individual_name_to_new_id[l_name]
    singles_rows.append((
        m["id"], m["card_id"], w_id, l_id, m["win_type"],
        to_int_or_none(m["match_type_id"]), m["duration"],
        to_int_or_none(m["title_id"]), m["title_change"]
    ))
    participation_rows.append((m["id"], w_id, "winner", "singles"))
    participation_rows.append((m["id"], l_id, "loser", "singles"))

dst.executemany(
    "INSERT INTO matches_singles VALUES (?,?,?,?,?,?,?,?,?)", singles_rows
)

# ---------------------------------------------------------------------------
# Step 6: populate matches_tag + participation (tag)
# ---------------------------------------------------------------------------
tag_rows = []
for m in classified["tag"]:
    w_raw = int(m["winner_id"])
    l_raw = int(m["loser_id"])
    w_members = [individual_name_to_new_id[n] for n in raw_id_to_members[w_raw]]
    l_members = [individual_name_to_new_id[n] for n in raw_id_to_members[l_raw]]
    tag_rows.append((
        m["id"], m["card_id"], w_raw, l_raw,
        ",".join(str(x) for x in w_members), ",".join(str(x) for x in l_members),
        m["win_type"], to_int_or_none(m["match_type_id"]), m["duration"],
        to_int_or_none(m["title_id"]), m["title_change"]
    ))
    for wid in w_members:
        participation_rows.append((m["id"], wid, "winner", "tag"))
    for lid in l_members:
        participation_rows.append((m["id"], lid, "loser", "tag"))

dst.executemany(
    "INSERT INTO matches_tag VALUES (?,?,?,?,?,?,?,?,?,?,?)", tag_rows
)

# ---------------------------------------------------------------------------
# Step 7: populate matches_multiman + participation (multiman)
# ---------------------------------------------------------------------------
multiman_rows = []
for m in classified["multiman"]:
    w_raw = int(m["winner_id"])
    l_raw = int(m["loser_id"])
    w_members = [individual_name_to_new_id[n] for n in raw_id_to_members[w_raw]]
    l_members = [individual_name_to_new_id[n] for n in raw_id_to_members[l_raw]]
    multiman_rows.append((
        m["id"], m["card_id"], w_raw, l_raw,
        ",".join(str(x) for x in w_members), ",".join(str(x) for x in l_members),
        m["win_type"], to_int_or_none(m["match_type_id"]), m["duration"],
        to_int_or_none(m["title_id"]), m["title_change"]
    ))
    for wid in w_members:
        participation_rows.append((m["id"], wid, "winner", "multiman"))
    for lid in l_members:
        participation_rows.append((m["id"], lid, "loser", "multiman"))

dst.executemany(
    "INSERT INTO matches_multiman VALUES (?,?,?,?,?,?,?,?,?,?,?)", multiman_rows
)

dst.executemany(
    "INSERT INTO participation VALUES (?,?,?,?)", participation_rows
)

# ---------------------------------------------------------------------------
# Step 8: clean Belts / Match_Types (drop id=1 blank-name junk row)
# ---------------------------------------------------------------------------
cur = src.execute("SELECT id, name FROM Belts WHERE id != 1 AND name IS NOT NULL AND TRIM(name) != ''")
dst.executemany("INSERT INTO belts_clean VALUES (?, ?)", cur.fetchall())

cur = src.execute("SELECT id, name FROM Match_Types WHERE id != 1 AND name IS NOT NULL AND TRIM(name) != ''")
dst.executemany("INSERT INTO match_types_clean VALUES (?, ?)", cur.fetchall())

dst.commit()

# ---------------------------------------------------------------------------
# Step 9: sanity report
# ---------------------------------------------------------------------------
print("\n--- Sanity checks ---")
print("wrestlers_individual rows:", dst.execute("SELECT COUNT(*) FROM wrestlers_individual").fetchone()[0])
print("wrestlers_teams rows:", dst.execute("SELECT COUNT(*) FROM wrestlers_teams").fetchone()[0])
print("matches_singles rows:", dst.execute("SELECT COUNT(*) FROM matches_singles").fetchone()[0])
print("matches_tag rows:", dst.execute("SELECT COUNT(*) FROM matches_tag").fetchone()[0])
print("matches_multiman rows:", dst.execute("SELECT COUNT(*) FROM matches_multiman").fetchone()[0])
print("participation rows:", dst.execute("SELECT COUNT(*) FROM participation").fetchone()[0])
print("unresolved matches (dropped, bad refs):", len(classified["unresolved"]))
print("belts_clean rows:", dst.execute("SELECT COUNT(*) FROM belts_clean").fetchone()[0])
print("match_types_clean rows:", dst.execute("SELECT COUNT(*) FROM match_types_clean").fetchone()[0])

# spot-check: Tommy Dreamer should now have participation rows across all 3 contexts
td_id = individual_name_to_new_id.get("Tommy Dreamer")
if td_id:
    cur = dst.execute("SELECT context, COUNT(*) FROM participation WHERE wrestler_id=? GROUP BY context", (td_id,))
    print(f"\nTommy Dreamer (individual id {td_id}) participation by context:", cur.fetchall())

src.close()
dst.close()
print("\nDone ->", DST)
