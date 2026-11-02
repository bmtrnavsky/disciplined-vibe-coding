"""DVC spec lock — hash the build spec at Define, note drift in run output.

Usage (run with the workdir as cwd):
    python spec_lock.py lock [--spec REL]            hash spec, write .pipeline/spec.lock
    python spec_lock.py check [--spec REL]           exit 0 clean / 1 drift / 2 lock broken
    python spec_lock.py declare --by NAME --why TXT re-hash spec, append declaration

Advisory only: nothing here blocks a run. `dvc_run.py` hashes at Define
and prints a drift line at Verify; drift is visibility, never a gate.
There is no pre_tool_call hook — the 8ba8aaa blocking hook was removed
on purpose (autonomous runs must never wait on a human). Reads were
never gated and still aren't.
"""

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

LOCK_NAME = "spec.lock"
DEFAULT_SPEC = ".pipeline/to-spec.md"


def _short(h):
    return (h or "?")[:12]


def sha256_file(path):
    """Hex digest of a file; raises OSError when missing/unreadable."""
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def lock_path_for(workdir):
    return Path(workdir) / ".pipeline" / LOCK_NAME


def read_lock(path):
    """Parse the lock; raises (ValueError/OSError) when broken — caller reports it."""
    raw = Path(path).read_text(encoding="utf-8")
    data = json.loads(raw)
    if not isinstance(data, dict) or not data.get("sha256") or not data.get("spec"):
        raise ValueError(f"lock {path} is not a valid spec lock")
    return data


def cmd_lock(workdir, spec_rel):
    digest = sha256_file(Path(workdir) / spec_rel)  # raises -> exit 2
    lock = {
        "spec": spec_rel,
        "sha256": digest,
        "locked_at": int(time.time()),
        "declarations": [],
    }
    lp = lock_path_for(workdir)
    lp.parent.mkdir(parents=True, exist_ok=True)
    lp.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")
    print(f"locked {spec_rel} sha256:{_short(digest)}")
    return 0


def cmd_check(workdir, spec_rel):
    try:
        lock = read_lock(lock_path_for(workdir))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"BLOCKED: lock missing or unreadable ({exc})", file=sys.stderr)
        return 2
    try:
        current = sha256_file(Path(workdir) / spec_rel)
    except OSError as exc:
        print(f"BLOCKED: spec unreadable ({exc})", file=sys.stderr)
        return 2
    if current != lock.get("sha256"):
        print(
            f"DRIFT: spec changed since lock "
            f"(lock {_short(lock.get('sha256'))} != current {_short(current)}); "
            "run `declare --by NAME --why REASON` to record it",
            file=sys.stderr,
        )
        return 1
    print(f"clean sha256:{_short(current)}")
    return 0


def cmd_declare(workdir, spec_rel, by, why):
    try:
        lock = read_lock(lock_path_for(workdir))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"BLOCKED: lock missing or unreadable ({exc})", file=sys.stderr)
        return 2
    try:
        current = sha256_file(Path(workdir) / spec_rel)
    except OSError as exc:
        print(f"BLOCKED: spec unreadable ({exc})", file=sys.stderr)
        return 2
    lock["declarations"].append(
        {"at": int(time.time()), "by": by, "why": why,
         "old": lock.get("sha256"), "new": current}
    )
    lock["sha256"] = current
    lock_path_for(workdir).write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")
    print(f"declared by {by}: {why} (now {_short(current)})")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="DVC spec lock")
    ap.add_argument("--workdir", default=".", help="build workdir (default: cwd)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_lock = sub.add_parser("lock", help="hash the spec and write the lock")
    p_lock.add_argument("--spec", default=DEFAULT_SPEC)
    p_check = sub.add_parser("check", help="re-hash and compare")
    p_check.add_argument("--spec", default=DEFAULT_SPEC)
    p_decl = sub.add_parser("declare", help="record a spec change, update hash")
    p_decl.add_argument("--spec", default=DEFAULT_SPEC)
    p_decl.add_argument("--by", required=True)
    p_decl.add_argument("--why", required=True)
    ns = ap.parse_args(argv)
    if ns.cmd == "lock":
        return cmd_lock(ns.workdir, ns.spec)
    if ns.cmd == "check":
        return cmd_check(ns.workdir, ns.spec)
    return cmd_declare(ns.workdir, ns.spec, ns.by, ns.why)


if __name__ == "__main__":
    sys.exit(main())
