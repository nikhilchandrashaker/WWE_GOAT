"""
Phase 5: win-prediction model.
Features per singles match (from the challenger's perspective, symmetrized):
  - win_rate_entering: wrestler's singles win rate BEFORE this match (career-to-date)
  - opp_win_rate_entering
  - h2h_win_rate_entering: head-to-head win rate vs this opponent before this match
  - is_title_match
  - experience_diff: matches_entering - opp_matches_entering
Target: 1 if this side won.

We build one row per (match, side-A-vs-side-B) using chronological order so "entering" stats
never peek at the future (avoid leakage).
"""
import sqlite3, datetime, json
from collections import defaultdict

CLEAN = "wwe_clean.sqlite"
SRC = "wwe_db_2026-01-18.sqlite"

clean = sqlite3.connect(CLEAN)
clean.row_factory = sqlite3.Row
src = sqlite3.connect(SRC)

card_meta = {cid: date for cid, date in src.execute("SELECT id, event_date FROM Cards")}
match_card = {mid: cid for mid, cid in src.execute("SELECT id, card_id FROM Matches")}

def match_date(mid):
    cid = match_card.get(mid)
    return card_meta.get(cid) if cid else None

singles = list(clean.execute("SELECT match_id, winner_id, loser_id, title_change FROM matches_singles"))
dated = []
for r in singles:
    d = match_date(r["match_id"])
    if d:
        try:
            dt = datetime.datetime.strptime(d[:10], "%Y-%m-%d")
            dated.append((dt, r["match_id"], r["winner_id"], r["loser_id"], r["title_change"]))
        except Exception:
            pass
dated.sort(key=lambda x: x[0])
print(f"Dated singles matches usable for chronological features: {len(dated)}")

career_wins = defaultdict(int)
career_matches = defaultdict(int)
h2h = defaultdict(lambda: defaultdict(lambda: [0,0]))  # h2h[a][b] = [a_wins, total]

X, y = [], []

for dt, mid, w, l, title_change in dated:
    w_matches = career_matches[w]; w_wins = career_wins[w]
    l_matches = career_matches[l]; l_wins = career_wins[l]
    w_wr = w_wins/w_matches if w_matches else 0.5
    l_wr = l_wins/l_matches if l_matches else 0.5
    h2h_w_total = h2h[w][l][1]
    h2h_w_wr = (h2h[w][l][0]/h2h_w_total) if h2h_w_total else 0.5
    exp_diff = w_matches - l_matches
    title_flag = 1 if title_change else 0

    # row 1: from winner's perspective (label=1)
    X.append([w_wr, l_wr, h2h_w_wr, exp_diff, title_flag])
    y.append(1)
    # row 2: from loser's perspective (label=0), mirror features
    h2h_l_total = h2h[l][w][1]
    h2h_l_wr = (h2h[l][w][0]/h2h_l_total) if h2h_l_total else 0.5
    X.append([l_wr, w_wr, h2h_l_wr, -exp_diff, title_flag])
    y.append(0)

    # update running stats AFTER generating features (no leakage)
    career_matches[w]+=1; career_wins[w]+=1
    career_matches[l]+=1
    h2h[w][l][0]+=1; h2h[w][l][1]+=1
    h2h[l][w][1]+=1

print(f"Training examples: {len(X)}")

from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, roc_auc_score

Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42, shuffle=True)

scaler = StandardScaler()
Xtr_s = scaler.fit_transform(Xtr)
Xte_s = scaler.transform(Xte)

model = LogisticRegression(max_iter=1000)
model.fit(Xtr_s, ytr)

pred = model.predict(Xte_s)
proba = model.predict_proba(Xte_s)[:,1]
acc = accuracy_score(yte, pred)
auc = roc_auc_score(yte, proba)
print(f"Test accuracy: {acc:.4f}")
print(f"Test AUC: {auc:.4f}")

feature_names = ["win_rate_entering","opp_win_rate_entering","h2h_win_rate_entering","experience_diff","is_title_match"]
coefs = dict(zip(feature_names, model.coef_[0].tolist()))
print("Coefficients:", coefs)
print("Intercept:", model.intercept_[0])
print("Scaler mean:", scaler.mean_.tolist())
print("Scaler scale:", scaler.scale_.tolist())

# baseline: always predict higher win_rate_entering wins
baseline_correct = sum(1 for i in range(len(Xte)) if (Xte[i][0] > Xte[i][1]) == bool(yte[i]))
baseline_acc = baseline_correct/len(Xte)
print(f"Baseline (higher win-rate wins) accuracy: {baseline_acc:.4f}")

model_export = {
    "feature_names": feature_names,
    "coefficients": model.coef_[0].tolist(),
    "intercept": model.intercept_[0],
    "scaler_mean": scaler.mean_.tolist(),
    "scaler_scale": scaler.scale_.tolist(),
    "test_accuracy": round(acc,4),
    "test_auc": round(auc,4),
    "baseline_accuracy": round(baseline_acc,4),
    "n_train": len(Xtr),
    "n_test": len(Xte),
}
with open("model_export.json","w") as f:
    json.dump(model_export, f, indent=2)
print("\nSaved model_export.json")

clean.close()
src.close()
