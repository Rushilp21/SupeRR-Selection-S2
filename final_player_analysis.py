"""Reproducible retrospective pressure-player analysis. No PDF/PPT output.
Input: previously verified context CSV. Libraries: pandas, numpy only.
"""
from pathlib import Path
import json, hashlib, shutil, zipfile
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'final_analysis'
OUT.mkdir(exist_ok=True)
SOURCE=ROOT/'pressure_analysis'/'deliveries_with_context_pressure_v1.csv'
SEED=20261114
MIN_TOTAL=500
MIN_HIGH=120
MIN_NORMAL=250
MIN_MATCHES=10
MIN_SEASONS=2
WICKET_VALUE=12.0
HIGH_PRIOR=150.0
NORMAL_PRIOR=300.0
UPLIFT=.2
SE_PENALTY=.5
BOOTSTRAPS=1000
CAL_KEYS=['competition_group','innings','innings_phase']
SETTINGS=[
 ('primary',.80,12,150,.2,'phase',1.0),
 ('pressure_top25',.75,12,150,.2,'phase',1.0),
 ('pressure_top15',.85,12,150,.2,'phase',1.0),
 ('pressure_top10',.90,12,150,.2,'phase',1.0),
 ('wicket_value8',.80,8,150,.2,'phase',1.0),
 ('wicket_value16',.80,16,150,.2,'phase',1.0),
 ('shrink75',.80,12,75,.2,'phase',1.0),
 ('shrink300',.80,12,300,.2,'phase',1.0),
 ('absolute_only',.80,12,150,0,'phase',1.0),
 ('uplift40',.80,12,150,.4,'phase',1.0),
 ('chase_no_closeness',.80,12,150,.2,'no_closeness',1.0),
 ('alternative_weights',.80,12,150,.2,'alternative',1.0),
 ('recent_weight',.80,12,150,.2,'phase',.85),
]

def save(d,name): d.to_csv(OUT/f'{name}.csv',index=False,na_rep='',encoding='utf-8')

def make_keys(d,cols):
    return pd.MultiIndex.from_frame(d[cols].astype('string').fillna('unknown'))

def model_predict(train,test,role):
    """Hierarchically shrunk peer run and dismissal rates; no player ID or result input."""
    base=['competition_group','innings','innings_phase']
    rolecol='role_band' if role=='batter' else 'bowling_family'
    levels=[(base,0),(base+['year'],600),(base+['year',rolecol],300),
        (base+['year',rolecol,'opponent_id','venue_country','wicket_band','chase_band'],150)]
    den=max(float(train.units.sum()),1)
    pred=np.tile([train.outcome_runs.sum()/den,train.outcome_dismissals.sum()/den],(len(test),1))
    for keys,prior in levels:
        g=train.groupby(keys,dropna=False).agg(n=('units','sum'),r=('outcome_runs','sum'),w=('outcome_dismissals','sum'))
        g.index=pd.MultiIndex.from_frame(g.index.to_frame(index=False).astype('string').fillna('unknown'))
        vals=g.reindex(make_keys(test,keys)).fillna(0).to_numpy(dtype=float)
        n=vals[:,0]
        if prior==0:
            for k in range(2): pred[:,k]=np.divide(vals[:,k+1],n,out=pred[:,k].copy(),where=n>0)
        else:
            for k in range(2): pred[:,k]=(vals[:,k+1]+prior*pred[:,k])/(n+prior)
    return pred

def crossfit(f,role):
    pred=np.empty((len(f),2))
    for fold in range(5):
        mask=f.fold.eq(fold).to_numpy()
        pred[mask]=model_predict(f.loc[~mask],f.loc[mask],role)
    return pred

def score_players(f,high,wicket_value=12,prior=150,uplift=.2,recency=1.0):
    a=f[['player_id','match_id','year','units','outcome_runs','outcome_dismissals','expected_runs','expected_dismissals']].copy()
    weight=recency**(2026-a.year)
    a['residual']=(a.outcome_runs-a.expected_runs*a.units-wicket_value*(a.outcome_dismissals-a.expected_dismissals*a.units))*f.sign*weight
    a['weighted_units']=a.units*weight
    a['high']=np.asarray(high,dtype=bool)
    h=a[a.high].groupby('player_id').agg(high_n=('weighted_units','sum'),high_residual=('residual','sum'))
    normal=a[~a.high].groupby('player_id').agg(normal_n=('weighted_units','sum'),normal_residual=('residual','sum'))
    out=h.join(normal,how='outer').fillna(0)
    out['high_shrunk']=out.high_residual/(out.high_n+prior)
    out['normal_shrunk']=out.normal_residual/(out.normal_n+NORMAL_PRIOR)
    out['uplift']=out.high_shrunk-out.normal_shrunk
    gm=a[a.high].groupby(['player_id','match_id']).agg(s=('residual','sum'),n=('weighted_units','sum')).reset_index()
    unshrunk=out.high_residual/out.high_n.replace(0,np.nan)
    gm['z2']=(gm.s-gm.player_id.map(unshrunk)*gm.n)**2
    variance=gm.groupby('player_id').agg(z2=('z2','sum'),clusters=('match_id','size'))
    out=out.join(variance)
    out['high_cluster_se']=np.sqrt(out.z2*out.clusters/(out.clusters-1).clip(lower=1))/(out.high_n+prior)
    out['rating_raw']=100*(out.high_shrunk-uplift*out.normal_shrunk-SE_PENALTY*out.high_cluster_se)
    return out,a,gm

