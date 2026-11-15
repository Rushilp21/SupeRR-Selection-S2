# Pressure analysis v1: completed stages and methodology

## Scope
This package completes scoring validation, before-delivery context reconstruction, and an initial explainable pressure definition. It does not contain final player ratings or auction recommendations. Original cleaned data and source fields are unchanged. All 200,999 supplied delivery rows remain in the main file.

The supplied submission screenshot asks for a PDF/PPT or dashboard explaining methodology, reliable players and how each could strengthen Rajasthan Royals for IPL 2027. Final player-role fit and auction availability must be researched later. No current RR squad or auction availability has been assumed.

## Stage 1: scoring validation
The source runs column agrees with Cricsheet batter runs in accepted innings. extras1_runs is a category code, not a run amount; extras_2_runs is not sufficient to reconstruct complete extras. Example: source match 13511 has 100 batting runs versus England's official 103 and 99 batting runs versus West Indies' official 104. Adding one per extras event would still give only 101 for the chase, showing that a default one-run imputation is wrong.

Downloaded Cricsheet IPL and men's T20I JSON archives provide supplementary scoring context. No reference-only match or player is added to the analysis population. Each accepted innings must have a unique exact-date/team-pair match, identical full-innings delivery count, batting team, batter-run sequence, over sequence and within-over delivery sequence. Source player IDs must map consistently to reference registry people within each innings and against the global modal crosswalk. Any innings failing these checks is left unverified; no approximate alignment or run correction is forced. Crosswalks and match-level decisions are in audit/. Reference name spellings are separate from source IDs/names. Multiple source IDs for one reference person, if found, are flagged rather than merged.

171,367 deliveries in 1,465 innings pass the context linkage (85.3% of all supplied deliveries). Ten innings in the five-match January 2022 England–West Indies series independently reconcile to the official Windies Cricket scoreboard for total, wickets and legal balls. This small independent check is not proof that every linked innings is error-free.

Revised-overs values are compared to reference quotas in audit/revised_limit_checks.csv. They are not universally converted from an undocumented field. Context uses reference recorded quotas, with source raw values preserved. All shortened or revised matches are excluded from pressure v1 because the time when a revision became known is not supplied. Public Cricsheet coverage is incomplete (including some Afghanistan matches); exclusion coverage must be considered in final ratings.

## Stage 2: reconstruct state BEFORE every delivery
- score_before is the sum of earlier reference team runs, plus a pre-innings penalty if recorded. Never includes the current delivery.
- wickets_before counts earlier team wickets; retired hurt/not-out is excluded. Known bowler-credit dismissal kinds are tracked separately from team wickets.
- legal_balls_before excludes reference wides/no-balls and excludes the current delivery. innings_ball_num is an event counter, not a legal-ball count.
- balls_remaining_before = recorded quota minus prior legal balls. Regular full T20 quota is 120; extra innings and unusual quotas remain present but are excluded from pressure v1.
- Second-innings target is the explicit reference target, otherwise reference first-innings total + 1. runs_required_before = target - score_before. Required run rate = 6 * runs_required_before / balls_remaining_before.
- current run rate = 6 * score_before / legal_balls_before, undefined before the first legal ball.
- powerplay/middle/death labels are <36, 36–89, >=90 prior legal balls. These fixed labels are intended for full T20 innings.

For rejected reference links, derived score/state fields are blank. They are not replaced by zero. Future final result, winner, player-of-match, the current delivery's runs/wicket and final innings total are never direct pressure-score inputs. Final first-innings total is a legitimate known target only once the chase begins. Reference target/overs fields can reflect later DLS revisions, so all revised/shortened games are excluded from pressure v1.

## Stage 3: pressure definition v1
Pressure is an explicit heuristic 0–100 index, NOT a calibrated probability, causal psychological measure, player-performance rating or final selection rule. We use the same match-level label for batter and bowler to measure performance in a demanding shared contest. First-innings and chase scores have different formulas and have not yet been calibrated to a common scale; later player comparisons must stratify by innings/phase rather than blindly pooling them.

Only accepted IPL/T20I context, innings 1/2, standard unrevised quotas, no miscounted-over/innings-penalty adjustments and nonterminal before-ball states receive a score. Other T20, super overs and unverified states are retained but excluded. Eligible deliveries: 166,227 across 715 matches.

Definitions:
- progress = prior legal balls / 120. Lateness L = progress squared.
- Wicket stress W = min(wickets_before/8, 1).
- Prior par rate P is computed separately for IPL/T20I from accepted standard FIRST innings on strictly earlier dates. Add 2,400 pseudo-balls at 8 rpo as an initial regularizing prior. All matches on the same date and all future dates are excluded. This is a broad format baseline, not a venue/opponent-adjusted expectation.
- K = source knockout flag, known from the scheduled fixture.

