"""Read-only typed receipt summary. Arbitrary text is represented by SHA256 IDs.

Usage: python scripts/summarize_receipt.py RECEIPT [--entry ID_OR_EXACT_NAME]
A successful exit means the summary was rendered, not that the receipt passed.
Full SHA256 locators bind the original bytes; this derived view grants no authority.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys


class InvalidReceipt(ValueError):
    """Unsupported or malformed input; messages never contain input data."""


def opaque(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def require(condition):
    if not condition:
        raise InvalidReceipt("malformed or unsupported receipt")


def adapt(receipt):
    require(isinstance(receipt, dict))
    rows = []
    if type(receipt.get("schema")) is int and receipt["schema"] == 1:
        require(receipt.get("status") in {"PASS", "FAIL"})
        require(
            isinstance(receipt.get("checks"), list)
            and isinstance(receipt.get("actions"), list)
        )
        require("qualified" not in receipt or type(receipt["qualified"]) is bool)
        for group in ("checks", "actions"):
            for row in receipt[group]:
                require(isinstance(row, dict) and isinstance(row.get("name"), str))
                require(
                    row.get("status")
                    in {"PASS", "FAIL", "INVALIDATED", "BLOCKED", "RUNNING"}
                )
                require("required" not in row or type(row["required"]) is bool)
                rows.append(
                    (
                        group,
                        row["name"],
                        {
                            "status": row["status"],
                            "required": row.get("required", True),
                        },
                    )
                )
        metadata = {
            "type": "candidate-validation",
            "status": receipt["status"],
            "qualified": receipt.get("qualified"),
            "failure_present": "failure" in receipt,
        }
    elif receipt.get("schema") == "codex-wake.cleanup.v1":
        require(
            receipt.get("kind") in {"plan", "result"}
            and receipt.get("status") in {"PASS", "HELD", "FAIL"}
        )
        require(
            isinstance(receipt.get("repository"), str)
            and isinstance(receipt.get("entries"), list)
        )
        seen = set()
        for row in receipt["entries"]:
            require(isinstance(row, dict))
            require(
                all(isinstance(row.get(key), str) for key in ("id", "path", "head"))
            )
            require(row["id"] not in seen)
            seen.add(row["id"])
            require(row.get("action") in {"retain", "remove", "prune"})
            require(
                row.get("disposition")
                in {
                    "eligible",
                    "retained_unknown",
                    "retained",
                    "removed",
                    "pruned",
                    "failed",
                    "unknown",
                }
            )
            require(
                isinstance(row.get("reasons"), list)
                and all(isinstance(reason, str) for reason in row["reasons"])
            )
            rows.append(
                (
                    "entries",
                    row["id"],
                    dict(
                        action=row["action"],
                        disposition=row["disposition"],
                        reason_count=len(row["reasons"]),
                        path_sha256=opaque(row["path"]),
                        head_sha256=opaque(row["head"]),
                    ),
                )
            )
        metadata = {
            "type": "cleanup",
            "kind": receipt["kind"],
            "status": receipt["status"],
            "repository_sha256": opaque(receipt["repository"]),
        }
    else:
        raise InvalidReceipt("malformed or unsupported receipt")
    return metadata, rows


def render(raw, locator, entry, budget):
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result)
            result[key] = value
        return result

    receipt = json.loads(raw, object_pairs_hook=unique_object)
    metadata, rows = adapt(receipt)
    counts = {}
    for key in ("status", "disposition", "action"):
        values = Counter(row[2][key] for row in rows if key in row[2])
        if values:
            counts[key] = dict(sorted(values.items()))
    entries = []
    for index, (group, name, fields) in enumerate(rows):
        identifier = opaque(f"{group}\0{index}\0{name}")
        entries.append(
            (name, dict(id=identifier, group=group, name_sha256=opaque(name), **fields))
        )
    selected = entries
    if entry is not None:
        selected = [item for item in entries if entry in (item[0], item[1]["id"])]
        require(len(selected) == 1)
    selected.sort(
        key=lambda item: (
            item[1].get("status") == "PASS"
            or item[1].get("disposition") in {"eligible", "removed", "pruned"},
            item[1]["id"],
        )
    )
    out = dict(
        schema="codex-wake.receipt-summary.v1",
        source_schema=receipt["schema"],
        source_sha256=hashlib.sha256(raw).hexdigest(),
        locator_sha256=opaque(str(locator)),
        **metadata,
        counts=counts,
        total_count=len(rows),
        selected_count=len(selected),
        failure_count=sum(
            row[2].get("status") == "FAIL" or row[2].get("disposition") == "failed"
            for row in rows
        ),
        unknown_count=sum(
            row[2].get("status") in {"BLOCKED", "RUNNING"}
            or row[2].get("disposition") in {"unknown", "retained_unknown"}
            for row in rows
        ),
        invalidated_count=sum(row[2].get("status") == "INVALIDATED" for row in rows),
        entries=[],
        omitted_count=len(rows),
        truncated=bool(rows),
        redaction="Arbitrary strings are SHA256 IDs; raw logs, reasons, argv and environment are excluded.",
        drill_down="Use the same receipt argument with --entry ID (or exact original name/id).",
    )

    def encode():
        return (
            json.dumps(out, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
            + "\n"
        ).encode()

    require(budget >= 1)
    if len(encode()) > budget:
        raise InvalidReceipt("mandatory summary fields exceed byte budget")
    for _, item in selected:
        out["entries"].append(item)
        out["omitted_count"] = len(rows) - len(out["entries"])
        out["truncated"] = out["omitted_count"] > 0
        if len(encode()) > budget:
            out["entries"].pop()
            out["omitted_count"] = len(rows) - len(out["entries"])
            out["truncated"] = out["omitted_count"] > 0
            break
    if entry is not None and not out["entries"]:
        raise InvalidReceipt("selected entry exceeds byte budget")
    return encode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipt", type=Path)
    parser.add_argument("--entry")
    parser.add_argument("--max-bytes", type=int, default=8192)
    args = parser.parse_args()
    try:
        output = render(
            args.receipt.read_bytes(), args.receipt, args.entry, args.max_bytes
        )
    except (OSError, ValueError, TypeError, RecursionError, UnicodeError):
        print(
            "Receipt summary unavailable: malformed/unsupported input, ambiguous entry, or insufficient byte budget.",
            file=sys.stderr,
        )
        return 1
    sys.stdout.buffer.write(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
