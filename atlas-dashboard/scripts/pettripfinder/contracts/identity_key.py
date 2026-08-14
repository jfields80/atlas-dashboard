"""``ptf_identity_key/1.0`` -- the ONE identity normaliser.

The defect this closes
----------------------
``normalize_name`` exists five times in ``scripts/pettripfinder`` with three
incompatible behaviours, and the committed censuses were written by a sixth
path matching none of them:

    input: "Holiday Inn Express & Suites Greenville"
      discovery.duplicates          -> "holiday inn express suites greenville"
      site_data                     -> "holiday inn express and suites greenville"
      importer.normalize            -> "Holiday Inn Express & Suites Greenville"
      committed Dayton census       -> "holiday inn express & suites greenville"
      committed routing record      -> "holiday inn express and suites greenville"

    input: "Le Méridien Columbus, The Joseph"
      discovery.duplicates          -> "le meridien columbus the joseph"
      site_data                     -> "le m ridien columbus the joseph"

Two consequences, both already observed. First, the ``routing ⊆ census``
invariant cannot be evaluated by string equality: Dayton reports two orphan
routes that are the SAME properties spelled by two normalisers, while
Cleveland's two orphans are genuinely absent. A gate written against today's
data would fail closed on correct records and pass records that are wrong.
Second, an unfolded diacritic is not merely unequal -- ``[^a-z0-9]+`` treats it
as a SEPARATOR, so "méridien" arrives as the tokens "m" and "ridien", and a
bare one-character token is free to match inside unrelated hotels' names.

The rule
--------
One function, one module, no alternatives. Every cross-layer join -- census to
partition, routing to census, policy record to seed row -- uses this and
nothing else.

What this module deliberately does NOT do
-----------------------------------------
It does not rename or delete the five existing ``normalize_name`` functions.
Several are load-bearing for purposes that are not identity: the
``discovery.duplicates`` variant drops ``&`` entirely BECAUSE fuzzy duplicate
detection wants "Express Suites" and "Express & Suites" to collide, which is
correct there and wrong here. Renaming public functions is also forbidden by
the repository's standing rules. They stay; what changes is that identity joins
stop calling them.

Why "&" becomes "and" rather than disappearing
----------------------------------------------
Both are defensible in isolation. "and" wins because the committed corpus
already leans that way -- the routing authority, the policy fact keys and three
of the five normalisers spell it "and" -- so it is the choice that migrates the
fewest records. Determinism matters more than the choice; a coin-flip settled
consistently beats a principle applied inconsistently.
"""

from __future__ import annotations

import re
from typing import Iterable, List, Mapping, Sequence, Tuple

from scripts.pettripfinder.discovery.duplicates import fold_accents

#: Versioned so a future change is a visible contract bump rather than a silent
#: rekeying of every join in the system.
IDENTITY_KEY_CONTRACT = "ptf_identity_key/1.0"

_NON_KEY_CHARS = re.compile(r"[^a-z0-9 ]+")


class IdentityKeyError(ValueError):
    """A name that cannot produce an identity key (fail closed)."""


def ptf_identity_key(name: str) -> str:
    """The canonical identity key for a property name.

        >>> ptf_identity_key("Holiday Inn Express & Suites Greenville")
        'holiday inn express and suites greenville'
        >>> ptf_identity_key("Comfort Suites Springfield I-70")
        'comfort suites springfield i 70'
        >>> ptf_identity_key("Le Méridien Columbus, The Joseph")
        'le meridien columbus the joseph'

    Raises ``IdentityKeyError`` when the result would be empty. A blank key
    would silently collide with every other blank key, joining unrelated
    properties to each other -- so a name made entirely of punctuation fails
    closed rather than producing a universal match.
    """
    if not isinstance(name, str):
        raise IdentityKeyError("identity key needs a string, got %r" % type(name).__name__)

    # Order matters. "&" has to become a word BEFORE the character filter runs,
    # or the filter turns it into a space and "Express & Suites" silently
    # becomes "express suites" -- which is the discovery.duplicates behaviour,
    # correct for deduplication and wrong for identity.
    folded = fold_accents(name).casefold().replace("&", " and ")
    stripped = _NON_KEY_CHARS.sub(" ", folded)
    key = " ".join(stripped.split())
    if not key:
        raise IdentityKeyError(
            "name %r produces an empty identity key; an empty key would match "
            "every other empty key" % (name,))
    return key


def is_canonical_key(value: str) -> bool:
    """True when ``value`` is already exactly what this contract produces.

    Used by the release gates to assert that a stored ``identity_key`` was not
    hand-written or produced by one of the legacy normalisers.
    """
    try:
        return bool(value) and ptf_identity_key(value) == value
    except IdentityKeyError:
        return False


def key_collisions(names: Iterable[str]) -> Mapping[str, Tuple[str, ...]]:
    """Names that share an identity key, as ``{key: (name, name, ...)}``.

    Only genuine collisions are returned -- a key reached by one name is not
    reported. Two DIFFERENT properties sharing a key is a census question that
    must be answered before either can publish, because the join layer cannot
    tell them apart.
    """
    by_key: dict = {}
    for name in names:
        by_key.setdefault(ptf_identity_key(name), []).append(name)
    return {k: tuple(v) for k, v in sorted(by_key.items()) if len(set(v)) > 1}


def rekey(rows: Sequence[Mapping], name_field: str = "canonical_name",
          key_field: str = "identity_key") -> List[dict]:
    """Return copies of ``rows`` carrying a canonical ``identity_key``.

    A pure transformation returning new dicts: nothing here writes to committed
    authority, and the input rows are left untouched so a caller can diff the
    before and after.
    """
    out: List[dict] = []
    for row in rows:
        name = row.get(name_field) or ""
        updated = dict(row)
        updated[key_field] = ptf_identity_key(name)
        out.append(updated)
    return out


def divergences(rows: Sequence[Mapping], *, name_field: str = "canonical_name",
                stored_field: str = "normalized_name") -> Tuple[dict, ...]:
    """Rows whose stored normalised name differs from the canonical key.

    This is the reporting half of the repair. It names every record that a
    migration will have to rekey, WITHOUT rekeying anything -- Phase A produces
    the list, Phase C acts on it.
    """
    found: List[dict] = []
    for row in rows:
        name = row.get(name_field) or ""
        stored = (row.get(stored_field) or "").strip()
        try:
            canonical = ptf_identity_key(name)
        except IdentityKeyError as exc:
            found.append({"canonical_name": name, "stored": stored,
                          "canonical": None, "error": str(exc)})
            continue
        if stored != canonical:
            found.append({"canonical_name": name, "stored": stored,
                          "canonical": canonical, "error": ""})
    return tuple(found)