def eligible_stats(f,high):
    a=f.copy();a['high']=np.asarray(high,dtype=bool)
    g=a.groupby('player_id').agg(total_units=('units','sum'),total_matches=('match_id','nunique'))
    h=a[a.high & a.units.gt(0)].groupby('player_id').agg(high_units=('units','sum'),high_matches=('match_id','nunique'),high_seasons=('year','nunique'))
    n=a[~a.high].groupby('player_id').units.sum().rename('normal_units')
    g=g.join(h).join(n).fillna(0)
    g['eligible']=(g.total_units.ge(MIN_TOTAL)&g.high_units.ge(MIN_HIGH)&g.normal_units.ge(MIN_NORMAL)&g.high_matches.ge(MIN_MATCHES)&g.high_seasons.ge(MIN_SEASONS))
    return g

def pressure_flags(f,setting):
    _,q,_,_,_,kind,_=setting
    col={'phase':'pressure_percentile','no_closeness':'pressure_percentile_no_closeness','alternative':'pressure_percentile_alternative'}[kind]
    return f[col].ge(q).to_numpy()

def bootstrap_primary(f,candidates,primary):
    # Whole-match resampling, same draws for all candidate players. Nuisance models,
    # calibration and candidate eligibility fixed; not a full model-refitting interval.
    high=f.pressure_percentile.ge(.8).to_numpy()
    _,a,_=score_players(f,high)
    a=a[a.player_id.isin(candidates)].copy()
    matches=sorted(f.match_id.unique())
    idx=pd.Index(candidates); mids=pd.Index(matches)
    def matrix(mask,value):
        p=a.loc[mask].groupby(['player_id','match_id'])[value].sum().unstack(fill_value=0)
        return p.reindex(index=idx,columns=mids,fill_value=0).to_numpy(float)
    hs=matrix(a.high,'residual');hn=matrix(a.high,'weighted_units')
    ns=matrix(~a.high,'residual');nn=matrix(~a.high,'weighted_units')
    rng=np.random.default_rng(SEED)
    weights=rng.multinomial(len(matches),np.full(len(matches),1/len(matches)),size=BOOTSTRAPS).T
    hmean=(hs@weights)/(hn@weights+HIGH_PRIOR)
    nmean=(ns@weights)/(nn@weights+NORMAL_PRIOR)
    penalty=primary.reindex(idx).high_cluster_se.to_numpy()[:,None]
    scores=100*(hmean-UPLIFT*nmean-SE_PENALTY*penalty)
    ranks=np.empty_like(scores)
    for k in range(BOOTSTRAPS):ranks[:,k]=pd.Series(scores[:,k]).rank(ascending=False,method='min').to_numpy()
    return pd.DataFrame({'player_id':candidates,'primary_bootstrap_score_p05':np.quantile(scores,.05,axis=1),
        'primary_bootstrap_score_p95':np.quantile(scores,.95,axis=1),
        'primary_bootstrap_top10_frequency':(ranks<=10).mean(axis=1),
        'primary_bootstrap_rank_p05':np.quantile(ranks,.05,axis=1),
        'primary_bootstrap_rank_p95':np.quantile(ranks,.95,axis=1)})

