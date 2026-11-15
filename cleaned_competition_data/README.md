# Cleaned competition data

Start with `deliveries_joined.csv`: 200,999 rows, 100 columns. One row per supplied delivery, sorted by match/innings/innings_ball_num. Includes all match and competition columns, both team names, role-specific XI fields and roster membership flags. Historical result/winner/man_of_the_match are included as metadata; do not use them to define pressure before a ball.

## Files
- deliveries_clean.csv: cleaned delivery source plus conservative quality flags.
- deliveries_joined.csv: main combined table; no filtering of competitions or super-over innings.
- matches_clean.csv: all 883 matches, including 16 abandoned matches with no delivery data.
- playing_eleven_clean.csv: one match/team/player row, not necessarily an actual appearance. Use is_played and account for impact-player records.
- players_clean.csv: player-ID lookup built from supplied names and referenced identifiers. Name aliases and shared-name flags included. Players with the same name but different IDs are never merged.
- competitions_clean.csv, teams_clean.csv, competition_team_player_mapping_clean.csv: normalized supporting dimensions.
- data_dictionary.csv: columns, data types, row grain, blank counts and descriptions for each output table. CSV cannot preserve physical pandas types; use this dictionary when reading IDs as nullable integers and flags as booleans.
- cleaning_report.json: machine-readable counts, quality findings and verification results.
- audit/: all conflicting original XI key rows, player-name observations, matches without deliveries, and deliveries needing review.

## Cleaning decisions
1. Original files remain unchanged. Trimmed surrounding whitespace, standardized blank cells as missing, typed IDs/counts/flags, validated dates. No source delivery removed and no values statistically imputed. Literal extras category `None` is preserved, not interpreted as a missing value.
2. XI keys had 40 extra records across 75 source rows. For each duplicate key, kept the single distinct nonmissing value per attribute. Conflicting values (such as batting order) are left missing, with source counts and conflicting-column names. Original rows are in audit. No arbitrary first-row selection for conflicting values.
3. Corrected dismissal label spelling and standardized labels in a separate clean column. Preserved original labels and inconsistent dismissed-player IDs; flagged 13 inconsistent delivery records rather than inventing wickets.
4. bowl_speed_raw retains every source value. bowl_speed_clean blanks nonpositive values and values outside 40–170, an explicitly assumed km/h plausibility interval. No guessing decimal corrections. Validity cannot establish the source unit.
5. extras1_runs renamed extras_type_code_raw because it maps exactly to extras category (None=6, wide=2, legbyes=3, byes=4, Overstep=1, other=5, Penalty=7). extras_2_runs renamed extras_secondary_value_raw. These fields are NOT treated as complete extras runs. runs renamed runs_recorded to avoid claiming verified batter/team scoring semantics. No team total, target, run rate, legal-ball counter or pressure score fabricated.
6. Revised-overs fields retained with _raw suffix: nonmissing values are above 20 and multiples of six, consistent with ball counts but not verified. No conversion or default 120-ball limit applied. A blank revised target remains unknown, not zero.
7. delivery_ist_time source text ends in UTC despite its column name. Retained text and added a parsed UTC-as-labeled timestamp. Match dates retained independently; no guessed timezone adjustment.
8. Super-over-like innings >2 retained and flagged is_extra_innings. Other T20 tournaments retained and labelled separately from IPL/T20I. Competition scope and pressure definitions remain downstream modeling choices.
9. man_of_the_match=0 converted to missing. Other IDs unchanged. No same-name ID merging.

## Join keys
- Deliveries -> matches: match_id (many-to-one).
- Matches -> competitions: comp_id (many-to-one).
- Team names: comp_id + batting_team_id / bowling_team_id (many-to-one).
- XI role context: match_id + role's team_id + role's player_id (many-to-one).
- Roster membership: comp_id + role's team_id + role's player_id (many-to-one).
Missing role context remains missing. A false roster flag indicates absence from the supplied mapping, not proof of ineligibility. Never join the full roster or XI by match alone: that would multiply deliveries.

## Before pressure modeling
Resolve extras scoring and revised-overs units with an authoritative schema or scorecard checks, then reconstruct legal balls, total runs, wickets and targets. Explicitly handle shortened games, other/penalty extras, retired-out/obstruction dismissals and extra innings. Use before-delivery state to avoid outcome leakage. No pressure definitions, eligibility thresholds or rankings have been imposed here.

## Verification
All delivery->match and match->competition joins matched. Every merge validated many-to-one. Delivery count and unique delivery IDs are unchanged after joins. All remaining unmatched supporting lookups are counted in cleaning_report.json. Original datasets: 200,999 deliveries, 883 matches; output retains all deliveries. Rebuild with the included clean_competition_data.py and pandas, with the original extracted files in sibling competition_data/.
