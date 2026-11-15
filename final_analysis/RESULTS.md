# Final historical pressure-performance conclusions

The ordered lists below summarize the supplied 2022–2026 sample under an explicit, tested model. They are descriptive rankings with uncertainty; they do not establish psychological clutch ability or guaranteed future form. No PDF/PPT was created.

## Top 10 batters
Rank | Batter | Pressure balls | Pressure matches | Pressure runs | Pressure SR
---:|---|---:|---:|---:|---:
1 | Rajat Patidar | 158 | 22 | 256 | 162.0
2 | Shreyas Iyer | 323 | 37 | 568 | 175.9
3 | Nicholas Pooran | 330 | 39 | 527 | 159.7
4 | Ruturaj Gaikwad | 173 | 23 | 271 | 156.6
5 | Fakhar Zaman | 192 | 21 | 294 | 153.1
6 | Suryakumar Yadav | 516 | 60 | 816 | 158.1
7 | Riyan Parag | 344 | 37 | 541 | 157.3
8 | Tim David | 298 | 41 | 481 | 161.4
9 | Ayush Badoni | 252 | 32 | 342 | 135.7
10 | Glenn Phillips | 200 | 21 | 244 | 122.0

## Top 10 bowlers
Rank | Bowler | Pressure legal balls | Pressure matches | Pressure wickets | Pressure economy
---:|---|---:|---:|---:|---:
1 | Kuldeep Yadav | 324 | 43 | 28 | 6.35
2 | Mustafizur Rahman | 374 | 39 | 29 | 6.48
3 | Sunil Narine | 309 | 32 | 17 | 5.55
4 | Abrar Ahmed | 195 | 19 | 13 | 5.02
5 | Matheesha Pathirana | 215 | 24 | 18 | 7.20
6 | Wanindu Hasaranga | 261 | 34 | 23 | 6.92
7 | Lockie Ferguson | 211 | 24 | 15 | 6.94
8 | Varun Chakravarthy | 510 | 55 | 30 | 6.68
9 | Josh Hazlewood | 359 | 42 | 24 | 7.84
10 | Shaheen Afridi | 181 | 23 | 17 | 7.66

Ordering uses adjusted impact, individual-baseline comparison, shrinkage, match-level uncertainty and consensus across 13 specifications. SR/economy shown here are descriptive; they alone do not determine the order. Pressure is the top fifth of raw before-ball tension within format/innings/phase, allowing fairer role coverage. Minimum samples: 500 total units, 120 pressure units, 250 ordinary units, 10 pressure matches, two seasons.

## Whole-project summary
1. Inspected the competition statement and six source CSVs. Preserved originals; cleaned types/missing values, reconciled conflicting XI keys and joined by validated IDs without multiplying delivery rows.
2. Identified missing extras amounts. Supplemented scoring from strictly matched Cricsheet innings while keeping the supplied players/performances as the population. Reconstructed scores, wickets, legal balls, targets and required rates before each event. Ten official sample innings reconciled.
3. Kept 166,227 accepted standard IPL/T20I delivery events across 715 matches. Excluded unresolved contexts, revisions/shortened matches, unusual innings and out-of-scope competitions. Calibrated pressure within innings phase; 33,252 events are high relative pressure.
4. Measured batting runs minus dismissal cost and bowling wickets versus runs conceded; attributed non-striker run-outs to the dismissed player, and excluded byes/leg-byes from bowlers' conceded runs. Estimated peer expectations from five held-out whole-match folds, adjusting for format, innings, phase, year, role, opponent, venue, wickets and chase demand with sparse-group shrinkage.
5. Compared adjusted pressure performance with each player's ordinary performance. Applied sample-size shrinkage and a match-cluster uncertainty penalty. Ranked 70 eligible batters and 78 bowlers by consensus across 13 prespecified variants, with 1,000 whole-match bootstrap resamples and season/format checks.

## Strength of evidence
Rajat Patidar, Shreyas Iyer and Nicholas Pooran appear in the batting top10 in 12 of 13 specifications. Kuldeep Yadav, Mustafizur Rahman, Sunil Narine and Abrar Ahmed appear in the bowling top10 in every specification. Adjacent positions and lower-list membership are less stable; inspect scenario and bootstrap columns rather than treating the exact order as certain.

## Historical 2026 validation — a material limit
- Batter: earlier-period vs 2026 rank correlation -0.374 across 28 comparable players. Pre-2026 top10 pressure residual in 2026: -0.247 per unit versus 0.288 for other training-eligible players.
- Bowler: earlier-period vs 2026 rank correlation -0.039 across 29 comparable players. Pre-2026 top10 pressure residual in 2026: 0.082 per unit versus 0.004 for other training-eligible players.

The batting training shortlist underperformed its comparison group in 2026, and bowling rank persistence was near zero. These findings do not support strong predictive claims for IPL 2027. Final rankings use all available historical evidence; no specification was tuned to hide this unfavorable validation. Missing context and selected sample coverage remain additional limitations.

## Rajasthan Royals use
Observed-role profiles are in rr_role_fit.csv. Riyan Parag is already listed in RR's official published 2026 squad: https://www.rajasthanroyals.com/rr-players . The ranking can inform role discussions, including middle-order batting, finishing, wicket-taking spin and late-over pace. Actual releases, auction eligibility/availability, price, overseas slots and existing-squad needs were not established by this statistical analysis. In particular, T20I-only players in these lists must not be represented as confirmed IPL auction options.

The main analysis is complete. Final deliverables are CSV/JSON/Markdown and a ZIP; no report was submitted to Unstop. See METHODOLOGY_AND_CONCLUSIONS.md for formulas and final_summary.json for machine-readable results. Cricsheet supplementary-data attribution and original license notices are included.
