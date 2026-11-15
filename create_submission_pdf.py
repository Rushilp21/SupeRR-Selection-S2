"""Compact four-page competition submission, using frozen results and sourced portraits."""
from pathlib import Path
import json,html,hashlib
import pandas as pd
import numpy as np
from PIL import Image as PILImage
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4,landscape
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT,TA_CENTER,TA_RIGHT
from reportlab.platypus import Paragraph,Table,TableStyle,Flowable
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parent
SRC=ROOT/'final_analysis'
ASSETS=ROOT/'assets'/'portraits'
OUT=ROOT/'output'/'pdf'
TMP=ROOT/'tmp'/'pdfs'
OUT.mkdir(parents=True,exist_ok=True);TMP.mkdir(parents=True,exist_ok=True)
PDF=OUT/'SupeRR_Selector_Round1_Submission.pdf'
W,H=landscape(A4);M=32;CW=W-2*M
NAVY=colors.HexColor('#14243C');PINK=colors.HexColor('#D82C75')
PALE=colors.HexColor('#FCECF3');INK=colors.HexColor('#24344A')
MUTED=colors.HexColor('#59697C');LINE=colors.HexColor('#DCE3EB')
BLUE=colors.HexColor('#4E6E94');LIGHT=colors.HexColor('#F2F5F9')
fonts=Path('C:/Windows/Fonts')
pdfmetrics.registerFont(TTFont('SubmitSans',str(fonts/'arial.ttf')))
pdfmetrics.registerFont(TTFont('SubmitBold',str(fonts/'arialbd.ttf')))
pdfmetrics.registerFontFamily('SubmitSans',normal='SubmitSans',bold='SubmitBold',italic='SubmitSans',boldItalic='SubmitBold')
FONT='SubmitSans';BOLD='SubmitBold'
styles={}
for name,size,leading,color in [('body',9.2,12.2,INK),('small',7.7,10,MUTED),('tiny',6.9,8.7,MUTED),('cell',8.3,10.1,INK),('head',7.4,9.2,colors.white)]:
    styles[name]=ParagraphStyle(name,fontName=BOLD if name=='head' else FONT,fontSize=size,leading=leading,textColor=color)
styles['head'].alignment=TA_CENTER
summary=json.loads((SRC/'final_summary.json').read_text())
hold=json.loads((SRC/'holdout_validation.json').read_text())
data={
 'batter':pd.read_csv(SRC/'top10_batters.csv').sort_values('final_rank'),
 'bowler':pd.read_csv(SRC/'top10_bowlers.csv').sort_values('final_rank'),
}
photos={p['player']:p for p in json.loads((ASSETS/'verified_official_photos.json').read_text())}
assert set(pd.concat(list(data.values())).player_name)==set(photos)
prepared={}
for name,p in photos.items():
    im=PILImage.open(ROOT/p['path']).convert('RGBA')
    # Publication-size resampling only; no identity or appearance changes.
    im.thumbnail((300,360),PILImage.Resampling.LANCZOS)
    dest=ASSETS/(name.replace(' ','_')+'_pdf.png');im.save(dest,optimize=True)
    prepared[name]=dest

fits={
 'Rajat Patidar':('Domestic middle-order spin-hitting; a No.4 option beside Parag/Jurel.','Conditional acquisition'),
 'Shreyas Iyer':('Domestic middle-order control after early wickets; provides a stabilising No.3-4 option.','Conditional acquisition'),
 'Nicholas Pooran':('Left-handed middle-order power and keeping cover; evaluate overseas balance with Hetmyer.','Conditional acquisition'),
 'Ruturaj Gaikwad':('Top-order stability and opening cover; role overlaps the Jaiswal/Sooryavanshi core.','Conditional acquisition'),
 'Fakhar Zaman':('Left-handed opening profile; use as a performance benchmark until IPL entry is verified.','Benchmark only'),
 'Suryakumar Yadav':('Domestic middle-over acceleration and flexible top-four batting.','Conditional acquisition'),
 'Riyan Parag':('Existing RR core: maintain a middle-order role, with pressure-recovery responsibility.','Existing RR player'),
 'Tim David':('Right-handed finishing power; a complementary option to Hetmyer, subject to overseas balance.','Conditional acquisition'),
 'Ayush Badoni':('Domestic No.4-6 depth and innings-repair cover for Parag/Jurel.','Conditional acquisition'),
 'Glenn Phillips':('Flexible middle-order cover with an off-spin option; check role need and overseas balance.','Conditional acquisition'),
 'Kuldeep Yadav':('Left-arm wrist-spin wickets in middle overs; offers variety alongside Bishnoi/Jadeja.','Conditional acquisition'),
 'Mustafizur Rahman':('Left-arm slower-ball death role; 2026 BCCI-directed release makes clearance a specific gate.','Clearance / entry unverified'),
 'Sunil Narine':('Middle-over run control; an overseas spin option whose role must complement the existing attack.','Conditional acquisition'),
 'Abrar Ahmed':('Middle-over spin-control profile; retain as a benchmark until IPL entry is verified.','Benchmark only'),
 'Matheesha Pathirana':('Specialist closing-over pace and yorker role beside Archer.','Conditional acquisition'),
 'Wanindu Hasaranga':('Wicket-taking leg-spin option; assess overlap with Bishnoi before committing a slot.','Conditional acquisition'),
 'Lockie Ferguson':('High-pace middle-over wicket option; an overseas alternative if pace variety is required.','Conditional acquisition'),
 'Varun Chakravarthy':('Domestic middle-over spin control and wicket-taking depth.','Conditional acquisition'),
 'Josh Hazlewood':('Powerplay seam discipline and new-ball partnership with Archer.','Conditional acquisition'),
 'Shaheen Afridi':('Left-arm new-ball strike profile; retain as a benchmark until IPL entry is verified.','Benchmark only'),
}

