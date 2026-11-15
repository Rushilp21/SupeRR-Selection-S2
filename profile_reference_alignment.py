import json, zipfile, pathlib, collections, re
import pandas as pd
ROOT=pathlib.Path(__file__).resolve().parent
REF=ROOT/'pressure_analysis'/'references'
def team(s):
 s=str(s).replace('Royal Challengers Bangalore','Royal Challengers Bengaluru').replace('United States of America','United States')
 return re.sub('[^a-z0-9]','',s.lower())
index=collections.defaultdict(list)
for archive in REF.glob('*.zip'):
 with zipfile.ZipFile(archive) as z:
  for f in z.namelist():
   if not f.endswith('.json'):continue
   j=json.loads(z.read(f));info=j['info']
   if str(info['dates'][0])<'2022-01-01':continue
   for date in info['dates']:
    index[(str(date),tuple(sorted(team(t) for t in info['teams'])))].append((archive.name,f,j))
b=pd.read_csv(ROOT/'cleaned_competition_data'/'deliveries_joined.csv',low_memory=False)
rows=[]
for mid,g in b.groupby('match_id',sort=False):
 r=g.iloc[0];cand=index.get((r.match_date,tuple(sorted([team(r.home_team),team(r.away_team)]))),[])
 base={'match_id':int(mid),'source_rows':len(g),'reference_candidates':len(cand),'date':r.match_date,'competition_group':r.competition_group}
 if len(cand)!=1:
  rows.append(dict(base,status='no_unique_match'));continue
 ar,f,j=cand[0]
 for inn,ig in g.groupby('innings',sort=True):
  rr=dict(base,innings=int(inn),reference_file=f,archive=ar)
  if int(inn)>len(j['innings']): rows.append(dict(rr,status='missing_reference_innings'));continue
  ri=j['innings'][int(inn)-1]
  flat=[dict(d,ref_over=o['over']+1) for o in ri['overs'] for d in o['deliveries']]
  rr.update(ref_rows=len(flat),innings_source_rows=len(ig),bat_team_equal=team(ri['team'])==team(ig.iloc[0].batting_team_name))
  if len(flat)!=len(ig): rows.append(dict(rr,status='length_mismatch'));continue
  runs=[d['runs']['batter'] for d in flat];overs=[d['ref_over'] for d in flat]
  rr.update(batter_run_mismatches=sum(a!=v for a,v in zip(runs,ig.runs_recorded)),over_mismatches=sum(a!=v for a,v in zip(overs,ig.overid)))
  rr['status']='exact_sequence' if rr['batter_run_mismatches']==rr['over_mismatches']==0 and rr['bat_team_equal'] else 'sequence_mismatch'
  rows.append(rr)
d=pd.DataFrame(rows)
d.to_csv(ROOT/'pressure_analysis'/'alignment_profile.csv',index=False)
print(d.groupby(['competition_group','status']).agg(innings_or_unmatched_matches=('match_id','size'),source_match_count=('match_id','nunique')).to_string())
print(d[d.status.eq('sequence_mismatch')].head(10).to_string(index=False))
print('source rows in exact innings',d.loc[d.status.eq('exact_sequence'),'innings_source_rows'].sum())
