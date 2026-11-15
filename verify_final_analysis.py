from pathlib import Path
import json,hashlib,zipfile
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'final_analysis'
SRC=ROOT/'pressure_analysis'/'deliveries_with_context_pressure_v1.csv'
source=pd.read_csv(SRC,usecols=['delivery_id','match_id','match_date','competition_group','innings','innings_phase',
    'venue_country','batting_order','striker_id','non_striker_id','batting_team_id','bowling_team_id','pace_or_spin',
    'wickets_before','chase_rate_ratio_before','non_striker_xi_batting_order'],low_memory=False)
cal=pd.read_csv(OUT/'delivery_pressure_calibration_v2.csv')
assert len(cal)==166227 and cal.delivery_id.is_unique
assert cal.high_pressure_v2.equals(cal.pressure_percentile.ge(.8))
assert cal.pressure_percentile.between(0,1).all()
assert cal.delivery_id.isin(source.delivery_id).all()
checks=['166227 unique source deliveries retained in calibration','all high-pressure flags agree with calibrated percentile']
for role,filename in [('batter','top10_batters'),('bowler','top10_bowlers')]:
    allplayers=pd.read_csv(OUT/f'{role}_all_player_ratings.csv')
    top=pd.read_csv(OUT/f'{filename}.csv')
    assert top.player_id.is_unique and top.final_rank.tolist()==list(range(1,11))
    assert (top.total_units>=500).all() and (top.high_units>=120).all() and (top.normal_units>=250).all()
    assert (top.high_matches>=10).all() and (top.high_seasons>=2).all()
    candidates=allplayers[allplayers.eligible]
    assert candidates.final_rank.is_unique
    variants=pd.read_csv(OUT/f'{role}_scenario_rankings.csv')
    assert variants.scenario.nunique()==13
    means=variants.groupby('player_id').scenario_rank.mean()
    assert np.allclose(candidates.set_index('player_id').mean_scenario_rank.sort_index(),means.sort_index())
    assert np.isclose(candidates.primary_bootstrap_top10_frequency.sum(),10)
    assert candidates.primary_bootstrap_score_p05.le(candidates.primary_bootstrap_score_p95).all()
    f=pd.read_csv(OUT/f'{role}_out_of_fold_expectations.csv')
    assert f.groupby('delivery_id').fold.nunique().eq(1).all()
    # Rebuild independent context groups, then manually audit predictions from ten
    # sampled rows without calling the implementation's model_predict function.
    f=f.merge(source,on='delivery_id',how='left',validate='many_to_one')
    assert f.match_id.notna().all()
    assert f.groupby('match_id').fold.nunique().eq(1).all()
    f['year']=f.match_date.str[:4].astype(int)
    f['wicket_band']=pd.cut(f.wickets_before,[-1,2,5,10],labels=['0_2','3_5','6plus']).astype('string')
    f['chase_band']=pd.cut(f.chase_rate_ratio_before,[-np.inf,.75,1.25,np.inf],labels=['low','par','high']).astype('string').fillna('first_innings')
    if role=='batter':
        orders=np.where(f.player_id.eq(f.striker_id),f.batting_order,f.non_striker_xi_batting_order)
        f['role_band']=pd.cut(orders,[0,3,5,7,20],labels=['top1_3','middle4_5','lower6_7','tail8plus']).astype('string').fillna('unknown')
        f['opponent_id']=f.bowling_team_id;rolecol='role_band';sign=1
    else:
        f['bowling_family']=f.pace_or_spin.fillna('Unknown');f['opponent_id']=f.batting_team_id;rolecol='bowling_family';sign=-1
    base=['competition_group','innings','innings_phase']
    levels=[(base,0),(base+['year'],600),(base+['year',rolecol],300),
        (base+['year',rolecol,'opponent_id','venue_country','wicket_band','chase_band'],150)]
    for _,r in f.sample(10,random_state=20261114).iterrows():
        train=f[f.fold.ne(r.fold)]
        assert not train.match_id.eq(r.match_id).any()
        expected=np.array([train.outcome_runs.sum(),train.outcome_dismissals.sum()])/train.units.sum()
        for keys,prior in levels:
            mask=np.ones(len(train),dtype=bool)
            for c in keys:mask &= train[c].astype('string').fillna('unknown').eq(str(r[c]) if pd.notna(r[c]) else 'unknown').to_numpy()
            g=train.loc[mask]
            if prior==0:
                if g.units.sum()>0:expected=np.array([g.outcome_runs.sum(),g.outcome_dismissals.sum()])/g.units.sum()
            else:expected=(np.array([g.outcome_runs.sum(),g.outcome_dismissals.sum()])+prior*expected)/(g.units.sum()+prior)
        assert np.allclose(expected,[r.expected_runs,r.expected_dismissals]),(role,r.delivery_id,expected)
    f=f.merge(cal[['delivery_id','high_pressure_v2']],on='delivery_id',how='left',validate='many_to_one')
    f['resid']=sign*((f.outcome_runs-f.expected_runs*f.units)-12*(f.outcome_dismissals-f.expected_dismissals*f.units))
    hp=f[f.high_pressure_v2].groupby('player_id').agg(n=('units','sum'),r=('resid','sum'))
    for r in top.itertuples(index=False):
        assert np.isclose(r.high_shrunk,hp.loc[r.player_id,'r']/(hp.loc[r.player_id,'n']+150))
    checks.extend([f'{role}: 10 unique eligible ordered finalists',f'{role}: consensus ranks independently reconciled',
        f'{role}: 1000-bootstrap inclusion frequencies sum to 10',f'{role}: all match folds isolated',
        f'{role}: 10 peer predictions independently recomputed',f'{role}: top10 primary shrunk impacts reconciled'])
holds=json.loads((OUT/'holdout_validation.json').read_text())
assert all(h['training_eligible_players']>=10 for h in holds)
assert all(h['rank_correlation_players_with_30_test_pressure_units']>=10 for h in holds)
assert not any(p.suffix.lower() in ['.pdf','.ppt','.pptx'] for p in OUT.rglob('*'))
checks+=['nonempty historical holdout comparison pools','no PDF/PPT created']
report={'all_checks_passed':True,'checks':checks,'sampled_peer_predictions':20}
(OUT/'verification_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