c=canvas.Canvas(str(PDF),pagesize=(W,H),pageCompression=1)
c.setTitle('SupeRR Selector Season 2 - Round 1 methodology and player rankings')
c.setAuthor('Competition analysis')
c.setSubject('Pressure definition, historical top10 rankings, evidence and conditional RR role fit')
page=0

def p(text,x,y,width,style='body'):
    pp=Paragraph(text,styles[style]);_,height=pp.wrap(width,1000)
    assert y-height>=33,(page,text[:80],y-height)
    pp.drawOn(c,x,y-height)
    return y-height

def title(main,sub):
    global page
    page+=1
    c.setFillColor(NAVY);c.rect(0,H-7,W,7,fill=1,stroke=0)
    c.setFillColor(PINK);c.setFont(BOLD,8.2);c.drawString(M,H-25,'SupeRR SELECTOR  |  SEASON 2  |  ROUND 1')
    c.setFillColor(NAVY);c.setFont(BOLD,22);c.drawString(M,H-53,main)
    return p(sub,M,H-63,CW,'small')-12

def footer():
    c.setStrokeColor(LINE);c.line(M,28,W-M,28)
    c.setFillColor(MUTED);c.setFont(FONT,7)
    c.drawString(M,16,'Historical IPL/T20I evidence, 2022-2026 | Prepared 15 November 2026')
    c.drawRightString(W-M,16,f'{page} / 4')
    c.showPage()

def h2(text,x,y):
    c.setFillColor(NAVY);c.setFont(BOLD,11.5);c.drawString(x,y-11,text)
    return y-20

def line(x,y,w):
    c.setStrokeColor(LINE);c.line(x,y,x+w,y)

def card(x,y,w,h,label,value):
    c.setFillColor(LIGHT);c.roundRect(x,y-h,w,h,5,fill=1,stroke=0)
    c.setFont(BOLD,16);c.setFillColor(NAVY);c.drawString(x+12,y-21,value)
    c.setFont(FONT,7.7);c.setFillColor(MUTED);c.drawString(x+12,y-35,label)

# 1. Concise methodology, including the full operational pressure definition.
y=title('Reliable players under pressure',
    'Methodology, ranked evidence and conditional Rajasthan Royals role fit for IPL 2027')
gap=9;kw=(CW-3*gap)/4
for i,(label,value) in enumerate([('usable standard-game matches','715'),('analysed delivery events','166,227'),('high relative-pressure events','33,252'),('eligible batters / bowlers','70 / 78')]):
    card(M+i*(kw+gap),y,kw,44,label,value)