def holdout_check(f,role):
    train=f[f.year.lt(2026)].copy().reset_index(drop=True)
    test=f[f.year.eq(2026)].copy().reset_index(drop=True)
    if len(test)==0:return {},pd.DataFrame()
    # A distinct historical check: pressure cutoffs and outcome baselines use pre-2026 only.
    positive=train[train.units.gt(0)].drop_duplicates('delivery_id')
    cut=positive.groupby(CAL_KEYS).pressure_score_v1.quantile(.8)
    cut.index=pd.MultiIndex.from_frame(cut.index.to_frame(index=False).astype('string').fillna('unknown'))
    train['holdout_high']=train.pressure_score_v1.ge(pd.Series(cut.reindex(make_keys(train,CAL_KEYS)).to_numpy(),index=train.index))
    test['holdout_high']=test.pressure_score_v1.ge(pd.Series(cut.reindex(make_keys(test,CAL_KEYS)).to_numpy(),index=test.index))
    assert train.holdout_high.any() and test.holdout_high.any(), 'Holdout calibration must cover both periods.'
    pred=crossfit(train,role);train[['expected_runs','expected_dismissals']]=pred
    test[['expected_runs','expected_dismissals']]=model_predict(train,test,role)
    est=eligible_stats(train,train.holdout_high)
    trainrating,_,_=score_players(train,train.holdout_high)
    qualified=est.index[est.eligible]
    assert len(qualified)>=10, 'Historical validation requires a real eligible comparison pool.'
    chosen=trainrating.reindex(qualified).sort_values('rating_raw',ascending=False).head(10).index
    testrating,ta,_=score_players(test,test.holdout_high)
    teststats=eligible_stats(test,test.holdout_high)
    common=trainrating.index.intersection(testrating.index)
    common=common[teststats.reindex(common).high_units.fillna(0).ge(30).to_numpy() & est.reindex(common).eligible.fillna(False).to_numpy()]
    rho=float(trainrating.loc[common,'rating_raw'].rank().corr(testrating.loc[common,'rating_raw'].rank())) if len(common)>2 else None
    def cohort(ids):
        g=ta[ta.high & ta.player_id.isin(ids)]
        return float(g.residual.sum()/g.weighted_units.sum()) if g.weighted_units.sum()>0 else None
    result={'role':role,'training_years':'2022-2025','test_year':2026,'training_eligible_players':len(qualified),
        'training_top10_observed_in_2026':int(teststats.reindex(chosen).total_units.fillna(0).gt(0).sum()),
        'rank_correlation_players_with_30_test_pressure_units':len(common),'train_test_rank_spearman':rho,
        'training_top10_2026_pressure_residual_per_unit':cohort(chosen),
        'other_training_eligible_2026_pressure_residual_per_unit':cohort(qualified.difference(chosen)),
        'interpretation':'Diagnostic historical test; final ranking uses all available years. Models and calibration for this check use no 2026 rows. Not a guaranteed forecast.'}
    table=teststats.join(testrating[['rating_raw','high_shrunk']],how='left')
    table['training_eligible']=table.index.isin(qualified);table['training_top10']=table.index.isin(chosen)
    table['training_rating']=trainrating.rating_raw.reindex(table.index)
    return result,table.reset_index()

