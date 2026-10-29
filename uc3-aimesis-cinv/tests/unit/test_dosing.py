"""Phase 3 deterministic dosing unit tests (`tests/unit/test_dosing.py`)."""

from __future__ import annotations

import math
from types import SimpleNamespace

from app.dosing import bsa_mosteller, compute_antiemetic_doses


def _fake_ctx() -> SimpleNamespace:
    return SimpleNamespace(state={})


def test_bsa_mosteller_24kg_120cm() -> None:
    """BSA for 24 kg / 120 cm is 0.894 m²."""
    assert bsa_mosteller(120.0, 24.0) == 0.894


def test_ondansetron_po_caps_at_8mg_and_volume_step() -> None:
    """Ondansetron PO for 150 kg / 200 cm caps at 8.0 mg and volume_ml is a multiple of step_ml."""
    ctx = _fake_ctx()
    res = compute_antiemetic_doses(
        antiemetics=["ondansetron"],
        weight_kg=150.0,
        height_cm=200.0,
        route="PO",
        tool_context=ctx,
    )
    assert len(res["doses"]) == 1
    row = res["doses"][0]
    assert row["dose_mg"] == 8.0
    assert row["capped"] is True
    assert math.isclose(row["volume_ml"] % row["step_ml"], 0.0, abs_tol=1e-6)
    assert ctx.state["facts_doses"] == res


def test_aprepitant_d1_and_d2_d3_and_volume_steps() -> None:
    """Aprepitant gives a D1 and a D2-D3 row and every volume_ml is a multiple of step_ml."""
    ctx = _fake_ctx()
    res = compute_antiemetic_doses(
        antiemetics=["ondansetron", "aprepitant", "dexamethasone", "olanzapine"],
        weight_kg=18.9,
        height_cm=110.0,
        route="PO",
        tool_context=ctx,
        indication="solid_tumor",
        age_years=5.0,
    )
    aprep_rows = [r for r in res["doses"] if r["drug"] == "aprepitant"]
    assert [r["days"] for r in aprep_rows] == ["D1", "D2-D3"]

    # Olanzapine 18.9 kg * 0.1 = 1.89 mg -> rounded DOWN to nearest 0.5 mg = 1.5 mg
    olanz_rows = [r for r in res["doses"] if r["drug"] == "olanzapine"]
    assert len(olanz_rows) == 1
    assert olanz_rows[0]["dose_mg"] == 1.5

    for r in res["doses"]:
        if "volume_ml" in r and "step_ml" in r:
            rem = round(r["volume_ml"] / r["step_ml"]) * r["step_ml"]
            assert math.isclose(r["volume_ml"], rem, abs_tol=1e-6)


def test_casus_2_all_blocks_dexamethasone() -> None:
    """Casus 2 (2 y, ALL) never contains an active dexamethasone dose ('GEEN Dexamethasone')."""
    ctx = _fake_ctx()
    res = compute_antiemetic_doses(
        antiemetics=["ondansetron", "aprepitant", "dexamethasone"],
        weight_kg=12.5,
        height_cm=88.0,
        route="PO",
        tool_context=ctx,
        indication="ALLTogether1 Induction B (ALL)",
        age_years=2.0,
    )
    assert res["dexamethasone_contraindicated"] is True
    dexa_rows = [r for r in res["doses"] if r["drug"] == "dexamethasone"]
    assert len(dexa_rows) == 1
    assert dexa_rows[0]["dose_mg"] is None
    assert dexa_rows[0]["blocked"] is True
    assert "GEEN DEXAMETHASONE" in dexa_rows[0]["note"]