y-=59
col=(CW-23)/2;right=M+col+23
yl=h2('1  Pressure definition - before each ball',M,y)
yl=p('Pressure reflects <b>lateness, wickets lost, scoring demand and knockout context</b>. All quantities use the state before the delivery. Current-ball outcomes and the final match winner are excluded.',M,yl,col)-8
yl=p('<b>Variables:</b> L = (prior legal balls / 120)<super>2</super>; W = min(wickets lost / 8, 1); K = knockout flag. P is the earlier-date scoring environment for IPL or T20I, regularised by 2,400 pseudo-balls at 8 runs/over.',M,yl,col)-8
yl=p('<b>Batting first:</b> D = clip((P - current run rate) / 4, 0, 1) after 12 legal balls; otherwise D = 0.<br/><b>Raw pressure = 35L + 35W + 20D + 10K.</b>',M,yl,col)-8
yl=p('<b>Chasing:</b> q = required run rate / P; R = clip(q / 2, 0, 1); C = exp(-((q - 1) / 0.75)<super>2</super>).<br/><b>Raw pressure = C x (45L + 30R + 15W + 10K).</b> C downweights very easy and extremely demanding chases.',M,yl,col)-8
yl=p('<b>High pressure:</b> empirical percentile rank >=0.80 within each <b>competition x innings x phase</b> group. Powerplay: prior legal balls 0-35; middle: 36-89; death: 90+. This compares relative tension within roles and phases.',M,yl,col)
yr=h2('2  Performance, baselines and selection',right,y)
yr=p('<b>Batting utility:</b> runs - 12 x individual dismissals.<br/><b>Bowling utility:</b> 12 x credited wickets - conceded runs. Run-outs are attributed to the dismissed batter; byes/leg-byes are excluded from bowlers\' conceded runs.',right,yr,col)-8
yr=p('<b>Peer adjustment:</b> subtract expected utility estimated from five held-out whole-match folds. Hierarchical rates account for competition, innings, phase, year, batting order/bowling family, opponent, venue country, wickets and chase demand; sparse groups shrink toward parent rates (600/300/150 units).',right,yr,col)-8
yr=p('<b>Pressure impact H</b> = 100 x pressure utility residual / (pressure units + 150).<br/><b>Usual impact U</b> = 100 x ordinary residual / (ordinary units + 300).<br/><b>Primary rating = H - 0.20U - 0.50SE(H).</b> SE uses match clusters, reducing rewards for uncertain samples.',right,yr,col)-8
yr=p('<b>Final rank:</b> mean rank across 13 specifications, lowest first; ties use the primary rating. Variants change pressure share (10/15/20/25%), wicket value (8/12/16), shrinkage, uplift, chase weighting and recency. The index on pages 2-3 rescales mean rank within the eligible pool.',right,yr,col)-8
yr=p('<b>Minimum evidence:</b> 500 total units, 120 pressure units, 250 ordinary units, 10 pressure matches and pressure exposure in two calendar years. Units are non-wide balls faced for batters and legal balls for bowlers.',right,yr,col)
bottom=min(yl,yr)-14
line(M,bottom,CW);bottom-=12
bottom=h2('3  Data preparation and scope',M,bottom)
bottom=p('Joined the six supplied CSVs by match, competition, team and player IDs; standardised missing values and resolved conflicting XI keys without multiplying deliveries. Reconstructed pre-ball scores, wickets, legal balls and targets. Missing extras amounts were supplemented using strictly matched Cricsheet innings. Unverified context, revised/shortened games, extra innings and other T20 competitions were excluded. Of 200,999 supplied events, 166,227 remain. Ten official sample innings reconciled.',M,bottom,CW,'small')-8
bottom=p('<b>Interpretation:</b> this is an operational definition of relative pressure, not an observed psychological measure. Weights and thresholds are declared assumptions; the validation limitations on page 4 remain material.',M,bottom,CW,'small')
footer()

class Portrait(Flowable):
    def __init__(self,name):
        Flowable.__init__(self);self.name=name;self.width=42;self.height=38
    def draw(self):
        cc=self.canv;im=ImageReader(str(prepared[self.name]));iw,ih=im.getSize()
        cc.saveState();cc.setFillColor(colors.HexColor('#F2F5F9'));cc.roundRect(0,0,42,38,3,fill=1,stroke=0)
        clip=cc.beginPath();clip.roundRect(0,0,42,38,3);cc.clipPath(clip,stroke=0,fill=0)
        scale=max(42/iw,38/(ih*.70));dw,dh=iw*scale,ih*scale
        cc.drawImage(im,(42-dw)/2,38-dh,width=dw,height=dh,mask='auto')
        cc.restoreState();cc.linkURL(photos[self.name]['image_url'],(0,0,42,38),relative=1,thickness=0)

