"""Blind goldfish review loop for the autonomous DVC run (card 2/4, fix A).

Contract (Brad's stop rules):

- After Build, the reviewer assembles a hash-locked packet: the locked
  to-spec, the lock (or lock-pending state), the plans, and the build
  output. Fixed file set, nothing else. No teardown scratch notes, no
  elephant responses, no chat history, no memory, no RAG.
- Goldfish reviews with ONE model call made outside any agent loop:
  system prompt = the packet template filled with only the stage and
  round list, user message = the packet inlined as delimited files,
  ``tools`` empty. It cannot amend anything, cannot run anything, and
  cannot approve: there is no approve verdict. An empty objection list
  IS the pass. Only the absence of objection ends the loop.
- Objections return to the elephant as new work (rework the artifact,
  never the spec); review then restarts from the top round, because
  rework can break earlier passes and no human is around to judge the
  blast radius.

Stop rules:

1. Same-round rule (Brad's number: 2) -- two CONSECUTIVE failures on one
   round stop the run. Consecutive, not cumulative: a pass resets the
   round, because fail-then-fix-then-break-again is regression, not
   guessing. (A cumulative reading would make rule 2 dead math: with 2
   rounds any 3rd failure must repeat a round, so a total cap could never
   fire on its own.)
2. Total failure cap = number of rounds + 1 (micro-spec: 3). A converging
   run fails each round at most once on first sight; the (R+1)-th failure
   proves cleared ground broke again -- global thrash, not convergence.

On either stop the run reports FAILURE: the round that could not pass,
the objections verbatim, and what the elephant tried. No partial success,
no spec loosening, no advance past Teardown.

Count keying (the p_g3 bypass): failure counts live in
``.pipeline/goldfish.json`` keyed (run_id -> round). The spec hash is
recorded on every verdict for audit but NEVER used as a key, so a mid-run
amendment + re-lock cannot reset the count.

Fail closed: an oversize packet, a missing spec, a swapped packet file,
or an unreachable provider stops the run as FAILURE (rule
``review-error``) -- never as a silent pass.

Test stub: ``DVC_GOLDFISH_STUB`` (comma-separated F/P verdicts consumed in
call order, one token per review call) is honored only when
``DVC_TEST_MODE=1`` -- the same gating shape as the sibling project's
provider stub. Production runs ignore it and call the provider.
"""

import argparse
import hashlib
import json
import os
import random
import re
import stat
import sys
import time
import urllib.request
from pathlib import Path

ROUNDS = ("consequence", "alternatives")

# Brad's number: two straight failures on one round, no third attempt.
SAME_ROUND_LIMIT = 2
# Backstop for genuinely new failures on every round: R rounds can fail at
# most once each on first sight in a converging run, so failure R+1 means
# cleared ground failed again.
TOTAL_FAILURE_CAP = len(ROUNDS) + 1

STATE_REL = ".pipeline/goldfish.json"
PACKETS_REL = ".pipeline/packets"
REVIEWS_REL = ".pipeline/reviews/goldfish"

FORMAT_PACKET = "dvc-packet-v1"
FORMAT_CALL = "dvc-goldfish-v1"

DEFAULT_MAX_TOKENS = 100_000
DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai"
DEFAULT_MODEL = "gemini-2.5-flash-lite"
KEY_ENV = "DVC_GOLDFISH_API_KEY"
BASE_ENV = "DVC_GOLDFISH_BASE_URL"
MODEL_ENV = "DVC_GOLDFISH_MODEL"
CAP_ENV = "DVC_GOLDFISH_MAX_TOKENS"
STUB_ENV = "DVC_GOLDFISH_STUB"
# The stub transport fakes a passing provider. It exists for tests only,
# and is honored exclusively under an explicit test flag:
# ``DVC_TEST_MODE=1``. In production the variable is ignored and the run
# fails closed on the missing provider key.
TEST_ENV = "DVC_TEST_MODE"

REPO_ROOT = Path(__file__).resolve().parent.parent

ROUND_EXPECTED = {
    "consequence": "what happens if we build exactly this, and where it breaks",
    "alternatives": "what else solves it, and whether this is the strongest option",
}

