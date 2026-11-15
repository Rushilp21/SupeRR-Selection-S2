"""Build the requested top-20 selection comparison PDF from frozen analysis outputs."""
from pathlib import Path
import json, hashlib, html
import numpy as np
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parent
SRC=ROOT/'final_analysis'
DEST=ROOT/'output'/'pdf'
TEMP=ROOT/'tmp'/'pdfs'
DEST.mkdir(parents=True,exist_ok=True);TEMP.mkdir(parents=True,exist_ok=True)
PDF=DEST/'RR_Pressure_Player_Selection_Audit.pdf'
PAGE_W,PAGE_H=landscape(A4)
MARGIN=34
WIDTH=PAGE_W-2*MARGIN
NAVY=colors.HexColor('#14243C')
INK=colors.HexColor('#24344A')
MUTED=colors.HexColor('#58677B')
PINK=colors.HexColor('#FCE6EF')
PINK_DARK=colors.HexColor('#A91D59')
PALE=colors.HexColor('#F3F5F8')
LINE=colors.HexColor('#D8DFE7')
BLUE=colors.HexColor('#E9F0F9')
AMBER=colors.HexColor('#FFF2D4')
font_path=Path('C:/Windows/Fonts')
if (font_path/'arial.ttf').exists():
    pdfmetrics.registerFont(TTFont('AuditSans',str(font_path/'arial.ttf')))
    pdfmetrics.registerFont(TTFont('AuditSans-Bold',str(font_path/'arialbd.ttf')))
    pdfmetrics.registerFontFamily('AuditSans',normal='AuditSans',bold='AuditSans-Bold',italic='AuditSans',boldItalic='AuditSans-Bold')
    FONT='AuditSans';BOLD='AuditSans-Bold'
else:FONT='Helvetica';BOLD='Helvetica-Bold'

ST={
 'title':ParagraphStyle('title',fontName=BOLD,fontSize=20,leading=24,textColor=NAVY,spaceAfter=7),
 'sub':ParagraphStyle('sub',fontName=FONT,fontSize=9,leading=12,textColor=MUTED,spaceAfter=8),
 'body':ParagraphStyle('body',fontName=FONT,fontSize=10,leading=14,textColor=INK,spaceAfter=7),
 'small':ParagraphStyle('small',fontName=FONT,fontSize=8.4,leading=11.5,textColor=MUTED,spaceAfter=5),
 'h2':ParagraphStyle('h2',fontName=BOLD,fontSize=12,leading=16,textColor=NAVY,spaceBefore=8,spaceAfter=5),
 'cell':ParagraphStyle('cell',fontName=FONT,fontSize=8.5,leading=10.2,textColor=INK),
 'head':ParagraphStyle('head',fontName=BOLD,fontSize=8,leading=10,textColor=colors.white,alignment=TA_CENTER),
}
story=[]
page_titles=[]
source_files={}
numeric_checks=[]

def read(name):
    p=SRC/name
    source_files[name]=hashlib.sha256(p.read_bytes()).hexdigest()
    return pd.read_csv(p)

def f(v,d=2):return '-' if pd.isna(v) else f'{v:,.{d}f}'
def n(v):return '-' if pd.isna(v) else f'{int(round(v)):,}'
def pct(v,d=1):return '-' if pd.isna(v) else f'{100*v:.{d}f}%'
def esc(v):return html.escape(str(v))
def para(text,style='body'):return Paragraph(text,ST[style])
def add(text,style='body'):story.append(para(text,style))
def heading(title,subtitle=None):
    if story:story.append(PageBreak())
    page_titles.append(title)
    add(title,'title')
    if subtitle:add(subtitle,'sub')
