"""Refresh the four-page submission while preserving both ranking-table layouts."""
from pathlib import Path

root = Path(__file__).resolve().parent
original = (root / 'create_submission_pdf.py').read_text(encoding='utf-8')
original = original.replace("PDF=OUT/'SupeRR_Selector_Round1_Submission.pdf'", "PDF=OUT/'SupeRR_Selector_Submission_Revised.pdf'")

# Keep the original table implementation, measurements, portraits and numbers.
original = original.replace("c.drawString(M,16,'Historical IPL/T20I evidence, 2022-2026 | Prepared 15 November 2026')", "# Page number only; no repeated promotional footer.")
original = original.replace("return p(sub,M,H-63,CW,'small')-12", "return H-85")
original = original.replace("Top10 models = selections among 13 specifications.", "Top10 models = top-10 selections in 13 analysis versions (13/13 = all versions; explained on page 4).")

page_one = r'''
# 1. Visual methodology overview with the operational definition retained.
pdfmetrics.registerFont(TTFont('SubmitDisplay',str(fonts/'ARIALNB.TTF')))
DISPLAY='SubmitDisplay'
for key,size,lead,colr in [('copy',8.5,11.3,INK),('micro',7.3,9.4,MUTED),('white',8.4,11.3,colors.white),('whiteSmall',7.2,9.4,colors.HexColor('#CDD2E5'))]:
    styles[key]=ParagraphStyle(key,fontName=FONT,fontSize=size,leading=lead,textColor=colr)

def textline(text,x,y,size=10,color=NAVY,font=BOLD):
    c.setFont(font,size);c.setFillColor(color);c.drawString(x,y,text)

def panel(x,top,width,height,fill=LIGHT,radius=7):
    c.setFillColor(fill);c.roundRect(x,top-height,width,height,radius,fill=1,stroke=0)

def portrait(name,x,top,width,height,bg=PALE,zoom=1.05):
    im=ImageReader(str(prepared[name]));iw,ih=im.getSize()
    c.saveState();panel(x,top,width,height,bg)
    cp=c.beginPath();cp.roundRect(x,top-height,width,height,7);c.clipPath(cp,stroke=0,fill=0)
    sc=max(width/iw,height/(ih*.85))*zoom;dw,dh=iw*sc,ih*sc
    c.drawImage(im,x+(width-dw)/2,top-dh,width=dw,height=dh,mask='auto')
    c.restoreState();c.linkURL(photos[name]['image_url'],(x,top-height,x+width,top),thickness=0)

def editorial_header(headline,height=100):
    global page
    page+=1
    c.setFillColor(NAVY);c.rect(0,H-height,W,height,fill=1,stroke=0)
    c.setFillColor(PINK);c.rect(M,H-26,5,9,fill=1,stroke=0)
    textline('SupeRR Selector Season 2',M+13,H-25,9.4,colors.white)
    textline(headline,M,H-66,32,colors.white,DISPLAY)

editorial_header('Pressure, defined.',137)
textline('Performance, measured.',M,H-105,28,colors.HexColor('#F489BC'),DISPLAY)
portrait('Rajat Patidar',603,H-18,88,101,colors.HexColor('#F4B8D4'))
portrait('Kuldeep Yadav',703,H-18,106,101,colors.HexColor('#F4B8D4'))
textline('#1 BATTER',607,H-130,6.8,colors.white)
textline('#1 BOWLER',707,H-130,6.8,colors.white)

top=H-149;gap=9;kw=(CW-3*gap)/4
for i,(label,value) in enumerate([('matches','715'),('usable deliveries','166,227'),('pressure events','33,252'),('eligible batters / bowlers','70 / 78')]):
    xx=M+i*(kw+gap);panel(xx,top,kw,43)
    textline(value,xx+12,top-22,22,NAVY,DISPLAY)
    textline(label,xx+12,top-35,7.6,MUTED,FONT)

top-=61;col=(CW-24)/2;right=M+col+24
textline('01',M,top,11,PINK,DISPLAY);textline('Identify pressure before each ball',M+24,top,16,NAVY,DISPLAY)
yl=top-13
yl=p('Use only the pre-ball state: balls remaining, wickets lost, scoring demand and knockout stage. The current-ball outcome and final match winner are excluded.',M,yl,col,'copy')-7
yl=p('<b>L</b> = (prior legal balls / 120)<super>2</super>; <b>W</b> = min(wickets lost / 8, 1); <b>K</b> = knockout flag. <b>P</b> = earlier-date IPL/T20I first-innings run rate, regularised with 2,400 pseudo-balls at 8 runs/over.',M,yl,col,'copy')-9
panel(M,yl,col,43,PALE)
textline('BATTING FIRST',M+11,yl-13,7.2,PINK)
p('<b>35L + 35W + 20D + 10K</b><br/>D = clip((P - current run rate) / 4, 0, 1); D = 0 before 12 legal balls.',M+11,yl-18,col-22,'micro')
yl-=51
panel(M,yl,col,66,LIGHT)
textline('CHASING',M+11,yl-13,7.2,PINK)
p('<b>C x (45L + 30R + 15W + 10K)</b><br/>q = required run rate / P; R = clip(q / 2, 0, 1).<br/>C = exp(-((q - 1) / 0.75)<super>2</super>), reducing the weight of almost-decided chases.',M+11,yl-18,col-22,'copy')
yl-=76
textline('TOP 20%',M,yl-22,26,PINK,DISPLAY)
p('<b>High pressure</b> = percentile rank &gt;= 0.80 within competition x innings x phase. Phases use prior legal balls: powerplay 0-35, middle 36-89, death 90+. The same flag applies to batter and bowler.',M+109,yl,col-109,'copy')

textline('02',right,top,11,PINK,DISPLAY);textline('Measure value against peers',right+24,top,16,NAVY,DISPLAY)
yr=top-13
yr=p('<b>Batting value:</b> runs - 12 x individual dismissals.<br/><b>Bowling value:</b> 12 x credited wickets - runs conceded. Run-outs follow the dismissed batter; bowler runs exclude byes and leg-byes.',right,yr,col,'copy')-7
yr=p('<b>Peer baseline:</b> five held-out whole-match folds. Hierarchical expectations account for competition, innings, phase, year, role, opponent, venue country, wickets and chase demand; sparse groups shrink toward parent rates (600/300/150 units).',right,yr,col,'copy')-9
panel(right,yr,col,42,NAVY)
textline('PRIMARY RATING',right+12,yr-13,7.1,colors.HexColor('#F489BC'))
textline('H - 0.20U - 0.50SE(H)',right+12,yr-32,18,colors.white,DISPLAY)
yr-=50
yr=p('<b>H</b> = 100 x pressure residual / (pressure units + 150).<br/><b>U</b> = 100 x ordinary residual / (ordinary units + 300).<br/><b>SE(H)</b> is match-cluster uncertainty. Shrinkage reduces the reward for small samples.',right,yr,col,'copy')-7
yr=p('<b>Final order:</b> lowest mean rank across 13 analysis versions; ties use the primary rating. The consensus index rescales mean rank within the eligible pool. The <b>Top10 models</b> column counts how many versions put a player in the top ten; page 4 explains all 13.',right,yr,col,'copy')-7
yr=p('<b>Minimum evidence:</b> 500 total units, 120 pressure units, 250 ordinary units, 10 pressure matches and two pressure-exposure years. Units = non-wide balls faced (batters) or legal balls (bowlers).',right,yr,col,'copy')

line(M,66,CW)
p('<b>Data:</b> six CSVs joined by match/team/player IDs without multiplying deliveries; pre-ball state reconstructed; missing extras supplemented only through strict Cricsheet matches. Standard games in IPL/T20I, 22 Jan 2022-1 Nov 2026: 166,227 of 200,999 events retained (17.3% excluded). Relative pressure is a modelling definition, not an observed psychological measure.',M,58,CW,'micro')
footer()

'''