def role_analysis(f,role):
    print('Fitting held-out-match peer baselines:',role,flush=True)
    pred=crossfit(f,role)
    f[['expected_runs','expected_dismissals']]=pred
    assert np.isfinite(pred).all()
    high=f.pressure_percentile.ge(.8)
    elig=eligible_stats(f,high)
    primary,a,gm=score_players(f,high)
    candidates=sorted(elig.index[elig.eligible].tolist())
    assert len(candidates)>=10,(role,len(candidates))
    allscores=[]
    for setting in SETTINGS:
        name,q,value,prior,uplift,kind,recency=setting
        flag=pressure_flags(f,setting)
        scores,_,_=score_players(f,flag,value,prior,uplift,recency)
        st=eligible_stats(f,flag)
        ss=scores.reindex(candidates).copy()
        support=st.reindex(candidates)
        supported=support.high_units.ge(50)&support.high_matches.ge(5)
        ss.loc[~supported,'rating_raw']=np.nan
        ranks=ss.rating_raw.rank(ascending=False,method='average').fillna(len(candidates)+1)
        for pid in candidates:
            allscores.append({'role':role,'scenario':name,'player_id':pid,'rating_raw':ss.loc[pid,'rating_raw'],
                'scenario_rank':ranks.loc[pid],'scenario_high_units':support.loc[pid,'high_units'],
                'scenario_high_matches':support.loc[pid,'high_matches'],'scenario_supported':bool(supported.loc[pid])})
    variants=pd.DataFrame(allscores)
    consensus=variants.groupby('player_id').agg(mean_scenario_rank=('scenario_rank','mean'),
        best_scenario_rank=('scenario_rank','min'),worst_scenario_rank=('scenario_rank','max'),
        scenario_top10_frequency=('scenario_rank',lambda s:s.le(10).mean()),
        supported_scenarios=('scenario_supported','sum'))
    rating=elig.join(primary.drop(columns=['high_n','normal_n']),how='left')
    rating=rating.join(consensus)
    rating['primary_rank']=rating.loc[rating.eligible,'rating_raw'].rank(ascending=False,method='min')
    ordered=rating[rating.eligible].sort_values(['mean_scenario_rank','rating_raw'],ascending=[True,False]).index
    rating['final_rank']=np.nan
    rating.loc[ordered,'final_rank']=np.arange(1,len(ordered)+1)
    rating['consensus_index']=100*(1-(rating.mean_scenario_rank-1)/(len(candidates)-1))
    print('Match bootstrap and season diagnostics:',role,'eligible',len(candidates),flush=True)
    boot=bootstrap_primary(f,candidates,primary)
    rating=rating.join(boot.set_index('player_id'))
    # Descriptive primary-pressure statistics. All dismissed players attributed by ID.
    for label,mask in [('high',high),('ordinary',~high)]:
        g=f[mask].groupby('player_id').agg(runs=('outcome_runs','sum'),dismissals=('outcome_dismissals','sum'),
            units=('units','sum'),events=('delivery_id','size'))
        for col in ['runs','dismissals','events']:rating[label+'_'+col]=g[col].reindex(rating.index).fillna(0)
        if role=='batter':rating[label+'_strike_rate']=100*g.runs/g.units.replace(0,np.nan)
        else:rating[label+'_economy']=6*g.runs/g.units.replace(0,np.nan)
    primary_a=a.copy()
    seasons=primary_a[primary_a.high].groupby(['player_id','year']).agg(high_units=('weighted_units','sum'),residual=('residual','sum')).reset_index()
    seasons['adjusted_impact_per100']=100*seasons.residual/seasons.high_units.replace(0,np.nan)
    informative=seasons[seasons.high_units.ge(20)]
    season_summary=informative.groupby('player_id').agg(informative_pressure_seasons=('year','size'),
        positive_pressure_seasons=('adjusted_impact_per100',lambda s:s.gt(0).sum()))
    rating=rating.join(season_summary)
    mpositive=gm[gm.n.gt(0)].groupby('player_id').s.agg(lambda s:s.gt(0).mean())
    rating['positive_pressure_match_share']=mpositive
    # Separate format audit exposes differing IPL/T20I evidence instead of hiding it.
    formats=[]
    for fmt,g in f.groupby('competition_group'):
        s,_,_=score_players(g,g.pressure_percentile.ge(.8))
        for pid,row in s.iterrows():formats.append({'role':role,'player_id':pid,'competition_group':fmt,
            'high_units':row.high_n,'high_adjusted_shrunk_per100':100*row.high_shrunk,'rating_raw':row.rating_raw})
    names=pd.read_csv(ROOT/'cleaned_competition_data'/'players_clean.csv',usecols=['player_id','player_name']).set_index('player_id')
    rating=rating.join(names)
    # Coverage represents the source rows whose context was accepted, not all career data.
    src=f[f.units.gt(0)]
    profile=src.groupby('player_id').agg(dominant_phase=('innings_phase',lambda s:s.mode().iloc[0]),
        ipl_units=('competition_group',lambda s:s.eq('IPL').sum()),t20i_units=('competition_group',lambda s:s.eq('T20I').sum()))
    # Bowler unit counts explicitly exclude illegal deliveries.
    if role=='bowler':
        piv=f.pivot_table(index='player_id',columns='competition_group',values='units',aggfunc='sum',fill_value=0)
        profile['ipl_units']=piv.get('IPL',0);profile['t20i_units']=piv.get('T20I',0)
    if role=='batter':profile['typical_batting_order']=src.groupby('player_id').batting_order.median()
    else:profile['bowling_family']=src.groupby('player_id').bowling_family.agg(lambda s:s.mode().iloc[0])
    rating=rating.join(profile)
    rating['role']=role
    rating=rating.reset_index().sort_values(['eligible','final_rank'],ascending=[False,True],na_position='last')
    top=rating[rating.final_rank.le(10)].copy()
    assert len(top)==10 and top.player_id.is_unique and top.eligible.all()
    save(rating,role+'_all_player_ratings')
    save(top,'top10_'+('batters' if role=='batter' else 'bowlers'))
    save(variants,role+'_scenario_rankings')
    save(seasons,role+'_season_consistency')
    save(pd.DataFrame(formats),role+'_format_evidence')
    save(gm,role+'_match_pressure_impact')
    save(f[['delivery_id','player_id','units','outcome_runs','outcome_dismissals','expected_runs','expected_dismissals','fold']],role+'_out_of_fold_expectations')
    print('Historical 2026 holdout:',role,flush=True)
    hold,holdtable=holdout_check(f,role)
    save(holdtable,role+'_2026_holdout')
    return top,rating,hold