def player_page(role):
    batter=role=='batter'
    y=title('Top 10 batters under pressure' if batter else 'Top 10 bowlers under pressure',
        'Ordered statistical rankings. RR contributions are role-fit hypotheses; acquisition depends on entry, release/trade, budget and squad balance.')
    headers=['Rk','Photo','Player','HP<br/>balls','HP<br/>SR' if batter else 'HP<br/>econ.','Usual<br/>SR' if batter else 'Usual<br/>econ.','HP<br/>outs' if batter else 'HP<br/>wkts','Index*','Top10<br/>models','How the player could strengthen RR']
    widths=[22,50,130,48,48,48,38,50,50,CW-484]
    rows=[[Paragraph(x,styles['head']) for x in headers]]
    for r in data[role].itertuples(index=False):
        fit,status=fits[r.player_name]
        name=f'<b>{html.escape(r.player_name)}</b>'
        if status=='Existing RR player':name+='<br/><font color="#A91D59">Existing RR core</font>'
        rrtext=html.escape(fit)+'<br/><font size="7.2" color="#6B5970">'+html.escape(status)+'</font>'
        values=[str(int(r.final_rank)),Portrait(r.player_name),name,str(int(r.high_units)),
            f'{r.high_strike_rate:.1f}' if batter else f'{r.high_economy:.2f}',
            f'{r.ordinary_strike_rate:.1f}' if batter else f'{r.ordinary_economy:.2f}',
            str(int(r.high_dismissals)),f'{r.consensus_index:.2f}',f'{int(round(13*r.scenario_top10_frequency))}/13',rrtext]
        row=[]
        for j,v in enumerate(values):
            if isinstance(v,Flowable):row.append(v);continue
            st=ParagraphStyle('v',parent=styles['cell'],alignment=TA_LEFT if j in [2,9] else TA_CENTER)
            row.append(Paragraph(v,st))
        rows.append(row)
    tab=Table(rows,colWidths=widths,rowHeights=[25]+[41]*10,hAlign='LEFT')
    cmds=[('BACKGROUND',(0,0),(-1,0),NAVY),('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('LEFTPADDING',(0,0),(-1,-1),4),('RIGHTPADDING',(0,0),(-1,-1),4),
        ('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0)]
    for i in range(1,11):
        cmds.extend([('BACKGROUND',(0,i),(-1,i),PALE if i%2 else colors.white),('LINEBELOW',(0,i),(-1,i),.3,LINE)])
    tab.setStyle(TableStyle(cmds))
    for i,row in enumerate(rows):
        for j,cell in enumerate(row):
            if isinstance(cell,Paragraph):
                _,ch=cell.wrap(widths[j]-8,1000)
                assert ch <= (25 if i==0 else 41),(page,i,j,ch)
    _,th=tab.wrap(CW,1000);tab.drawOn(c,M,y-th)
    foot=y-th-7
    unit='HP balls = non-wide balls faced; SR = 100 x runs / balls. Outs include individual non-striker run-outs.' if batter else 'HP balls = legal deliveries; economy = 6 x bowler runs / legal balls. Wickets exclude run-outs/retirements.'
    foot=p('<b>Evidence:</b> '+unit+' Usual = eligible ordinary-pressure events. *Index is a relative consensus measure, not a probability. Top10 models = selections among 13 specifications. Photo kits may be historical; portraits link to their sources.',M,foot,CW,'tiny')
    assert foot>=35,(role,foot)
    footer()

player_page('batter');player_page('bowler')

# 4. Compact charts, validation and actionable interpretation.
y=title('Reliability, limitations and RR application',
    'Historical rankings are supported by sensitivity checks; the separate future-year test limits forecasting claims.')
c.setFillColor(PINK);c.rect(M,y-7,9,7,fill=1,stroke=0)
p('Adjusted pressure impact H',M+15,y+1,180,'small')
c.setFillColor(BLUE);c.rect(M+199,y-7,9,7,fill=1,stroke=0)
p('Adjusted usual impact U',M+214,y+1,180,'small')
y-=23

def impact_chart(role,x,top,width):
    frame=data[role];labelw=109;plotx=x+labelw;plotw=width-labelw-24
    lo,hi=-20,60
    def xp(value):return plotx+(value-lo)/(hi-lo)*plotw
    c.setFont(BOLD,10);c.setFillColor(NAVY);c.drawString(x,top,'Batters' if role=='batter' else 'Bowlers')
    start=top-19;rowh=14.1
    for tick in [-20,0,20,40,60]:
        c.setStrokeColor(LINE);c.setLineWidth(.4);c.line(xp(tick),start+8,xp(tick),start-9*rowh-8)
        c.setFont(FONT,6.8);c.setFillColor(MUTED);c.drawCentredString(xp(tick),start-10*rowh-5,str(tick))
    c.setStrokeColor(MUTED);c.line(xp(0),start+8,xp(0),start-9*rowh-8)
    for i,r in enumerate(frame.itertuples(index=False)):
        yy=start-i*rowh
        c.setFillColor(INK);c.setFont(FONT,7.3);c.drawString(x,yy-1,f'{int(r.final_rank)}. {r.player_name}')
        for val,color,dy in [(100*r.high_shrunk,PINK,1.7),(100*r.normal_shrunk,BLUE,-3.5)]:
            c.setFillColor(color);c.rect(min(xp(0),xp(val)),yy+dy,abs(xp(val)-xp(0)),4.2,fill=1,stroke=0)
    return start-10*rowh-12

chartw=(CW-27)/2
chart_bottom=min(impact_chart('batter',M,y,chartw),impact_chart('bowler',M+chartw+27,y,chartw))
y=chart_bottom-7
y=p('Per 100 exposure units, after context adjustment and sample shrinkage. Compare within category. A high rank can coexist with H below U; final selection combines absolute pressure performance, uplift, uncertainty and scenario consensus.',M,y,CW,'tiny')-9
line(M,y,CW);y-=11
left=M;right=M+(CW+22)/2;col=(CW-22)/2
yl=h2('Validation and limitations',left,y)
yl=p('<b>Checks:</b> 13 specifications; 1,000 whole-match bootstrap resamples; match/season consistency; minimum samples. Patidar, Iyer and Pooran appear in 12/13 top10s; Kuldeep, Mustafizur, Narine and Abrar in 13/13.',left,yl,col,'small')-7
yl=p('<b>2026 holdout:</b> training on 2022-2025 gave rank correlations of <b>-0.374 for batting</b> (28 comparable players) and <b>-0.039 for bowling</b> (29). Earlier batting selections underperformed peers in 2026. These results do not establish reliable 2027 predictive power.',left,yl,col,'small')-7
yl=p('<b>Limits:</b> 17.3% of source events excluded; incomplete competition coverage; subjective pressure weights and wicket value; forced top-fifth pressure grouping; conditional bootstrap intervals omit full model uncertainty. Exact rank boundaries are uncertain.',left,yl,col,'small')
yr=h2('RR 2027: use the ranking as a role screen',right,y)
yr=p('<b>Published 2026 roster baseline:</b> Parag/Jurel/Hetmyer in the middle order, Jaiswal/Sooryavanshi opening, Archer in pace and Bishnoi/Jadeja in spin. The player tables identify complementary roles and possible overlaps; they do not assert confirmed vacancies.',right,yr,col,'small')-7
yr=p('<b>Acquisition gates:</b> verify the final 2027 registered pool, releases/trades, availability, clearances, price and overseas balance. Parag is an existing-player decision. Fakhar, Abrar and Shaheen remain statistical role benchmarks with unverified auction entry. Mustafizur has a specific clearance flag following his reported BCCI-directed 2026 release.',right,yr,col,'small')-7
yr=p('<b>RR role priorities:</b> test domestic middle-order depth, middle-over wicket-taking and closing-over cover against the confirmed 2027 squad. The profiles above identify options for those checks; final bids require verified availability, role need and price.',right,yr,col,'small')
y=min(yl,yr)-11
line(M,y,CW);y-=8
y=p('<b>Sources:</b> supplied six-file competition pack and saved ranking outputs; supplementary <link href="https://cricsheet.org/">Cricsheet</link> data (<link href="https://opendatacommons.org/licenses/by/1-0/">ODC-By v1.0</link>); <link href="https://www.rajasthanroyals.com/rr-players">official RR squad</link>; <link href="https://www.iplt20.com/news/article/ipl-governing-council-announces-tata-ipl-player-regulations-2025-27">IPL 2025-27 regulations</link>; <link href="https://indianexpress.com/article/sports/cricket/mustafizur-rahman-released-by-kkr-following-bcci-instruction-10453190/">Mustafizur release report</link>. Portraits: IPL, ICC, Cricket Australia, RR/GT/MI and Wisden; each photo links to its provider. Images are cropped/scaled for layout; team kits do not establish 2027 affiliation.',M,y,CW,'tiny')
footer();c.save()

r=PdfReader(str(PDF));assert len(r.pages)==4
text='\n'.join(p.extract_text() for p in r.pages)
for role,d in data.items():
    for name in d.player_name:assert name in text,name
for i,pdfpage in enumerate(r.pages):
    assert f'{i+1} / 4' in pdfpage.extract_text()
assert '-0.374' in text and '-0.039' in text
manifest={'pdf':str(PDF),'pages':4,'portraits':len(photos),'source_photo_manifest':'verified_official_photos.json',
    'rankings_preserved':True,'all_20_player_names_found':True,'weak_holdout_results_disclosed':True,
    'auction_fit':'Conditional role assessments; three unverified-entry benchmarks and Mustafizur clearance flag.',
    'bytes':PDF.stat().st_size,'sha256':hashlib.sha256(PDF.read_bytes()).hexdigest()}
(TMP/'submission_pdf_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps(manifest,indent=2))
