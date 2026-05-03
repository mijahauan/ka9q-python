#!/usr/bin/env python3
"""Check ka9q-radio upstream for changes that could break ka9q-python clients.

Compares the pinned ka9q-radio commit (ka9q_radio_compat) against an
upstream ref (default: origin/main) and reports a severity:

    pass  — no upstream commits, or upstream advanced but no header touched
    warn  — header touched but no stream-critical field affected
            (review opportunity — might be new fields to expose)
    fail  — a stream-critical field was removed or its TLV value shifted
            (RTP delivery to clients is at risk; do not advance the pin
            without updating ka9q-python first)

Usage:
    python scripts/check_upstream_drift.py
    python scripts/check_upstream_drift.py --json
    python scripts/check_upstream_drift.py --no-fetch
    python scripts/check_upstream_drift.py --ka9q-radio /path/to/ka9q-radio
    python scripts/check_upstream_drift.py --remote upstream --branch master

Exit codes:
    0  pass or warn (informational)
    1  fail (stream-critical change detected)
    2  setup error (missing repo, missing pin, git failure)
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional

# Reuse sync_types' C enum parser — single source of truth for that grammar.
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from sync_types import parse_c_enum  # noqa: E402

PROJECT_ROOT = SCRIPT_DIR.parent
COMPAT_FILE = PROJECT_ROOT / "ka9q_radio_compat"


# ---------------------------------------------------------------------------
# Stream-critical allowlist
#
# Status TLV IDs / enum values whose shift, removal, or value change would
# corrupt RTP delivery to ka9q-python clients (wrong audio, wrong tuning,
# missing channel) rather than just losing a metadata counter.  Conservative
# by design: adding a non-critical name here only creates noise; missing a
# critical one masks real breakage.
#
# Lives here (not in the ka9q/ package) because it is a repo-level dev tool
# concern, not part of the PyPI runtime surface.
# ---------------------------------------------------------------------------

STREAM_CRITICAL_STATUS_TYPES: dict[str, str] = {
    # RTP wire delivery
    "OUTPUT_DATA_DEST_SOCKET":   "RTP destination multicast — clients won't find the stream",
    "OUTPUT_DATA_SOURCE_SOCKET": "RTP source addr — used by clients for filtering",
    "OUTPUT_SSRC":               "RTP SSRC — channel identity on the wire",
    "OUTPUT_TTL":                "Multicast TTL — affects whether stream crosses subnets",
    "OUTPUT_SAMPRATE":           "Sample rate — wrong value corrupts decoder buffering",
    "OUTPUT_ENCODING":           "Payload encoding — wrong value = garbage audio",
    "OUTPUT_CHANNELS":           "Mono/stereo — wrong value misframes audio",
    "RTP_PT":                    "RTP payload type — affects RFC 3550 routing",
    "RTP_TIMESNAP":              "RTP↔clock timestamp linkage — WSPR/timing relies on this",
    "GPS_TIME":                  "GPS-aligned timestamp — paired with RTP_TIMESNAP",
    "STATUS_INTERVAL":           "Status refresh cadence — affects ManagedStream recovery",

    # Channel identity / tuning (wrong value = wrong audio reaches the client)
    "RADIO_FREQUENCY":           "Channel center frequency",
    "PRESET":                    "Mode preset string — drives demod chain",
    "DEMOD_TYPE":                "Demodulator type",
    "LIFETIME":                  "Channel TTL — wrong value = channels expire unexpectedly",
}

# Enums whose every value is stream-critical: any TLV-value shift means
# clients decode samples wrong or request the wrong demod.
STREAM_CRITICAL_ENUMS: frozenset = frozenset({"Encoding", "DemodType"})


HEADER_FILES = {
    # path-in-repo  → (enum-name, python-class-name)
    "src/status.h": ("status_type", "StatusType"),
    "src/rtp.h":    ("encoding",    "Encoding"),
    "src/radio.h":  ("demod_type",  "DemodType"),
    "src/window.h": ("window_type", "WindowType"),
}


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class FieldChange:
    """A single field-level change between pin and upstream."""
    kind:   str   # "added" | "removed" | "value_changed"
    name:   str
    pin:    Optional[int] = None    # None for "added"
    head:   Optional[int] = None    # None for "removed"
    severity: str = "warn"          # "warn" | "fail"
    reason: str = ""                # human-readable why-it-matters

    def to_dict(self) -> dict:
        return {
            "kind":     self.kind,
            "name":     self.name,
            "pin":      self.pin,
            "head":     self.head,
            "severity": self.severity,
            "reason":   self.reason,
        }


@dataclass
class HeaderDelta:
    """Per-header change set."""
    header:  str   # e.g. "src/status.h"
    enum:    str   # e.g. "StatusType"
    changes: list[FieldChange] = field(default_factory=list)

    @property
    def severity(self) -> str:
        if any(c.severity == "fail" for c in self.changes):
            return "fail"
        if self.changes:
            return "warn"
        return "pass"

    def to_dict(self) -> dict:
        return {
            "header":   self.header,
            "enum":     self.enum,
            "severity": self.severity,
            "changes":  [c.to_dict() for c in self.changes],
        }


@dataclass
class CommitInfo:
    sha:      str
    subject:  str
    touches_headers: bool

    def to_dict(self) -> dict:
        return {
            "sha":              self.sha,
            "subject":          self.subject,
            "touches_headers":  self.touches_headers,
        }


@dataclass
class DriftReport:
    severity:       str                 # "pass" | "warn" | "fail"
    pin:            str
    upstream_ref:   str
    upstream_sha:   Optional[str]
    commits:        list[CommitInfo]    # pin..upstream
    header_deltas:  list[HeaderDelta]
    summary:        str
    error:          Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "severity":      self.severity,
            "pin":           self.pin,
            "upstream_ref":  self.upstream_ref,
            "upstream_sha":  self.upstream_sha,
            "commits":       [c.to_dict() for c in self.commits],
            "header_deltas": [d.to_dict() for d in self.header_deltas],
            "summary":       self.summary,
            "error":         self.error,
        }


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------

def _git(repo: Path, *args: str) -> str:
    """Run a git command in repo, return stdout (raises CalledProcessError)."""
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True, text=True, check=True,
    )
    return result.stdout


def _read_pin(compat_file: Path) -> str:
    for line in compat_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            return line
    raise ValueError(f"no commit hash found in {compat_file}")


def _resolve_upstream(repo: Path, remote: str, branch: str, fetch: bool) -> tuple[str, str]:
    """Return (ref-name, resolved-sha) for the upstream tip."""
    if fetch:
        _git(repo, "fetch", "--quiet", remote)
    ref = f"{remote}/{branch}"
    sha = _git(repo, "rev-parse", ref).strip()
    return ref, sha


def _commits_between(repo: Path, base: str, head: str) -> list[tuple[str, str]]:
    """Return [(sha, subject), ...] for base..head, oldest first."""
    out = _git(repo, "log", "--reverse", "--pretty=%H%x09%s", f"{base}..{head}")
    pairs: list[tuple[str, str]] = []
    for line in out.splitlines():
        if "\t" in line:
            sha, subject = line.split("\t", 1)
            pairs.append((sha, subject))
    return pairs


def _files_changed_in(repo: Path, sha: str) -> set[str]:
    out = _git(repo, "show", "--name-only", "--pretty=", sha)
    return {ln.strip() for ln in out.splitlines() if ln.strip()}


def _file_at(repo: Path, ref: str, path: str) -> str:
    """Return file contents at the given git ref. '' if missing at that ref."""
    try:
        return _git(repo, "show", f"{ref}:{path}")
    except subprocess.CalledProcessError:
        return ""


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

def _classify_change(enum_class: str, kind: str, name: str) -> tuple[str, str]:
    """Return (severity, reason) for a single change."""
    if kind == "added":
        # New fields don't break anything, but operator should review for
        # opportunity to expose new capabilities.
        return ("warn", "new field upstream — review for client exposure")

    # Removal or value change
    if enum_class == "StatusType":
        rationale = STREAM_CRITICAL_STATUS_TYPES.get(name)
        if rationale:
            return ("fail", rationale)
        return ("warn", "non-stream-critical metadata field")

    if enum_class in STREAM_CRITICAL_ENUMS:
        return ("fail", f"{enum_class} value shift — clients decode wrong format")

    # WindowType etc — not stream-critical
    return ("warn", f"{enum_class} change — non-stream-critical")


def _diff_enum(
    enum_class: str,
    pin_entries:  Iterable[tuple[str, int, str]],
    head_entries: Iterable[tuple[str, int, str]],
) -> list[FieldChange]:
    pin_map  = {n: v for n, v, _ in pin_entries}
    head_map = {n: v for n, v, _ in head_entries}
    changes: list[FieldChange] = []

    for name, val in head_map.items():
        if name not in pin_map:
            sev, reason = _classify_change(enum_class, "added", name)
            changes.append(FieldChange("added", name, head=val,
                                       severity=sev, reason=reason))
        elif pin_map[name] != val:
            sev, reason = _classify_change(enum_class, "value_changed", name)
            changes.append(FieldChange("value_changed", name,
                                       pin=pin_map[name], head=val,
                                       severity=sev, reason=reason))

    for name, val in pin_map.items():
        if name not in head_map:
            sev, reason = _classify_change(enum_class, "removed", name)
            changes.append(FieldChange("removed", name, pin=val,
                                       severity=sev, reason=reason))

    return changes


def _aggregate_severity(deltas: list[HeaderDelta]) -> str:
    if any(d.severity == "fail" for d in deltas):
        return "fail"
    if any(d.severity == "warn" for d in deltas):
        return "warn"
    return "pass"


# ---------------------------------------------------------------------------
# Main analysis
# ---------------------------------------------------------------------------

def analyze(
    radio_repo:  Path,
    pin:         str,
    remote:      str,
    branch:      str,
    fetch:       bool,
) -> DriftReport:
    upstream_ref, upstream_sha = _resolve_upstream(radio_repo, remote, branch, fetch)

    if upstream_sha == pin:
        return DriftReport(
            severity="pass",
            pin=pin,
            upstream_ref=upstream_ref,
            upstream_sha=upstream_sha,
            commits=[],
            header_deltas=[],
            summary=f"in sync at {pin[:12]}",
        )

    raw_commits = _commits_between(radio_repo, pin, upstream_sha)
    commits: list[CommitInfo] = []
    header_paths = set(HEADER_FILES.keys())
    any_header_touched = False

    for sha, subject in raw_commits:
        touched = _files_changed_in(radio_repo, sha)
        touches_h = bool(touched & header_paths)
        any_header_touched |= touches_h
        commits.append(CommitInfo(sha=sha, subject=subject, touches_headers=touches_h))

    if not any_header_touched:
        return DriftReport(
            severity="pass",
            pin=pin,
            upstream_ref=upstream_ref,
            upstream_sha=upstream_sha,
            commits=commits,
            header_deltas=[],
            summary=(f"upstream advanced {len(commits)} commit"
                     f"{'s' if len(commits) != 1 else ''}; "
                     f"no header changes (contract intact)"),
        )

    deltas: list[HeaderDelta] = []
    for header_path, (enum_name, py_class) in HEADER_FILES.items():
        pin_text  = _file_at(radio_repo, pin, header_path)
        head_text = _file_at(radio_repo, upstream_sha, header_path)
        if pin_text == head_text:
            continue
        try:
            pin_entries  = parse_c_enum(pin_text,  enum_name) if pin_text  else []
            head_entries = parse_c_enum(head_text, enum_name) if head_text else []
        except ValueError as exc:
            deltas.append(HeaderDelta(
                header=header_path, enum=py_class,
                changes=[FieldChange(
                    kind="parse_error", name=enum_name,
                    severity="warn",
                    reason=f"could not parse enum {enum_name}: {exc}",
                )],
            ))
            continue
        changes = _diff_enum(py_class, pin_entries, head_entries)
        if changes:
            deltas.append(HeaderDelta(header=header_path, enum=py_class, changes=changes))

    severity = _aggregate_severity(deltas)
    if severity == "fail":
        n_fail = sum(1 for d in deltas for c in d.changes if c.severity == "fail")
        summary = (f"{n_fail} stream-critical change"
                   f"{'s' if n_fail != 1 else ''} — RTP delivery at risk")
    elif severity == "warn":
        n = sum(len(d.changes) for d in deltas)
        summary = (f"{n} header change{'s' if n != 1 else ''}; "
                   f"none stream-critical")
    else:
        summary = "headers touched but no field-level changes"
    return DriftReport(
        severity=severity, pin=pin,
        upstream_ref=upstream_ref, upstream_sha=upstream_sha,
        commits=commits, header_deltas=deltas, summary=summary,
    )


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

_SEV_GLYPH = {
    "pass": "\033[32m✓\033[0m",
    "warn": "\033[33m⚠\033[0m",
    "fail": "\033[31m✗\033[0m",
}


def _print_human(report: DriftReport) -> None:
    glyph = _SEV_GLYPH.get(report.severity, "?")
    print(f"  {glyph}  ka9q-radio drift: {report.summary}")
    print(f"     pin:      {report.pin[:12]}")
    if report.upstream_sha:
        print(f"     upstream: {report.upstream_sha[:12]}  ({report.upstream_ref})")

    if report.error:
        print(f"     error:    {report.error}")
        return

    if report.commits:
        print(f"     commits:  {len(report.commits)} ahead")
        for c in report.commits[-10:]:
            mark = "H" if c.touches_headers else " "
            print(f"       [{mark}] {c.sha[:12]}  {c.subject}")
        if len(report.commits) > 10:
            print(f"       … {len(report.commits) - 10} earlier commit(s) elided")

    for d in report.header_deltas:
        sym = _SEV_GLYPH.get(d.severity, "?")
        print(f"     {sym}  {d.header} ({d.enum}):")
        for c in d.changes:
            csym = _SEV_GLYPH.get(c.severity, "?")
            if c.kind == "added":
                detail = f"+{c.name} = {c.head}"
            elif c.kind == "removed":
                detail = f"-{c.name}  (was {c.pin})"
            elif c.kind == "value_changed":
                detail = f"~{c.name}: {c.pin} → {c.head}"
            else:
                detail = f"?{c.name}"
            print(f"         {csym}  {detail}  — {c.reason}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--ka9q-radio", type=Path, default=None,
                        help="Path to ka9q-radio source tree (default: ../ka9q-radio)")
    parser.add_argument("--remote", default="origin",
                        help="Git remote name (default: origin)")
    parser.add_argument("--branch", default="main",
                        help="Upstream branch (default: main)")
    parser.add_argument("--no-fetch", action="store_true",
                        help="Skip 'git fetch' (use local refs as-is)")
    parser.add_argument("--json", action="store_true",
                        help="Emit machine-readable JSON")
    args = parser.parse_args()

    repo = (args.ka9q_radio.resolve() if args.ka9q_radio
            else (PROJECT_ROOT / ".." / "ka9q-radio").resolve())

    if not (repo / ".git").exists():
        err = f"not a git repo: {repo}"
        if args.json:
            json.dump({"severity": "fail", "error": err}, sys.stdout)
            sys.stdout.write("\n")
        else:
            print(f"  \033[31m✗\033[0m  ka9q-radio drift: {err}", file=sys.stderr)
        return 2

    if not COMPAT_FILE.exists():
        err = f"missing pin file: {COMPAT_FILE}"
        if args.json:
            json.dump({"severity": "fail", "error": err}, sys.stdout)
            sys.stdout.write("\n")
        else:
            print(f"  \033[31m✗\033[0m  ka9q-radio drift: {err}", file=sys.stderr)
        return 2

    pin = _read_pin(COMPAT_FILE)

    try:
        report = analyze(repo, pin, args.remote, args.branch, fetch=not args.no_fetch)
    except subprocess.CalledProcessError as exc:
        err = f"git failed: {exc.stderr.strip() or exc}"
        if args.json:
            json.dump({"severity": "fail", "error": err, "pin": pin}, sys.stdout)
            sys.stdout.write("\n")
        else:
            print(f"  \033[31m✗\033[0m  ka9q-radio drift: {err}", file=sys.stderr)
        return 2

    if args.json:
        json.dump(report.to_dict(), sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        _print_human(report)

    return 1 if report.severity == "fail" else 0


if __name__ == "__main__":
    sys.exit(main())
