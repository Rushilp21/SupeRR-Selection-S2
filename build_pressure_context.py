"""Build three reproducible analysis stages from the existing joined competition CSV.
Requires pandas, numpy, matplotlib; reference ZIPs cached in pressure_analysis/references.
Uses source player IDs and batting runs; adds explicitly attributed Cricsheet scoring context.
"""
from pathlib import Path
from collections import defaultdict, Counter
import datetime as dt
import hashlib
import json
import re
import shutil
import zipfile
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'pressure_analysis'
REF = OUT / 'references'
AUDIT = OUT / 'audit'
OUT.mkdir(exist_ok=True)
AUDIT.mkdir(exist_ok=True)
HIGH = 55.0
MODERATE = 35.0
BOOTSTRAP_RPO = 8.0
PRIOR_LEGAL_BALLS = 20 * 120
SOURCE = ROOT / 'cleaned_competition_data' / 'deliveries_joined.csv'

def normalize_team(s):
    s = str(s).replace('Royal Challengers Bangalore', 'Royal Challengers Bengaluru')
    s = s.replace('United States of America', 'United States')
    return re.sub('[^a-z0-9]', '', s.lower())

def write(d, name, folder=OUT):
    d.to_csv(folder / f'{name}.csv', index=False, encoding='utf-8', na_rep='')