ROUND_LINE_RE = re.compile(
    r"^ROUND\s+([A-Za-z][A-Za-z0-9_-]*)\s*:\s*(PASS|FAIL)\b(.*)$",
    re.IGNORECASE,
)

# Workdir entries that never enter a packet: run plumbing, history, and
# bytecode. Everything else the build produced is the artifact under review.
SKIP_TOP = {".pipeline", ".turing", ".git", "__pycache__", ".venv", "venv",
            "node_modules", ".hg", ".svn"}
MAX_OUTPUT_FILES = 50
MAX_FILE_BYTES = 100_000


class DvcReviewError(Exception):
    """Fail-closed review error: packet or provider unusable. Never a pass."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _short(h):
    return (h or "?")[:12]


def _stub_allowed() -> bool:
    return os.environ.get(TEST_ENV) == "1"


def _stub_tokens():
    """Verdict script for tests; None in production (stub ignored there)."""
    if not _stub_allowed():
        return None
    raw = os.environ.get(STUB_ENV, "")
    tokens = [t.strip().upper() for t in raw.split(",") if t.strip()]
    return tokens or None


def _est_tokens(data: bytes) -> int:
    return max(1, len(data) // 4)


def _config():
    cap_raw = os.environ.get(CAP_ENV, "")
    try:
        cap = int(cap_raw) if cap_raw else DEFAULT_MAX_TOKENS
    except ValueError:
        raise DvcReviewError(
            f"{CAP_ENV} must be a positive integer, got {cap_raw!r}")
    if cap <= 0:
        raise DvcReviewError(
            f"{CAP_ENV} must be a positive integer, got {cap_raw!r}")
    return {
        "base_url": os.environ.get(BASE_ENV, "") or DEFAULT_BASE_URL,
        "model": os.environ.get(MODEL_ENV, "") or DEFAULT_MODEL,
        "key_env": KEY_ENV,
        "max_tokens": cap,
    }


# ---------- packet ----------

def _packet_files(workdir: Path, define_spec: bytes | None = None):
    """Fixed file set. Never teardown scratch, never elephant responses,
    never run plumbing. Sees only the packet files.

    The spec entry is the spec as locked at Define when define_spec is
    given (fix E) — never the current file, so a build that hollowed
    the spec cannot shrink what the reviewer judges.
    """
    workdir = Path(workdir)
    root = workdir.resolve()
    files: list[tuple[str, bytes]] = []
    if define_spec is not None:
        files.append((".pipeline/to-spec.md", define_spec))
    else:
        try:
            files.append((".pipeline/to-spec.md",
                          _safe_read_bytes(root, workdir / ".pipeline" / "to-spec.md",
                                           ".pipeline/to-spec.md")))
        except OSError as exc:
            raise DvcReviewError("packet cannot be assembled: spec unreadable "
                                 f"({exc}); failing closed") from None
    lock = workdir / ".pipeline" / "spec.lock"
    try:
        files.append((".pipeline/spec.lock",
                      _safe_read_bytes(root, lock, ".pipeline/spec.lock")))
    except OSError:
        files.append((".pipeline/lock-pending.txt",
                      b"no spec.lock yet (pre-lock review)\n"))
    plans = sorted((workdir / ".pipeline" / "plans").glob("*.md"))
    if not plans:
        files.append((".pipeline/plans/EMPTY.txt",
                      b"no plan file written (empty plan)\n"))
    for plan in plans:
        try:
            files.append((plan.relative_to(workdir).as_posix(),
                          _safe_read_bytes(root, plan,
                                           plan.relative_to(workdir).as_posix())))
        except OSError:
            continue
    outputs, inventory = _collect_outputs(workdir)
    if not outputs and len(inventory) == 0:
        files.append((".pipeline/outputs/EMPTY.txt",
                      b"no build output present (empty artifact)\n"))
    for rel, data in outputs:
        files.append((rel, data))
    files.append((".pipeline/outputs-inventory.txt",
                  ("# build outputs — names and sizes; binary files are "
                   "listed, never inlined\n\n"
                   + ("\n".join(inventory) if inventory else "(none)")
                   + "\n").encode()))
    return files


def _safe_read_bytes(root: Path, path: Path, rel: str) -> bytes:
    """Read one workdir file without trusting workdir contents (fix F).

    The build owns the workdir before packet assembly, so every candidate
    is checked before it is read: a symlink is refused outright, a
    hardlink (nlink > 1, one file with two names) is refused, and a path
    resolving outside the workdir is refused. The open itself refuses to
    follow a link (O_NOFOLLOW where the platform has it). Trust violations
    raise DvcReviewError (fail closed); a simply missing file raises
    OSError so callers keep their missing-vs-hostile distinction.
    """
    try:
        st = os.lstat(path)
    except OSError:
        raise
    if stat.S_ISLNK(st.st_mode):
        raise DvcReviewError(
            f"packet refuses link: {rel} is a symlink; failing closed")
    if st.st_nlink > 1:
        raise DvcReviewError(
            f"packet refuses link: {rel} has {st.st_nlink} hardlinks; "
            f"failing closed")
    try:
        real = path.resolve()
    except OSError as exc:
        raise DvcReviewError(
            f"packet cannot resolve {rel} ({exc}); failing closed") from None
    if real != root and root not in real.parents:
        raise DvcReviewError(
            f"packet refuses escape: {rel} resolves outside the workdir; "
            f"failing closed")
    try:
        fd = os.open(os.fspath(path),
                     os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    except OSError as exc:
        raise DvcReviewError(
            f"packet cannot open {rel} ({exc}); failing closed") from None
    try:
        with os.fdopen(fd, "rb") as fh:
            return fh.read()
    except OSError as exc:
        raise DvcReviewError(
            f"packet cannot read {rel} ({exc}); failing closed") from None


def _collect_outputs(workdir: Path):
    """Build output: text files enter the packet; anything else (binaries
    like .db files) is listed in the inventory only, never inlined.
    Inlining binary bytes as decoded text shows the reviewer mojibake it
    then misreads as content — the sibling project's packet excludes data
    files for the same reason. Returns (included, inventory_lines).

    Every candidate goes through _safe_read_bytes: a build-planted link
    to an outside file is refused at assembly and never reaches the
    model provider (fix F HIGH-1).
    """
    included = []
    inventory = []
    root = Path(workdir).resolve()
    for path in sorted(workdir.rglob("*")):
        try:
            rel = path.relative_to(workdir).as_posix()
        except ValueError:
            continue
        top = rel.split("/", 1)[0]
        if top in SKIP_TOP or path.suffix == ".pyc":
            continue
        try:
            st = os.lstat(path)
        except OSError:
            continue
        if not (stat.S_ISREG(st.st_mode) or stat.S_ISLNK(st.st_mode)):
            continue  # dirs, fifos, sockets never enter the packet
        data = _safe_read_bytes(root, path, rel)  # raises on link/escape
        size = len(data)
        try:
            data.decode("utf-8")
        except UnicodeDecodeError:
            inventory.append(
                f"- {rel}: {size} bytes (binary, not inlined; "
                f"sha256:{_sha(data)[:12]})")
            continue
        if size > MAX_FILE_BYTES:
            raise DvcReviewError(
                f"packet exceeds per-file cap: {rel} is {size} bytes "
                f"(cap {MAX_FILE_BYTES}); failing closed")
        included.append((rel, data))
        inventory.append(f"- {rel}: {size} bytes (inlined)")
        if len(included) > MAX_OUTPUT_FILES:
            raise DvcReviewError(
                f"packet exceeds file cap ({MAX_OUTPUT_FILES} files); "
                f"failing closed")
    return included, inventory


def do_packet(workdir, define_spec: bytes | None = None) -> dict:
    """Assemble the fixed file set under .pipeline/packets/<hash>/.

    The directory name is the packet's own content hash, so the builder
    cannot swap what the reviewer sees without changing the path. Pass
    define_spec (the spec bytes as locked at Define) and the packet
    carries that — never the current file (fix E).
    """
    workdir = Path(workdir)
    cfg = _config()
    files = _packet_files(workdir, define_spec)
    digest = hashlib.sha256(f"{FORMAT_PACKET}\n".encode())
    manifest_files = []
    total = 0
    for rel, data in files:
        digest.update(f"{rel}\n{len(data)}\n".encode() + data)
        tokens = _est_tokens(data)
        total += tokens
        manifest_files.append({"path": rel, "bytes": len(data),
                               "tokens": tokens, "sha256": _sha(data)})
    packet_hash = digest.hexdigest()[:16]
    if total > cfg["max_tokens"]:
        listing = "\n".join(
            f"  {f['path']}: {f['bytes']} bytes (~{f['tokens']} tokens)"
            for f in manifest_files)
        raise DvcReviewError(
            f"packet exceeds goldfish cap ({total} > {cfg['max_tokens']} "
            f"tokens); failing closed:\n{listing}")
    dest = workdir / PACKETS_REL / packet_hash
    dest.mkdir(parents=True, exist_ok=True)
    for rel, data in files:
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    manifest = {"format": FORMAT_PACKET, "packet_hash": packet_hash,
                "files": manifest_files, "tokens_total": total,
                "cap": cfg["max_tokens"],
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    (dest / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    return {"packet_hash": packet_hash, "files": len(files),
            "tokens": total, "dir": str(dest)}


def _verify_packet(packet_dir: Path, manifest: dict):
    """Refuse a swapped packet: every file must match its recorded hash."""
    for f in manifest["files"]:
        data = (packet_dir / f["path"]).read_bytes()
        if _sha(data) != f["sha256"]:
            raise DvcReviewError(
                f"packet file changed on disk: {f['path']} "
                f"(expected {f['sha256'][:12]}, refusing swapped packet)")


# ---------- brief + call ----------

def load_brief_template() -> str:
    path = REPO_ROOT / "templates" / "goldfish-packet.md"
    if not path.is_file():
        raise DvcReviewError(
            "missing templates/goldfish-packet.md (repo install incomplete)")
    return path.read_text(encoding="utf-8")


def build_brief(rounds: list[str]) -> str:
    """Fill the template with ONLY the stage and round list. The elephant
    cannot add prose: this is the whole system prompt."""
    lines = []
    for r in rounds:
        lines.append(f"ROUND {r}: {ROUND_EXPECTED[r]}.")
    tmpl = load_brief_template()
    brief = tmpl.replace("{{STAGE}}", "teardown").replace(
        "{{ROUNDS}}", "\n".join(lines) + "\n")
    leftover = re.search(r"{{[A-Z_]+}}", brief)
    if leftover:
        raise DvcReviewError(
            "goldfish-packet.md template has unfilled placeholders")
    return brief


def _stub_response(rounds, verdict: str) -> str:
    if verdict == "pass":
        return "".join(f"ROUND {r}: PASS — stubbed pass.\n" for r in rounds)
    return "".join(
        f"ROUND {r}: FAIL — objection: the artifact says nothing about "
        f"{ROUND_EXPECTED[r]}.\n" for r in rounds)


def _provider_call(cfg: dict, model: str, system: str,
                   user: str) -> tuple[str, str, int, int]:
    key = os.environ.get(cfg["key_env"], "")
    if not key:
        raise DvcReviewError(
            f"no provider key reachable ({cfg['key_env']} is unset); "
            f"goldfish rounds cannot run — failing closed")
    payload = json.dumps({"model": model,
                          "messages": [{"role": "system", "content": system},
                                       {"role": "user", "content": user}],
                          "temperature": 0}).encode()
    req = urllib.request.Request(
        cfg["base_url"].rstrip("/") + "/chat/completions", data=payload,
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {key}"})
    import ssl as _ssl
    ctx = _ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=120, context=ctx) as resp:
            raw = resp.read()
    except Exception as exc:
        raise DvcReviewError(
            f"goldfish provider call failed ({exc}); failing closed"
        ) from None
    try:
        body = json.loads(raw.decode("utf-8"))
        text = body["choices"][0]["message"]["content"]
        usage = body.get("usage") or {}
        rid = str(body.get("id") or "")
    except (ValueError, KeyError, IndexError, TypeError):
        raise DvcReviewError(
            "goldfish provider returned an unparseable response; "
            "failing closed") from None
    tin = int(usage.get("prompt_tokens") or _est_tokens(
        (system + user).encode()))
    tout = int(usage.get("completion_tokens") or _est_tokens(text.encode()))
    return text, rid, tin, tout


def _inline_packet(packet_dir: Path, manifest: dict) -> str:
    """The user message: the packet inlined as delimited files. Nothing else
    is in the request — no chat, no memory, no builder notes."""
    parts = []
    for f in manifest["files"]:
        data = (packet_dir / f["path"]).read_bytes()
        parts.append(f"===== FILE {f['path']} =====\n"
                     + data.decode("utf-8", errors="replace"))
    return "\n".join(parts) + "\n"


def _request_envelope(model: str, brief: str, manifest: dict) -> dict:
    return {"model": model, "system": brief,
            "user_files": [{"path": f["path"], "sha256": f["sha256"],
                            "bytes": f["bytes"]} for f in manifest["files"]],
            "tools": []}


def _request_hash(model: str, brief: str, packet_dir: Path,
                  manifest: dict) -> str:
    digest = hashlib.sha256(
        f"{FORMAT_CALL}\n{model}\n".encode() + brief.encode() + b"\n[]\n")
    _verify_packet(packet_dir, manifest)  # refuse a swapped packet first
    for f in manifest["files"]:
        digest.update((packet_dir / f["path"]).read_bytes())
    return digest.hexdigest()


def parse_verdicts(text: str, rounds: list[str]) -> dict[str, tuple[str, str]]:
    """Map each requested round to (verdict, objection). Missing rounds, or
    a round the reviewer cannot judge, fail closed."""
    found: dict[str, tuple[str, str]] = {}
    for line in text.splitlines():
        m = ROUND_LINE_RE.match(line.strip())
        if m and m.group(1).lower() in rounds:
            found[m.group(1).lower()] = (m.group(2).upper(),
                                         m.group(3).strip())
    missing = [r for r in rounds if r not in found]
    if missing:
        raise DvcReviewError(
            f"goldfish response names no verdict for round(s) "
            f"{', '.join(missing)}; recorded as-is and the round does not "
            f"pass:\n{text.strip()[:2000]}")
    out = {}
    for r, (verdict, note) in found.items():
        if "cannot judge" in note.lower() or "can't judge" in note.lower():
            out[r] = ("FAIL", f"reviewer states it cannot judge: {note}")
        else:
            out[r] = (verdict, note)
    return out


def do_review_run(workdir, rounds: list[str],
                   define_spec: bytes | None = None) -> dict:
    """One packet + one model call covering all rounds. Returns the recorded
    call (verdicts, packet path, envelope, raw response)."""
    workdir = Path(workdir)
    cfg = _config()
    pkt = do_packet(workdir, define_spec)
    packet_dir = Path(pkt["dir"])
    manifest = json.loads((packet_dir / "manifest.json").read_text(
        encoding="utf-8"))
    brief = build_brief(rounds)
    brief_hash = _sha(brief.encode())
    stub = None
    tokens = _stub_tokens()
    if tokens is not None:
        tok = tokens.pop(0) if tokens else "P"
        text = _stub_response(rounds, "pass" if tok.startswith("P") else "fail")
        rid = ""
        tin = _est_tokens(brief.encode())
        tout = _est_tokens(text.encode())
        stub = tok
    else:
        user_msg = _inline_packet(packet_dir, manifest)
        text, rid_base, tin, tout = _provider_call(
            cfg, cfg["model"], brief, user_msg)
        rid = rid_base
    request_hash = _request_hash(cfg["model"], brief, packet_dir, manifest)
    try:
        verdicts = parse_verdicts(text, rounds)
    except DvcReviewError as exc:
        verdicts = {r: ("FAIL", str(exc)) for r in rounds}
    try:
        seq = max([int(p.stem.split("-")[-1])
                   for p in (workdir / REVIEWS_REL).glob("call-*.json")]
                  + [0]) + 1
    except ValueError:
        seq = 1
    if stub is not None:
        rid = f"stub-{seq:04d}"
    rec = {"format": FORMAT_CALL, "rounds": list(rounds),
           "packet_hash": pkt["packet_hash"], "packet_dir": pkt["dir"],
           "brief_hash": brief_hash, "request_hash": request_hash,
           "request": _request_envelope(cfg["model"], brief, manifest),
           "response": text, "model": cfg["model"],
           "provider_request_id": rid or f"stub-{seq:04d}",
           "tokens_in": tin, "tokens_out": tout,
           "results": {r: {"verdict": v.lower(), "note": n}
                       for r, (v, n) in verdicts.items()},
           "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    if not rec["provider_request_id"]:
        rec["provider_request_id"] = f"stub-{seq:04d}"
    base = workdir / REVIEWS_REL
    base.mkdir(parents=True, exist_ok=True)
    (base / f"call-{seq:04d}.json").write_text(
        json.dumps(rec, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rec


# ---------- loop + state (stop rules unchanged) ----------

def state_path_for(workdir):
    return Path(workdir) / STATE_REL


def new_state(run_id):
    return {
        "run_id": run_id,
        "rounds": list(ROUNDS),
        "same_round_limit": SAME_ROUND_LIMIT,
        "total_failure_cap": TOTAL_FAILURE_CAP,
        "total_failures": 0,
        # Counts keyed by round within this run file -- never by spec hash,
        # so a mid-run amendment + re-lock cannot reset them (p_g3 bypass).
        "per_round": {
            r: {"fails_consec": 0, "attempts": 0} for r in ROUNDS
        },
        "verdicts": [],
        "outcome": None,
    }


def save_state(workdir, state):
    path = state_path_for(workdir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def format_failure(state, rule, round_name):
    """Failure report: the round, verbatim objections, elephant's tries."""
    fails = [v for v in state["verdicts"]
             if v["round"] == round_name and v["verdict"] == "FAIL"]
    lines = [
        f"STOP: goldfish loop ends -- FAILURE ({rule}).",
        f"round that could not pass: {round_name}",
        f"run: {state['run_id']} "
        f"(failures total {state['total_failures']}, "
        f"cap {TOTAL_FAILURE_CAP}; round consecutive {fails[-1]['round_fails_consec'] if fails else '?'} "
        f"of {SAME_ROUND_LIMIT})",
        "objections (verbatim):",
    ]
    for v in fails:
        for ob in v["objections"]:
            lines.append(f"  - {ob}")
    lines.append("what the elephant tried in response:")
    for i, v in enumerate(fails, 1):
        lines.append(f"  - after '{round_name}' failure {i} of {len(fails)}: "
                     f"{v['elephant_response']}")
    hashes = ", ".join(_short(v["spec_sha"]) for v in fails)
    lines.append(f"spec hashes across these failures: {hashes} "
                 f"(count keyed by round within run {state['run_id']}; "
                 f"amendment does not reset it)")
    return "\n".join(lines)


