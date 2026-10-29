-- UC3 AImesis -- BigQuery schema (EU multi-region, europe-west1 processing)
--
-- Two governance properties are enforced in the schema itself rather than
-- left to application discipline:
--   1. FAERS counts carry a mandatory `signal_only` flag and a caveat string,
--      so no dashboard can render a spontaneous report count as an incidence
--      rate without carrying the warning with it.
--   2. QTc reference rows carry a `synthetic` flag, so demonstration data can
--      never be silently mistaken for licensed CredibleMeds content.

CREATE SCHEMA IF NOT EXISTS uc3_aimesis
  OPTIONS (location = 'EU', description = 'AImesis paediatric CINV data products');

-- ---------------------------------------------------------------------------
-- Regimen emetogenicity
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS uc3_aimesis.chemo_emetogenicity_matrix (
    regimen_id        STRING    NOT NULL OPTIONS (description = 'Regimen acronym, e.g. COJEC'),
    full_name         STRING             OPTIONS (description = 'Expanded regimen name'),
    indication        STRING             OPTIONS (description = 'Tumour type / protocol context'),
    cycle_length_days INT64              OPTIONS (description = 'Cycle length in days'),
    drug_combination  ARRAY<STRING>      OPTIONS (description = 'Component cytotoxic drugs'),
    emetogenic_tier   STRING    NOT NULL OPTIONS (description = 'Peak tier across the cycle'),
    day_risks         JSON               OPTIONS (description = 'Per-day tier, drugs and rationale'),
    escalated         BOOL               OPTIONS (description = 'Combination rule raised the tier'),
    source            STRING             OPTIONS (description = 'Protocol defining the regimen'),
    source_url        STRING    NOT NULL OPTIONS (description = 'Citable URL'),
    computed_at       TIMESTAMP NOT NULL OPTIONS (description = 'Classification timestamp')
)
PARTITION BY DATE(computed_at)
CLUSTER BY regimen_id, emetogenic_tier
OPTIONS (description = 'Deterministic emetogenic classification of named paediatric regimens.');

-- ---------------------------------------------------------------------------
-- Interaction alerts
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS uc3_aimesis.ddi_qtc_risk_catalog (
    drug_a          STRING    NOT NULL OPTIONS (description = 'First agent'),
    drug_b          STRING    NOT NULL OPTIONS (description = 'Second agent'),
    kind            STRING    NOT NULL OPTIONS (description = 'cyp | qtc'),
    cyp_pathway     STRING             OPTIONS (description = 'Enzyme, e.g. CYP3A4'),
    mechanism       STRING    NOT NULL OPTIONS (description = 'Why the interaction occurs'),
    severity        STRING    NOT NULL OPTIONS (description = 'contraindicated|major|moderate|minor'),
    clinical_action STRING    NOT NULL OPTIONS (description = 'What the clinician should do'),
    evidence        STRING             OPTIONS (description = 'Citation supporting the rule'),
    computed_at     TIMESTAMP NOT NULL OPTIONS (description = 'Materialisation timestamp')
)
PARTITION BY DATE(computed_at)
CLUSTER BY severity, kind, drug_a
OPTIONS (description = 'Pairwise CYP and additive-QTc alerts with explicit clinical actions.');

-- ---------------------------------------------------------------------------
-- QTc reference (licence-sensitive)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS uc3_aimesis.qtc_risk_reference (
    drug          STRING NOT NULL OPTIONS (description = 'Normalised drug name'),
    risk_category STRING NOT NULL OPTIONS (description = 'known|possible|conditional|avoid_clqts'),
    route_note    STRING          OPTIONS (description = 'Route or dose dependence'),
    -- TRUE means demonstration data. Never clinical.
    synthetic     BOOL   NOT NULL OPTIONS (description = 'TRUE for demo data, not licensed content'),
    licence       STRING NOT NULL OPTIONS (description = 'UNKNOWN means do not redistribute')
)
CLUSTER BY risk_category
OPTIONS (description = 'Per-drug QT/TdP risk. Licensed content in production; check `synthetic`.');

-- ---------------------------------------------------------------------------
-- FAERS signals
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS uc3_aimesis.faers_signal_summary (
    reaction     STRING NOT NULL OPTIONS (description = 'MedDRA preferred term'),
    report_count INT64  NOT NULL OPTIONS (description = 'Spontaneous report count, NOT a rate'),
    signal_only  BOOL   NOT NULL OPTIONS (description = 'Always TRUE; guards rendering'),
    caveat       STRING NOT NULL OPTIONS (description = 'Interpretation warning')
)
CLUSTER BY reaction
OPTIONS (description = 'FAERS spontaneous reports. No denominator. Never an incidence rate.');

-- ---------------------------------------------------------------------------
-- Safety view: only alerts a clinician must act on
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW uc3_aimesis.v_actionable_alerts AS
SELECT
    drug_a, drug_b, kind, cyp_pathway, mechanism, severity, clinical_action, evidence
FROM uc3_aimesis.ddi_qtc_risk_catalog
WHERE severity IN ('contraindicated', 'major')
ORDER BY
    CASE severity WHEN 'contraindicated' THEN 0 ELSE 1 END,
    drug_a;
