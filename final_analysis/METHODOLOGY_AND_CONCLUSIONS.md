# Final player analysis — 14 November 2026

## What was analyzed
Supplied IPL/T20I data from 2022-01-22 to 2026-11-01. Primary population remains the supplied data; Cricsheet supplementary extras/legality/targets were previously matched with strict innings/identity checks. Of 200,999 supplied delivery events, 166,227 from 715 matches have accepted standard-game context. Missing/unverified contexts, revised games and super overs remain excluded. No PDF or PPT was made.

## Pressure calibration
The initial raw pressure score overselected first innings. We now label high RELATIVE pressure at the top 20% within each competition group × innings × phase (12 cells). This compares openers with openers and death situations with death situations; it does not claim powerplay pressure and death pressure are psychologically identical. The underlying raw scores use pre-delivery resources, scoring difficulty and knockout context. No current ball result or final match winner is a pressure input. Empirical percentile calibration uses the retrospective context distribution across the analysis period, not a real-time forecasting claim. Independent 2026 checks use only earlier calibration data. High events: 33,252 (20.0%).

## Outcomes and attribution
Batting utility = batter runs - 12 × individual dismissals. Every dismissal is allocated to its named reference player; non-striker run-outs have zero faced-ball exposure but still carry their actual dismissal cost. Retired hurt/not-out is excluded; retired out/obstruction retained as individual dismissals. Batting exposure is non-wide deliveries, including no-balls; wide dismissals count without a ball-faced denominator. Batting strike rate in descriptive output uses that convention.
Bowling utility = 12 × bowler-credited wickets - bowler runs conceded. Bowler runs = batter runs + wides + no-ball penalties, excluding byes, leg-byes and penalty runs. Bowler exposure is legal balls; illegal delivery costs and any credited wickets remain in totals. Economy uses legal balls. Run-outs/retirements/obstruction do not count as bowler wickets.

## Fair peer expectations
We estimate run and dismissal rates separately, without player ID or final results as predictors. Whole matches are assigned to five deterministic folds. Each delivery receives expectations trained on other folds only. Hierarchical groups: format/innings/phase; then year; then batting-order band (or bowling family); then opponent team, venue country, wickets band and chase-demand band. Sparse child groups shrink toward their parent with 600, 300 and 150 exposure-unit pseudo-counts. Expected outcome = expected per-unit rate × delivery exposure. This is a transparent peer-rate model, not a causal estimate; opponent and venue adjustments are incomplete, especially for sparse opponents. Out-of-fold predictions are exported.

## Player score and reliability
For each player, context-adjusted high-pressure impact h = total high-pressure utility residual/(high units+150). Usual impact u = normal-pressure residual/(normal units+300). The primary score per 100 exposure units is 100×[h - 0.2u - 0.5SE(h)]. Thus the underlying performance term is 80% absolute adjusted pressure performance plus 20% uplift from usual performance; the uncertainty term penalizes inconsistent/small samples. SE uses whole-match clusters. Positive match/season shares are separately exported, not silently treated as guarantees.

Eligibility was fixed before viewing ranking names: >=500 total units, >=120 high units, >=250 ordinary units, >=10 high-pressure matches and >=2 high-pressure calendar seasons. The same count rules apply to faced balls for batting and legal deliveries for bowling. Eligible pool: 70 batters and 78 bowlers. This deliberately excludes exciting small samples; exclusion is not evidence of poor ability.

## Final order and sensitivity
The final order is equal-weight mean rank across 13 predeclared scenarios: primary; top25/top15/top10 pressure fractions; dismissal value 8/16; shrinkage 75/300; usual-uplift weight 0/0.4; removing chase-closeness downweighting; alternative pressure-component weights; and 0.85-per-year recency weighting. Scenario ranks use the fixed primary candidate pool, requiring >=50 high units and >=5 high matches per scenario or assigning an unsupported worst rank. Consensus index rescales mean rank to 0–100 relative to eligible peers; it is not a win probability or a universal skill score. Exact neighboring positions can be uncertain.

1,000 whole-match bootstrap resamples estimate primary-score intervals and primary top10 inclusion frequency, with models/calibration/candidate pool and uncertainty penalty fixed. These are conditional sample-uncertainty intervals, not complete model-uncertainty intervals. They concern the primary score; the final consensus rank can differ. Scenario top10 frequency is the fraction of specifications selecting a player; it is not a probability of being objectively top10.

## Historical validation
For a separate 2026 check, all outcome baselines and pressure thresholds are refit using 2022–2025 only. Training primary top10 selections are then compared with other training-eligible players on 2026 context-adjusted pressure impact. Rank correlation uses eligible players with >=30 pressure units in 2026. This checks historical persistence and can expose weak predictiveness; it is not a promise about IPL 2027. Results are in holdout_validation.json, including unfavorable results where present. Final lists use all years and consensus specifications, not just this historical training list.

## Rajasthan Royals interpretation
rr_role_fit.csv describes each selected player's observed batting position or bowling phase/style as a possible RR contribution. It does not assume the player is released, eligible, available, affordable, an overseas-slot fit or an unmet need in the current RR squad. Performance rankings and a purchasable auction shortlist are separate decisions. No unsupported current squad claim is made.

## Limitations and conclusions
Rankings are dataset- and method-dependent. Coverage excludes some Afghanistan matches and other provider/reference conflicts; player_source_coverage.csv exposes each player's source inclusion share. Missing context can bias comparisons. No domestic leagues beyond supplied IPL/T20I are added. Venue/opponent shrinkage cannot fully remove competition-strength effects. Pressure is operationally defined, not directly observed psychology. Participation, age, injury and auction availability are not assessed as rating inputs. Final conclusions are evidence-based historical selections, with uncertainty and sensitivity supplied for review.

## Files
top10_batters.csv and top10_bowlers.csv are the ordered conclusions. All-player ratings, scenario rankings, season/format/match evidence, bootstraps, 2026 diagnostics, calibration and coverage are included. final_summary.json contains key results. No report upload or dropdown submission has been made.

Sources: supplied competition CSVs; prior verified context and audit package; Cricsheet https://cricsheet.org/ (ODC-By v1.0, https://opendatacommons.org/licenses/by/1-0/). Supplementary records have been transformed/combined; original license notices preserved. No external reputation ranking was used to choose names.
