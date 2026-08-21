"""Evidence for a capture that reached a page and was then declined.

PTF-MILWAUKEE-CLOSURE-ASSESSMENT-031 could not classify three of Milwaukee's
nineteen unresolved properties, and the reason was not that the answer was
hard. It was that nobody had written anything down.

A capture that navigates, renders, and is then refused by the identity gate or
finds no policy container persists NOTHING. So "this property publishes no pet
policy" and "this page cannot be bound to this identity" are claims the archive
can neither support nor refute. Drury and Potawatomi carry the first; Brewhouse
carries the second. Answering any of them today costs a provider call, to
re-observe something we already observed.

WHAT THIS CHANGES, AND WHAT IT DOES NOT
---------------------------------------
It changes AUDITABILITY. The verdict is untouched: this module is called on the
way out of a decline, after the outcome is decided, and it returns nothing the
caller uses. A declined capture stays declined.

The artifact set is deliberately NOT the one a successful capture writes, and
the difference is structural rather than a convention someone has to remember.
There is no ``policy-block.txt`` and there is no locator record. Every consumer
in this codebase finds an observation by looking for that block -- the store's
``_attempt_dir``, the canonical replay, the re-derivation seams -- so a
declined directory cannot be mistaken for evidence of a policy no matter who
reads it next. It can only be read by something that goes looking for a
decline.

WHAT IS KEPT
------------
The document, the page text, and a manifest naming the outcome, the failure,
the URL asked for and the URL served, the provider, and whatever the identity
gate saw. Hashes so the document can be checked against a later capture of the
same page. No credential is written: the manifest carries no auth, no zone and
no session, and the only URLs in it are the property's own.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Mapping, Optional

#: The manifest a declined capture writes. Named so nothing looking for an
#: observation can find it, and so anything auditing declines can.
DECLINED_ARTIFACT = "declined.json"
DECLINED_CONTRACT = "ptf-declined-capture/1.0"

#: Files a declined capture may write. ``policy-block.txt`` is absent on
#: purpose and its absence is what makes this directory unmistakable.
DOCUMENT_ARTIFACT = "rendered.html"
TEXT_ARTIFACT = "page-text.txt"

#: Outcomes worth keeping evidence for: the page arrived and something after
#: the fetch declined it. A navigation that never reached a page has no
#: document to keep, and an access denial has a challenge page rather than the
#: property's.
KEEPABLE_OUTCOMES = ("IDENTITY_MISMATCH", "POLICY_NOT_FOUND")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_text(text: str) -> str:
    import hashlib
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def keep(*, run_dir: Path, slug: str, attempt: int, outcome: str,
         html: str, body_text: str, requested_url: str, final_url: str,
         title: str, provider: str, identity: Optional[Mapping] = None,
         locator: Optional[Mapping] = None, detail: str = "") -> Dict:
    """Write the evidence for one declined capture. Never raises.

    Failure to persist an audit trail must not turn a decline into a capture
    error: the verdict was already decided and this runs after it. A broken
    write is reported in the return value and swallowed.
    """
    record = {
        "contract": DECLINED_CONTRACT,
        "written_at": _now(),
        "outcome": outcome,
        "verdict": "DECLINED",
        "verdict_note": ("this capture was declined and remains declined. "
                         "Nothing here is an observation: there is no policy "
                         "block and no locator record, and no current-state "
                         "row can be built from this directory."),
        "detail": detail,
        "requested_url": requested_url,
        "final_url": final_url,
        "title": title,
        "provider": provider,
        "identity": dict(identity or {}),
        "locator": dict(locator or {}),
        "document_sha256": sha256_text(html),
        "document_chars": len(html or ""),
        "page_text_sha256": sha256_text(body_text),
        "page_text_chars": len(body_text or ""),
        "persisted": False,
    }
    if outcome not in KEEPABLE_OUTCOMES:
        record["skipped"] = ("this outcome has no property document to keep")
        return record
    try:
        directory = Path(run_dir) / slug / ("declined-%02d" % attempt)
        directory.mkdir(parents=True, exist_ok=True)
        (directory / DOCUMENT_ARTIFACT).write_text(html or "",
                                                   encoding="utf-8")
        (directory / TEXT_ARTIFACT).write_text(body_text or "",
                                               encoding="utf-8")
        record["persisted"] = True
        record["directory"] = str(directory)
        (directory / DECLINED_ARTIFACT).write_bytes(
            (json.dumps(record, indent=1, ensure_ascii=False) + "\n")
            .encode("utf-8"))
    except Exception as exc:                                    # noqa: BLE001
        record["persisted"] = False
        record["error"] = "%s: %s" % (type(exc).__name__, exc)
    return record


def read(directory: Path) -> Optional[Dict]:
    """The manifest of a declined capture, or None when there is not one."""
    path = Path(directory) / DECLINED_ARTIFACT
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def is_declined_directory(directory: Path) -> bool:
    """True when this directory holds a decline and not an observation."""
    directory = Path(directory)
    return ((directory / DECLINED_ARTIFACT).is_file()
            and not (directory / "policy-block.txt").is_file())


__all__ = ["DECLINED_ARTIFACT", "DECLINED_CONTRACT", "DOCUMENT_ARTIFACT",
           "TEXT_ARTIFACT", "KEEPABLE_OUTCOMES", "keep", "read",
           "is_declined_directory", "sha256_text"]