page_four = r'''
# 4. Explain sensitivity checks visually; retain the material limitations.
editorial_header('How stable are the selections?',92)
textline('13 checks = 1 baseline + 12 assumption changes',M,H-119,18,NAVY,DISPLAY)
textline('A setting is one version of the analysis, not a match or a dataset.',M,H-135,8.7,MUTED,FONT)

left=M;tw=405;right=left+tw+24;rw=CW-tw-24;top=H-151
families=[
 ('01','Baseline','Top 20% pressure; wicket value 12; shrinkage 150; U weight 0.20'),
 ('02-04','Pressure threshold','Top 25%, 15% and 10% instead of 20%'),
 ('05-06','Wicket value','8 and 16 instead of 12 runs per dismissal'),
 ('07-08','Sample shrinkage','75 and 300 instead of 150 pressure units'),
 ('09-10','Ordinary-impact weight','0 and 0.40 instead of 0.20'),
 ('11-12','Chase pressure','No closeness adjustment; alternative component weights'),
 ('13','Recency','Older-year weight = 0.85 per year; 2026 weight = 1'),
]
rowh=19
for i,(num,key,desc) in enumerate(families):
    yy=top-i*rowh
    panel(left,yy,tw,rowh-1,PALE if i%2==0 else LIGHT,3)
    textline(num,left+8,yy-12,7.6,PINK,BOLD)
    textline(key,left+44,yy-12,7.7,NAVY,BOLD)
    p(desc,left+164,yy-4,tw-173,'micro')
p('Each version ranks the same primary-eligible pool. A version with fewer than 50 pressure units or five pressure matches assigns an unsupported worst rank.',left,top-7*rowh-6,tw,'micro')

panel(right,top,rw,158,NAVY)
portrait('Kuldeep Yadav',right+12,top-12,83,108,colors.HexColor('#F3B9D4'))
textline('13/13',right+111,top-41,38,colors.white,DISPLAY)
p('<b>Kuldeep Yadav</b> was selected in the top ten in every analysis version.',right+111,top-51,rw-125,'white')
for j in range(13):
    c.setFillColor(colors.HexColor('#F489BC'));c.circle(right+114+j*12.8,top-101,3.3,fill=1,stroke=0)
p('<b>12/13</b> means selected in 12 versions. Higher counts show less sensitivity to the tested assumptions; they are not future success probabilities.',right+12,top-127,rw-24,'whiteSmall')

top=H-333;col=(CW-24)/2;right=M+col+24
panel(M,top,col,137,NAVY)
textline('2026 HOLDOUT TEST',M+14,top-20,8,colors.HexColor('#F489BC'))
textline('-0.374',M+14,top-53,29,colors.white,DISPLAY)
textline('-0.039',M+col/2+6,top-53,29,colors.white,DISPLAY)
textline('batting rank correlation (28 players)',M+14,top-67,7.2,colors.HexColor('#CDD2E5'),FONT)
textline('bowling (29 players)',M+col/2+6,top-67,7.2,colors.HexColor('#CDD2E5'),FONT)
p('Training used 2022-2025; testing used 2026. Earlier batting top-ten selections underperformed other eligible batters. Rank persistence was weak: <b>the model is not a validated 2027 forecast.</b>',M+14,top-80,col-28,'white')

textline('RR role checks',right,top-13,19,NAVY,DISPLAY)
smallgap=8;smallw=(col-2*smallgap)/3
for j,(name,role) in enumerate([('Rajat Patidar','Domestic middle order'),('Kuldeep Yadav','Middle-over wickets'),('Matheesha Pathirana','Closing-over pace')]):
    xx=right+j*(smallw+smallgap)
    panel(xx,top-25,smallw,80,PALE)
    portrait(name,xx+7,top-31,42,46,LIGHT)
    names=name.split(' ')
    p('<b>'+html.escape(' '.join(names[:-1]))+'<br/>'+html.escape(names[-1])+'</b>',xx+55,top-35,smallw-60,'micro')
    textline(role,xx+7,top-95,7.1,NAVY,FONT)
p('Illustrative role options, not confirmed auction targets. Verify the 2027 pool, release/trade, clearance, fitness, price and overseas balance. Parag is existing RR core; Fakhar, Abrar and Shaheen are benchmark-only until entry is verified. Mustafizur needs a specific clearance check.',right,top-113,col,'micro')

yy=105
line(M,yy,CW)
p('<b>Reliability limits:</b> 13 versions and 1,000 whole-match bootstraps test sensitivity and sampling variation, not every modelling choice. Bootstrap expectations and eligibility are fixed. Incomplete coverage, subjective weights and uncertain rank cutoffs remain material. RR fits use the published 2026 squad as a baseline, not confirmed 2027 vacancies.',M,yy-8,CW,'micro')
p('<b>Sources:</b> supplied pack and saved rankings; <link href="https://cricsheet.org/">Cricsheet</link> (<link href="https://opendatacommons.org/licenses/by/1-0/">ODC-By v1.0</link>); <link href="https://www.rajasthanroyals.com/rr-players">RR squad</link>; <link href="https://www.iplt20.com/news/article/ipl-governing-council-announces-tata-ipl-player-regulations-2025-27">IPL regulations</link>; <link href="https://indianexpress.com/article/sports/cricket/mustafizur-rahman-released-by-kkr-following-bcci-instruction-10453190/">Mustafizur release report</link>. Portraits link to IPL, ICC, Cricket Australia, RR/GT/MI or Wisden sources; kits may be historical.',M,yy-43,CW,'tiny')
footer();c.save()
'''

start = original.index('# 1. Concise methodology')
end = original.index('class Portrait(Flowable):')
original = original[:start] + page_one + original[end:]
start = original.index('# 4. Compact charts')
end = original.index('footer();c.save()',start) + len('footer();c.save()')
original = original[:start] + page_four + original[end:]
if globals().get('WATCHLIST_EDITION'):
    original = original.replace('page 4', 'page 5')
    original = original.replace("PDF=OUT/'SupeRR_Selector_Submission_Revised.pdf'", "PDF=TMP/'watchlist_base.pdf'")
exec(compile(original,str(root/'create_submission_pdf.py'),'exec'),{'__file__':str(root/'create_submission_pdf.py'),'__name__':'__main__'})
