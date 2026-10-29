"""Declared serving targets for UC3."""

from __future__ import annotations

from typing import List

from config.settings import settings
from shared.contracts import DataProductSpec, UseCase

UC = UseCase.AIMESIS

CHEMO_EMETOGENICITY_MATRIX = DataProductSpec(
    name="chemo_emetogenicity_matrix",
    use_case=UC,
    kind="bigquery_table",
    description=(
        "One row per named regimen with its component drugs and per-day "
        "emetogenic tier. Deterministic classification of an oncologist's order."
    ),
    partition_field="computed_at",
    clustering=["regimen_id", "emetogenic_tier"],
    schema=[
        {"name": "regimen_id", "type": "STRING", "mode": "REQUIRED", "description": "Regimen acronym, e.g. COJEC"},
        {"name": "full_name", "type": "STRING", "mode": "NULLABLE", "description": "Expanded regimen name"},
        {"name": "indication", "type": "STRING", "mode": "NULLABLE", "description": "Tumour type / protocol context"},
        {"name": "cycle_length_days", "type": "INTEGER", "mode": "NULLABLE", "description": "Cycle length"},
        {"name": "drug_combination", "type": "STRING", "mode": "REPEATED", "description": "Component cytotoxic drugs"},
        {"name": "emetogenic_tier", "type": "STRING", "mode": "REQUIRED", "description": "Peak tier: high|moderate|low|minimal"},
        {"name": "day_risks", "type": "JSON", "mode": "NULLABLE", "description": "Per-day tier, contributing drugs and rationale"},
        {"name": "escalated", "type": "BOOLEAN", "mode": "NULLABLE", "description": "Combination rule raised the tier"},
        {"name": "source", "type": "STRING", "mode": "NULLABLE", "description": "Protocol the regimen definition came from"},
        {"name": "source_url", "type": "STRING", "mode": "REQUIRED", "description": "Citable URL"},
        {"name": "computed_at", "type": "TIMESTAMP", "mode": "REQUIRED", "description": "Classification timestamp"},
    ],
)

DDI_QTC_RISK_CATALOG = DataProductSpec(
    name="ddi_qtc_risk_catalog",
    use_case=UC,
    kind="bigquery_table",
    description=(
        "Pairwise CYP and additive-QTc interaction alerts with an explicit "
        "clinical action. Drives polypharmacy contraindication warnings."
    ),
    partition_field="computed_at",
    clustering=["severity", "kind", "drug_a"],
    schema=[
        {"name": "drug_a", "type": "STRING", "mode": "REQUIRED", "description": "First agent"},
        {"name": "drug_b", "type": "STRING", "mode": "REQUIRED", "description": "Second agent"},
        {"name": "kind", "type": "STRING", "mode": "REQUIRED", "description": "cyp | qtc"},
        {"name": "cyp_pathway", "type": "STRING", "mode": "NULLABLE", "description": "Enzyme, e.g. CYP3A4"},
        {"name": "mechanism", "type": "STRING", "mode": "REQUIRED", "description": "Why the interaction occurs"},
        {"name": "severity", "type": "STRING", "mode": "REQUIRED", "description": "contraindicated|major|moderate|minor"},
        {"name": "clinical_action", "type": "STRING", "mode": "REQUIRED", "description": "What the clinician should do"},
        {"name": "evidence", "type": "STRING", "mode": "NULLABLE", "description": "Citation supporting the rule"},
        {"name": "computed_at", "type": "TIMESTAMP", "mode": "REQUIRED", "description": "When the rule was materialised"},
    ],
)

QTC_RISK_REFERENCE = DataProductSpec(
    name="qtc_risk_reference",
    use_case=UC,
    kind="bigquery_table",
    description=(
        "Per-drug QT/TdP risk category. NOTE: sourced from licensed "
        "CredibleMeds content in production; the `synthetic` flag marks "
        "demonstration rows that must never be used clinically."
    ),
    clustering=["risk_category"],
    schema=[
        {"name": "drug", "type": "STRING", "mode": "REQUIRED", "description": "Normalised drug name"},
        {"name": "risk_category", "type": "STRING", "mode": "REQUIRED", "description": "known|possible|conditional|avoid_clqts"},
        {"name": "route_note", "type": "STRING", "mode": "NULLABLE", "description": "Route or dose dependence"},
        {"name": "synthetic", "type": "BOOLEAN", "mode": "REQUIRED", "description": "TRUE for demonstration data, not licensed content"},
        {"name": "licence", "type": "STRING", "mode": "REQUIRED", "description": "Redistribution licence; UNKNOWN means do not redistribute"},
    ],
)

FAERS_SIGNAL_SUMMARY = DataProductSpec(
    name="faers_signal_summary",
    use_case=UC,
    kind="bigquery_table",
    description=(
        "FAERS spontaneous report counts. SIGNAL ONLY -- no denominator, no "
        "verification. Must never be rendered as an incidence rate."
    ),
    clustering=["reaction"],
    schema=[
        {"name": "reaction", "type": "STRING", "mode": "REQUIRED", "description": "MedDRA preferred term"},
        {"name": "report_count", "type": "INTEGER", "mode": "REQUIRED", "description": "Spontaneous reports, NOT a rate"},
        {"name": "signal_only", "type": "BOOLEAN", "mode": "REQUIRED", "description": "Always TRUE; guards downstream rendering"},
        {"name": "caveat", "type": "STRING", "mode": "REQUIRED", "description": "Interpretation warning shown with any display"},
    ],
)

CINV_GUIDELINES_INDEX = DataProductSpec(
    name="cinv_pediatric_guidelines",
    use_case=UC,
    kind="vertex_index",
    description=(
        "Vectorised guideline narrative, for source-grounded explanations of "
        "why a given antiemetic regimen was recommended."
    ),
    options={
        "dimensions": settings.embedding_dim,
        "distance_measure": "COSINE_DISTANCE",
        "algorithm": "TREE_AH",
        "embedding_model": settings.embedding_model,
        "filterable_fields": ["guideline_id", "issuer", "section", "chunk_level"],
    },
)

ALL_PRODUCTS: List[DataProductSpec] = [
    CHEMO_EMETOGENICITY_MATRIX,
    DDI_QTC_RISK_CATALOG,
    QTC_RISK_REFERENCE,
    FAERS_SIGNAL_SUMMARY,
    CINV_GUIDELINES_INDEX,
]
