# 🩺 XC Ski Labs — Immune System

An automated "immune system" for the race database: it tests things, finds
issues, **auto-heals the safe ones, opens a PR for the judgment calls**, and keeps
a running ledger so the same mistake can't come back unseen.

Built for a team of one. You should have to think about it for ~2 minutes a day.

---

## The 10-second mental model

```
        ┌─────────────────────────────────────────────────────┐
        │  LAYER 1  (dumb, fast, free)   scripts/immune_check.py│
        │  valid data · score math · index/page parity ·        │
        │  money-path alive · near-duplicates · security        │
        └───────────────┬─────────────────────────────────────┘
                        │  every problem → one of three lanes
        ┌───────────────▼─────────────────────────────────────┐
        │  LAYER 2  (smart, nightly)   the scheduled Claude agent│
        │  reads Layer-1 findings, does the judgment reads,     │
        │  runs the REPAIR LOOP, sends you ONE digest email     │
        └───────────────┬─────────────────────────────────────┘
                        │
     🟢 auto-heal        🟡 PR for you            🔴 issue only
   (ship if verified)  (propose, you approve)   (money path/security)
```

Layer 1 is the **verifier** — the thing that can't be fooled. Nothing auto-heals
unless it makes Layer 1 go green *without turning anything new red*. That single
rule (borrowed from Karpathy's AutoResearch loop: *keep the change only if the
metric improved, else roll back*) is what makes autonomous repair safe.

---

## The three lanes (the whole safety model)

| Lane | What's in it | What happens |
|------|--------------|--------------|
| 🟢 **auto-heal** | stale search index, stale/missing pages, drifted homepage counters, wrong-typed video IDs | Repair loop applies the safe fix → Layer 1 must stay green → commits. Logged. |
| 🟡 **needs you** | **all ratings/scores/tiers**, missing content, bad discipline, malformed JSON, slug↔filename, near-duplicate races, orphaned quotes, brand-name leaks | A fix is *proposed* into a branch/PR. You get a 1-click link in the digest. |
| 🔴 **issue only** | **anything on the money path** (`/questionnaire/`, `/coaching/`), possible secret exposure, systemic breakage | No edit. Flagged red in the digest. You (or the agent, with your yes) handle it. |

**Hard rule:** the money path never auto-heals, even if the fix looks trivial.
This is encoded in `immune_check.py` (money-path findings are always RED).

The lane for every check lives in the `RULES` table in `scripts/immune_check.py`.
To move something between lanes, edit one row there — that's the whole policy surface.

---

## Layer 1 — the verifier (already built, runnable now)

```bash
python3 scripts/immune_check.py            # fast, offline: data + index + duplicates + money-path wiring
python3 scripts/immune_check.py --regen     # regenerate output/ first, then also pages/branding/homepage
python3 scripts/immune_check.py --live       # also hit production for dead money-path / 404s
python3 scripts/immune_check.py --json        # machine JSON (what the nightly agent reads)
python3 scripts/immune_check.py --fail-on red # CI mode: only fail the build on a true emergency
```

It reuses your existing, battle-tested `preflight.py` and `check_links.py` — it
does not reinvent them. It writes `immune/report.json` (latest full result) and
appends a run record to `immune/ledger.jsonl`. **It never edits, commits, or deploys.**

---

## Layer 2 — the nightly agent (the REPAIR LOOP)

Once a night a scheduled Claude Code agent runs this exact routine:

1. **Scan.** `python3 scripts/immune_check.py --regen --live --json` → the findings.
2. **For each 🟢 finding — the Karpathy repair loop:**
   - Apply the finding's safe `auto_fix` command (e.g. regenerate the index).
   - Re-run `immune_check.py`. If it's green *and nothing new went red* → keep it.
     If anything went red → **roll back** and demote the finding to 🟡 (a PR).
   - Commit the kept fix to `main` with a `[immune] auto-heal:` message.
3. **For each 🟡 finding:** write the proposed fix to a branch, open a PR titled
   `[immune] NEEDS YOU: <title>`, leave the diff for you.
4. **For each 🔴 finding:** open a GitHub issue (or reuse the open one); never edit.
5. **Log.** Append a `type:"fix"` record to `immune/ledger.jsonl` for anything
   healed or PR'd, including the `regression_check` that will now catch a recurrence.
6. **Report.** Send ONE digest email (below). Deploy only if you've turned on
   deploy authority (see switches) — otherwise it stops at "committed, awaiting deploy."

### The nightly digest (your morning ritual)
```
Subject: 🩺 Immune report — <date> (<N> need you)

✅ AUTO-HEALED (n)   <one line each>
⚠️ NEEDS YOU (n)     <title → PR link>
🔴 ISSUE (n)         <title → issue link>
🧬 <k> regressions of past bugs · streak: <d> days green
```

---

## The ledger — why the same mistake can't sneak back

`immune/ledger.jsonl` is the memory. Two record types:
- `type:"scan"` — every run's counts (the health history / streak).
- `type:"fix"` — a resolved issue: what broke, root cause, the fix, and crucially
  **`regression_check`** — the exact check in `immune_check.py` that now fails if
  it recurs.

The rule that makes it an immune system, not a diary: **every fix must name a
regression_check.** If a new class of bug appears that no check would catch, the
nightly agent's job includes adding a rule to `immune_check.py` before closing it.
(Seeded already with the two real resolved issues: the `traversee-du-massacre`
duplicate and the questionnaire money-path 404.)

---

## Flip-the-switch wiring (what turns the loop ON)

Layer 1 works today. To turn on the nightly Layer 2 loop, three switches — each
optional, each reversible:

1. **Schedule the nightly agent.** A `/schedule` cloud routine running the Layer-2
   routine above. (Ask Claude: "create the immune nightly routine for XC Ski Labs.")
   Runs whether your Mac is on or not.
2. **Digest email.** Set `RESEND_API_KEY` in `.env`; the agent emails the digest to
   your address. Until then it prints the digest to the run log.
3. **Deploy authority (default OFF — keep it off until you trust it).** With it off,
   the loop commits fixes but never deploys; you deploy with
   `python3 scripts/preflight.py --deploy`. With it on, the loop may run the matching
   `deploy.py --sync-* --purge-cache` for 🟢 fixes only — never for money-path changes.

## CI (the cheap always-on layer)
`.github/workflows/immune.yml` runs `immune_check.py --fail-on red` on every push +
nightly — so a change that kills the money path or leaks a secret turns the build
red immediately, for free, without waiting for the nightly agent.

---

## Cloning to the other brands
The shape is identical; only the checks differ. Gravel God and Roadie Labs are
near-twins of this repo (same static-site pattern) → copy `immune_check.py`, swap
paths/criteria, reuse their `preflight`/`check_links`. Endure Labs is the live app
→ the verifier checks API health + `/plan` `/calendar` timing + Supabase advisors
instead of static pages, but the lanes, ledger, repair loop, and digest are the same.
