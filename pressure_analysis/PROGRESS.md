# Analysis progress — 14 November 2026

Completed three stages: validated scoring fields; reconstructed before-delivery state where reference alignment passed; implemented and inspected pressure v1.

- Source delivery rows preserved: 200,999.
- Accepted context: 171,367 deliveries (85.3%), 750 matches with at least one accepted innings.
- Pressure-eligible: 166,227 deliveries, 715 matches.
- High pressure at score >=55: 10,163 deliveries (6.1% of eligible).
- Independent official innings checks: 10/10 passed.
- Rankings, player-performance scoring, RR role-fit and final PDF/PPT remain outstanding.

Start with METHODOLOGY.md and coverage_and_exclusions.csv, then use pressure_eligible_v1 in deliveries_with_context_pressure_v1.csv. This is an intermediate analysis package, not a final competition submission.

## Pressure calibration finding
The current common cutoff labels 10.15% of eligible first-innings events and 1.64% of chase events as high pressure. These formulas are not on a calibrated common scale. This is a material modeling limitation: do not pool the two high-pressure samples into final player rankings. Next compare within innings/phase/format and test alternative pressure components/calibration before selecting players. Threshold sensitivity alone does not resolve this difference.