First innings:
After at least 12 legal balls, deficit D = clip((P-current_rpo)/4, 0, 1); otherwise D=0.
pressure = clip(35*L + 35*W + 20*D + 10*K, 0, 100).
This emphasizes late resource scarcity and scoring below a prior environment. It is imperfect for fast-scoring first innings with many wickets in hand; that sensitivity must be tested before final ratings.

Chase:
q = required_rpo / P.
Competitive tension C = exp(-((q-1)/0.75)^2).
Scoring load R = clip(q/2, 0, 1).
pressure = C*(45*L + 30*R + 15*W + 10*K).
The tension term downweights very easy chases and extremely demanding required rates, instead of treating a nearly lost chase as automatically the highest pressure. This is a modeling judgment, not evidence that a chase is literally unwinnable. It can underweight early huge-target chases and must be compared with alternative definitions.

Bands: high >=55, moderate >=35 and <55, ordinary <35. These thresholds and weights are starting assumptions, not fitted to famous players or chosen to force a desired top 10. Sensitivity at high thresholds 45, 50, 55, 60 and 65 is exported. Weight/formula sensitivity, innings comparability, player-ranking stability and predictive validity remain future work. 10,163 deliveries are high pressure at 55 (6.1% of eligible events).

## Outputs and next use
- deliveries_with_context_pressure_v1.csv: main file; extends the 100-column joined CSV with provenance, scoring context, quality gates and pressure components. Use pressure_eligible_v1 before modeling.
- pressure_distribution.csv and coverage_and_exclusions.csv: denominators, exclusions and high/moderate/ordinary counts.
- pressure_threshold_sensitivity.csv: changes in exposure when the high cutoff changes.
- player_pressure_exposure.csv: qualifying deliveries, legal deliveries and match/season coverage per player/format. These are exposure counts, not performance rankings. A wide is an exposure event but not a legal ball; do not use event count as an economy denominator.
- pressure_examples.csv: before-state examples from each pressure band/innings.
- historical_scoring_priors.csv: prior-only environment values by date and format.
- data_dictionary.csv: provenance/type/blank count for each column; original column detail remains in the previous cleaning package.
- audit/: rejected links, reference player crosswalk, wicket disagreements, innings totals, extras-category comparison and official validation checks.
- source_manifest.json: reference URLs and content hashes. External extras and legality are attributed to Cricsheet. Check competition external-data permissions before final submission; the PDF supplied here does not specify an external-data rule.

## Remaining work
1. Review coverage bias, rejected innings and duplicate-person IDs. Resolve or explicitly justify exclusions; obtain missing provider scoring data where possible. Check external-data terms for the competition.
2. Define fair batting/bowling performance metrics with correct denominators and dismissal attribution. Establish phase/innings/format/opposition baselines and minimum exposure; shrink small samples.
3. Validate pressure alternatives and player-rating stability across seasons, matches, thresholds and holdouts. Estimate uncertainty and consistency; avoid turning exposure count into merit.
4. Rank the top 10 batters and top 10 bowlers with supporting evidence.
5. Research RR squad needs, roles, overseas constraints and actual IPL 2027 auction eligibility/availability. A statistical top-10 player need not be an available auction target. Separate performance ranking from acquisition recommendations.
6. Assemble and render-check the submission PDF/PPT, matching the Unstop dropdown rankings; optional dashboard link and journey content are separate.

## Sources
- Primary: supplied cleaned_competition_data/deliveries_joined.csv and its source archive.
- Cricsheet downloads: https://cricsheet.org/downloads/ ; JSON definitions: https://cricsheet.org/format/json/ ; licensing: https://cricsheet.org/licensing/ . Supplementary scoring fields are modified/combined into this analysis; supplied source data remains separately attributed to the competition.
- Independent scoreboard: https://www.windiescricket.com/series/england-in-west-indies-2021-22-16230/

Reproducibility: build_pressure_context.py, cached original reference archives, input checksum and archive checksums are retained locally. No originals overwritten. Scripts/reference ZIPs are excluded from the compact results ZIP but remain in the workspace.

## Pressure calibration finding
The current common cutoff labels 10.15% of eligible first-innings events and 1.64% of chase events as high pressure. These formulas are not on a calibrated common scale. This is a material modeling limitation: do not pool the two high-pressure samples into final player rankings. Next compare within innings/phase/format and test alternative pressure components/calibration before selecting players. Threshold sensitivity alone does not resolve this difference.