def _spec_sha(workdir):
    try:
        data = (Path(workdir) / ".pipeline" / "to-spec.md").read_bytes()
    except OSError:
        return "?"
    return _sha(data)


def run_loop(workdir, elephant_respond, run_id, define_spec=None):
    """Run rounds until no objection (PASS) or a stop rule fires (FAIL).

    Each iteration assembles a fresh packet from the workdir and makes one
    model call covering every round. ``elephant_respond``(round,
    objections) reworks the artifact on disk (never the spec) and returns
    a response text. Returns the state dict (outcome.result is PASS/FAIL).
    define_spec (bytes) freezes the spec entry at the Define version —
    the reviewer judges that, never the current file (fix E).
    """
    workdir = Path(workdir)
    state = new_state(run_id)
    seq = 0
    while True:
        try:
            call = do_review_run(workdir, list(ROUNDS),
                                 define_spec=define_spec)
        except DvcReviewError as exc:
            seq += 1
            rnd = ROUNDS[0]
            st = state["per_round"][rnd]
            st["attempts"] += 1
            st["fails_consec"] += 1
            state["total_failures"] += 1
            state["verdicts"].append({
                "seq": seq, "round": rnd, "verdict": "FAIL",
                "spec_sha": _spec_sha(workdir),
                "packet_hash": None,
                "objections": [str(exc)],
                "elephant_response": "no rework possible; review error",
                "round_fails_consec": st["fails_consec"],
            })
            save_state(workdir, state)
            state["outcome"] = {"result": "FAIL", "rule": "review-error",
                                "round": rnd, "run_id": run_id,
                                "failures_total": state["total_failures"]}
            save_state(workdir, state)
            print(format_failure(state, f"review error: {exc}", rnd),
                  flush=True)
            return state
        spec_sha = _spec_sha(workdir)
        failed_rounds = [r for r in ROUNDS
                         if call["results"][r]["verdict"] != "pass"]
        for rnd in ROUNDS:
            seq += 1
            st = state["per_round"][rnd]
            st["attempts"] += 1
            res = call["results"][rnd]
            if res["verdict"] == "pass":
                st["fails_consec"] = 0
                state["verdicts"].append({
                    "seq": seq, "round": rnd, "verdict": "PASS",
                    "spec_sha": spec_sha,
                    "packet_hash": call["packet_hash"],
                    "objections": [],
                    "elephant_response": None,
                })
                save_state(workdir, state)
                print(f"goldfish {rnd}: no objection "
                      f"(attempt {st['attempts']}, spec {_short(spec_sha)}, "
                      f"packet {call['packet_hash'][:12]})", flush=True)
                continue
            ob = (f"OBJECTION {rnd}: {res['note']}"
                  if res["note"] else f"OBJECTION {rnd}: no reason given.")
            print(ob, flush=True)
            st["fails_consec"] += 1
            state["total_failures"] += 1
            response = elephant_respond(rnd, [ob])
            state["verdicts"].append({
                "seq": seq, "round": rnd, "verdict": "FAIL",
                "spec_sha": spec_sha,
                "packet_hash": call["packet_hash"],
                "objections": [ob],
                "elephant_response": response,
                "round_fails_consec": st["fails_consec"],
            })
            save_state(workdir, state)
        if not failed_rounds:
            state["outcome"] = {"result": "PASS", "run_id": run_id,
                                "rounds": list(ROUNDS),
                                "failures_total": state["total_failures"]}
            save_state(workdir, state)
            print(f"goldfish loop: PASS -- {len(ROUNDS)} rounds, "
                  f"{state['total_failures']} objection(s) answered, "
                  f"run {run_id}", flush=True)
            return state
        first = failed_rounds[0]
        st = state["per_round"][first]
        if st["fails_consec"] >= SAME_ROUND_LIMIT:
            state["outcome"] = {"result": "FAIL", "rule": "same-round",
                                "round": first, "run_id": run_id,
                                "failures_total": state["total_failures"]}
            save_state(workdir, state)
            print(format_failure(state, "same-round rule: "
                                 f"'{first}' failed twice, no third attempt",
                                 first), flush=True)
            return state
        if state["total_failures"] >= TOTAL_FAILURE_CAP:
            state["outcome"] = {"result": "FAIL", "rule": "total-cap",
                                "round": first, "run_id": run_id,
                                "failures_total": state["total_failures"]}
            save_state(workdir, state)
            print(format_failure(state, "total failure cap: "
                                 f"{state['total_failures']} failures "
                                 f"(cap {TOTAL_FAILURE_CAP})", first),
                  flush=True)
            return state
        print("elephant reworks the artifact; "
              "re-reviewing from the top", flush=True)
        # loop: fresh packet, fresh call; consecutive counts persist.


def make_run_id():
    return (f"{int(time.time())}x{os.getpid()}x{random.randint(0, 65535):04x}")


def cmd_packet(args):
    """Assemble a packet for a workdir; print its path and hash."""
    pkt = do_packet(args.workdir)
    print(f"packet: {pkt['dir']}")
    print(f"hash: {pkt['packet_hash']} "
          f"({pkt['files']} files, ~{pkt['tokens']} tokens)")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Blind goldfish review (no approve)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("packet", help="assemble the hash-locked review packet")
    p.add_argument("--workdir", default=".")
    ns = ap.parse_args(argv)
    if ns.cmd == "packet":
        return cmd_packet(ns)
    return 2


if __name__ == "__main__":
    sys.exit(main())