def build_frames(b):
    common=['delivery_id','match_id','year','fold','competition_group','innings','innings_phase','venue_country',
        'wicket_band','chase_band','pressure_score_v1','pressure_percentile','pressure_percentile_no_closeness','pressure_percentile_alternative']
    bat=b[common].copy()
    bat['player_id']=b.striker_id.astype(int);bat['batting_order']=b.batting_order
    bat['role_band']=pd.cut(b.batting_order,[0,3,5,7,20],labels=['top1_3','middle4_5','lower6_7','tail8plus']).astype('string').fillna('unknown')
    bat['opponent_id']=b.bowling_team_id
    bat['units']=b.wide_runs.eq(0).astype(int)
    bat['outcome_runs']=b.batter_runs_on_delivery
    dismissed=b.reference_dismissed_player_ids.fillna('[]').map(json.loads)
    bat['outcome_dismissals']=[int(pid in ids) for pid,ids in zip(b.reference_batter_id,dismissed)]
    nonmask=np.array([pid in ids for pid,ids in zip(b.reference_non_striker_id,dismissed)])
    extra=bat.loc[nonmask].copy()
    extra['player_id']=b.loc[nonmask,'non_striker_id'].astype(int)
    order=b.loc[nonmask,'non_striker_xi_batting_order']
    extra['batting_order']=order
    extra['role_band']=pd.cut(order,[0,3,5,7,20],labels=['top1_3','middle4_5','lower6_7','tail8plus']).astype('string').fillna('unknown')
    extra['units']=0;extra['outcome_runs']=0;extra['outcome_dismissals']=1
    bat=pd.concat([bat,extra],ignore_index=True)
    bat['sign']=1
    bowl=b[common].copy()
    bowl['player_id']=b.bowler_id.astype(int);bowl['opponent_id']=b.batting_team_id
    bowl['bowling_family']=b.pace_or_spin.fillna('Unknown')
    bowl['units']=b.counts_as_legal_delivery.astype(int)
    bowl['outcome_runs']=b.batter_runs_on_delivery+b.wide_runs+b.no_ball_runs
    bowl['outcome_dismissals']=b.bowler_wickets_on_delivery
    bowl['sign']=-1
    assert np.isclose(bat.outcome_runs.sum(),b.batter_runs_on_delivery.sum())
    assert bat.outcome_dismissals.sum()==b.team_wickets_on_delivery.sum()
    assert bowl.outcome_runs.sum()==(b.team_runs_on_delivery-b.bye_runs-b.leg_bye_runs-b.penalty_runs_on_delivery).sum()
    return bat,bowl

