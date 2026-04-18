import csv, random
from datetime import datetime, timedelta

random.seed(42)

EVENT_SEQUENCES = {
    "pattern_A": {
        "week1": [
            ("signed_up",0),("created_workspace",0),("created_project",0),
            ("added_task",0),("added_task",0),("invited_teammate",1),
            ("teammate_joined",1),("teammate_commented",2),
            ("assigned_task",2),("added_task",3),("logged_in",4),
            ("teammate_added_task",5),("logged_in",6),
        ],
        "return": [
            ("logged_in",15),("added_task",15),("teammate_commented",16),
            ("logged_in",18),("assigned_task",19),("added_task",20),
            ("logged_in",22),("teammate_added_task",23),("logged_in",25),
            ("added_task",27),("logged_in",29),
        ]
    },
    "pattern_B": {
        # AT RISK: invited teammate, teammate joined but collab event never happened
        # teammate_joined = 1, collab_within_48h = 0
        # score = 0 + 0.25 + 0.15*(1/3) + 0.10*(3/7) = ~0.40 → clearly At Risk
        "week1": [
            ("signed_up",0),("created_workspace",0),("created_project",0),
            ("added_task",1),("invited_teammate",2),
            ("teammate_joined",4),  # joined 48h+ after invite — collab window missed
            ("logged_in",5),("added_task",6),
        ],
        "return": []  # no return — they churned without full activation
    },
    "pattern_C": {
        "week1": [
            ("signed_up",0),("created_workspace",0),("created_project",0),
            ("added_task",1),("added_task",2),("logged_in",3),("added_task",4),
        ],
        "return": []
    },
    "pattern_D": {
        "week1": [
            ("signed_up",0),("viewed_onboarding",0),
            ("logged_in",2),("logged_in",5),
        ],
        "return": []
    },
    "pattern_E": {
        "week1": [("signed_up",0)],
        "return": []
    },
    "pattern_F": {
        "week1": [
            ("signed_up",0),("created_workspace",0),("created_project",0),
            ("added_task",0),("added_task",0),("added_task",0),
            ("invited_teammate",0),("invited_teammate",1),
            ("teammate_joined",1),("teammate_commented",1),
            ("assigned_task",1),("teammate_joined",2),
            ("teammate_commented",2),("assigned_task",2),
            ("added_task",3),("logged_in",4),
            ("teammate_added_task",4),("logged_in",5),
            ("added_task",6),("logged_in",6),
        ],
        "return": [
            ("logged_in",14),("added_task",14),("teammate_commented",15),
            ("assigned_task",15),("logged_in",16),("teammate_added_task",17),
            ("logged_in",18),("added_task",19),("logged_in",20),
            ("teammate_commented",21),("logged_in",22),("added_task",23),
            ("assigned_task",24),("logged_in",25),("teammate_added_task",26),
            ("logged_in",27),("added_task",28),("logged_in",29),
        ]
    },
    # NOISE: hit collab within 48h BUT still churned
    "pattern_G": {
        "week1": [
            ("signed_up",0),("created_workspace",0),("created_project",0),
            ("added_task",1),("invited_teammate",1),
            ("teammate_joined",2),("teammate_commented",2),("logged_in",4),
        ],
        "return": []
    },
    # NOISE: solo power user — never invited anyone but came back anyway
    "pattern_H": {
        "week1": [
            ("signed_up",0),("created_workspace",0),("created_project",0),
            ("added_task",0),("added_task",1),("logged_in",2),
            ("added_task",3),("logged_in",4),("added_task",5),("logged_in",6),
        ],
        "return": [
            ("logged_in",15),("added_task",16),("logged_in",18),
            ("added_task",20),("logged_in",23),
        ]
    },
    # NOISE: lurker who came back after a re-engagement email
    "pattern_I": {
        "week1": [
            ("signed_up",0),("viewed_onboarding",0),("logged_in",3),
        ],
        "return": [
            ("logged_in",18),("created_project",18),("added_task",19),
        ]
    },
    # AT RISK variant 2: invited teammate but teammate never joined at all
    # teammate_joined=0, collab_within_48h=0, invited=1, sessions=3
    # score = 0 + 0 + 0.15*(1/3) + 0.10*(3/7) = ~0.09 → Likely churned
    # To push into at-risk we need them to have invited multiple times with some sessions
    # invited=3 → 0.15*(3/3)=0.15, sessions=5 → 0.10*(5/7)=0.07 → score ~0.22 still low
    # Best at-risk pattern: teammate_joined=1, no collab, moderate sessions
    # score = 0.25 + 0.15*(1/3) + 0.10*(4/7) = 0.25+0.05+0.057 = 0.357 → At Risk ✓
    "pattern_J": {
        "week1": [
            ("signed_up",0),("created_workspace",0),("created_project",0),
            ("added_task",0),("invited_teammate",1),
            ("teammate_joined",2),  # joined quickly but no collab event ever
            ("logged_in",3),("logged_in",4),("added_task",5),
        ],
        "return": []
    },
}

