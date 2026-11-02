"""DVC spec lock — hash the build spec at Define, refuse undeclared drift.

Usage (run with the workdir as cwd):
    python spec_lock.py lock [--spec REL]            hash spec, write .pipeline/spec.lock
    python spec_lock.py check [--spec REL]           exit 0 clean / 1 drift / 2 lock broken
    python spec_lock.py declare --by NAME --why TXT re-hash spec, append declaration

The blocking gate is `on_pre_tool_call`, registered from `__init__.py`.
It refuses `write_file`/`patch`/`terminal` calls inside a DVC workdir whose
spec hash has moved without a recorded declaration, and fails closed when
the lock is missing or unreadable. Reads are never gated.
"""

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

LOCK_NAME = "spec.lock"
DEFAULT_SPEC = ".pipeline/to-spec.md"
# Mutation surface only: writes and command runs. Reads are never blocked.
GATED_TOOLS = {"write_file", "patch", "terminal"}


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
    """Parse the lock; raises (ValueError/OSError) when broken — fail closed."""
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


def _workdir_from_args(tool_name, args):
    """Best-effort workdir: the target path's own tree, else cwd.

    Plugin pre_tool_call callbacks get tool_name/args but no cwd, so the
    scope comes from the call itself: the file/command the agent is about
    to touch decides which workdir's lock applies.
    """
    args = args if isinstance(args, dict) else {}
    candidates = []
    for key in ("path", "file", "filename"):
        if args.get(key):
            candidates.append(str(args[key]))
    cmd = args.get("command")
    if tool_name == "terminal" and isinstance(cmd, str):
        # Only path-like tokens can name a workdir; bare commands use cwd.
        candidates += [tok for tok in cmd.replace(";", " ").split() if "/" in tok or "\\" in tok]
    for cand in candidates:
        p = Path(cand)
        if not p.is_absolute():
            p = Path.cwd() / p
        for parent in [p if p.is_dir() else p.parent, *p.parents]:
            if (parent / ".pipeline").is_dir():
                return str(parent)
    return str(Path.cwd())


def on_pre_tool_call(tool_name=None, args=None, **_ignored):
    """Block undeclared spec drift; fail closed on any unreadable state.

    Returns None to allow, or {"action": "block", "message": ...} to refuse.
    Pure function of (tool_name, args) — no imports beyond stdlib, so the
    plugin registers it directly and the case runner calls it directly.
    """
    base = str(tool_name or "").split(".")[-1]
    if base not in GATED_TOOLS:
        return None
    workdir = _workdir_from_args(base, args)
    if not (Path(workdir) / ".pipeline").is_dir():
        return None  # No DVC run here: never gate non-DVC sessions.
    try:
        lock = read_lock(lock_path_for(workdir))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {"action": "block",
                "message": f"[spec-lock] BLOCKED: lock missing or unreadable ({exc}); "
                           "re-run `spec_lock.py lock` or restore .pipeline/spec.lock."}
    spec_rel = lock.get("spec") or DEFAULT_SPEC
    try:
        current = sha256_file(Path(workdir) / spec_rel)
    except OSError as exc:
        return {"action": "block",
                "message": f"[spec-lock] BLOCKED: spec unreadable ({exc}); "
                           "restore the spec file or re-lock."}
    if current == lock.get("sha256"):
        return None
    # Declared drift already re-hashes, so any remaining mismatch is undeclared.
    rel = str((args or {}).get("path") or (args or {}).get("command") or base)
    if ".pipeline/" in rel.replace("\\", "/") or (
        base == "terminal" and isinstance((args or {}).get("command"), str)
        and "spec_lock.py" in (args or {})["command"]
    ):
        return None  # Bookkeeping stays possible while drifted.
    return {"action": "block",
            "message": f"[spec-lock] BLOCKED: spec changed without a declaration "
                       f"(lock {_short(lock.get('sha256'))} != current {_short(current)}); "
                       "run `spec_lock.py declare --by NAME --why REASON` to record it."}


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
