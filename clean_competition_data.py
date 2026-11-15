"""Rebuild cleaned CSVs from the extracted competition_data folder; requires pandas.
Run: python clean_competition_data.py
No source files are overwritten. No uncertain extras/score semantics are invented.
"""
from pathlib import Path
import json
import shutil
import pandas as pd

ROOT = Path(__file__).resolve().parent
SRC = ROOT / 'competition_data'
OUT = ROOT / 'cleaned_competition_data'
AUDIT = OUT / 'audit'
OUT.mkdir(exist_ok=True)
AUDIT.mkdir(exist_ok=True)
stats = {}
dictionary = []

def load(name):
    d = pd.read_csv(SRC / f'{name}.csv', dtype='string', keep_default_na=False)
    for c in d:
        d[c] = d[c].str.strip().replace('', pd.NA)
        if c.endswith('_id') or c in ['innings','overid','over_ball_num','innings_ball_num',
                'batting_order','runs','extras1_runs','extras_2_runs','match_number',
                'first_inn_revised_overs','second_inn_revised_overs','revised_target',
                'man_of_the_match']:
            d[c] = pd.to_numeric(d[c], errors='raise').astype('Int64')
        elif c.startswith('is_') or c == 'knock_out':
            vals = d[c].str.lower()
            assert vals.dropna().isin(['true','false','0','1']).all(), (name,c)
            d[c] = vals.map({'true':True,'false':False,'1':True,'0':False}).astype('boolean')
        elif c == 'bowl_speed':
            d[c] = pd.to_numeric(d[c], errors='raise').astype('Float64')
    stats[name] = {'input_rows':len(d),'exact_duplicate_rows':int(d.duplicated().sum())}
    # Exact duplicates only; nonidentical duplicate keys require explicit handling below.
    return d.drop_duplicates().reset_index(drop=True)

SPECIAL = {
 'delivery_id':'Stable key match_id:innings:innings_ball_num; source key uniqueness validated.',
 'source_row_number':'Original CSV row number, including header as row 1.',
 'runs_recorded':'Original runs field. Boundary flags are consistent with batter runs; exact scoring semantics are undocumented. Do not treat as verified team runs.',
 'extras_type_code_raw':'Original extras1_runs. It maps one-to-one to extras_type, so it is not summed as runs.',
 'extras_secondary_value_raw':'Original extras_2_runs; semantics undocumented. Not treated as complete extras runs.',
 'extras_type_raw':'Original extras_type, including literal None.',
 'extras_type_clean':'Standardized category; overstep renamed no_ball_overstep. other remains unresolved.',
 'extras_scoring_unresolved':'True for non-none categories or a nonzero secondary value. No complete team-run reconstruction attempted.',
 'bowl_speed_raw':'Unmodified original numeric bowl_speed; source units undocumented.',
 'bowl_speed_clean':'Raw speed retained only in inclusive 40–170 plausibility range, assuming km/h. Other values blanked, never rescaled.',
 'bowl_speed_quality':'missing_or_nonpositive, outside_plausible_kmh_range, or plausible_assuming_kmh. Assumption, not unit verification.',
 'dismissal_type_clean':'Normalized dismissal label, including correction of Obstracting spelling. Original retained.',
 'dismissal_record_inconsistent':'Wicket flag, dismissal label and dismissed player ID do not agree.',
 'bowler_credited_wicket_candidate':'Wicket with a known bowler-credit dismissal type. False for known non-bowler types, blank for unknown; not final adjudication.',
 'is_extra_innings':'innings > 2; retained and kept separate for downstream super-over handling.',
 'delivery_timestamp_utc_as_labeled':'Timestamp parsed using the UTC suffix supplied in the source. Name delivery_ist_time conflicts with that suffix; no IST reinterpretation.',
 'competition_group':'IPL by competition name; otherwise T20I by format; otherwise Other T20. Other T20 is not silently removed.',
 'has_ball_data':'Match has at least one supplied delivery record.',
 'delivery_count':'Number of supplied delivery records, including illegal deliveries.',
 'xi_source_record_count':'Number of original XI records consolidated into this match/team/player key.',
 'xi_conflicting_columns':'Pipe-separated columns with disagreeing nonmissing values; those values are blanked in the consolidated row.',
 'player_name':'Canonical modal nonmissing source name by player ID, with mapping preferred on ties. Different IDs are never merged by name.',
 'player_name_aliases':'All distinct observed source names for this ID, JSON encoded.',
 'shared_name_across_ids':'Same canonical name occurs for different IDs; IDs remain separate.',
}