def note(text):add(text,'small')
def legend():
    t=Table([[para('PINK ROWS: selected ranks 1-10','small'),para('WHITE / GREY ROWS: alternatives ranked 11-20','small')]],colWidths=[WIDTH/2]*2)
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(0,0),PINK),('BACKGROUND',(1,0),(1,0),PALE),('LEFTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),2)]))
    story.extend([t,Spacer(1,6)])

def table(headers,rows,widths=None,selected=None,font=8.5,row_height=16.4,header_height=29,left_cols=(1,),center_all=False):
    if widths is None:widths=[1]*len(headers)
    widths=[WIDTH*w/sum(widths) for w in widths]
    grid=[[Paragraph(str(x),ST['head']) for x in headers]]
    for row in rows:
        cells=[]
        for j,x in enumerate(row):
            st=ParagraphStyle('c',parent=ST['cell'],fontSize=font,leading=font+1.8,alignment=TA_CENTER if center_all else (TA_LEFT if j in left_cols else TA_RIGHT))
            cells.append(Paragraph(esc(x),st))
        grid.append(cells)
    for i,row in enumerate(grid):
        limit=header_height if i==0 else row_height
        for j,cell in enumerate(row):
            _,height=cell.wrap(widths[j]-10,limit)
            assert height<=limit+.1,('Cell exceeds fixed row height',headers[j],i,height,limit)
    t=Table(grid,colWidths=widths,rowHeights=[header_height]+[row_height]*len(rows),repeatRows=1,hAlign='LEFT')
    commands=[('BACKGROUND',(0,0),(-1,0),NAVY),('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),
        ('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0),
        ('LINEBELOW',(0,0),(-1,0),.5,NAVY)]
    for i in range(len(rows)):
        chosen=selected[i] if selected is not None else False
        commands.append(('BACKGROUND',(0,i+1),(-1,i+1),PINK if chosen else (PALE if i%2 else colors.white)))
        commands.append(('LINEBELOW',(0,i+1),(-1,i+1),.25,LINE))
    if selected is not None and any(selected) and not all(selected):
        last=max(i for i,x in enumerate(selected) if x)
        commands.append(('LINEBELOW',(0,last+1),(-1,last+1),1.2,PINK_DARK))
    t.setStyle(TableStyle(commands))
    story.extend([t,Spacer(1,7)])
    return t

def box(title,text,color=AMBER):
    t=Table([[para('<b>'+title+'</b><br/>'+text)]],colWidths=[WIDTH])
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),color),('LEFTPADDING',(0,0),(-1,-1),11),('RIGHTPADDING',(0,0),(-1,-1),11),('TOPPADDING',(0,0),(-1,-1),9),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
    story.extend([t,Spacer(1,8)])

data={};scenarios={}
coverage=read('player_source_coverage.csv')
for role in ['batter','bowler']:
    d=read(f'{role}_all_player_ratings.csv')
    d=d[d.eligible].sort_values('final_rank').head(20).copy()
    assert d.final_rank.tolist()==list(range(1,21))
    d=d.merge(coverage[coverage.role.eq(role)][['player_id','accepted_share']],on='player_id',how='left',validate='one_to_one')
    selected=read('top10_batters.csv' if role=='batter' else 'top10_bowlers.csv')
    assert d.head(10).player_id.tolist()==selected.player_id.tolist()
    assert np.allclose(d.rating_raw,100*(d.high_shrunk-.2*d.normal_shrunk-.5*d.high_cluster_se))
    if role=='batter':assert np.allclose(d.high_strike_rate,100*d.high_runs/d.high_units)
    else:assert np.allclose(d.high_economy,6*d.high_runs/d.high_units)
    v=read(f'{role}_scenario_rankings.csv')
    avg=v.groupby('player_id').scenario_rank.mean()
    assert np.allclose(d.set_index('player_id').mean_scenario_rank,avg.reindex(d.player_id))
    assert d.player_id.is_unique
    data[role]=d;scenarios[role]=v
    numeric_checks.append(f'{role}: ranks 1-20, unchanged top10 IDs, primary score, displayed rate and mean-scenario-rank arithmetic all reconcile')
summary=json.loads((SRC/'final_summary.json').read_text())
hold=json.loads((SRC/'holdout_validation.json').read_text())
calibration=read('pressure_calibration_summary.csv')
spec=json.loads((SRC/'analysis_specification.json').read_text())
verification=json.loads((SRC/'verification_report.json').read_text())
assert verification['all_checks_passed']

# 1. Executive audit and document map.
heading('Pressure-player selection audit',
    'Top 20 batters and top 20 bowlers | Existing rankings preserved | Prepared 15 November 2026')
box('What this document establishes',
    'The numbers below reproduce how the existing top 10 were selected. They allow you to inspect and challenge each choice. They do not prove a unique, objectively correct top 10 or a high probability of competition selection.',BLUE)
add('The analysis uses the supplied IPL/T20I population from <b>22 January 2022 to 1 November 2026</b>. Scoring context was supplemented from strictly matched Cricsheet records. All comparisons below use the saved 14 November analysis; no players have been moved to make the tables look more convincing.')
table(['Supplied events','Usable events','Usable matches','High-pressure events','Eligible batters','Eligible bowlers'],
    [[n(summary['source_rows']),n(summary['model_delivery_rows']),n(summary['model_matches']),n(summary['high_pressure_events']),n(summary['eligible_batters']),n(summary['eligible_bowlers'])]],
    [1,1,1,1.2,1,1],row_height=27,header_height=24,font=12,center_all=True)
add('How to inspect the selections','h2')
add('<b>Pages 2-5:</b> complete top-20 performance and scoring tables. <b>Pages 6-7:</b> all 13 scenario ranks. <b>Pages 8-9:</b> coverage, season consistency and bootstrap uncertainty. <b>Page 10:</b> direct comparisons around the rank-10 cutoff. <b>Pages 11-12:</b> pressure definition, formulas and worked calculations. <b>Pages 13-14:</b> future-year validation, limitations and source traceability.')
box('Material caution from validation',
    'Pre-2026 batting selections underperformed the other training-eligible batters in 2026. Bowling rank persistence was near zero. These are historical, model-dependent rankings; forecasting strength has not been established.')
note('Selection rules: at least 500 total exposure units, 120 high-pressure units, 250 ordinary units, 10 pressure matches and pressure exposure in two calendar years. Units are non-wide balls faced for batting and legal balls for bowling. Highlighting denotes selection, not certainty.')

# 2. Batter descriptive top20.
heading('Batters: top 20 performance comparison',
    'Descriptive statistics from the primary high-pressure definition. Strike rate alone did not determine the order.')
legend()
rows=[]
for r in data['batter'].itertuples(index=False):
    rows.append([n(r.final_rank),r.player_name,str(int(r.player_id)),n(r.high_units),n(r.high_runs),n(r.high_dismissals),f(r.high_strike_rate,1),f(r.ordinary_strike_rate,1),f(r.high_strike_rate-r.ordinary_strike_rate,1),n(r.high_matches),f(r.high_runs/r.high_dismissals,1) if r.high_dismissals else '-'])
table(['Rank','Player','Player<br/>ID','HP<br/>balls','HP<br/>runs','HP<br/>outs','HP<br/>SR','Ordinary<br/>SR','SR<br/>change','HP<br/>matches','HP runs<br/>per out'],rows,[27,145,43,50,50,45,65,65,65,55,63],selected=[True]*10+[False]*10)
note('<b>Definitions:</b> HP = high pressure. SR = 100 x runs / non-wide balls faced, including no-balls. Outs are attributed to the dismissed player, including non-striker run-outs; retired hurt is excluded. Ordinary SR uses eligible events outside the pressure group. SR change = HP SR - ordinary SR.')
note('<b>Reading example:</b> Glenn Phillips (rank 10) has a lower HP SR than Virat Kohli (rank 11). The selection depends on the adjusted score and cross-scenario ordering shown on the next page, not a strike-rate cutoff. Source: batter_all_player_ratings.csv, keyed by player_id.')

# 3. Bat selection actual numbers.
def score_page(role,title):
    heading(title,'Actual selection quantities. All H, U, SE and primary-score figures are expressed per 100 exposure units.')
    legend();rows=[]
    for r in data[role].itertuples(index=False):
        rows.append([n(r.final_rank),r.player_name,f(100*r.high_shrunk,3),f(100*r.normal_shrunk,3),f(100*r.high_cluster_se,3),f(r.rating_raw,3),n(r.primary_rank),f(r.mean_scenario_rank,3),f(r.consensus_index,2),f'{int(round(13*r.scenario_top10_frequency))}/13'])
    table(['Final<br/>rank','Player','Adjusted<br/>HP: H','Adjusted<br/>usual: U','HP error<br/>scale: SE','Primary<br/>score','Primary<br/>rank','Mean rank<br/>(13 models)','Consensus<br/>index','Top10<br/>models'],rows,[27,145,66,66,66,66,48,74,68,54],selected=[True]*10+[False]*10)
    note('<b>Primary score = H - 0.20 x U - 0.50 x SE.</b> H measures shrunk context-adjusted pressure performance. U measures shrunk context-adjusted ordinary performance. The U term gives a modest reward for improvement over usual form; the SE term penalizes uncertainty. Higher primary scores are better.')
    note('<b>The final order sorts the mean rank across 13 scenarios, lowest first.</b> Exact mean-rank ties use the higher primary score. The index is a rescaled mean rank within the eligible pool; 95 does not mean a 95% probability of being correct. Different primary and final ranks are intentional. Full formulas and worked arithmetic: pages 11-12.')
score_page('batter','Batters: the values that selected the top 10')

# 4. Bowl comparison.
heading('Bowlers: top 20 performance comparison',
    'Lower economy and higher wicket output help, but opposition/context adjustments and uncertainty also affect selection.')
legend();rows=[]
for r in data['bowler'].itertuples(index=False):
    rows.append([n(r.final_rank),r.player_name,str(int(r.player_id)),n(r.high_units),n(r.high_runs),n(r.high_dismissals),f(r.high_economy,2),f(r.ordinary_economy,2),f(r.ordinary_economy-r.high_economy,2),n(r.high_matches),f(r.high_runs/r.high_dismissals,1) if r.high_dismissals else '-'])
table(['Rank','Player','Player<br/>ID','HP legal<br/>balls','HP runs<br/>conceded','HP<br/>wickets','HP<br/>economy','Ordinary<br/>economy','Economy<br/>improvement','HP<br/>matches','HP runs<br/>per wicket'],rows,[27,145,43,55,55,45,65,65,65,55,53],selected=[True]*10+[False]*10)
note('<b>Definitions:</b> Economy = 6 x bowler runs conceded / legal balls. Conceded runs include batter runs, wides and no-ball penalties; byes, leg-byes and penalty runs are excluded. Wickets are bowler-credited dismissals, excluding run-outs and retirements. Positive economy improvement means fewer runs per over under pressure.')
note('<b>Important:</b> each player faced different contexts and sample sizes. Abrar Ahmed has a lower raw pressure economy than Kuldeep Yadav, but the final ranking also accounts for wickets, peer expectations, shrinkage and 13-model consensus. Source: bowler_all_player_ratings.csv.')

# 5. Bowl calculation.
score_page('bowler','Bowlers: the values that selected the top 10')

# 6-7. All scenarios for all20 each.
scenario_names=[x[0] for x in spec['settings']]
scenario_labels=['Base','P25','P15','P10','W8','W16','S75','S300','U0','U40','No C','Alt','Recent']
def scenario_page(role,title):
    heading(title,'Each number is the player\'s rank in that scenario among the fixed primary-eligible candidate pool. Lower is better.')
    legend();v=scenarios[role].pivot(index='player_id',columns='scenario',values='scenario_rank')
    rows=[]
    for r in data[role].itertuples(index=False):
        ranks=[f(v.loc[r.player_id,c],0) if float(v.loc[r.player_id,c]).is_integer() else f(v.loc[r.player_id,c],1) for c in scenario_names]
        rows.append([n(r.final_rank),r.player_name]+ranks+[f(r.mean_scenario_rank,3)])
    table(['Rk','Player']+scenario_labels+['Mean'],rows,[25,140]+[37]*13+[50],selected=[True]*10+[False]*10,font=8.2,row_height=16.2,header_height=25)
    note('<b>Scenario key:</b> Base = top 20% pressure, wicket value 12, pressure shrinkage 150, usual-performance weight 0.20. P25/P15/P10 = top 25%/15%/10% pressure. W8/W16 = dismissal values 8/16. S75/S300 = pressure shrinkage 75/300. U0/U40 = usual-performance weight 0/0.40. No C = remove chase-closeness downweighting. Alt = alternative pressure component weights. Recent = 0.85 weighting per year further in the past.')
    note(f'<b>Aggregation:</b> mean = sum of these 13 ranks / 13. A scenario needs at least 50 pressure units and five pressure matches per player; otherwise its rank is set to {71 if role=="batter" else 79}, worse than the {70 if role=="batter" else 78}-player eligible pool. Final order uses the unrounded means. Scenario top10 counts measure specification stability, not the chance that a player is objectively top10.')
scenario_page('batter','Batters: all 13 scenario ranks')
scenario_page('bowler','Bowlers: all 13 scenario ranks')

# 8-9. Reliability and sample selection bias.
def reliability_page(role,title):
    heading(title,'Uncertainty and coverage are part of the evidence. Wide rank intervals mean the exact ordering is weakly determined.')
    legend();rows=[]
    for r in data[role].itertuples(index=False):
        rows.append([n(r.final_rank),r.player_name,n(r.high_matches),pct(r.positive_pressure_match_share),
            f'{n(r.positive_pressure_seasons)}/{n(r.informative_pressure_seasons)}',pct(r.accepted_share),
            f'{f(r.primary_bootstrap_rank_p05,1)} - {f(r.primary_bootstrap_rank_p95,1)}',
            pct(r.primary_bootstrap_top10_frequency),
            f'{f(r.primary_bootstrap_score_p05,2)} to {f(r.primary_bootstrap_score_p95,2)}',
            f'{int(round(13*r.scenario_top10_frequency))}/13'])
    table(['Rk','Player','HP<br/>matches','Positive HP<br/>matches','Positive<br/>years','Source<br/>coverage','Primary rank<br/>5th-95th pct','Bootstrap<br/>top10 freq','Primary score<br/>5th-95th pct','Top10<br/>models'],rows,[25,145,45,70,55,60,90,70,115,52],selected=[True]*10+[False]*10,font=8.2)
    note('<b>Positive HP matches:</b> share of sampled pressure matches with positive context-adjusted utility residual, not match wins. <b>Positive years:</b> above-peer pressure calendar years / calendar years with at least 20 pressure units. <b>Source coverage:</b> share of supplied striker or bowler delivery events retained in accepted standard-game analysis; it is not career coverage.')
    note('<b>Bootstrap:</b> 1,000 whole-match resamples, holding calibration, peer expectations, candidate eligibility and the original uncertainty penalty fixed. These are conditional primary-model intervals; they do not measure all model uncertainty and are not intervals for final consensus rank. Fractional rank quantiles arise from interpolation. Bootstrap top10 frequency is not a probability of being truly top10.')
reliability_page('batter','Batters: how reliable are the comparisons?')
reliability_page('bowler','Bowlers: how reliable are the comparisons?')

# 10. Challenge the actual cutoff.
heading('Challenge the cutoff: selected 10th versus 11th',
    'The cutoff is an ordering decision, not evidence of a clear skill discontinuity between ranks 10 and 11.')
for role,label in [('batter','Batting boundary'),('bowler','Bowling boundary')]:
    add(label,'h2')
    g=data[role][data[role].final_rank.between(8,13)]
    rows=[]
    metric='high_strike_rate' if role=='batter' else 'high_economy'
    for r in g.itertuples(index=False):
        rows.append([n(r.final_rank),r.player_name,f(getattr(r,metric),2),n(r.high_dismissals),f(r.rating_raw,3),n(r.primary_rank),f(r.mean_scenario_rank,3),f'{int(round(13*r.scenario_top10_frequency))}/13'])
    table(['Final rank','Player','HP SR' if role=='batter' else 'HP economy','HP outs' if role=='batter' else 'HP wickets','Primary score','Primary rank','Mean rank','Top10 models'],rows,[40,160,85,70,100,75,100,90],selected=g.final_rank.le(10).tolist(),font=9,row_height=18,header_height=24)
add('<b>Phillips versus Kohli:</b> Phillips has 244 runs and two outs in 200 pressure balls; Kohli has 354 runs and seven outs in 218. Phillips has lower raw SR, but a slightly higher primary adjusted score (12.517 vs 11.527) and a lower mean scenario rank (13.923 vs 14.692). This is a narrow, model-dependent selection; the uncertainty ranges overlap widely.','small')
add('<b>Shaheen versus Holder and Taskin:</b> Shaheen\'s mean rank (13.077) beats Holder\'s (14.615) and Taskin\'s (15.000), while Taskin has a better primary-model rank and makes more scenario top10s. Mean rank and top10 frequency answer different questions. Shaheen\'s selection is fragile: only 1/13 scenarios individually place him in their top10.','small')

# 11. Exact pressure definition and thresholds.
heading('Pressure definition: exactly what was counted',
    'All inputs are evaluated before the delivery. No current-delivery runs, current wicket or final match winner enters the pressure formula.')
add('<b>Let</b> L = (prior legal balls / 120)<super>2</super>; W = min(wickets lost / 8, 1); K = 1 for the supplied knockout flag, otherwise 0. P is the prior scoring environment, separately for IPL/T20I, estimated from strictly earlier-date accepted first innings with 2,400 pseudo-balls at 8 runs/over.')
add('<b>First innings:</b> D = clip((P - current run rate) / 4, 0, 1) after 12 legal balls, otherwise 0.<br/><b>Raw score = 35L + 35W + 20D + 10K.</b><br/><b>Chase:</b> q = required run rate / P; C = exp(-((q - 1) / 0.75)<super>2</super>); R = clip(q / 2, 0, 1).<br/><b>Raw score = C x (45L + 30R + 15W + 10K).</b> C downweights very easy or extremely demanding chases.')
rows=[]
for r in calibration.sort_values(['competition_group','innings','innings_phase']).itertuples(index=False):
    rows.append([r.competition_group,n(r.innings),r.innings_phase,n(r.deliveries),f(r.raw_p80,3),n(r.high_deliveries),pct(r.high_share,2)])
table(['Competition','Innings','Phase','Eligible events','Raw 80th percentile','High events','High share'],rows,[90,60,110,130,150,120,110],font=8.5,row_height=16,header_height=23,left_cols=(0,2))
note('<b>Final high-pressure rule:</b> empirical percentile rank >=0.80 within each competition x innings x phase group. Powerplay = fewer than 36 prior legal balls; middle = 36-89; death = 90+. The displayed raw 80th-percentile values summarize these groups; the implementation uses empirical percentile ranks with averaged ties, not rounded cutoffs.')
note('<b>Limitation:</b> selecting the top fifth within every group forces some relatively routine states into the pressure sample. The weights and percentile rule are modeling judgments, not validated measures of psychological pressure. Retrospective calibration uses the full context distribution; the separate 2026 test uses earlier calibration only.')

# 12. Trace the complete arithmetic on representative selections.
heading('Worked calculations: from runs to selection scores',
    'These examples show actual saved inputs, not illustrative or invented numbers. Full top-20 score components are on pages 3 and 5.')
rows=[]
for role,name in [('batter','Rajat Patidar'),('batter','Shreyas Iyer'),('bowler','Kuldeep Yadav'),('bowler','Mustafizur Rahman')]:
    r=data[role].set_index('player_name').loc[name]
    actual=r.high_runs-12*r.high_dismissals if role=='batter' else 12*r.high_dismissals-r.high_runs
    expected=actual-r.high_residual
    rows.append([name,n(r.high_units),f(actual,3),f(expected,3),f(r.high_residual,3),f(100*r.high_shrunk,3),f(100*r.normal_shrunk,3),f(100*r.high_cluster_se,3),f(r.rating_raw,3)])
table(['Player','HP units','Actual HP<br/>utility','Expected HP<br/>utility','HP residual','H per<br/>100','U per<br/>100','SE per<br/>100','Primary<br/>score'],rows,[160,60,100,110,95,80,80,80,90],font=9,row_height=24,header_height=30,left_cols=(0,))
add('1. Define the observed contribution','h2')
add('<b>Batting utility = batter runs - 12 x individual outs.</b> For Patidar: 256 - 12 x 3 = 220.<br/><b>Bowling utility = 12 x credited wickets - runs conceded.</b> For Kuldeep: 12 x 28 - 343 = -7. A negative raw utility is possible; the comparison is against what the same contexts normally yield.')
add('2. Subtract contextual expectations and shrink small samples','h2')
add('Expected runs and dismissal rates come from other-match folds, with hierarchical groups for competition, innings, phase, year, batting-order band or bowling family, opponent, venue country, wickets and chase demand. <b>HP residual = actual HP utility - expected HP utility.</b><br/><b>H = 100 x HP residual / (HP units + 150).</b> <b>U = 100 x ordinary residual / (ordinary units + 300).</b> The added units shrink small samples toward zero adjusted impact; they are not actual extra balls.')
add('3. Account for uncertainty, then aggregate scenarios','h2')
add('<b>Primary score = H - 0.20U - 0.50SE.</b> For Patidar, 27.374 - 0.20 x 12.321 - 0.50 x 10.537 = approximately 19.641. SE uses match-cluster variability after shrinkage. Final selection then sorts the mean of the 13 scenario ranks. Patidar\'s mean 3.769 narrowly beats Iyer\'s 3.923 despite Iyer\'s stronger primary score.')
note('All group rates are estimated out of fold: the target match is excluded from the training fold. These are retrospective peer expectations rather than a fully causal estimate. The same player may occur in other training matches; this is match holdout, not leave-player-out fitting. Rounding in this report can produce small arithmetic differences.')
note('<b>Peer-rate equation:</b> child rate = (training outcome sum + alpha x parent rate) / (training exposure + alpha), separately for runs and dismissals. The base group is competition/innings/phase; year groups use alpha 600; batting-order-band or bowling-family groups use 300; the finer opponent/venue/wickets/chase-demand groups use 150. Expected utility is the sum of expected per-unit utility x actual exposure. Player ID is not a predictor.')
note('<b>Error-scale equation:</b> let s_m be a pressure match\'s adjusted residual, n_m its exposure, n the total exposure, mu = total residual / n, and M the number of pressure match clusters. SE per 100 = 100 x sqrt[M/(M-1) x sum((s_m - mu x n_m)<super>2</super>)] / (n + 150). Zero-ball dismissal contributions remain in their match clusters.')

# 13. Report validation honestly.
heading('Validation: what supports the choices, and what fails',
    'A stable retrospective specification does not automatically predict future pressure performance.')
add('Separate historical test: train on 2022-2025, evaluate in 2026','h2')
rows=[]
for h in hold:
    rows.append([h['role'].capitalize(),n(h['training_eligible_players']),n(h['training_top10_observed_in_2026']),n(h['rank_correlation_players_with_30_test_pressure_units']),f(h['train_test_rank_spearman'],3),f(h['training_top10_2026_pressure_residual_per_unit'],3),f(h['other_training_eligible_2026_pressure_residual_per_unit'],3)])
table(['Category','Training<br/>eligible pool','Train top10<br/>seen in 2026','Rank-test<br/>players','Rank<br/>correlation','Top10 test<br/>impact / unit','Other eligible<br/>test impact / unit'],rows,[90,100,120,95,100,140,140],font=10,row_height=31,header_height=31,left_cols=(0,))
box('Interpretation: predictive evidence is weak',
    'Batters: earlier selections underperformed the comparison pool in 2026, with negative rank persistence. Bowlers: the earlier top10 had a slightly positive cohort result, but individual rank persistence was approximately zero. These results do not establish reliable IPL 2027 forecasting power.')
add('What the checks do support','h2')
add('Saved checks confirm unique source delivery IDs, correct outcome attribution, bowler-run treatment, separation of whole-match folds and minimum sample rules. Twenty sampled peer predictions were independently recomputed in the saved validation. For this PDF, the displayed top-20 rates, primary scores, mean scenario ranks and original top10 IDs were independently reconciled again.')
add('What remains a material limitation','h2')
add('<b>Coverage:</b> 34,772 of 200,999 supplied events are outside the main analysis, including unresolved context, revised games and other exclusions. Missingness can bias player comparisons.<br/><b>Model choices:</b> pressure weights, percentile grouping, wicket value and shrinkage are subjective; tested alternatives do not cover all reasonable choices.<br/><b>Uncertainty:</b> many bootstrap rank ranges are wide; conditional resampling omits full model refitting uncertainty.<br/><b>Selection use:</b> these are historical performance lists. Auction eligibility, releases, cost, availability and overseas-slot fit were not verified.')
note('The 2026 check refits outcome baselines and pressure thresholds using pre-2026 data only. Final reported rankings use all available years and consensus specifications; the historical training top10 is a different list. The unfavorable validation is included rather than used to retune the selected names.')

# 14. Proof trail and sources.
heading('Evidence trail and how to verify the report',
    'Audit scope: arithmetic and traceability of the saved analysis, with explicit model limitations. This PDF does not independently rescore every source match.')
add('Source artifacts for each comparison','h2')
rows=[
 ['batter_all_player_ratings.csv / bowler_all_player_ratings.csv','Ranks 1-20, raw rates, score components, sample sizes and bootstrap values; join by player_id.'],
 ['batter_scenario_rankings.csv / bowler_scenario_rankings.csv','The 13 rank values used to calculate mean_scenario_rank and final ordering.'],
 ['player_source_coverage.csv','Accepted share of supplied player delivery events; join on role + player_id.'],
 ['pressure_calibration_summary.csv / analysis_specification.json','Actual group cutoffs, eligible counts, pressure scenarios and minimum-sample rules.'],
 ['batter_out_of_fold_expectations.csv / bowler_out_of_fold_expectations.csv','Delivery/player-level observed runs, dismissals, exposure, fold and peer expectations.'],
 ['batter_match_pressure_impact.csv / bowler_match_pressure_impact.csv','Match-cluster pressure residuals used for uncertainty and positive-match evidence.'],
 ['holdout_validation.json / verification_report.json','Historical 2026 results and recorded implementation checks.'],
 ['final_player_analysis.py / verify_final_analysis.py','Reproducible ranking and independent calculation-verification scripts.'],
 ]
table(['Artifact in the existing analysis package','Evidence supplied'],rows,[330,440],font=8.6,row_height=26,header_height=24,left_cols=(0,1))
add('Reproducible ordering and input integrity','h2')
add('Filter <b>eligible = True</b>, sort <b>final_rank</b>, and retain ranks 1-20. Pink shading is exactly <b>final_rank &lt;= 10</b>. The order is mean scenario rank ascending, then primary score descending for exact ties. Index = 100 x [1 - (mean rank - 1) / (eligible pool size - 1)]. Full-precision values, not rounded display values, determine order.','small')
for name in ['batter_all_player_ratings.csv','bowler_all_player_ratings.csv']:
    note('<b>SHA-256 '+name+':</b> '+source_files[name])
add('Sources and attribution','h2')
note('Primary population: user-supplied competition data pack and cleaned/joined CSVs. Supplementary scoring: <link href="https://cricsheet.org/">Cricsheet</link>, <link href="https://cricsheet.org/format/json/">JSON documentation</link>, licensed under <link href="https://opendatacommons.org/licenses/by/1-0/">ODC-By v1.0</link>; data transformed into matched context features. Original license notices remain in the analysis package. Independent initial scorecard checks: <link href="https://www.windiescricket.com/series/england-in-west-indies-2021-22-16230/">official Windies 2022 series scoreboard</link>. No reputation-based external player ranking was used.')
note('Final audit conclusion: the saved selections can be numerically reproduced under the declared method. The evidence does not establish that every selected player is superior to every unselected alternative, or that the competition will accept the chosen definitions.')

def decorate(canvas,doc):
    canvas.saveState()
    canvas.setFillColor(NAVY);canvas.rect(0,PAGE_H-8,PAGE_W,8,fill=1,stroke=0)
    canvas.setFont(FONT,8);canvas.setFillColor(MUTED)
    canvas.drawString(MARGIN,18,'RR pressure-player selection audit | Historical analysis | 15 Nov 2026')
    canvas.drawRightString(PAGE_W-MARGIN,18,f'{doc.page} / {len(page_titles)}')
    canvas.setStrokeColor(LINE);canvas.setLineWidth(.5);canvas.line(MARGIN,30,PAGE_W-MARGIN,30)
    canvas.restoreState()

doc=SimpleDocTemplate(str(PDF),pagesize=(PAGE_W,PAGE_H),rightMargin=MARGIN,leftMargin=MARGIN,
    topMargin=27,bottomMargin=39,title='Pressure-player selection audit: top 20 batters and bowlers',
    author='Competition analysis',subject='Numerical comparisons, selected top10 highlights and uncertainty')
doc.build(story,onFirstPage=decorate,onLaterPages=decorate)
reader=PdfReader(str(PDF))
assert len(reader.pages)==len(page_titles),(len(reader.pages),len(page_titles))
text='\n'.join(p.extract_text() for p in reader.pages)
for role in ['batter','bowler']:
    for name in data[role].player_name:assert name in text,name
manifest={'pdf':str(PDF),'pages':len(reader.pages),'page_titles':page_titles,'source_sha256':source_files,
    'numeric_checks':numeric_checks,'all_40_player_names_found':True,'rankings_changed':False,
    'selected_highlight':'Pink background for final_rank <=10 in each top20 table',
    'caution':'Evidence reproduces model choices; it does not prove objectively optimal selections.'}
(TEMP/'selection_audit_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps({'pdf':str(PDF),'pages':len(reader.pages),'bytes':PDF.stat().st_size,'numeric_checks':numeric_checks},indent=2))
