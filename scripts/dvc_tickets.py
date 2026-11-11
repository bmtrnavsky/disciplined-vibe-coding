"""Publish gate for to-tickets (M7): approval is recorded, not claimed.

    python scripts/dvc_tickets.py --interactive --by Brad --tickets T1,T2 approve
    python scripts/dvc_tickets.py --tickets T1,T2 check

`approve` refuses without the explicit `--interactive` flag. That flag is
the only interactivity signal this pack uses: nothing infers headless from
context, a prompt, or a session shape. A headless run therefore cannot
record approval, so `check` fails and it cannot publish — it drafts and
stops, which is what the skill says it does.

The approval binds the plan's digest and the exact ticket set. The digest
is the file's sha256 with two bookkeeping lines left out: its `Status:` line
and the `— card: <id>` ids written on ticket headings at publish. So the
plan can be stamped APPROVED and have its cards recorded without breaking
the approval; every other edit does break it. `check` also requires a
Teardown pass recorded against that same digest, which proves teardown ran
on this plan, not that the review was good. Approvals append: the file is
an audit trail, and `check` reads the newest matching record. Records older
than v2 carry no digest; they are compared by raw sha256.
"""

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dvc_stage  # noqa: E402

APPROVALS_REL = ".pipeline/ticket-approval.json"
PLANS_REL = ".pipeline/plans"
FORMAT = "dvc-tickets-v2"


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _plan_path(workdir, plan):
    if plan:
        return Path(plan)
    plans = sorted((Path(workdir) / PLANS_REL).glob("*.md"))
    if len(plans) != 1:
        raise SystemExit(f"cannot pick the plan ({len(plans)} under {PLANS_REL}/); "
                         "pass --plan")
    return plans[0]


def _ticket_ids(raw):
    return sorted({t.strip() for t in (raw or "").split(",") if t.strip()})


def _load(workdir):
    path = Path(workdir) / APPROVALS_REL
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SystemExit(f"{APPROVALS_REL} unreadable ({exc}); refusing") from None
    return data.get("approvals") or []


def approve(workdir, plan_ref, tickets, by):
    ids = _ticket_ids(tickets)
    if not ids:
        raise SystemExit("no ticket ids given; nothing to approve")
    plan = _plan_path(workdir, plan_ref)
    if not plan.is_file():
        raise SystemExit(f"plan not found: {plan}")
    rec = {"format": FORMAT, "approved_by": by,
           "approved_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
           "tickets": ids, "plan": plan.name, "plan_sha256": _sha(plan),
           "plan_digest": dvc_stage.plan_digest(plan)}
    path = Path(workdir) / APPROVALS_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"format": FORMAT, "approvals": _load(workdir) + [rec]}
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")
    return rec


def check(workdir, plan_ref, tickets):
    """Return (ok, one-line reason). Fails closed: no record, no publish."""
    ids = _ticket_ids(tickets)
    if not ids:
        return False, "no ticket ids given; nothing to publish"
    plan = _plan_path(workdir, plan_ref)
    if not plan.is_file():
        return False, f"plan not found: {plan}"
    sha = _sha(plan)
    digest = dvc_stage.plan_digest(plan)
    reasons = []
    for rec in reversed(_load(workdir)):
        if rec.get("plan") != plan.name:
            continue
        # v1 records carry no digest; they keep the raw-sha comparison.
        if rec.get("plan_digest"):
            changed = rec["plan_digest"] != digest
        else:
            changed = rec.get("plan_sha256") != sha
        if changed:
            reasons.append(f"plan body changed since {rec.get('approved_by')} "
                           f"approved it ({rec.get('approved_at')}); the Status "
                           "line and card ids do not count; re-approve")
            continue
        approved = rec.get("tickets") or []
        missing = [t for t in ids if t not in approved]
        if missing:
            reasons.append("tickets not approved: " + ", ".join(missing))
            continue
        extra = [t for t in approved if t not in ids]
        if extra:
            reasons.append("approval covers tickets not in this cut: "
                           + ", ".join(extra))
            continue
        ok, why = dvc_stage.teardown_for_plan(workdir, plan)
        if not ok:
            return False, f"teardown gate: {why}"
        return True, (f"publish approved by {rec.get('approved_by')} at "
                      f"{rec.get('approved_at')} (plan digest {digest[:12]}); "
                      f"{why}")
    if reasons:
        return False, reasons[0]
    return False, ("no approval recorded for this plan and ticket set; a headless "
                   "run cannot record one — draft and stop")


def main(argv=None):
    ap = argparse.ArgumentParser(description="DVC to-tickets publish gate")
    ap.add_argument("--workdir", default=".")
    ap.add_argument("--plan", default=None, help="plan file (default: the one in .pipeline/plans/)")
    ap.add_argument("--tickets", required=True, help="comma-separated ticket ids")
    ap.add_argument("--interactive", action="store_true",
                    help="approve only: the explicit interactive-session signal")
    ap.add_argument("--by", default="", help="approve only: who approved")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("approve", help="record the quiz approval")
    sub.add_parser("check", help="fail unless this cut is approved")

    ns = ap.parse_args(argv)
    if ns.cmd == "check":
        ok, why = check(ns.workdir, ns.plan, ns.tickets)
        print(f"{'publish gate: OK' if ok else 'PUBLISH GATE FAILED'}: {why}",
              flush=True)
        return 0 if ok else 1
    if not ns.interactive:
        print("headless: no --interactive flag, so no approval is recorded. "
              "Draft under .pipeline/tickets/ and stop.", file=sys.stderr,
              flush=True)
        return 2
    if not ns.by.strip():
        print("approve needs --by NAME: an approval without a name is unlogged.",
              file=sys.stderr, flush=True)
        return 2
    rec = approve(ns.workdir, ns.plan, ns.tickets, ns.by.strip())
    print(f"approval recorded: {len(rec['tickets'])} ticket(s) by "
          f"{rec['approved_by']} (plan digest {rec['plan_digest'][:12]})",
          flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