def save(d, name, grain, directory=OUT):
    d.to_csv(directory / f'{name}.csv', index=False, encoding='utf-8', na_rep='')
    if directory == OUT:
        for c in d:
            desc = SPECIAL.get(c)
            if desc is None and c.endswith('_revised_overs_raw'):
                desc='Original revised_overs field. Values exceed 20 and are multiples of six, suggesting balls, but interpretation is unverified. Not used as an overs limit.'
            if desc is None and c.startswith(('striker_xi_','non_striker_xi_','bowler_xi_')):
                desc='Role-specific XI attribute joined on match_id, corresponding team_id and player_id. Blank when missing or conflicting.'
            if desc is None and c.endswith('_in_competition_roster'):
                desc='Membership in supplied competition/team/player mapping; false indicates unmatched supplied roster, not proof player was ineligible.'
            dictionary.append({'file':f'{name}.csv','column':c,'dtype':str(d[c].dtype),
                'missing_count':int(d[c].isna().sum()),'row_grain':grain,
                'description':desc or 'Source field, whitespace trimmed and blank cells standardized; numeric IDs/counts and boolean flags typed where applicable. See README for provenance.'})

b=load('ball_by_ball'); m=load('matches'); c=load('competitions')
t=load('teams'); roster=load('competition_team_player_mapping'); xi=load('playing_eleven')
for d,key in [(b,['match_id','innings','innings_ball_num']), (m,['match_id']),
              (c,['comp_id']),(t,['comp_id','team_id']),
              (roster,['comp_id','team_id','player_id'])]:
    assert not d.duplicated(key).any(), key

# Resolve XI duplicate keys conservatively: retain consensus values, blank conflicts.
xkeys=['match_id','team_id','player_id']
xdupes=xi[xi.duplicated(xkeys,keep=False)].copy()
save(xdupes,'playing_eleven_duplicate_keys','original XI record',AUDIT)
group=xi.groupby(xkeys,dropna=False,sort=False)
x=group.first().reset_index()
x['xi_source_record_count']=group.size().to_numpy()
conflicts=group[[col for col in xi if col not in xkeys]].nunique(dropna=True).reset_index()
x['xi_conflicting_columns']=''
for col in xi:
    if col in xkeys: continue
    mask=conflicts[col].gt(1)
    x.loc[mask,col]=pd.NA
    x.loc[mask,'xi_conflicting_columns'] += col+'|'
x['xi_conflicting_columns']=x['xi_conflicting_columns'].str.rstrip('|').replace('',pd.NA)

# Build a player dimension from all named roles and identifiers; keep name collisions.
names=[roster[['player_id','player_name']]]
for role in ['striker','non_striker','bowler']:
    names.append(b[[f'{role}_id',f'{role}_name']].rename(columns={f'{role}_id':'player_id',f'{role}_name':'player_name'}))
named=pd.concat(names,ignore_index=True).dropna()
counts=named.groupby(['player_id','player_name'],sort=False).size().reset_index(name='observations')
counts['mapping_name']=pd.MultiIndex.from_frame(counts[['player_id','player_name']]).isin(pd.MultiIndex.from_frame(roster[['player_id','player_name']]))
counts=counts.sort_values(['player_id','observations','mapping_name'],ascending=[True,False,False],kind='stable')
ids=pd.concat([xi.player_id,roster.player_id,b.striker_id,b.non_striker_id,b.bowler_id,b.dismissed_player_id,m.home_team_captain_id,m.away_team_captain_id,m.man_of_the_match]).dropna()
ids=ids[ids.gt(0)].drop_duplicates().sort_values()
players=pd.DataFrame({'player_id':ids}).merge(counts.drop_duplicates('player_id')[['player_id','player_name']],on='player_id',how='left',validate='one_to_one')
aliases=named.groupby('player_id').player_name.agg(lambda s:json.dumps(sorted(s.unique().tolist()),ensure_ascii=False)).rename('player_name_aliases')
players=players.merge(aliases,on='player_id',how='left',validate='one_to_one')
players['shared_name_across_ids']=players.player_name.notna() & players.player_name.duplicated(keep=False)
save(counts,'player_name_observations','observed player ID/name pair',AUDIT)