NAMES = [
    "Sarah","Marcus","Priya","James","Lena","Tom","Ana","Kevin",
    "Diana","Ryan","Sofia","Chris","Maya","Alex","Jordan","Taylor",
    "Morgan","Casey","Blake","Drew","Avery","Quinn","Riley","Sage",
    "Harper","Logan","Peyton","Reese","Skylar","Jamie","Cameron","Finley",
    "Emerson","Parker","Rowan","Hayden","Kendall","Sawyer","Dakota","River",
    "Nora","Ellis","Remy","Sloane","Wren","Paige","Juno","Sable",
    "Nova","Reid","Zara","Leon","Iris","Cole","Vera","Dean",
    "Mia","Eli","Cleo","Owen","Fen","Ash","Zoe","Kai",
    "Theo","Nyx","Sam","Luna","Max","Skye","Rue","Bo",
    "Arlo","Fern","Cass","Opal","Bram","Jade","Cora","Luca",
    "Finn","Willa","Rhys","Bex","Tate","Ivy","Jett","Maeve",
    "Cruz","Seren","Nico","Prue","Knox","Aria","Zeb","Tess",
    "Beau","Suki","Dax","Lark","Cove","Nell","Reef","June",
    "Wolf","Ciel","Ren","Faye","Cade","Lyra","Bash","Wren2",
    "Pace","Bryn","Zane","Plum","Bolt","Clove","Haze","Birch",
][:120]

# Deterministically assign patterns to guarantee realistic noise distribution.
# Explicit pattern assignments for noise users — rest assigned randomly.
FORCED_PATTERNS = {
    # Force 10 H users (no signal, retained) spread across cohort
    5:"pattern_H", 15:"pattern_H", 25:"pattern_H", 35:"pattern_H", 45:"pattern_H",
    55:"pattern_H", 65:"pattern_H", 75:"pattern_H", 85:"pattern_H", 95:"pattern_H",
    # Force 5 I users (lurker, retained)
    10:"pattern_I", 30:"pattern_I", 50:"pattern_I", 70:"pattern_I", 90:"pattern_I",
    # Force 12 G users (signal hit, still churned)
    8:"pattern_G", 18:"pattern_G", 28:"pattern_G", 38:"pattern_G", 48:"pattern_G",
    58:"pattern_G", 68:"pattern_G", 78:"pattern_G", 88:"pattern_G", 98:"pattern_G",
    108:"pattern_G", 118:"pattern_G",
    # Force 15 J users (teammate joined, no collab = clearly at-risk score ~0.35)
    3:"pattern_J",  13:"pattern_J", 23:"pattern_J", 33:"pattern_J", 43:"pattern_J",
    53:"pattern_J", 63:"pattern_J", 73:"pattern_J", 83:"pattern_J", 93:"pattern_J",
    103:"pattern_J",112:"pattern_J",116:"pattern_J",
    # Force 10 B users (invited, teammate joined late = at-risk score ~0.40)
    7:"pattern_B",  17:"pattern_B", 37:"pattern_B", 47:"pattern_B", 57:"pattern_B",
    67:"pattern_B", 77:"pattern_B", 87:"pattern_B", 97:"pattern_B", 107:"pattern_B",
}

POOL_WEIGHTS = {"pattern_A":0.30,"pattern_C":0.30,"pattern_D":0.20,
                "pattern_E":0.10,"pattern_F":0.10}

rows = []
base_dt = datetime(2024, 1, 1, 9, 0, 0)
pattern_counts = {}

for i, name in enumerate(NAMES):
    if i in FORCED_PATTERNS:
        pattern = FORCED_PATTERNS[i]
    else:
        pattern = random.choices(list(POOL_WEIGHTS.keys()),
                                  weights=list(POOL_WEIGHTS.values()))[0]
    pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1

    seq = EVENT_SEQUENCES[pattern]
    all_events = seq["week1"] + seq["return"]
    signup_day = i // 2   # 2 signups per day → 60 days

    for (event, day_offset) in all_events:
        h = random.randint(8, 22)
        m = random.randint(0, 59)
        ts = base_dt + timedelta(days=signup_day + day_offset, hours=h, minutes=m)
        rows.append({
            "user_id":   f"usr_{i+1:03d}",
            "user_name": name,
            "event":     event,
            "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
        })

rows.sort(key=lambda r: r["timestamp"])

with open("events.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["user_id","user_name","event","timestamp"])
    w.writeheader()
    w.writerows(rows)

print(f"Generated {len(rows)} raw events for {len(NAMES)} users over 60 days")
print(f"Date range: {rows[0]['timestamp'][:10]} to {rows[-1]['timestamp'][:10]}")
print(f"\nPattern distribution:")
for p, cnt in sorted(pattern_counts.items()):
    noise = " ← noise" if p in ("pattern_G","pattern_H","pattern_I") else ""
    print(f"  {p}: {cnt} users{noise}")
print(f"\nNoise users ensure:")
print(f"  G ({pattern_counts.get('pattern_G',0)} users): hit activation signal but churned")
print(f"  H ({pattern_counts.get('pattern_H',0)} users): no signal but retained (solo power user)")
print(f"  I ({pattern_counts.get('pattern_I',0)} users): lurker who returned → Retention if missed > 0%")
