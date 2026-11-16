"""Render conditional recruitment profiles without inventing 2027 auction availability."""
from pathlib import Path
import json,csv,html

ROOT=Path(__file__).resolve().parent
DIST=ROOT/'superr-dashboard/dist'
data=json.loads((DIST/'data.json').read_text(encoding='utf-8'))
pool={p['player_name']:p for group in data.values() for p in group}
spec=[
 ('Ayush Badoni','Domestic middle order','Scouting priority','Innings-repair and No.4–6 depth alongside the middle-order core.','Pressure SR trails his ordinary rate; assess acceleration and the actual vacancy.'),
 ('Suyash Sharma','Domestic spin control','Scouting priority','Leg-spin run control without using an overseas slot.','Only five pressure wickets; check wicket-taking upside and overlap with existing spinners.'),
 ('Lockie Ferguson','Overseas pace','Role alternative','High-pace variation and middle-over wicket-taking cover.','Check current fitness, release status and the opportunity cost of an overseas slot.'),
 ('Glenn Phillips','Overseas batting cover','Role alternative','Flexible middle-order batting and an off-spin option.','Pressure SR is 122.0 in this sample; the case rests on survival/context, not proven pressure acceleration.'),
 ('Vaibhav Arora','Domestic new-ball seam','Role alternative','Powerplay seam depth and a domestic new-ball option.','Pressure economy is 9.24; wickets must justify the run-concession cost.'),
 ('Mohsin Khan','Domestic left-arm pace','Role alternative','Left-arm variety and powerplay cover if the confirmed squad needs it.','Mixed model support; verify current fitness and sustained availability.'),
]
cards=[];records=[]
for name,need,priority,fit,concern in spec:
 p=pool[name];bat=p['role']=='batter'
 rate=p['high_strike_rate' if bat else 'high_economy'];ordinary=p['ordinary_strike_rate' if bat else 'ordinary_economy']
 precision=1 if bat else 2;label='SR' if bat else 'economy'
 rate_text=f'{rate:.{precision}f}';ordinary_text=f'{ordinary:.{precision}f}'
 records.append({'player':name,'role_need':need,'review_priority':priority,'2027_auction_entry':'Not verified','free_agent_status':'Not verified','base_price_2027':'Not verified','high_pressure_rate':rate,'rate_type':label,'ordinary_rate':ordinary,'pressure_balls':int(p['high_units']),'pressure_matches':int(p['high_matches']),'rr_role':fit,'concern':concern,'source_check_date':'2026-11-17'})
 cards.append(f'''<article class="auction-card"><div class="auction-card-top"><div><span class="auction-priority">{priority}</span><h3>{html.escape(name)}</h3><p>{need}</p></div><img src="{p['photo']}" alt="{name}" loading="lazy" width="150" height="170"></div><div class="auction-metrics"><div><strong>{rate_text}</strong><span>Pressure {label}</span></div><div><strong>{ordinary_text}</strong><span>Ordinary {label}</span></div><div><strong>{int(p['high_units'])}</strong><span>HP balls · {int(p['high_matches'])} matches</span></div></div><div class="auction-card-copy"><b>RR role hypothesis</b><p>{fit}</p><b>Before shortlisting</b><p>{concern}</p></div><div class="auction-entry"><span class="auction-status-dot"></span> Auction entry unverified · conditional review</div></article>''')
section='''<!-- AUCTION WATCHLIST START -->
<section class="auction-section section" id="auction-watchlist" aria-labelledby="auction-heading">
 <div class="section-heading"><div><div class="eyebrow">IPL 2027 · CONDITIONAL RECRUITMENT</div><h2 id="auction-heading">Auction<br><span>Watchlist.</span></h2></div><p>Six role-led scouting profiles.<br>Promote to a bid list only after entry is verified.</p></div>
 <div class="auction-verification"><div><span class="auction-status-dot"></span><b>Provisional · source check: 17 November 2026</b></div><p>A final official 2027 auction shortlist was not verified in the sources reviewed. These profiles are <b>not confirmed free agents or available auction players</b>. An absence from a squad list is insufficient evidence of eligibility.</p></div>
 <div class="auction-gates" aria-label="Recruitment decision sequence"><div><span>01</span><b>Verify entry</b><p>Official release or contract status, then the final 2027 auction shortlist.</p></div><div><span>02</span><b>Confirm the role</b><p>Check the actual RR squad gap, fitness, availability and overseas balance.</p></div><div><span>03</span><b>Set a bid case</b><p>Use verified base price and available purse. No speculative bid caps are assigned here.</p></div></div>
 <div class="auction-grid">'''+''.join(cards)+'''</div>
 <div class="auction-bottom"><p><b>How to read this:</b> priorities reflect conditional role review, not a new combined batting/bowling ranking or a 2027 forecast. All statistics are from the supplied historical analysis. The original rankings remain unchanged.</p><a href="auction_watchlist.csv" download>Download scouting checklist ↓</a></div>
 <details class="auction-sources"><summary>Availability evidence &amp; source notes</summary><div><p>The <a href="https://www.iplt20.com/news" target="_blank" rel="noopener">official IPL news feed</a> was reviewed for 2027 squad movements and pool announcements. No final 2027 shortlist was verified in that review. Status must be rechecked before making recruitment claims.</p><p>Registration and final auction shortlisting are separate steps; see the <a href="https://www.iplt20.com/news/article/tata-ipl-2026-player-auction-list-announced" target="_blank" rel="noopener">official 2026 auction announcement</a> for a documented example, not a 2027 availability list.</p><p>Historical rank does not establish availability: <a href="https://www.iplt20.com/news/article/rishabh-pant-and-kuldeep-yadav-complete-high-profile-trade-between-dc-and-lsg" target="_blank" rel="noopener">IPL confirmed Kuldeep Yadav’s move to LSG</a>. His pressure ranking is therefore not treated as evidence that RR can bid for him.</p><p>Candidate eligibility, 2027 base prices, release decisions and clearance are unverified. The six cards are a research queue; any retained, traded, withdrawn or ineligible player must be excluded from an auction-only bid list.</p></div></details>
</section>
<!-- AUCTION WATCHLIST END -->'''
page=DIST/'index.html';text=page.read_text(encoding='utf-8')
if '<!-- AUCTION WATCHLIST START -->' in text:
 start=text.index('<!-- AUCTION WATCHLIST START -->');end=text.index('<!-- AUCTION WATCHLIST END -->')+len('<!-- AUCTION WATCHLIST END -->');text=text[:start]+section+text[end:]
else:text=text.replace('  </main>',section+'\n  </main>')
text=text.replace('<a href="#method">Method</a></nav>','<a href="#method">Method</a><a href="#auction-watchlist">Auction Watchlist</a></nav>')
page.write_text(text,encoding='utf-8')
with (DIST/'auction_watchlist.csv').open('w',newline='',encoding='utf-8') as out:
 writer=csv.DictWriter(out,fieldnames=list(records[0]));writer.writeheader();writer.writerows(records)
(DIST/'auction_watchlist_sources.json').write_text(json.dumps({'checked_on':'2026-11-17','status':'Provisional: final 2027 auction pool not verified','sources':['https://www.iplt20.com/news','https://www.iplt20.com/news/article/tata-ipl-2026-player-auction-list-announced','https://www.iplt20.com/news/article/rishabh-pant-and-kuldeep-yadav-complete-high-profile-trade-between-dc-and-lsg'],'profiles':records},indent=2),encoding='utf-8')
print('Rendered six conditional auction profiles with source notes; added navigation item after Method.')
