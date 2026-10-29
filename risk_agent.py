"""Classify emetogenic risk for a regimen of antineoplastic agents.

This module answers one question: given one or more chemotherapy medications,
what is the emetogenicity risk (minimal, low, moderate, or high)?

The algorithm, in plain if/then terms:

1. Normalize every input first. Lowercase it. Strip whitespace. Strip a
   leading "*" (the reference data uses "*" as a footnote marker, not part of
   the name). If a dose is given, also strip unit formatting noise (spaces,
   "m²"/"m^2" -> "m2") so "1 g/m2" and "1g/m2" are treated as identical.

2. If exactly one medication is given, classify it alone.
   - Look up the medication by name in the single-medication table.
   - If it isn't found, return None and log a warning. Stop here.
   - If it's found once, return that classification. Dose and route don't
     matter; there's nothing to disambiguate.
   - If it's found multiple times (the drug has dose- or route-dependent
     thresholds), narrow down using the entered dose and route:
       - If a dose is given, parse it to a number in mg. If the unit is
         grams, convert to mg (and log the conversion). Compare that number
         against each entry's lower/upper dose bounds.
       - If a bound is null, treat it as unconstrained; it always matches.
       - If the entered dose can't be parsed (e.g. "12 million units/m2"),
         or if its scale (per body-surface-area vs. absolute) doesn't match
         a bound's scale, fall back to comparing the raw strings instead,
         and log that the fallback happened.
       - If a route is given and an entry's route is null, that entry still
         matches (null route is also unconstrained).
       - If, after all that, no entry is compatible with the given dose and
         route, fall back to considering every entry for that medication.
       - If more than one entry remains compatible, prefer the one whose
         route matches exactly.
       - If there's still a tie, return the single highest-risk
         classification among the tied entries. Log how the input was
         finally interpreted either way.

3. If more than one medication is given, first check the known-combination
   table before classifying each drug separately.
   - If every medication listed in one combination-table entry is present
     somewhere in the input regimen (extra, unrelated medications in the
     regimen are fine), that counts as a match. Matching also respects the
     same dose/route/null-is-wildcard rules as step 2.
   - If more than one combination entry matches, return the single
     highest-risk classification among them.
   - If no combination matches, classify each medication in the regimen
     individually (via step 2's logic), ignore any that aren't recognized,
     and return the single highest-risk classification among the rest.
   - If none of the medications are recognized at all, return None rather
     than guessing.

Every fallback and every interpreted dose/route/classification is logged
(warnings for ambiguous fallbacks, info for normal interpretation), so the
reasoning behind a result is never silent.
"""

import json
import logging
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

CLASSIFICATION_ORDER = ["minimal", "low", "moderate", "high"]

JSON_PATH = Path(__file__).parent / "risk_data" / "pogo_single_antineoplastic_medicine.json"
MULTI_JSON_PATH = Path(__file__).parent / "risk_data" / "pogo_multi_antineoplastic_medicine.json"

# Matches doses like "250mg", "1g/m2", "3g/m2/dose" after `_normalize_dose`.
DOSE_PATTERN = re.compile(r"^(?P<value>\d+(?:\.\d+)?)(?P<unit>mg|g)(?P<per_m2>/m2)?(?:/dose)?$")