c['competition_group']='Other T20'
c.loc[c.match_format.eq('T20I'),'competition_group']='T20I'
c.loc[c.comp_name.str.match(r'^IPL\b',na=False),'competition_group']='IPL'
m=m.rename(columns={'first_inn_revised_overs':'first_inn_revised_overs_raw','second_inn_revised_overs':'second_inn_revised_overs_raw'})
m['man_of_the_match']=m.man_of_the_match.mask(m.man_of_the_match.eq(0))
m['match_date']=pd.to_datetime(m.match_date,format='%Y-%m-%d',errors='raise').dt.strftime('%Y-%m-%d')
matches=m.merge(c,on='comp_id',how='left',validate='many_to_one',indicator='_competition_join')
assert matches._competition_join.eq('both').all()
matches=matches.drop(columns='_competition_join')
matches['delivery_count']=matches.match_id.map(b.groupby('match_id').size()).fillna(0).astype('Int64')
matches['has_ball_data']=matches.delivery_count.gt(0)
save(matches.loc[~matches.has_ball_data],'matches_without_deliveries','match',AUDIT)

b.insert(0,'source_row_number',b.index+2)
b.insert(0,'delivery_id',b.match_id.astype(str)+':'+b.innings.astype(str)+':'+b.innings_ball_num.astype(str))
b=b.rename(columns={'runs':'runs_recorded','extras1_runs':'extras_type_code_raw','extras_2_runs':'extras_secondary_value_raw','extras_type':'extras_type_raw','bowl_speed':'bowl_speed_raw','dismissal_type':'dismissal_type_raw'})
b['extras_type_clean']=b.extras_type_raw.str.lower().replace({'overstep':'no_ball_overstep','legbyes':'leg_byes'})
b['extras_scoring_unresolved']=b.extras_type_clean.ne('none')|b.extras_secondary_value_raw.ne(0)
b['bowl_speed_quality']='plausible_assuming_kmh'
b.loc[b.bowl_speed_raw.isna()|b.bowl_speed_raw.le(0),'bowl_speed_quality']='missing_or_nonpositive'
b.loc[b.bowl_speed_raw.gt(0)&~b.bowl_speed_raw.between(40,170),'bowl_speed_quality']='outside_plausible_kmh_range'
b['bowl_speed_clean']=b.bowl_speed_raw.where(b.bowl_speed_raw.between(40,170))
b['dismissal_type_clean']=b.dismissal_type_raw.str.lower().replace({'stump':'stumped','runout':'run_out','retire out':'retired_out','hit wicket':'hit_wicket','obstracting the field':'obstructing_the_field','obstructing the field':'obstructing_the_field'})
b['dismissal_record_inconsistent']=(b.is_wicket & (b.dismissed_player_id.isna()|b.dismissal_type_clean.isna()))|(~b.is_wicket & (b.dismissed_player_id.notna()|b.dismissal_type_clean.notna()))
b['bowler_credited_wicket_candidate']=pd.Series(pd.NA,index=b.index,dtype='boolean')
b.loc[~b.is_wicket,'bowler_credited_wicket_candidate']=False
b.loc[b.is_wicket&b.dismissal_type_clean.isin(['bowled','caught','lbw','stumped','hit_wicket']),'bowler_credited_wicket_candidate']=True
b.loc[b.is_wicket&b.dismissal_type_clean.isin(['run_out','retired_out','obstructing_the_field']),'bowler_credited_wicket_candidate']=False
b['is_extra_innings']=b.innings.gt(2)
b['delivery_timestamp_utc_as_labeled']=pd.to_datetime(b.delivery_ist_time,format='%Y-%m-%d %H:%M:%S UTC',utc=True,errors='raise').dt.strftime('%Y-%m-%dT%H:%M:%SZ')
b=b.sort_values(['match_id','innings','innings_ball_num'],kind='stable').reset_index(drop=True)

joined=b.merge(matches,on='match_id',how='left',validate='many_to_one',indicator='_match_join')
assert joined._match_join.eq('both').all()
joined=joined.drop(columns='_match_join')
join_stats={}
for role,teamcol in [('striker','batting_team_id'),('non_striker','batting_team_id'),('bowler','bowling_team_id')]:
    renamed=x.rename(columns={'team_id':teamcol,'player_id':f'{role}_id',**{col:f'{role}_xi_{col}' for col in x if col not in xkeys}})
    joined=joined.merge(renamed,on=['match_id',teamcol,f'{role}_id'],how='left',validate='many_to_one')
    join_stats[f'{role}_xi_unmatched_deliveries']=int(joined[f'{role}_xi_xi_source_record_count'].isna().sum())
    rkeys=roster[['comp_id','team_id','player_id']].rename(columns={'team_id':teamcol,'player_id':f'{role}_id'})
    rkeys[f'{role}_in_competition_roster']=True
    joined=joined.merge(rkeys,on=['comp_id',teamcol,f'{role}_id'],how='left',validate='many_to_one')
    joined[f'{role}_in_competition_roster']=joined[f'{role}_in_competition_roster'].eq(True)
    join_stats[f'{role}_roster_unmatched_deliveries']=int((~joined[f'{role}_in_competition_roster']).sum())
