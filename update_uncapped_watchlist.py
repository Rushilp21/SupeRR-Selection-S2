"""Build the supplemental scouting watchlist from frozen ratings, retaining the main rankings."""
from pathlib import Path
import json, pandas as pd

ROOT=Path(__file__).resolve().parent
DIST=ROOT/'superr-dashboard/dist'
profiles=[
('Ayush Badoni','batter','Domestic middle-order depth and innings-repair cover alongside Parag/Jurel.','Stronger evidence'),
('Suyash Sharma','bowler','Leg-spin run control; assess overlap with existing RR spin options.','Stronger evidence'),
('Vaibhav Arora','bowler','Domestic new-ball seam option; wicket evidence is stronger than containment.','Role review'),
('Mohsin Khan','bowler','Left-arm pace variety and powerplay cover, subject to current fitness.','Role review'),
('Shashank Singh','batter','Right-handed finishing cover; pressure SR trails his ordinary scoring rate.','Role review'),
('Nehal Wadhera','batter','Left-handed middle-order depth; pressure acceleration needs investigation.','Role review'),
('Prabhsimran Singh','batter','Opening and keeping cover; assess overlap with the existing top order.','Role review'),
('Digvesh Rathi','bowler','Spin development option; limited support from this pressure model.','Monitor only'),
('Rahul Tewatia','batter','Left-handed finishing profile, but weak pressure evidence in this sample.','Monitor only'),
('Yash Dayal','bowler','Left-arm seam cover; weak pressure results make him a lower-priority review.','Monitor only'),
]
data=json.loads((DIST/'data.json').read_text())
portraits=json.loads((ROOT/'assets/portraits/watchlist_sources.json').read_text())
rows=[]
for rank,(name,role,fit,status) in enumerate(profiles,1):
    frame=pd.read_csv(ROOT/'final_analysis'/f'{role}_all_player_ratings.csv')
    p=frame.loc[frame.player_name.eq(name)].iloc[0].to_dict()
    p={k:(None if pd.isna(v) else v) for k,v in p.items()}
    assert p['eligible'] and p['t20i_units']==0
    p.update(original_rank=p['final_rank'],final_rank=rank,watchlist_rank=rank,role=role,fit=fit,status=status,photo=f"assets/{int(p['player_id'])}.png",photoSource=portraits[name]['image_url'])
    rows.append(p)
data['uncapped']=rows
(DIST/'data.json').write_text(json.dumps(data,ensure_ascii=False,allow_nan=False),encoding='utf-8')
pd.DataFrame(rows).to_csv(DIST/'uncapped_watchlist.csv',index=False)
print('Built 10 supplemental watchlist profiles; original batting and bowling lists preserved.')