def _normalize(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    return value.strip().lstrip("*").lower()


def _normalize_dose(value: Optional[str]) -> Optional[str]:
    """Normalize a dose string's formatting without converting units.

    Unifies superscript/caret exponents (e.g. "m²", "m^2" -> "m2") and removes
    all whitespace, so "1 g/m2", "1g/m2", and "1 G/M\u00b2" are treated as the
    same dose. Does NOT convert between units (e.g. mg vs g stay distinct).
    """
    norm = _normalize(value)
    if norm is None:
        return None
    norm = norm.translate(str.maketrans({"\u00b2": "2", "\u00b3": "3", "^": ""}))
    return re.sub(r"\s+", "", norm)


def _value_matches(
    entered_norm: Optional[str],
    *raw_entry_values: Optional[str],
    normalize=_normalize,
) -> bool:
    """True if `entered_norm` satisfies an entry's allowed value(s).

    A field with no non-null allowed values (e.g. a null route) is
    unconstrained and always matches, even if the caller didn't specify
    anything. Otherwise the caller must have specified a value that equals
    one of the allowed values.
    """
    allowed = {v for v in (normalize(x) for x in raw_entry_values) if v is not None}
    if not allowed:
        return True
    return entered_norm is not None and entered_norm in allowed


def _parse_dose_mg(dose_norm: Optional[str]) -> Optional[tuple[float, bool]]:
    """Parse a normalized dose string into (value_in_mg, is_per_m2).

    Converts "g" doses to "mg" (x1000) and always logs how the dose was
    interpreted. Returns None if the string isn't a plain mg/g dose (e.g.
    "12 million units/m2"), signaling that numeric comparison isn't possible.
    """
    if dose_norm is None:
        return None
    match = DOSE_PATTERN.match(dose_norm)
    if not match:
        return None

    value = float(match.group("value"))
    unit = match.group("unit")
    per_m2 = match.group("per_m2") is not None
    scale = "per-m2" if per_m2 else "absolute"

    if unit == "g":
        value_mg = value * 1000
        logger.info(
            "Interpreted dose '%s' as %s mg (%s) — converted from g to mg for threshold comparison.",
            dose_norm, value_mg, scale,
        )
        return value_mg, per_m2

    logger.info("Interpreted dose '%s' as %s mg (%s).", dose_norm, value, scale)
    return value, per_m2


def _dose_compatible(
    dose_norm: Optional[str],
    lower_raw: Optional[str],
    upper_raw: Optional[str],
) -> bool:
    """True if `dose_norm` falls within the [lower_raw, upper_raw] dose bounds.

    Bounds are parsed to mg and compared numerically (mg/m2 vs g/m2 are made
    comparable via conversion). A null bound is unconstrained. Every fallback
    (unparseable dose, scale mismatch between the entered dose and a bound) is
    logged as a warning so ambiguous input is never silently resolved.
    """
    lower_norm = _normalize_dose(lower_raw)
    upper_norm = _normalize_dose(upper_raw)
    if lower_norm is None and upper_norm is None:
        return True
    if dose_norm is None:
        return False

    entered = _parse_dose_mg(dose_norm)
    if entered is None:
        logger.warning(
            "Dose '%s' isn't a recognized numeric mg/g dose; falling back to exact string "
            "match against bound(s) %r.",
            dose_norm, [v for v in (lower_norm, upper_norm) if v is not None],
        )
        return _value_matches(dose_norm, lower_norm, upper_norm)

    entered_mg, entered_per_m2 = entered
    lower = _parse_dose_mg(lower_norm)
    upper = _parse_dose_mg(upper_norm)

    # Only compare bounds expressed on the same scale (per-BSA vs absolute) as the entered dose.
    if lower is not None and lower[1] != entered_per_m2:
        logger.warning(
            "Ignoring lower bound '%s' for dose '%s': scale mismatch (%s vs %s).",
            lower_norm, dose_norm,
            "per-m2" if lower[1] else "absolute", "per-m2" if entered_per_m2 else "absolute",
        )
        lower = None
    if upper is not None and upper[1] != entered_per_m2:
        logger.warning(
            "Ignoring upper bound '%s' for dose '%s': scale mismatch (%s vs %s).",
            upper_norm, dose_norm,
            "per-m2" if upper[1] else "absolute", "per-m2" if entered_per_m2 else "absolute",
        )
        upper = None

    if lower is None and upper is None:
        logger.warning(
            "No numerically comparable bound remains for dose '%s'; falling back to exact "
            "string match against bound(s) %r.",
            dose_norm, [v for v in (lower_norm, upper_norm) if v is not None],
        )
        return _value_matches(dose_norm, lower_norm, upper_norm)

    if lower is not None and entered_mg < lower[0]:
        return False
    if upper is not None and entered_mg > upper[0]:
        return False
    return True


def _entry_compatible(dose_norm: Optional[str], route_norm: Optional[str], entry: dict) -> bool:
    return _dose_compatible(
        dose_norm, entry.get("dose_lower_bound"), entry.get("dose_upper_bound")
    ) and _value_matches(route_norm, entry.get("administration_route"))


def _med_fields(med: dict) -> tuple[Optional[str], Optional[str], Optional[str]]:
    return (
        med.get("medication") or med.get("name"),
        med.get("dose") or None,
        med.get("administration_route") or None,
    )


def classify_medication(
    medication: str,
    dose: Optional[str] = None,
    administration_route: Optional[str] = None,
    json_path: Path = JSON_PATH,
) -> Optional[str]:
    """Look up a single medication's emetogenicity classification.

    Returns one of "high", "moderate", "low", "minimal", or None if not found.
    Dose and administration_route are optional and used as tie-breakers when
    a medication has multiple entries with different dose/route bounds. Every
    fallback (unrecognized medication, ambiguous dose/route) is logged as a
    warning, and the final interpretation is always logged as info.
    """
    with open(json_path, "r") as f:
        data = json.load(f)

    med_name = _normalize(medication)
    dose_norm = _normalize_dose(dose)
    route_norm = _normalize(administration_route)

    matches = [
        (classification, entry)
        for classification, entries in data.items()
        for entry in entries
        if _normalize(entry.get("medication")) == med_name
    ]

    if not matches:
        logger.warning(
            "Medication '%s' not found in %s; returning no classification.",
            medication, json_path.name,
        )
        return None

    if len(matches) == 1:
        chosen = matches[0]
    else:
        candidates = [
            (classification, entry)
            for classification, entry in matches
            if _entry_compatible(dose_norm, route_norm, entry)
        ]
        if not candidates:
            logger.warning(
                "No entry for '%s' is compatible with dose=%r, route=%r; falling back to "
                "the highest-risk of %d known entries.",
                medication, dose, administration_route, len(matches),
            )
            candidates = matches

        # Among candidates, prefer one with an exact route match.
        exact_route = [
            (classification, entry)
            for classification, entry in candidates
            if route_norm and _normalize(entry.get("administration_route")) == route_norm
        ]
        candidates = exact_route or candidates

        # Tie-break: the highest-risk classification among remaining candidates.
        chosen = max(candidates, key=lambda m: CLASSIFICATION_ORDER.index(m[0]))

    classification, entry = chosen
    logger.info(
        "Interpreted '%s' (dose=%r, route=%r) as '%s' via entry (dose_lower_bound=%r, "
        "dose_upper_bound=%r, administration_route=%r).",
        medication, dose, administration_route, classification,
        entry.get("dose_lower_bound"), entry.get("dose_upper_bound"), entry.get("administration_route"),
    )
    return classification


def _combo_entry_matches(medications: list[dict], combo_medications: list[dict]) -> bool:
    """True if every component of `combo_medications` matches a distinct medication
    in `medications` (a subset match) — extra medications in the regimen are allowed.
    """
    if len(medications) < len(combo_medications):
        return False

    remaining = list(medications)
    for entry in combo_medications:
        combo_name = _normalize(entry.get("medication"))

        match_idx = next(
            (
                i
                for i, med in enumerate(remaining)
                if _normalize(_med_fields(med)[0]) == combo_name
                and _entry_compatible(
                    _normalize_dose(_med_fields(med)[1]), _normalize(_med_fields(med)[2]), entry
                )
            ),
            None,
        )
        if match_idx is None:
            return False
        remaining.pop(match_idx)
    return True


def classify_combination(
    medications: list[dict],
    json_path: Path = MULTI_JSON_PATH,
) -> Optional[str]:
    """Look up a regimen's classification in the multi-medication combination table.

    A regimen matches a combination entry if the entry's medications are a
    subset of the regimen (matching name, dose, and route per
    `_entry_compatible`) — extra, unrelated medications in the regimen are
    allowed. If multiple combination entries match (e.g. two different risky
    pairs within a larger regimen), the highest-risk one is returned.
    """
    with open(json_path, "r") as f:
        data = json.load(f)

    matches = [
        classification
        for classification, entries in data.items()
        for entry in entries
        if _combo_entry_matches(medications, entry["medications"])
    ]
    if not matches:
        return None

    result = max(matches, key=CLASSIFICATION_ORDER.index)
    logger.info(
        "Regimen contains %d known combination(s); using highest-risk combination "
        "classification '%s'.",
        len(matches), result,
    )
    return result


def _highest_single_classification(medications: list[dict], json_path: Path) -> Optional[str]:
    """Classify each medication individually and return the highest-risk result.

    Used when no multi-drug combination matches the regimen.
    """
    per_drug = []
    for med in medications:
        name, dose, route = _med_fields(med)
        per_drug.append((name, classify_medication(name, dose, route, json_path)))

    known = [c for _, c in per_drug if c is not None]
    if not known:
        logger.warning(
            "No multi-drug combination matched and none of the medications were recognized: %s",
            [name for name, _ in per_drug],
        )
        return None

    result = max(known, key=CLASSIFICATION_ORDER.index)
    logger.info(
        "No multi-drug combination matched; using the highest single-drug classification "
        "'%s' among %s.",
        result, per_drug,
    )
    return result


def classify_regimen(
    medications: list[dict],
    json_path: Path = JSON_PATH,
    multi_json_path: Path = MULTI_JSON_PATH,
):
    """Classify a list of medications.

    Each item in `medications` is a dict with keys:
      - "medication" (required)
      - "dose" (optional, may be blank/None)
      - "administration_route" (optional, may be blank/None)

    If more than one medication is given, the combination table is checked
    first (a subset match is enough; extra medications are ignored); a match
    there returns its classification directly (a single str). Otherwise,
    returns the highest-risk classification among the individual medications.

    A single medication returns a list of one dict with the original fields
    plus "classification", for parity with per-drug lookups elsewhere.
    """
    if len(medications) > 1:
        combo_classification = classify_combination(medications, multi_json_path)
        if combo_classification is not None:
            return combo_classification
        return _highest_single_classification(medications, json_path)

    results = []
    for med in medications:
        name, dose, route = _med_fields(med)
        classification = classify_medication(name, dose, route, json_path)
        results.append({**med, "classification": classification})
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    single = [
        {"medication": "Cisplatin", "dose": "", "administration_route": ""},
    ]
    print("single-drug regimen:", classify_regimen(single))

    # No known combo for this pair: falls back to the highest single-drug classification.
    no_combo_pair = [
        {"medication": "Cisplatin", "dose": "", "administration_route": ""},
        {"medication": "Etoposide", "dose": "", "administration_route": "oral"},
    ]
    print("non-combo pair (highest-single fallback):", classify_regimen(no_combo_pair))

    combo = [
        {"medication": "Cyclophosphamide", "dose": "", "administration_route": ""},
        {"medication": "doxorubicin", "dose": "", "administration_route": ""},
    ]
    print("combination regimen:", classify_regimen(combo))

    # Exact dose threshold shared by two buckets (high lower bound == moderate upper bound).
    print("Methotrexate @ 12 g/m2:", classify_medication("Methotrexate", dose="12 g/m2"))

    # Numeric threshold now resolves doses between known bounds correctly.
    print("Methotrexate @ 500 mg/m2:", classify_medication("Methotrexate", dose="500 mg/m2"))

    # Dose given in grams is converted to mg to compare against an mg-based bound (logs the conversion).
    print("Carmustine @ 0.5 g/m2:", classify_medication("Carmustine", dose="0.5 g/m2"))

    # Numeric thresholds correctly resolve doses below/above the 250 mg/m2 cutoff.
    print("Carmustine @ 100 mg/m2:", classify_medication("Carmustine", dose="100 mg/m2"))
    print("Carmustine @ 300 mg/m2:", classify_medication("Carmustine", dose="300 mg/m2"))
    # Large gram dose converts to mg and clearly exceeds the high threshold.
    print("Carmustine @ 3 g/m2:", classify_medication("Carmustine", dose="3 g/m2"))

    # Route differentiates buckets; an unconstrained (null-route) entry wins when no route is given.
    print("Busulfan, no route:", classify_medication("Busulfan"))

    # Specifying the matching route resolves to the route-specific entry.
    print("Busulfan, oral:", classify_medication("Busulfan", administration_route="oral"))

    # Superfluous/non-matching route falls back to the unconstrained entry instead of failing.
    print("Busulfan, bogus route:", classify_medication("Busulfan", administration_route="IV"))

    # Medication not found in either table.
    print("Unknown drug:", classify_medication("Not A Real Drug"))

    # Dose exactly at a gram-denominated threshold, expressed in different formats.
    print("Cyclophosphamide @ 1g/m2:", classify_medication("Cyclophosphamide", dose="1g/m2"))
    print("Cyclophosphamide @ 1000mg/m2:", classify_medication("Cyclophosphamide", dose="1000 mg/m2"))
    print("Cyclophosphamide @ 999mg/m2:", classify_medication("Cyclophosphamide", dose="999 mg/m2"))

    # Case- and asterisk-insensitive name matching.
    print("CISPLATIN (upper):", classify_medication("CISPLATIN"))
    print("*Cyclophosphamide @ 1g/m2:", classify_medication("*Cyclophosphamide", dose="1g/m2"))

    # Non-mass dose unit ("million units"): not numerically parseable, falls back to the single known entry.
    print("Aldesleukin, nonsense dose:", classify_medication("Aldesleukin", dose="not a real dose"))

    # Mixed-scale bounds (one bound is absolute "250 mg", the other is per-BSA "12 g/m2"): the
    # mismatched-scale bound is ignored rather than mis-compared, falling back cautiously.
    print("Methotrexate @ 10 mg/m2:", classify_medication("Methotrexate", dose="10 mg/m2"))

    # A single-entry medication ignores dose/route entirely, even if they look inconsistent.
    print("Cisplatin, bogus dose+route:", classify_medication("Cisplatin", dose="9999 mg", administration_route="nasal"))

    # Combination matching is order-independent.
    reversed_combo = [
        {"medication": "doxorubicin", "dose": "", "administration_route": ""},
        {"medication": "Cyclophosphamide", "dose": "", "administration_route": ""},
    ]
    print("reversed combination regimen:", classify_regimen(reversed_combo))

    # A known risky pair plus an unrelated third drug: the pair is still detected as a
    # subset of the regimen, so this now returns the combo classification directly.
    three_drug_with_hidden_combo = [
        {"medication": "Cyclophosphamide", "dose": "", "administration_route": ""},
        {"medication": "doxorubicin", "dose": "", "administration_route": ""},
        {"medication": "Vinorelbine", "dose": "", "administration_route": ""},
    ]
    print("3-drug regimen (hidden combo subset):", classify_regimen(three_drug_with_hidden_combo))

    # No known combo among these three: falls back to the highest single-drug classification.
    no_combo_regimen = [
        {"medication": "Cisplatin", "dose": "", "administration_route": ""},
        {"medication": "Etoposide", "dose": "", "administration_route": ""},
        {"medication": "Vinorelbine", "dose": "", "administration_route": ""},
    ]
    print("3-drug regimen (no combo, highest-single fallback):", classify_regimen(no_combo_regimen))

    # Unknown medication mixed into a known one: combo lookup fails, falls back to the
    # highest-risk among recognized medications (unrecognized ones are ignored, not fatal).
    unknown_in_regimen = [
        {"medication": "Cisplatin", "dose": "", "administration_route": ""},
        {"medication": "Not A Real Drug", "dose": "", "administration_route": ""},
    ]
    print("regimen with unknown drug:", classify_regimen(unknown_in_regimen))

    # All-unknown regimen: no combo, no recognized drugs — returns None rather than guessing.
    all_unknown_regimen = [
        {"medication": "Not A Real Drug", "dose": "", "administration_route": ""},
        {"medication": "Also Not Real", "dose": "", "administration_route": ""},
    ]
    print("regimen with all unknown drugs:", classify_regimen(all_unknown_regimen))

    # Empty regimen should not raise.
    print("empty regimen:", classify_regimen([]))