for role in ['batting','bowling']:
    teamcol=f'{role}_team_id'
    lookup=t.rename(columns={'team_id':teamcol,'team_name':f'{role}_team_name'})
    joined=joined.merge(lookup,on=['comp_id',teamcol],how='left',validate='many_to_one')
    join_stats[f'{role}_team_unmatched_deliveries']=int(joined[f'{role}_team_name'].isna().sum())
assert len(joined)==len(b)==200999
assert joined.delivery_id.is_unique
assert not x.duplicated(xkeys).any()

save(b,'deliveries_clean','delivery')
save(joined,'deliveries_joined','delivery with match/competition/team/role-specific XI context')
save(matches,'matches_clean','match with competition context and delivery coverage')
save(c,'competitions_clean','competition')
save(t,'teams_clean','competition/team')
save(roster,'competition_team_player_mapping_clean','competition/team/player')
save(x,'playing_eleven_clean','match/team/player; conflicting duplicate values blanked')
save(players,'players_clean','player ID')
save(b.loc[b.extras_scoring_unresolved|b.dismissal_record_inconsistent|b.bowl_speed_quality.eq('outside_plausible_kmh_range')],'deliveries_for_review','delivery with scoring/dismissal/speed concern',AUDIT)
pd.DataFrame(dictionary).to_csv(OUT/'data_dictionary.csv',index=False,encoding='utf-8')

report={
 'source_files':stats,'output_delivery_rows':len(joined),'output_delivery_columns':len(joined.columns),
 'match_count':len(matches),'matches_with_deliveries':int(matches.has_ball_data.sum()),
 'matches_without_deliveries':int((~matches.has_ball_data).sum()),'player_ids':len(players),
 'xi_input_rows':len(xi),'xi_output_unique_keys':len(x),'xi_duplicate_key_source_rows':len(xdupes),
 'xi_keys_with_conflicts':int(x.xi_conflicting_columns.notna().sum()),
 'name_collision_player_ids':int(players.shared_name_across_ids.sum()),
 'extras_scoring_unresolved_deliveries':int(b.extras_scoring_unresolved.sum()),
 'dismissal_inconsistent_deliveries':int(b.dismissal_record_inconsistent.sum()),
 'bowling_speed_quality':b.bowl_speed_quality.value_counts().to_dict(),
 'extra_innings_deliveries':int(b.is_extra_innings.sum()),'join_checks':join_stats,
 'assertions_passed':['source primary keys unique except explicitly reconciled XI keys','all deliveries match a match','all matches match a competition','all joins many-to-one','delivery row count preserved','delivery_id unique','XI output keys unique'],
 'match_date_min':matches.match_date.min(),'match_date_max':matches.match_date.max(),
 'competition_group_delivery_counts':joined.competition_group.value_counts().to_dict(),
 'score_reconstruction':'Not attempted: extras amount semantics are not documented. Do not use raw extras type code as runs.',
}
(OUT/'cleaning_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
readme=f'''# Cleaned competition data

Start with `deliveries_joined.csv`: {len(joined):,} rows, {len(joined.columns)} columns. One row per supplied delivery, sorted by match/innings/innings_ball_num. Includes all match and competition columns, both team names, role-specific XI fields and roster membership flags. Historical result/winner/man_of_the_match are included as metadata; do not use them to define pressure before a ball.

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
2. XI keys had {len(xi)-len(x)} extra records across {len(xdupes)} source rows. For each duplicate key, kept the single distinct nonmissing value per attribute. Conflicting values (such as batting order) are left missing, with source counts and conflicting-column names. Original rows are in audit. No arbitrary first-row selection for conflicting values.
3. Corrected dismissal label spelling and standardized labels in a separate clean column. Preserved original labels and inconsistent dismissed-player IDs; flagged {int(b.dismissal_record_inconsistent.sum())} inconsistent delivery records rather than inventing wickets.
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
'''
(OUT/'README.md').write_text(readme,encoding='utf-8')
shutil.copy2(Path(__file__),OUT/'clean_competition_data.py')
zip_path=shutil.make_archive(str(ROOT/'cleaned_competition_data'),'zip',root_dir=OUT)
print(json.dumps(report,indent=2))
print('ZIP',zip_path)