def main():
    print('Loading verified context and freezing analysis specification...',flush=True)
    spec={'seed':SEED,'eligibility':{'total_units':MIN_TOTAL,'high_units':MIN_HIGH,'ordinary_units':MIN_NORMAL,
        'high_matches':MIN_MATCHES,'high_seasons':MIN_SEASONS},'pressure':'Within-format/innings/phase empirical percentile of before-ball v1 score, high >=80th percentile.',
        'settings':SETTINGS,'consensus':'Equal-weight mean scenario rank among primary-eligible players.',
        'bootstrap_replicates':BOOTSTRAPS,'no_pdf_or_ppt':True}
    (OUT/'analysis_specification.json').write_text(json.dumps(spec,indent=2),encoding='utf-8')
    use=['delivery_id','match_id','match_date','competition_group','innings','innings_phase','venue_country','batting_order',
        'striker_id','non_striker_id','bowler_id','batting_team_id','bowling_team_id','pace_or_spin',
        'pressure_eligible_v1','pressure_score_v1','pressure_lateness','pressure_wicket_stress','pressure_scoring_deficit',
        'pressure_chase_load','pressure_chase_closeness','knock_out','wickets_before','chase_rate_ratio_before',
        'batter_runs_on_delivery','wide_runs','no_ball_runs','bye_runs','leg_bye_runs','penalty_runs_on_delivery',
        'team_runs_on_delivery','bowler_wickets_on_delivery','team_wickets_on_delivery','reference_dismissed_player_ids',
        'reference_batter_id','reference_non_striker_id','counts_as_legal_delivery','non_striker_xi_batting_order']
    allrows=pd.read_csv(SOURCE,usecols=use,low_memory=False)
    b=allrows[allrows.pressure_eligible_v1].copy().reset_index(drop=True)
    b['year']=b.match_date.str[:4].astype(int)
    b['fold']=(b.match_id.astype(int)*2654435761%4294967296%5).astype(int)
    b['wicket_band']=pd.cut(b.wickets_before,[-1,2,5,10],labels=['0_2','3_5','6plus']).astype('string')
    b['chase_band']=pd.cut(b.chase_rate_ratio_before,[-np.inf,.75,1.25,np.inf],labels=['low','par','high']).astype('string').fillna('first_innings')
    b['pressure_raw_no_closeness']=np.where(b.innings.eq(1),b.pressure_score_v1,
        45*b.pressure_lateness+30*b.pressure_chase_load+15*b.pressure_wicket_stress+10*b.knock_out)
    b['pressure_raw_alternative']=np.where(b.innings.eq(1),
        40*b.pressure_lateness+25*b.pressure_wicket_stress+25*b.pressure_scoring_deficit+10*b.knock_out,
        b.pressure_chase_closeness*(35*b.pressure_lateness+35*b.pressure_chase_load+20*b.pressure_wicket_stress+10*b.knock_out))
    for source,target in [('pressure_score_v1','pressure_percentile'),('pressure_raw_no_closeness','pressure_percentile_no_closeness'),('pressure_raw_alternative','pressure_percentile_alternative')]:
        b[target]=b.groupby(CAL_KEYS)[source].rank(method='average',pct=True)
    b['high_pressure_v2']=b.pressure_percentile.ge(.8)
    assert b.delivery_id.is_unique and len(b)==166227
    save(b[['delivery_id','match_id','year','competition_group','innings','innings_phase','pressure_score_v1',
        'pressure_percentile','pressure_percentile_no_closeness','pressure_percentile_alternative','high_pressure_v2']],
        'delivery_pressure_calibration_v2')
    calibration=b.groupby(CAL_KEYS).agg(deliveries=('delivery_id','size'),high_deliveries=('high_pressure_v2','sum'),
        raw_p80=('pressure_score_v1',lambda s:s.quantile(.8))).reset_index()
    calibration['high_share']=calibration.high_deliveries/calibration.deliveries
    save(calibration,'pressure_calibration_summary')
    bat,bowl=build_frames(b)
    topbat,allbat,holdbat=role_analysis(bat,'batter')
    topbowl,allbowl,holdbowl=role_analysis(bowl,'bowler')
    holds=[holdbat,holdbowl]
    (OUT/'holdout_validation.json').write_text(json.dumps(holds,indent=2),encoding='utf-8')
    # Original-supply coverage by player, including rows omitted from context modeling.
    original=pd.read_csv(SOURCE,usecols=['striker_id','bowler_id','pressure_eligible_v1'],low_memory=False)
    coverage=[]
    for role,col in [('batter','striker_id'),('bowler','bowler_id')]:
        total=original.groupby(col).size();accepted=original[original.pressure_eligible_v1].groupby(col).size()
        for pid,n in total.items():coverage.append({'role':role,'player_id':int(pid),'source_delivery_events':int(n),
            'accepted_delivery_events':int(accepted.get(pid,0)),'accepted_share':float(accepted.get(pid,0)/n)})
    save(pd.DataFrame(coverage),'player_source_coverage')
    # Role-fit descriptions are derived from observed cricket roles, not auction availability.
    fits=[]
    for role,top in [('batter',topbat),('bowler',topbowl)]:
        for r in top.itertuples(index=False):
            if role=='batter':
                order=r.typical_batting_order
                fit='Top-order scoring and pressure recovery' if order<=3 else ('Middle-order scoring and chase control' if order<=5 else 'Finishing and late-innings scoring')
            else:fit=f'{r.bowling_family} bowling; strongest exposure in {r.dominant_phase} overs'
            fits.append({'category':role,'rank':int(r.final_rank),'player_id':int(r.player_id),'player_name':r.player_name,
                'observed_role_fit_for_RR':fit,'auction_availability':'Not established; this is a performance ranking, not a confirmed purchasable-player list.'})
    save(pd.DataFrame(fits),'rr_role_fit')
    summary={'analysis_period':[str(b.match_date.min()),str(b.match_date.max())],
        'source_rows':len(allrows),'model_delivery_rows':len(b),'model_matches':int(b.match_id.nunique()),
        'high_pressure_events':int(b.high_pressure_v2.sum()),'high_pressure_share':float(b.high_pressure_v2.mean()),
        'eligible_batters':int(allbat.eligible.sum()),'eligible_bowlers':int(allbowl.eligible.sum()),
        'scenarios':len(SETTINGS),'bootstrap_samples':BOOTSTRAPS,
        'batting_primary_dismissals_attributed':int(bat.outcome_dismissals.sum()),
        'bowler_credited_wickets':int(bowl.outcome_dismissals.sum()),
        'final_batters':topbat[['final_rank','player_id','player_name','consensus_index','high_units','high_matches','high_strike_rate','primary_bootstrap_top10_frequency','scenario_top10_frequency']].to_dict('records'),
        'final_bowlers':topbowl[['final_rank','player_id','player_name','consensus_index','high_units','high_matches','high_economy','high_dismissals','primary_bootstrap_top10_frequency','scenario_top10_frequency']].to_dict('records'),
        'validation':['original 166227 eligible unique deliveries retained','all batsman dismissals assigned to dismissed source player including non-striker run-outs',
            'bowler runs exclude byes/leg-byes/penalties','five folds isolate whole matches','expectations finite',
            'minimum sample rules enforced','13 predeclared scenarios','1000 whole-match conditional bootstrap draws',
            '2026 diagnostic uses pre-2026 training and cutoffs','exactly 10 unique eligible IDs per final list'],
        'main_analysis_complete':True,'pdf_or_ppt_created':False}
    (OUT/'final_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    write_methodology(summary,holds)
    write_results()
    notices=ROOT/'pressure_analysis'/'third_party_notices'
    if notices.exists():shutil.copytree(notices,OUT/'third_party_notices',dirs_exist_ok=True)
    shutil.copy2(ROOT/'pressure_analysis'/'source_manifest.json',OUT/'context_source_manifest.json')
    shutil.copy2(Path(__file__),OUT/Path(__file__).name)
    package_results()
    print(json.dumps(summary,indent=2),flush=True)
    print('HOLDOUT',json.dumps(holds,indent=2),flush=True)

def write_results():
    s=json.loads((OUT/'final_summary.json').read_text(encoding='utf-8'))
    holds=json.loads((OUT/'holdout_validation.json').read_text(encoding='utf-8'))
    s['historical_holdout']=holds
    s['forecast_validation_conclusion']='Weak persistence: pre-2026 batting top10 underperformed other eligible batters in 2026; bowler rank persistence was near zero. Rankings describe historical evidence and do not establish a reliable 2027 forecast.'
    (OUT/'final_summary.json').write_text(json.dumps(s,indent=2),encoding='utf-8')
    bat=pd.read_csv(OUT/'top10_batters.csv');bowl=pd.read_csv(OUT/'top10_bowlers.csv')
    text='''# Final historical pressure-performance conclusions

The ordered lists below summarize the supplied 2022–2026 sample under an explicit, tested model. They are descriptive rankings with uncertainty; they do not establish psychological clutch ability or guaranteed future form. No PDF/PPT was created.

## Top 10 batters
Rank | Batter | Pressure balls | Pressure matches | Pressure runs | Pressure SR
---:|---|---:|---:|---:|---:
'''
    for r in bat.itertuples(index=False):text+=f'{int(r.final_rank)} | {r.player_name} | {int(r.high_units)} | {int(r.high_matches)} | {int(r.high_runs)} | {r.high_strike_rate:.1f}\n'
    text+='\n## Top 10 bowlers\nRank | Bowler | Pressure legal balls | Pressure matches | Pressure wickets | Pressure economy\n---:|---|---:|---:|---:|---:\n'
    for r in bowl.itertuples(index=False):text+=f'{int(r.final_rank)} | {r.player_name} | {int(r.high_units)} | {int(r.high_matches)} | {int(r.high_dismissals)} | {r.high_economy:.2f}\n'
    text+='''
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
'''
    for h in holds:
        text+=f"- {h['role'].capitalize()}: earlier-period vs 2026 rank correlation {h['train_test_rank_spearman']:.3f} across {h['rank_correlation_players_with_30_test_pressure_units']} comparable players. Pre-2026 top10 pressure residual in 2026: {h['training_top10_2026_pressure_residual_per_unit']:.3f} per unit versus {h['other_training_eligible_2026_pressure_residual_per_unit']:.3f} for other training-eligible players.\n"
    text+='''
The batting training shortlist underperformed its comparison group in 2026, and bowling rank persistence was near zero. These findings do not support strong predictive claims for IPL 2027. Final rankings use all available historical evidence; no specification was tuned to hide this unfavorable validation. Missing context and selected sample coverage remain additional limitations.

## Rajasthan Royals use
Observed-role profiles are in rr_role_fit.csv. Riyan Parag is already listed in RR's official published 2026 squad: https://www.rajasthanroyals.com/rr-players . The ranking can inform role discussions, including middle-order batting, finishing, wicket-taking spin and late-over pace. Actual releases, auction eligibility/availability, price, overseas slots and existing-squad needs were not established by this statistical analysis. In particular, T20I-only players in these lists must not be represented as confirmed IPL auction options.

The main analysis is complete. Final deliverables are CSV/JSON/Markdown and a ZIP; no report was submitted to Unstop. See METHODOLOGY_AND_CONCLUSIONS.md for formulas and final_summary.json for machine-readable results. Cricsheet supplementary-data attribution and original license notices are included.
'''
    (OUT/'RESULTS.md').write_text(text,encoding='utf-8')
    fit=pd.read_csv(OUT/'rr_role_fit.csv')
    fit['verified_current_RR_context']=np.where(fit.player_name.eq('Riyan Parag'),
        'Listed in official published RR 2026 squad; existing player, not a new acquisition recommendation.',
        'Current acquisition status not assessed.')
    fit['roster_reference']=np.where(fit.player_name.eq('Riyan Parag'),'https://www.rajasthanroyals.com/rr-players','')
    save(fit,'rr_role_fit')

def package_results():
    with zipfile.ZipFile(ROOT/'final_player_analysis.zip','w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in OUT.rglob('*'):
            if p.is_file():z.write(p,p.relative_to(OUT))
    with zipfile.ZipFile(ROOT/'final_player_analysis.zip') as z:assert z.testzip() is None

def write_methodology(s,holds):
    text=f'''# Final player analysis — 14 November 2026

## What was analyzed
Supplied IPL/T20I data from {s['analysis_period'][0]} to {s['analysis_period'][1]}. Primary population remains the supplied data; Cricsheet supplementary extras/legality/targets were previously matched with strict innings/identity checks. Of 200,999 supplied delivery events, {s['model_delivery_rows']:,} from {s['model_matches']} matches have accepted standard-game context. Missing/unverified contexts, revised games and super overs remain excluded. No PDF or PPT was made.

## Pressure calibration
The initial raw pressure score overselected first innings. We now label high RELATIVE pressure at the top 20% within each competition group × innings × phase (12 cells). This compares openers with openers and death situations with death situations; it does not claim powerplay pressure and death pressure are psychologically identical. The underlying raw scores use pre-delivery resources, scoring difficulty and knockout context. No current ball result or final match winner is a pressure input. Empirical percentile calibration uses the retrospective context distribution across the analysis period, not a real-time forecasting claim. Independent 2026 checks use only earlier calibration data. High events: {s['high_pressure_events']:,} ({s['high_pressure_share']:.1%}).

## Outcomes and attribution
Batting utility = batter runs - 12 × individual dismissals. Every dismissal is allocated to its named reference player; non-striker run-outs have zero faced-ball exposure but still carry their actual dismissal cost. Retired hurt/not-out is excluded; retired out/obstruction retained as individual dismissals. Batting exposure is non-wide deliveries, including no-balls; wide dismissals count without a ball-faced denominator. Batting strike rate in descriptive output uses that convention.
Bowling utility = 12 × bowler-credited wickets - bowler runs conceded. Bowler runs = batter runs + wides + no-ball penalties, excluding byes, leg-byes and penalty runs. Bowler exposure is legal balls; illegal delivery costs and any credited wickets remain in totals. Economy uses legal balls. Run-outs/retirements/obstruction do not count as bowler wickets.

## Fair peer expectations
We estimate run and dismissal rates separately, without player ID or final results as predictors. Whole matches are assigned to five deterministic folds. Each delivery receives expectations trained on other folds only. Hierarchical groups: format/innings/phase; then year; then batting-order band (or bowling family); then opponent team, venue country, wickets band and chase-demand band. Sparse child groups shrink toward their parent with 600, 300 and 150 exposure-unit pseudo-counts. Expected outcome = expected per-unit rate × delivery exposure. This is a transparent peer-rate model, not a causal estimate; opponent and venue adjustments are incomplete, especially for sparse opponents. Out-of-fold predictions are exported.

## Player score and reliability
For each player, context-adjusted high-pressure impact h = total high-pressure utility residual/(high units+150). Usual impact u = normal-pressure residual/(normal units+300). The primary score per 100 exposure units is 100×[h - 0.2u - 0.5SE(h)]. Thus the underlying performance term is 80% absolute adjusted pressure performance plus 20% uplift from usual performance; the uncertainty term penalizes inconsistent/small samples. SE uses whole-match clusters. Positive match/season shares are separately exported, not silently treated as guarantees.

Eligibility was fixed before viewing ranking names: >=500 total units, >=120 high units, >=250 ordinary units, >=10 high-pressure matches and >=2 high-pressure calendar seasons. The same count rules apply to faced balls for batting and legal deliveries for bowling. Eligible pool: {s['eligible_batters']} batters and {s['eligible_bowlers']} bowlers. This deliberately excludes exciting small samples; exclusion is not evidence of poor ability.

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
'''
    (OUT/'METHODOLOGY_AND_CONCLUSIONS.md').write_text(text,encoding='utf-8')

if __name__=='__main__':main()
