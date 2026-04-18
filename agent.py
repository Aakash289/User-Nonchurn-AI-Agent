"""
User NonChurn AI — Agentic version
===================================
Claude acts as a proper AI agent with a tool loop.
It receives the raw event log and autonomously decides:
  - which features to compute
  - which correlations to investigate
  - how to define the activation signal
  - what segments to create
  - what actions to recommend

Claude calls tools one at a time, reasons about the results,
then decides what to do next — exactly like a real data analyst.
"""

import csv, json, math, os, sys
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import anthropic

# ── TOOL DEFINITIONS ──────────────────────────────────────────────────────────
# These are the tools Claude can call. Each one does exactly one thing.
# Claude decides when to call them and in what order.

TOOLS = [
    {
        "name": "load_events",
        "description": "Load the raw event log from events.csv. Returns summary stats and the first 20 rows so Claude can understand the data structure before analysis.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "compute_user_features",
        "description": "For every user, compute behavioural features from their first 7 days: projects_created, tasks_added, teammates_invited, teammate_joined, collab_within_48h, sessions, watched_onboarding. Also derives the retention label from whether the user had any activity after Day 13.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "run_correlations",
        "description": "Compute Pearson correlation between every feature and the retention label. Returns a ranked list of features by predictive power. Use this to discover which user actions actually predict long-term retention.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "analyse_feature",
        "description": "Deep dive into a specific feature. Returns retention rates split by whether users did vs did not perform this action, plus the lift ratio. Use this to validate a hypothesis about what drives retention.",
        "input_schema": {
            "type": "object",
            "properties": {
                "feature_name": {
                    "type": "string",
                    "description": "The feature to analyse, e.g. collab_within_48h or teammate_joined"
                }
            },
            "required": ["feature_name"]
        }
    },
    {
        "name": "define_activation_signal",
        "description": "Formally define the activation signal with a name, description, and the feature that represents it. This becomes the official definition stored in the results.",
        "input_schema": {
            "type": "object",
            "properties": {
                "feature": {
                    "type": "string",
                    "description": "The feature name that defines the activation signal"
                },
                "description": {
                    "type": "string",
                    "description": "Plain English description of what the activation signal means in product terms"
                },
                "reasoning": {
                    "type": "string",
                    "description": "Why this feature was chosen as the activation signal over alternatives"
                }
            },
            "required": ["feature", "description", "reasoning"]
        }
    },
    {
        "name": "score_and_segment_users",
        "description": "Apply the scoring formula to every user and assign them to High Activation, At Risk, or Likely Churned segments. Also generates a recommended action per user.",
        "input_schema": {
            "type": "object",
            "properties": {
                "weights": {
                    "type": "object",
                    "description": "Weight for each feature in the scoring formula. Must sum to 1.0. E.g. {collab_within_48h: 0.5, teammate_joined: 0.25, teammates_invited: 0.15, sessions: 0.10}",
                    "additionalProperties": {"type": "number"}
                },
                "high_threshold": {
                    "type": "number",
                    "description": "Score threshold above which user is High Activation (e.g. 0.65)"
                },
                "risk_threshold": {
                    "type": "number",
                    "description": "Score threshold above which user is At Risk (e.g. 0.30)"
                }
            },
            "required": ["weights", "high_threshold", "risk_threshold"]
        }
    },
    {
        "name": "generate_growth_report",
        "description": "Ask Claude to write a final plain-English growth report summarising all findings: the activation signal, retention rates, segment breakdown, key insights, and recommended actions. This is the human-readable output.",
        "input_schema": {
            "type": "object",
            "properties": {
                "findings": {
                    "type": "string",
                    "description": "A summary of all key findings so far to include in the report"
                }
            },
            "required": ["findings"]
        }
    },
    {
        "name": "save_results",
        "description": "Save all computed results to agent_results.json so the dashboard can read them.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
]

# ── AGENT STATE ───────────────────────────────────────────────────────────────
# This is shared state that tool functions read from and write to.
state = {
    "events": [],
    "by_user": {},
    "features": {},          # user_id -> feature dict
    "retention": {},         # user_id -> 0 or 1
    "correlations": {},      # feature -> r value
    "activation_signal": {}, # the chosen signal definition
    "scores": {},            # user_id -> score
    "segments": {},          # user_id -> segment
    "growth_report": "",
    "dataset": [],           # final per-user records
    "agent_log": [],         # everything Claude said and did
}

# ── TOOL IMPLEMENTATIONS ──────────────────────────────────────────────────────

def load_events():
    try:
        with open("events.csv") as f:
            for row in csv.DictReader(f):
                row["timestamp"] = datetime.strptime(row["timestamp"], "%Y-%m-%d %H:%M:%S")
                state["events"].append(row)
        by_user = defaultdict(list)
        for e in state["events"]:
            by_user[e["user_id"]].append(e)
        state["by_user"] = dict(by_user)

        event_types = Counter(e["event"] for e in state["events"])
        sample = state["events"][:20]
        return {
            "status": "ok",
            "total_events": len(state["events"]),
            "total_users": len(state["by_user"]),
            "event_types": dict(event_types),
            "date_range": {
                "first": str(state["events"][0]["timestamp"].date()),
                "last":  str(state["events"][-1]["timestamp"].date()),
            },
            "sample_rows": [
                {"user": e["user_name"], "event": e["event"], "timestamp": str(e["timestamp"])}
                for e in sample
            ]
        }
    except FileNotFoundError:
        return {"status": "error", "message": "events.csv not found. Run generate_data.py first."}


def compute_user_features():
    def pearson(xs, ys):
        n = len(xs)
        if n < 2: return 0
        mx, my = sum(xs)/n, sum(ys)/n
        num = sum((x-mx)*(y-my) for x,y in zip(xs,ys))
        dx  = math.sqrt(sum((x-mx)**2 for x in xs) or 1e-9)
        dy  = math.sqrt(sum((y-my)**2 for y in ys) or 1e-9)
        return round(num/(dx*dy), 3)

    for uid, uevts in state["by_user"].items():
        evts = sorted(uevts, key=lambda e: e["timestamp"])
        signup_evt  = next((e for e in evts if e["event"] == "signed_up"), evts[0])
        signup_time = signup_evt["timestamp"]
        week  = [e for e in evts if (e["timestamp"] - signup_time).days <= 7]
        names = [e["event"] for e in week]

        invited = "invited_teammate" in names
        collab_48 = False
        if invited:
            invite_ts   = next(e["timestamp"] for e in week if e["event"] == "invited_teammate")
            collab_evts = {"teammate_commented", "assigned_task", "teammate_added_task"}
            for e in week:
                if e["event"] in collab_evts:
                    if (e["timestamp"] - invite_ts).total_seconds() <= 48 * 3600:
                        collab_48 = True; break

        daily_scores = []
        for day in range(8):
            w  = [e for e in evts if (e["timestamp"] - signup_time).days <= day]
            ns = [e["event"] for e in w]
            inv = "invited_teammate" in ns
            c48 = False
            if inv:
                inv_ts = next(e["timestamp"] for e in w if e["event"] == "invited_teammate")
                for e in w:
                    if e["event"] in {"teammate_commented","assigned_task","teammate_added_task"}:
                        if (e["timestamp"] - inv_ts).total_seconds() <= 48 * 3600:
                            c48 = True; break
            s = round(
                int(c48) * 0.50 + int("teammate_joined" in ns) * 0.25 +
                min(ns.count("invited_teammate"), 3) / 3 * 0.15 +
                min(len(set(e["timestamp"].date() for e in w)), 7) / 7 * 0.10, 3
            )
            today_evts = [e["event"] for e in evts if (e["timestamp"] - signup_time).days == day]
            daily_scores.append({"day": day, "score": s, "events": today_evts})

        state["features"][uid] = {
            "user_name":          uevts[0]["user_name"],
            "signup_date":        signup_time.strftime("%Y-%m-%d"),
            "projects_created":   names.count("created_project"),
            "tasks_added":        names.count("added_task"),
            "teammates_invited":  names.count("invited_teammate"),
            "teammate_joined":    int("teammate_joined" in names),
            "collab_within_48h":  int(collab_48),
            "sessions":           len(set(e["timestamp"].date() for e in week)),
            "watched_onboarding": int("viewed_onboarding" in names),
            "daily_scores":       daily_scores,
        }

        late = [e for e in evts if (e["timestamp"] - signup_time).days >= 14]
        state["retention"][uid] = int(len(late) > 0)

    retained = sum(state["retention"].values())
    feat_sample = dict(list(state["features"].items())[:3])
    feat_preview = {uid: {k:v for k,v in f.items() if k != "daily_scores"}
                    for uid, f in feat_sample.items()}
    return {
        "status": "ok",
        "users_processed": len(state["features"]),
        "retained_users": retained,
        "churned_users": len(state["features"]) - retained,
        "retention_rate": f"{retained/len(state['features']):.1%}",
        "feature_preview": feat_preview,
        "features_computed": ["projects_created","tasks_added","teammates_invited",
                               "teammate_joined","collab_within_48h","sessions","watched_onboarding"]
    }


def run_correlations():
    FEAT_COLS = ["projects_created","tasks_added","teammates_invited",
                 "teammate_joined","collab_within_48h","sessions","watched_onboarding"]
    def pearson(xs, ys):
        n = len(xs)
        if n < 2: return 0
        mx, my = sum(xs)/n, sum(ys)/n
        num = sum((x-mx)*(y-my) for x,y in zip(xs,ys))
        dx  = math.sqrt(sum((x-mx)**2 for x in xs) or 1e-9)
        dy  = math.sqrt(sum((y-my)**2 for y in ys) or 1e-9)
        return round(num/(dx*dy), 3)

    uids = list(state["features"].keys())
    y    = [state["retention"][uid] for uid in uids]
    corrs = {}
    for feat in FEAT_COLS:
        x = [state["features"][uid][feat] for uid in uids]
        corrs[feat] = pearson(x, y)
    state["correlations"] = corrs
    ranked = sorted(corrs.items(), key=lambda x: abs(x[1]), reverse=True)
    return {
        "status": "ok",
        "correlations_ranked": ranked,
        "interpretation": {
            "strongest_predictor": ranked[0][0],
            "strongest_r": ranked[0][1],
            "negative_predictors": [(f,r) for f,r in ranked if r < 0],
            "weak_predictors": [(f,r) for f,r in ranked if abs(r) < 0.2],
        }
    }


def analyse_feature(feature_name):
    if not state["features"]:
        return {"status": "error", "message": "Run compute_user_features first"}
    uids  = list(state["features"].keys())
    hit   = [uid for uid in uids if state["features"][uid].get(feature_name, 0)]
    miss  = [uid for uid in uids if not state["features"][uid].get(feature_name, 0)]
    ret_hit  = sum(state["retention"][uid] for uid in hit)  if hit  else 0
    ret_miss = sum(state["retention"][uid] for uid in miss) if miss else 0
    rate_hit  = ret_hit  / len(hit)  if hit  else 0
    rate_miss = ret_miss / len(miss) if miss else 0
    lift = round(rate_hit / rate_miss, 2) if rate_miss > 0 else None
    return {
        "feature": feature_name,
        "users_who_did_it": len(hit),
        "users_who_did_not": len(miss),
        "retention_if_triggered": f"{rate_hit:.1%}",
        "retention_if_missed": f"{rate_miss:.1%}",
        "lift": f"{lift}x" if lift else "infinite",
        "raw": {
            "retained_hit": ret_hit, "total_hit": len(hit),
            "retained_miss": ret_miss, "total_miss": len(miss),
            "rate_hit": round(rate_hit, 4), "rate_miss": round(rate_miss, 4)
        }
    }


def define_activation_signal(feature, description, reasoning):
    r = state["correlations"].get(feature, 0)
    analysis = analyse_feature(feature)
    state["activation_signal"] = {
        "feature": feature,
        "description": description,
        "reasoning": reasoning,
        "top_r": r,
        "retention_hit":  analysis["raw"]["rate_hit"],
        "retention_miss": analysis["raw"]["rate_miss"],
        "lift": analysis["raw"]["rate_hit"] / analysis["raw"]["rate_miss"]
               if analysis["raw"]["rate_miss"] > 0 else None,
    }
    return {"status": "ok", "activation_signal": state["activation_signal"]}


def score_and_segment_users(weights, high_threshold, risk_threshold):
    if not state["features"]:
        return {"status": "error", "message": "Run compute_user_features first"}

    # Normalise weights so they always sum to exactly 1.0
    total_w = sum(weights.values()) or 1
    weights = {k: v / total_w for k, v in weights.items()}

    def get_action(score, f):
        if score >= high_threshold:       return "Upsell — show upgrade prompt"
        if f["teammates_invited"] > 0:    return "Nudge teammate — send reminder"
        if f["projects_created"]  > 0:    return "Show invite prompt in-app"
        return "Win-back email after 72h"

    dataset = []
    for uid, feats in state["features"].items():
        score = 0.0
        for feat, w in weights.items():
            val = feats.get(feat, 0)
            # Normalise all features to 0-1 range before applying weight
            if feat == "teammates_invited":
                val = min(val, 3) / 3
            elif feat == "sessions":
                val = min(val, 7) / 7
            elif feat == "tasks_added":
                val = min(val, 10) / 10
            elif feat == "projects_created":
                val = min(val, 5) / 5
            # Binary features (collab_within_48h, teammate_joined, watched_onboarding)
            # are already 0 or 1 — no normalisation needed
            else:
                val = min(max(val, 0), 1)
            score += val * w
        # Hard cap at 1.0 — score is a probability-like value
        score = round(min(score, 1.0), 3)
        seg   = "High activation" if score >= high_threshold else (
                "At risk"         if score >= risk_threshold else "Likely churned")
        state["scores"][uid]   = score
        state["segments"][uid] = seg
        dataset.append({
            "user_id":    uid,
            "user_name":  feats["user_name"],
            "retained":   state["retention"][uid],
            "score":      score,
            "segment":    seg,
            "action":     get_action(score, feats),
            **{k: v for k, v in feats.items() if k != "daily_scores"},
            "daily_scores": feats["daily_scores"],
        })

    state["dataset"] = dataset
    seg_counts = Counter(d["segment"] for d in dataset)
    return {
        "status": "ok",
        "segments": dict(seg_counts),
        "weights_used": weights,
        "thresholds": {"high": high_threshold, "risk": risk_threshold},
        "sample_scored": [
            {"user": d["user_name"], "score": d["score"], "segment": d["segment"],
             "action": d["action"], "collab_48h": d["collab_within_48h"]}
            for d in sorted(dataset, key=lambda x: -x["score"])[:8]
        ]
    }


def generate_growth_report(findings):
    sig  = state["activation_signal"]
    segs = Counter(d["segment"] for d in state["dataset"])
    total = len(state["dataset"])
    report = f"""
USER NONCHURN AI - GROWTH ANALYSIS REPORT
==========================================
Generated by Claude AI Agent

ACTIVATION SIGNAL
{sig.get('description', 'Not defined')}

Feature: {sig.get('feature', 'N/A')}
Pearson r: {sig.get('top_r', 'N/A')}
Retention if triggered: {sig.get('retention_hit', 0):.0%}
Retention if missed:    {sig.get('retention_miss', 0):.0%}
Lift: {round(sig['lift'], 1) if sig.get('lift') else 'infinite'}x

AGENT REASONING
{sig.get('reasoning', 'N/A')}

COHORT BREAKDOWN ({total} users)
High Activation : {segs.get('High activation', 0)} users ({segs.get('High activation', 0)/total:.0%})
At Risk         : {segs.get('At risk', 0)} users ({segs.get('At risk', 0)/total:.0%})
Likely Churned  : {segs.get('Likely churned', 0)} users ({segs.get('Likely churned', 0)/total:.0%})

KEY FINDINGS
{findings}

RECOMMENDED ACTIONS
High Activation: Show upgrade prompt immediately. These users have experienced the product's core collaborative value.
At Risk: Send an automated email nudging the invitee to take action. One teammate action closes the loop.
Likely Churned: Win-back email at 72h. Exclude from engagement budget after 7 days if no response.
""".strip()
    state["growth_report"] = report
    return {"status": "ok", "report": report}


def save_results():
    if not state["dataset"]:
        return {"status": "error", "message": "No dataset. Run score_and_segment_users first."}
    sig      = state["activation_signal"]
    seg_counts = Counter(d["segment"] for d in state["dataset"])
    results  = {
        "summary": {
            "total_users":  len(state["dataset"]),
            "total_events": len(state["events"]),
            "n_high":       seg_counts.get("High activation", 0),
            "n_risk":       seg_counts.get("At risk", 0),
            "n_churn":      seg_counts.get("Likely churned", 0),
        },
        "activation_signal": {
            "top_feature":    sig.get("feature", "collab_within_48h"),
            "top_r":          sig.get("top_r", 0),
            "retention_hit":  round(sig.get("retention_hit", 0), 4),
            "retention_miss": round(sig.get("retention_miss", 0), 4),
            "lift":           round(sig["lift"], 2) if sig.get("lift") else None,
            "description":    sig.get("description", ""),
            "agent_reasoning": sig.get("reasoning", ""),
        },
        "top_correlation": {
            "feature": sorted(state["correlations"].items(), key=lambda x: abs(x[1]), reverse=True)[0][0]
                       if state["correlations"] else "",
            "r": sorted(state["correlations"].items(), key=lambda x: abs(x[1]), reverse=True)[0][1]
                 if state["correlations"] else 0,
        },
        "correlations": dict(sorted(state["correlations"].items(), key=lambda x: abs(x[1]), reverse=True)),
        "growth_report": state["growth_report"],
        "agent_log":     state["agent_log"],
        "users":         state["dataset"],
    }
    with open("agent_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    return {"status": "ok", "saved_to": "agent_results.json", "records": len(state["dataset"])}


# ── TOOL DISPATCHER ───────────────────────────────────────────────────────────
def run_tool(name, inputs):
    if   name == "load_events":           return load_events()
    elif name == "compute_user_features": return compute_user_features()
    elif name == "run_correlations":      return run_correlations()
    elif name == "analyse_feature":       return analyse_feature(**inputs)
    elif name == "define_activation_signal": return define_activation_signal(**inputs)
    elif name == "score_and_segment_users":  return score_and_segment_users(**inputs)
    elif name == "generate_growth_report":   return generate_growth_report(**inputs)
    elif name == "save_results":          return save_results()
    else: return {"error": f"Unknown tool: {name}"}


# ── SYSTEM PROMPT ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are User NonChurn AI, an autonomous growth analytics agent.

Your goal: analyse a SaaS product's raw event log and identify the Activation Signal — the specific user action in the first 7 days that statistically predicts long-term retention. Then segment all users and recommend targeted interventions.

You work by calling tools one at a time. After each tool result, you reason about what you learned and decide what to do next.

Your analysis process:
1. Load and understand the raw data
2. Compute behavioural features for every user
3. Run correlations to see which actions predict retention
4. Deep-dive into the most interesting features to validate hypotheses
5. Formally define the Activation Signal with clear reasoning
6. Score and segment all users using weights derived from the correlation analysis
7. Generate a plain-English growth report explaining your findings
8. Save everything to agent_results.json

Be rigorous. When you find the top correlating feature, check whether it is also the most actionable one — not just the most statistically significant. A product team can engineer an invitation flow; they cannot engineer someone watching more sessions.

After define_activation_signal, always call score_and_segment_users with weights that reflect the correlation strengths you discovered. Then generate_growth_report. Then save_results.

Think step by step. Do not call multiple tools at once — call one, read the result, then decide the next step."""


# ── AGENT LOOP ────────────────────────────────────────────────────────────────
def run_agent():
    client   = anthropic.Anthropic()
    messages = []

    user_message = """Analyse the product event log and identify the Activation Signal.
Run the full pipeline: load data, compute features, find correlations, validate your findings,
define the activation signal with clear reasoning, score all users, write a growth report,
and save the results. Think carefully at each step."""

    messages.append({"role": "user", "content": user_message})

    print("\n" + "="*60)
    print("USER NONCHURN AI - AGENT STARTING")
    print("="*60)
    print(f"Goal: {user_message}\n")

    step = 0
    while True:
        step += 1
        print(f"\n[Step {step}] Calling Claude...")

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages
        )

        # Append assistant response
        messages.append({"role": "assistant", "content": response.content})

        # Print what Claude said
        for block in response.content:
            if hasattr(block, "text") and block.text:
                print(f"\nClaude: {block.text}")
                state["agent_log"].append({"step": step, "type": "thought", "content": block.text})

        # Check if done
        if response.stop_reason == "end_turn":
            print("\n" + "="*60)
            print("AGENT COMPLETE")
            print("="*60)
            break

        # Process tool calls
        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    tool_name   = block.name
                    tool_inputs = block.input
                    print(f"\n  Tool call: {tool_name}({json.dumps(tool_inputs, indent=2) if tool_inputs else ''})")

                    result = run_tool(tool_name, tool_inputs)
                    print(f"  Result preview: {str(result)[:300]}...")

                    state["agent_log"].append({
                        "step": step,
                        "type": "tool_call",
                        "tool": tool_name,
                        "inputs": tool_inputs,
                        "result_preview": str(result)[:200]
                    })

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result, default=str)
                    })

            messages.append({"role": "user", "content": tool_results})

    # Final summary
    if state["dataset"]:
        seg_counts = Counter(d["segment"] for d in state["dataset"])
        print(f"\nTotal users analysed : {len(state['dataset'])}")
        print(f"High activation      : {seg_counts.get('High activation', 0)}")
        print(f"At risk              : {seg_counts.get('At risk', 0)}")
        print(f"Likely churned       : {seg_counts.get('Likely churned', 0)}")
        if state["activation_signal"]:
            sig = state["activation_signal"]
            print(f"\nActivation signal    : {sig.get('feature')}")
            print(f"Pearson r            : {sig.get('top_r')}")
            print(f"Retention if hit     : {sig.get('retention_hit', 0):.0%}")
            print(f"Retention if missed  : {sig.get('retention_miss', 0):.0%}")
        print("\nResults saved to agent_results.json")
        if state["growth_report"]:
            print("\n" + "="*60)
            print(state["growth_report"])


if __name__ == "__main__":
    run_agent()