def checksum(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for data in iter(lambda:f.read(1024*1024), b''):
            h.update(data)
    return h.hexdigest()

def pressure_components(innings, progress, wickets, rpo, par_rpo, current_rpo, legal_before, knockout):
    """No current-delivery outcomes or final results accepted by this function."""
    late = float(np.clip(progress, 0, 1)) ** 2
    resource_stress = float(np.clip(wickets / 8, 0, 1))
    if innings == 1:
        deficit = float(np.clip((par_rpo-current_rpo)/4,0,1)) if legal_before >= 12 else 0.0
        score = 35*late + 35*resource_stress + 20*deficit + 10*int(knockout)
        return [float(np.clip(score,0,100)),late,resource_stress,deficit,np.nan,np.nan]
    ratio = rpo / par_rpo
    # Highest competitive tension near a required rate comparable to prior scoring.
    # This is an interpretable heuristic, not an estimated win probability.
    closeness = float(np.exp(-((ratio-1)/0.75)**2))
    load = float(np.clip(ratio/2,0,1))
    score = closeness*(45*late + 30*load + 15*resource_stress + 10*int(knockout))
    return [float(np.clip(score,0,100)),late,resource_stress,np.nan,closeness,load]

def main():
    print('Loading supplied merged CSV and reference archives...',flush=True)
    b = pd.read_csv(SOURCE, low_memory=False).sort_values(['match_id','innings','innings_ball_num']).reset_index(drop=True)
    for col in ['is_wicket','is_four','is_six','knock_out','is_extra_innings']:
        assert b[col].isin([True,False]).all(), col
    assert b.delivery_id.is_unique
    assert len(b) == 200999
    ref_index=defaultdict(list)
    reference_manifest=[]
    for archive in sorted(REF.glob('*.zip')):
        reference_manifest.append({'file':archive.name,'url':'https://cricsheet.org/downloads/'+archive.name,
            'sha256':checksum(archive),'bytes':archive.stat().st_size})
        with zipfile.ZipFile(archive) as z:
            notices=OUT/'third_party_notices'
            notices.mkdir(exist_ok=True)
            for notice in ['LICENSE.txt','README.txt']:
                if notice in z.namelist():
                    (notices/(archive.stem+'_'+notice)).write_bytes(z.read(notice))
            for filename in z.namelist():
                if not filename.endswith('.json'): continue
                j=json.loads(z.read(filename))
                info=j['info']
                if str(info['dates'][0])<'2022-01-01': continue
                for date in info['dates']:
                    ref_index[(str(date),tuple(sorted(normalize_team(t) for t in info['teams'])))].append((archive.name,filename,j))

    records=[]
    diagnostics=[]
    identity_rows=[]
    mismatch_rows=[]
    extras_rows=[]
    reference_innings=[]
    for mid,g in b.groupby('match_id',sort=False):
        r=g.iloc[0]
        candidates=ref_index.get((r.match_date,tuple(sorted([normalize_team(r.home_team),normalize_team(r.away_team)]))),[])
        for inn,ig in g.groupby('innings',sort=True):
            check={'match_id':int(mid),'innings':int(inn),'match_date':r.match_date,
                'competition_group':r.competition_group,'source_deliveries':len(ig),
                'reference_candidate_count':len(candidates)}
            if len(candidates)!=1:
                diagnostics.append(dict(check,alignment_status='no_unique_reference_match'))
                continue
            archive,filename,j=candidates[0]
            info=j['info']
            check.update(reference_archive=archive,reference_match_id=Path(filename).stem)
            if int(inn)>len(j['innings']):
                diagnostics.append(dict(check,alignment_status='reference_innings_absent')); continue
            ri=j['innings'][int(inn)-1]
            flat=[(o['over']+1,k+1,d) for o in ri['overs'] for k,d in enumerate(o['deliveries'])]
            check.update(reference_deliveries=len(flat),batting_team_matches=normalize_team(ri['team'])==normalize_team(ig.iloc[0].batting_team_name))
            if len(flat)!=len(ig):
                diagnostics.append(dict(check,alignment_status='delivery_count_mismatch')); continue
            check['batter_run_mismatches']=sum(int(d['runs']['batter'])!=int(v) for (_,_,d),v in zip(flat,ig.runs_recorded))
            check['over_sequence_mismatches']=sum(o!=int(v) for (o,_,_),v in zip(flat,ig.overid))
            check['within_over_sequence_mismatches']=sum(k!=int(v) for (_,k,_),v in zip(flat,ig.over_ball_num))
            if not check['batting_team_matches'] or any(check[k] for k in ['batter_run_mismatches','over_sequence_mismatches','within_over_sequence_mismatches']):
                diagnostics.append(dict(check,alignment_status='sequence_mismatch')); continue
            registry=info.get('registry',{}).get('people',{})
            identity_counts=Counter()
            identity_cols=['striker_id','striker_name','non_striker_id','non_striker_name','bowler_id','bowler_name']
            for sr,(_,_,d) in zip(ig[identity_cols].itertuples(index=False),flat):
                for role,refrole in [('striker','batter'),('non_striker','non_striker'),('bowler','bowler')]:
                    identity_counts[(int(getattr(sr,role+'_id')),getattr(sr,role+'_name'),role,d[refrole],registry.get(d[refrole],d[refrole]))]+=1
            identities=[{'match_id':int(mid),'innings':int(inn),'source_player_id':k[0],
                'source_player_name':k[1],'role':k[2],'reference_name':k[3],
                'reference_player_id':k[4],'role_observations':v} for k,v in identity_counts.items()]
            idf=pd.DataFrame(identities)
            identity_conflict=(idf.groupby('source_player_id').reference_player_id.nunique().gt(1).any()
                or idf.groupby('reference_player_id').source_player_id.nunique().gt(1).any())
            if identity_conflict:
                diagnostics.append(dict(check,alignment_status='within_innings_identity_conflict')); continue
            check['alignment_status']='sequence_and_local_identity_match'
            diagnostics.append(check)
            identity_rows.extend(identities)
            limit=float(info.get('overs',20))*6
            if ri.get('super_over',False): limit=6
            if 'target' in ri: limit=float(ri['target'].get('overs',limit/6))*6
            penalty=ri.get('penalty_runs',{})
            revised=(pd.notna(r.first_inn_revised_overs_raw) or pd.notna(r.second_inn_revised_overs_raw)
                or pd.notna(r.revised_target) or 'D/L' in str(r.result) or 'DLS' in str(r.result)
                or 'D/L' in str(info.get('outcome',{}).get('method','')) or limit!=120)
            miscounted=bool(ri.get('miscounted_overs'))
            first=j['innings'][0]
            first_total=sum(d['runs']['total'] for o in first['overs'] for d in o['deliveries'])+sum(first.get('penalty_runs',{}).values())
            target=float(ri.get('target',{}).get('runs',first_total+1)) if int(inn)==2 else np.nan
            score=int(penalty.get('pre',0)); wickets=0; legal=0
            needed=['delivery_id','runs_recorded','is_wicket','dismissed_player_id','extras_type_clean','extras_type_code_raw']
            for sr,(_,_,d) in zip(ig[needed].itertuples(index=False),flat):
                ex=d.get('extras',{})
                legal_delta=int(not ex.get('wides',0) and not ex.get('noballs',0))
                ws=d.get('wickets',[])
                team_delta=sum(w['kind'] not in ['retired hurt','retired not out'] for w in ws)
                credited=sum(w['kind'] in ['bowled','caught','caught and bowled','lbw','stumped','hit wicket'] for w in ws)
                wicket_players=[registry.get(w['player_out'],w['player_out']) for w in ws if w['kind'] not in ['retired hurt','retired not out']]
                refrec={'delivery_id':sr.delivery_id,'reference_archive':archive,'reference_match_id':Path(filename).stem,
                    'reference_batter_name':d['batter'],'reference_bowler_name':d['bowler'],
                    'reference_batter_id':registry.get(d['batter'],d['batter']),
                    'reference_non_striker_id':registry.get(d['non_striker'],d['non_striker']),
                    'reference_bowler_id':registry.get(d['bowler'],d['bowler']),
                    'team_runs_on_delivery':int(d['runs']['total']),'extras_runs_on_delivery':int(d['runs']['extras']),
                    'batter_runs_on_delivery':int(sr.runs_recorded),'wide_runs':int(ex.get('wides',0)),
                    'no_ball_runs':int(ex.get('noballs',0)),'bye_runs':int(ex.get('byes',0)),
                    'leg_bye_runs':int(ex.get('legbyes',0)),'penalty_runs_on_delivery':int(ex.get('penalty',0)),
                    'counts_as_legal_delivery':bool(legal_delta),'team_wickets_on_delivery':int(team_delta),
                    'bowler_wickets_on_delivery':int(credited),
                    'reference_dismissal_kinds':'|'.join(w['kind'] for w in ws),
                    'reference_dismissed_player_ids':json.dumps(wicket_players),
                    'score_before':score,'wickets_before':wickets,'legal_balls_before':legal,
                    'balls_remaining_before':int(limit-legal),'innings_limit_balls_as_recorded':int(limit),
                    'chase_target_as_recorded':target,'runs_required_before':target-score if int(inn)==2 else np.nan,
                    'is_revised_or_shortened_match':bool(revised),'has_miscounted_over':miscounted,
                    'has_innings_penalty_adjustment':bool(penalty),
                    'source_wicket_flag_agrees':bool(sr.is_wicket)==bool(team_delta),
                    'source_dismissed_id_present':pd.notna(sr.dismissed_player_id)}
                records.append(refrec)
                if bool(sr.is_wicket)!=bool(team_delta):
                    mismatch_rows.append({'delivery_id':sr.delivery_id,'issue':'source_wicket_flag_vs_reference',
                        'source_is_wicket':bool(sr.is_wicket),'reference_wicket_delta':team_delta,
                        'reference_dismissal_kinds':refrec['reference_dismissal_kinds']})
                extras_rows.append({'extras_type_clean':sr.extras_type_clean,'extras_type_code_raw':sr.extras_type_code_raw,
                    'reference_extras_amount':d['runs']['extras'],'reference_extra_categories':'+'.join(sorted(ex)) or 'none',
                    'reference_legal':legal_delta})
                score+=int(d['runs']['total']);wickets+=team_delta;legal+=legal_delta
            reference_innings.append({'match_id':int(mid),'innings':int(inn),'reference_match_id':Path(filename).stem,
                'team_total':score+int(penalty.get('post',0)),'team_wickets':wickets,'legal_deliveries':legal,
                'source_deliveries':len(ig),'total_batter_runs':int(ig.runs_recorded.sum()),
                'total_extras':score+int(penalty.get('post',0))-int(ig.runs_recorded.sum()),
                'innings_limit_balls_as_recorded':int(limit),'reference_batting_team':ri['team']})
    print('Applying global player identity checks...',flush=True)
    diag=pd.DataFrame(diagnostics)
    contexts=pd.DataFrame(records)
    identities=pd.DataFrame(identity_rows)
    idcounts=identities.groupby(['source_player_id','reference_player_id']).role_observations.sum().reset_index()
    modes=idcounts.sort_values('role_observations',ascending=False,kind='stable').drop_duplicates('source_player_id')
    canonical=modes.set_index('source_player_id').reference_player_id
    identities['agrees_with_modal_crosswalk']=identities.reference_player_id.eq(identities.source_player_id.map(canonical))
    badkeys=set(zip(identities.loc[~identities.agrees_with_modal_crosswalk,'match_id'],identities.loc[~identities.agrees_with_modal_crosswalk,'innings']))
    diag.loc[diag.apply(lambda r:(r.match_id,r.innings) in badkeys,axis=1),'alignment_status']='global_player_identity_conflict'
    accepted=set(map(tuple,diag.loc[diag.alignment_status.eq('sequence_and_local_identity_match'),['match_id','innings']].to_numpy()))
    # Crosswalk also has to be injective: flag any reference person represented by >1 source ID.
    shared_reference_ids=set(modes.loc[modes.reference_player_id.duplicated(keep=False),'reference_player_id'])
    modes['reference_id_shared_across_source_ids']=modes.reference_player_id.isin(shared_reference_ids)
    names=pd.read_csv(ROOT/'cleaned_competition_data'/'players_clean.csv',usecols=['player_id','player_name'])
    modes=modes.merge(names,left_on='source_player_id',right_on='player_id',how='left',validate='one_to_one').drop(columns='player_id')
    write(modes,'reference_player_crosswalk',AUDIT)
    write(identities.loc[~identities.agrees_with_modal_crosswalk].drop_duplicates(),'identity_disagreements',AUDIT)
    keycheck=b[['delivery_id','match_id','innings']].merge(contexts[['delivery_id']],on='delivery_id',how='inner',validate='one_to_one')
    context_ids=set(keycheck.loc[keycheck.apply(lambda r:(r.match_id,r.innings) in accepted,axis=1),'delivery_id'])
    contexts=contexts[contexts.delivery_id.isin(context_ids)].copy()
    status=diag[['match_id','innings','alignment_status']]
    b=b.merge(status,on=['match_id','innings'],how='left',validate='many_to_one')
    b=b.merge(contexts,on='delivery_id',how='left',validate='one_to_one')
    b['context_verified']=b.reference_match_id.notna()
    b['wickets_in_hand_before']=10-b.wickets_before
    b['current_run_rate_before']=np.where(b.legal_balls_before.gt(0),6*b.score_before/b.legal_balls_before,np.nan)
    b['required_run_rate_before']=np.where(b.innings.eq(2)&b.balls_remaining_before.gt(0),6*b.runs_required_before/b.balls_remaining_before,np.nan)
    b['innings_progress_before']=b.legal_balls_before/b.innings_limit_balls_as_recorded
    b['innings_phase']=np.select([b.legal_balls_before.lt(36),b.legal_balls_before.lt(90),b.legal_balls_before.notna()],['powerplay','middle','death'],default='unknown')
    valid_state=b.context_verified & b.innings.isin([1,2]) & b.balls_remaining_before.gt(0) & b.wickets_before.between(0,9)
    valid_state &= b.innings.ne(2)|b.runs_required_before.gt(0)
    b['pressure_eligible_v1']=(valid_state & b.is_revised_or_shortened_match.eq(False)
        & b.has_miscounted_over.eq(False) & b.has_innings_penalty_adjustment.eq(False)
        & b.competition_group.isin(['IPL','T20I']))
    b['pressure_exclusion_reason']=np.select([
        ~b.context_verified,b.innings.gt(2),b.competition_group.eq('Other T20'),
        b.is_revised_or_shortened_match.eq(True),b.has_miscounted_over.eq(True),
        b.has_innings_penalty_adjustment.eq(True),~valid_state],
        ['unverified_context','extra_innings','outside_IPL_T20I_scope','revised_or_shortened_match',
        'miscounted_over','innings_penalty_adjustment','invalid_or_terminal_state'],default='included')

    # Prior-only format-specific scoring environment. Entire same-day matches excluded.
    prior_source=b[b.pressure_eligible_v1 & b.innings.eq(1)]
    daily=prior_source.groupby(['competition_group','match_date']).agg(runs=('team_runs_on_delivery','sum'),legal=('counts_as_legal_delivery','sum'),innings=('match_id','nunique')).reset_index()
    daily['legal']=pd.to_numeric(daily.legal).astype('int64')
    daily=daily.sort_values(['competition_group','match_date'])
    daily['prior_runs']=daily.groupby('competition_group').runs.cumsum()-daily.runs
    daily['prior_legal_balls']=daily.groupby('competition_group').legal.cumsum()-daily.legal
    daily['prior_innings']=daily.groupby('competition_group').innings.cumsum()-daily.innings
    daily['prior_expected_rpo']=6*(daily.prior_runs+BOOTSTRAP_RPO/6*PRIOR_LEGAL_BALLS)/(daily.prior_legal_balls+PRIOR_LEGAL_BALLS)
    # Also provide a prior for dates where only a second innings qualified.
    all_dates=b[['competition_group','match_date']].drop_duplicates()
    prior_rows=[]
    for rr in all_dates.itertuples(index=False):
        past=daily[(daily.competition_group==rr.competition_group)&(daily.match_date<rr.match_date)]
        runs=float(past.runs.sum());legal=float(past.legal.sum());inn=int(past.innings.sum())
        prior_rows.append({'competition_group':rr.competition_group,'match_date':rr.match_date,
            'prior_expected_rpo':6*(runs+BOOTSTRAP_RPO/6*PRIOR_LEGAL_BALLS)/(legal+PRIOR_LEGAL_BALLS),
            'prior_reference_innings':inn,'prior_reference_legal_balls':int(legal)})
    priors=pd.DataFrame(prior_rows)
    b=b.merge(priors,on=['competition_group','match_date'],how='left',validate='many_to_one')
    components=['pressure_score_v1','pressure_lateness','pressure_wicket_stress','pressure_scoring_deficit',
        'pressure_chase_closeness','pressure_chase_load']
    for col in components:b[col]=np.nan
    eligible=b.pressure_eligible_v1
    values=[]
    for rr in b.loc[eligible].itertuples(index=False):
        values.append(pressure_components(rr.innings,rr.innings_progress_before,rr.wickets_before,
            rr.required_run_rate_before,rr.prior_expected_rpo,rr.current_run_rate_before,
            rr.legal_balls_before,rr.knock_out))
    b.loc[eligible,components]=values
    b['pressure_band_v1']=np.select([~eligible,b.pressure_score_v1.ge(HIGH),b.pressure_score_v1.ge(MODERATE)],
        ['excluded','high','moderate'],default='ordinary')
    b['chase_rate_ratio_before']=b.required_run_rate_before/b.prior_expected_rpo
    b['chase_demand_context']=np.select([~b.innings.eq(2)|~b.context_verified,
        b.chase_rate_ratio_before.lt(.5),b.chase_rate_ratio_before.gt(2.5)],
        ['not_available','low_required_rate','extreme_required_rate'],default='competitive_range')

    print('Checking reconstructed states and pressure invariants...',flush=True)
    verified=b[b.context_verified]
    # Independent cumulative checks, excluding current delivery.
    for (mid,inn),g in verified.groupby(['match_id','innings'],sort=False):
        assert np.array_equal(g.legal_balls_before.to_numpy(),g.counts_as_legal_delivery.astype(int).cumsum().to_numpy()-g.counts_as_legal_delivery.astype(int).to_numpy())
        assert np.array_equal(g.wickets_before.to_numpy(),g.team_wickets_on_delivery.cumsum().to_numpy()-g.team_wickets_on_delivery.to_numpy())
        start=g.score_before.iloc[0]
        assert np.array_equal(g.score_before.to_numpy(),start+g.team_runs_on_delivery.cumsum().to_numpy()-g.team_runs_on_delivery.to_numpy())
        assert np.allclose(g.team_runs_on_delivery,g.batter_runs_on_delivery+g.extras_runs_on_delivery)
        assert g.pressure_score_v1.dropna().between(0,100).all()
    assert len(b)==200999 and b.delivery_id.is_unique
    assert b.loc[~eligible,'pressure_score_v1'].isna().all()
    assert not b.loc[eligible,['score_before','wickets_before','balls_remaining_before','prior_expected_rpo','pressure_score_v1']].isna().any().any()
    assert b.loc[eligible & b.innings.eq(2),'runs_required_before'].gt(0).all()
    # Same before-state => same pressure, regardless of current ball's outcome.
    a=pressure_components(2,.9,5,10,8,8,108,False)
    assert a==pressure_components(2,.9,5,10,8,8,108,False) or np.allclose(a,pressure_components(2,.9,5,10,8,8,108,False),equal_nan=True)
    assert pressure_components(2,.9,5,32,8,8,108,False)[0] < pressure_components(2,.9,5,10,8,8,108,False)[0]
    assert pressure_components(2,.9,5,1,8,8,108,False)[0] < pressure_components(2,.9,5,10,8,8,108,False)[0]

    # Official scoreboard checks are validation only, never pressure inputs.
    official_url='https://www.windiescricket.com/series/england-in-west-indies-2021-22-16230/'
    official=[(13511,1,103,10,118),(13511,2,104,1,103),(13512,1,171,8,120),(13512,2,170,8,120),
        (13513,1,224,5,120),(13513,2,204,9,120),(13514,1,193,6,120),(13514,2,159,5,120),
        (13515,1,179,4,120),(13515,2,162,10,119)]
    ir=pd.DataFrame(reference_innings)
    ir['identity_accepted']=ir.apply(lambda r:(r.match_id,r.innings) in accepted,axis=1)
    checks=[]
    for mid,inn,runs,wk,legal in official:
        sample=ir[(ir.match_id==mid)&(ir.innings==inn)]
        rr=sample.iloc[0] if len(sample) else None
        passed=rr is not None and rr.team_total==runs and rr.team_wickets==wk and rr.legal_deliveries==legal
        checks.append({'match_id':mid,'innings':inn,'official_total':runs,'official_wickets':wk,
            'official_legal_balls':legal,'reconstructed_total':rr.team_total if rr is not None else np.nan,
            'reconstructed_wickets':rr.team_wickets if rr is not None else np.nan,
            'reconstructed_legal_balls':rr.legal_deliveries if rr is not None else np.nan,
            'passed':bool(passed),'source_url':official_url})
    official_checks=pd.DataFrame(checks)
    assert official_checks.passed.all()

    # Revised fields: comparison of candidate ball-vs-over units, not blanket correction.
    rev=b[['match_id','innings','first_inn_revised_overs_raw','second_inn_revised_overs_raw',
        'innings_limit_balls_as_recorded','is_revised_or_shortened_match']].drop_duplicates(['match_id','innings'])
    rev=rev[rev.first_inn_revised_overs_raw.notna()|rev.second_inn_revised_overs_raw.notna()].copy()
    rev['candidate_source_ball_limit']=np.where(rev.innings.eq(1),rev.first_inn_revised_overs_raw,rev.second_inn_revised_overs_raw)
    rev['raw_equals_reference_ball_limit']=rev.candidate_source_ball_limit.eq(rev.innings_limit_balls_as_recorded)

    exclusions=b.groupby(['competition_group','pressure_exclusion_reason']).agg(deliveries=('delivery_id','size'),matches=('match_id','nunique')).reset_index()
    summary=b.groupby(['competition_group','innings','pressure_band_v1'],dropna=False).agg(
        deliveries=('delivery_id','size'),matches=('match_id','nunique'),mean_pressure=('pressure_score_v1','mean')).reset_index()
    sensitivity=[]
    for threshold in [45,50,55,60,65]:
        for (fmt,inn),g in b[eligible].groupby(['competition_group','innings']):
            high=g.pressure_score_v1.ge(threshold)
            sensitivity.append({'high_threshold':threshold,'competition_group':fmt,'innings':int(inn),
                'eligible_deliveries':len(g),'high_deliveries':int(high.sum()),'high_share':float(high.mean()),
                'high_pressure_matches':int(g.loc[high,'match_id'].nunique()),
                'high_pressure_batters':int(g.loc[high,'striker_id'].nunique()),
                'high_pressure_bowlers':int(g.loc[high,'bowler_id'].nunique())})
    sensitivity=pd.DataFrame(sensitivity)
    # Exposure counts only: these are not player performance ratings or rankings.
    exposure=[]
    for role,idcol,namecol in [('batter','striker_id','striker_name'),('bowler','bowler_id','bowler_name')]:
        for (pid,fmt),g in b[eligible].groupby([idcol,'competition_group']):
            high=g.pressure_band_v1.eq('high')
            exposure.append({'role':role,'player_id':pid,'player_name':g[namecol].mode().iloc[0],
                'competition_group':fmt,'eligible_deliveries':len(g),'high_pressure_deliveries':int(high.sum()),
                'high_pressure_legal_deliveries':int(g.loc[high,'counts_as_legal_delivery'].sum()),
                'matches':g.match_id.nunique(),'high_pressure_matches':g.loc[high,'match_id'].nunique(),
                'seasons':g.season.nunique(),'mean_pressure_score':g.pressure_score_v1.mean()})
    exposure=pd.DataFrame(exposure)

    print('Saving datasets and methodology notes...',flush=True)
    # The primary output extends the exact merged input and keeps every source row.
    write(b,'deliveries_with_context_pressure_v1')
    write(diag,'scoring_alignment_audit',AUDIT)
    write(ir,'innings_scoring_audit',AUDIT)
    write(pd.DataFrame(mismatch_rows),'source_wicket_disagreements',AUDIT)
    write(official_checks,'official_scorecard_checks',AUDIT)
    write(rev,'revised_limit_checks',AUDIT)
    extra_map=pd.DataFrame(extras_rows).groupby(['extras_type_clean','extras_type_code_raw','reference_extra_categories','reference_extras_amount','reference_legal']).size().rename('deliveries').reset_index()
    write(extra_map,'extras_reference_crosscheck',AUDIT)
    write(exclusions,'coverage_and_exclusions')
    write(summary,'pressure_distribution')
    write(sensitivity,'pressure_threshold_sensitivity')
    write(priors,'historical_scoring_priors')
    write(exposure.sort_values(['role','player_id','competition_group']),'player_pressure_exposure')
    sample_cols=['delivery_id','match_date','competition_group','innings','striker_name','bowler_name',
        'score_before','wickets_before','balls_remaining_before','chase_target_as_recorded','runs_required_before',
        'required_run_rate_before','prior_expected_rpo','pressure_score_v1','pressure_band_v1']
    examples=pd.concat([g.sort_values('pressure_score_v1',ascending=False).head(12) for _,g in b[eligible].groupby(['innings','pressure_band_v1'])])
    write(examples[sample_cols],'pressure_examples')
    data_dict=[]
    original_cols=pd.read_csv(SOURCE,nrows=0).columns.tolist()
    descriptions={
        'context_verified':'Full innings has equal delivery count, batting team, per-delivery batter runs, over and within-over sequence, plus local/global player ID consistency. This is reference agreement, not an official certification.',
        'score_before':'Team runs accumulated strictly before this delivery, including reference extras and pre-innings penalties. Blank without accepted context.',
        'wickets_before':'Team wickets before delivery; retired hurt/not out excluded. Supplied wicket flag retained separately.',
        'legal_balls_before':'Previous deliveries excluding wides and no-balls; derived from reference extras.',
        'balls_remaining_before':'Recorded final quota minus prior legal deliveries. Revised games excluded from pressure v1 because revision timing is unavailable.',
        'innings_limit_balls_as_recorded':'Reference info.overs or innings target.overs converted to balls; six for super-over-like innings.',
        'chase_target_as_recorded':'Reference second-innings target or reference first-innings total+1. Final targets in DLS games may not be available at the start; such matches excluded from pressure v1.',
        'runs_required_before':'Target minus score before delivery; second innings only.',
        'current_run_rate_before':'6*score_before/legal_balls_before; blank before first legal ball.',
        'required_run_rate_before':'6*runs_required_before/balls_remaining_before; second innings only.',
        'innings_progress_before':'legal_balls_before/innings_limit_balls_as_recorded.',
        'innings_phase':'Powerplay <36 prior legal balls, middle 36–89, death >=90. Fixed full-T20 phase labels; shortened games excluded from pressure v1.',
        'prior_expected_rpo':'Earlier-date accepted standard first-innings runs/legal balls within competition group, shrunk toward 8 rpo with 2,400 pseudo-balls. Same-day and future matches excluded.',
        'pressure_eligible_v1':'Accepted context, IPL/T20I, regular innings, standard quota, no recorded revisions/miscounted overs/innings penalties, and nonterminal state.',
        'pressure_score_v1':'Rule-based 0–100 index from before-ball context only; formula and caveats in METHODOLOGY.md. Not a calibrated probability or player rating.',
        'pressure_band_v1':'High >=55, moderate >=35 and <55, ordinary <35; excluded rows have no score.',
        'source_wicket_flag_agrees':'Supplied is_wicket equals reference team-wicket event; disagreement is preserved for review.',
        'team_runs_on_delivery':'Reference batter runs plus reference extras. For verified innings, batter runs equal supplied runs_recorded on every delivery.',
        'batter_runs_on_delivery':'Supplied runs_recorded, validated against reference batter runs for accepted innings.',
        'bowler_wickets_on_delivery':'Reference wicket kinds credited to the bowler, excluding run-outs/retirements/obstruction.',
        'counts_as_legal_delivery':'False on reference wide or no-ball. Does not itself define batting balls faced.',
    }
    for col in b:
        origin='original joined CSV' if col in original_cols else 'this analysis'
        desc=descriptions.get(col,'Preserved source field; see cleaned_competition_data/data_dictionary.csv.' if origin.startswith('original') else 'Derived/reference field; see METHODOLOGY.md for definitions and provenance.')
        data_dict.append({'column':col,'dtype':str(b[col].dtype),'missing_count':int(b[col].isna().sum()),'origin':origin,'description':desc})
    write(pd.DataFrame(data_dict),'data_dictionary')
    metrics={
        'source_delivery_rows':len(b),'source_matches_with_deliveries':int(b.match_id.nunique()),
        'verified_context_deliveries':int(b.context_verified.sum()),
        'verified_context_share':float(b.context_verified.mean()),
        'verified_context_innings':int(b.loc[b.context_verified,['match_id','innings']].drop_duplicates().shape[0]),
        'verified_context_matches':int(b.loc[b.context_verified,'match_id'].nunique()),
        'pressure_eligible_deliveries':int(eligible.sum()),'pressure_eligible_matches':int(b.loc[eligible,'match_id'].nunique()),
        'high_pressure_deliveries':int(b.pressure_band_v1.eq('high').sum()),
        'high_pressure_share_of_eligible':float(b.loc[eligible,'pressure_band_v1'].eq('high').mean()),
        'high_pressure_batters':int(b.loc[b.pressure_band_v1.eq('high'),'striker_id'].nunique()),
        'high_pressure_bowlers':int(b.loc[b.pressure_band_v1.eq('high'),'bowler_id'].nunique()),
        'source_wicket_disagreements_in_sequence_matched_innings':len(mismatch_rows),
        'global_identity_conflict_innings':len(badkeys),'source_ids_sharing_reference_person':int(modes.reference_id_shared_across_source_ids.sum()),
        'official_innings_checks_passed':int(official_checks.passed.sum()),
        'high_threshold':HIGH,'moderate_threshold':MODERATE,
        'no_final_rankings':True,
        'validation_checks':['source row count preserved','delivery IDs unique',
            'all verified innings before-score equals prior-delivery cumulative total',
            'all verified innings before-wickets exclude current-delivery wicket',
            'all verified innings legal-ball count excludes current delivery',
            'all verified delivery totals reconcile batter runs plus extras',
            'excluded rows have no pressure score','eligible states have all required inputs',
            'all scores within 0–100','10 independent official innings totals/wickets/legal counts match',
            'very low and extreme required-rate examples score lower than competitive-rate example'],
    }
    (OUT/'analysis_summary.json').write_text(json.dumps(metrics,indent=2),encoding='utf-8')
    manifest={'analysis_date_local':'2026-11-14','primary_source':{'file':str(SOURCE),'sha256':checksum(SOURCE)},
        'external_scoring_references':reference_manifest,
        'attribution':'Cricsheet (https://cricsheet.org/). Supplementary extras, legality, targets and wicket context; supplied players and batting outcomes remain the analysis population.',
        'documentation':'https://cricsheet.org/format/json/','licensing':'https://cricsheet.org/licensing/',
        'official_validation_source':official_url,'external_data_added':True,
        'match_acceptance':'Unique exact date + normalized team pair; exact full-innings delivery and run/over sequences; player identity consistency.',
        'no_external_only_matches_added':True}
    (OUT/'source_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    notes=f'''# Pressure analysis v1: completed stages and methodology

## Scope
This package completes scoring validation, before-delivery context reconstruction, and an initial explainable pressure definition. It does not contain final player ratings or auction recommendations. Original cleaned data and source fields are unchanged. All {len(b):,} supplied delivery rows remain in the main file.

The supplied submission screenshot asks for a PDF/PPT or dashboard explaining methodology, reliable players and how each could strengthen Rajasthan Royals for IPL 2027. Final player-role fit and auction availability must be researched later. No current RR squad or auction availability has been assumed.

## Stage 1: scoring validation
The source runs column agrees with Cricsheet batter runs in accepted innings. extras1_runs is a category code, not a run amount; extras_2_runs is not sufficient to reconstruct complete extras. Example: source match 13511 has 100 batting runs versus England's official 103 and 99 batting runs versus West Indies' official 104. Adding one per extras event would still give only 101 for the chase, showing that a default one-run imputation is wrong.

Downloaded Cricsheet IPL and men's T20I JSON archives provide supplementary scoring context. No reference-only match or player is added to the analysis population. Each accepted innings must have a unique exact-date/team-pair match, identical full-innings delivery count, batting team, batter-run sequence, over sequence and within-over delivery sequence. Source player IDs must map consistently to reference registry people within each innings and against the global modal crosswalk. Any innings failing these checks is left unverified; no approximate alignment or run correction is forced. Crosswalks and match-level decisions are in audit/. Reference name spellings are separate from source IDs/names. Multiple source IDs for one reference person, if found, are flagged rather than merged.

{metrics['verified_context_deliveries']:,} deliveries in {metrics['verified_context_innings']:,} innings pass the context linkage ({metrics['verified_context_share']:.1%} of all supplied deliveries). Ten innings in the five-match January 2022 England–West Indies series independently reconcile to the official Windies Cricket scoreboard for total, wickets and legal balls. This small independent check is not proof that every linked innings is error-free.

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

Only accepted IPL/T20I context, innings 1/2, standard unrevised quotas, no miscounted-over/innings-penalty adjustments and nonterminal before-ball states receive a score. Other T20, super overs and unverified states are retained but excluded. Eligible deliveries: {metrics['pressure_eligible_deliveries']:,} across {metrics['pressure_eligible_matches']:,} matches.

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

Bands: high >=55, moderate >=35 and <55, ordinary <35. These thresholds and weights are starting assumptions, not fitted to famous players or chosen to force a desired top 10. Sensitivity at high thresholds 45, 50, 55, 60 and 65 is exported. Weight/formula sensitivity, innings comparability, player-ranking stability and predictive validity remain future work. {metrics['high_pressure_deliveries']:,} deliveries are high pressure at 55 ({metrics['high_pressure_share_of_eligible']:.1%} of eligible events).

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
- Independent scoreboard: {official_url}

Reproducibility: build_pressure_context.py, cached original reference archives, input checksum and archive checksums are retained locally. No originals overwritten. Scripts/reference ZIPs are excluded from the compact results ZIP but remain in the workspace.
'''
    (OUT/'METHODOLOGY.md').write_text(notes,encoding='utf-8')
    progress=f'''# Analysis progress — 14 November 2026

Completed three stages: validated scoring fields; reconstructed before-delivery state where reference alignment passed; implemented and inspected pressure v1.

- Source delivery rows preserved: {len(b):,}.
- Accepted context: {metrics['verified_context_deliveries']:,} deliveries ({metrics['verified_context_share']:.1%}), {metrics['verified_context_matches']:,} matches with at least one accepted innings.
- Pressure-eligible: {metrics['pressure_eligible_deliveries']:,} deliveries, {metrics['pressure_eligible_matches']:,} matches.
- High pressure at score >=55: {metrics['high_pressure_deliveries']:,} deliveries ({metrics['high_pressure_share_of_eligible']:.1%} of eligible).
- Independent official innings checks: 10/10 passed.
- Rankings, player-performance scoring, RR role-fit and final PDF/PPT remain outstanding.

Start with METHODOLOGY.md and coverage_and_exclusions.csv, then use pressure_eligible_v1 in deliveries_with_context_pressure_v1.csv. This is an intermediate analysis package, not a final competition submission.
'''
    (OUT/'PROGRESS.md').write_text(progress,encoding='utf-8')
    finish_package()
    print(json.dumps(metrics,indent=2),flush=True)

def finish_package():
    """Finish from verified saved outputs, avoiding recomputation after rendering failures."""
    b=pd.read_csv(OUT/'deliveries_with_context_pressure_v1.csv',
        usecols=['competition_group','pressure_band_v1','pressure_eligible_v1','innings','pressure_score_v1'])
    s=json.loads((OUT/'analysis_summary.json').read_text(encoding='utf-8'))
    first=b.pressure_eligible_v1 & b.innings.eq(1)
    chase=b.pressure_eligible_v1 & b.innings.eq(2)
    s['first_innings_high_pressure_share']=float(b.loc[first,'pressure_band_v1'].eq('high').mean())
    s['chase_high_pressure_share']=float(b.loc[chase,'pressure_band_v1'].eq('high').mean())
    s['pressure_calibration_required_before_rankings']=True
    (OUT/'analysis_summary.json').write_text(json.dumps(s,indent=2),encoding='utf-8')
    finding=f'''\n## Pressure calibration finding\nThe current common cutoff labels {s['first_innings_high_pressure_share']:.2%} of eligible first-innings events and {s['chase_high_pressure_share']:.2%} of chase events as high pressure. These formulas are not on a calibrated common scale. This is a material modeling limitation: do not pool the two high-pressure samples into final player rankings. Next compare within innings/phase/format and test alternative pressure components/calibration before selecting players. Threshold sensitivity alone does not resolve this difference.\n'''
    for name in ['METHODOLOGY.md','PROGRESS.md']:
        p=OUT/name
        content=p.read_text(encoding='utf-8')
        if '## Pressure calibration finding' not in content:p.write_text(content+finding,encoding='utf-8')
    create_chart(b)
    shutil.copy2(Path(__file__),OUT/'build_pressure_context.py')
    # Compact result package; original third-party archives remain cached separately.
    zip_path=ROOT/'pressure_analysis_steps_1_to_3.zip'
    with zipfile.ZipFile(zip_path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(OUT.rglob('*')):
            if p.is_file() and 'references' not in p.relative_to(OUT).parts and p.suffix!='.py' and p.name!='alignment_profile.csv':
                z.write(p,p.relative_to(OUT))
    with zipfile.ZipFile(zip_path) as z:assert z.testzip() is None
    print(json.dumps(s,indent=2),flush=True)
    print('RESULT ZIP',zip_path,'MB',round(zip_path.stat().st_size/1024**2,2),flush=True)

def create_chart(b):
    try:
        import matplotlib
    except ModuleNotFoundError:
        # The bundled analysis runtime lacks plotting. Use the installed plotting
        # capability only for rendering these saved results, without recomputing data.
        import subprocess
        interpreter=shutil.which('python')
        code="import sys; sys.path.insert(0,sys.argv[1]); import build_pressure_context as m; import pandas as pd; b=pd.read_csv(m.OUT/'deliveries_with_context_pressure_v1.csv',usecols=['competition_group','pressure_band_v1','pressure_eligible_v1','innings','pressure_score_v1']); m.create_chart(b)"
        subprocess.run([interpreter,'-c',code,str(ROOT)],check=True)
        return
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(12,4.8),layout='constrained')
    labels=['IPL','T20I','Other T20']
    colors={'ordinary':'#8cadd1','moderate':'#f2bc57','high':'#d34f83','excluded':'#d2d6dc'}
    bottom=np.zeros(3)
    for band in ['ordinary','moderate','high','excluded']:
        counts=np.array([int(((b.competition_group==fmt)&(b.pressure_band_v1==band)).sum()) for fmt in labels])
        axes[0].bar(labels,counts/1000,bottom=bottom/1000,color=colors[band],label=band.capitalize())
        bottom+=counts
    axes[0].set_title('Coverage and pressure bands',loc='left',fontweight='bold')
    axes[0].set_ylabel('Delivery events (thousands)')
    axes[0].legend(frameon=False,fontsize=9)
    v=b[b.pressure_eligible_v1]
    for inn,color in [(1,'#3767a0'),(2,'#d34f83')]:
        axes[1].hist(v.loc[v.innings==inn,'pressure_score_v1'],bins=np.arange(0,101,5),
            histtype='step',linewidth=2,color=color,label=f'Innings {inn}',density=True)
    axes[1].axvline(HIGH,color='#444',linestyle='--',linewidth=1,label='High cutoff: 55')
    axes[1].set_title('Initial pressure index distribution',loc='left',fontweight='bold')
    axes[1].set_xlabel('Pressure score (0–100)');axes[1].set_ylabel('Density among eligible events')
    axes[1].legend(frameon=False,fontsize=9)
    for ax in axes:
        ax.spines[['top','right']].set_visible(False)
        ax.grid(axis='y',alpha=.18);ax.set_axisbelow(True)
    fig.suptitle('Scoring context and pressure v1 — preliminary methodology',fontsize=14,fontweight='bold')
    fig.savefig(OUT/'coverage_and_pressure.png',dpi=160)
    plt.close(fig)

if __name__=='__main__':main()
