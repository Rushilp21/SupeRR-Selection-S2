"""Append the supplemental watchlist to the approved four-page submission."""
from pathlib import Path
import io,json,shutil,html,runpy
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape,A4
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Table,TableStyle,Paragraph,Image as RLImage
from reportlab.lib.styles import ParagraphStyle
from pypdf import PdfReader,PdfWriter

ROOT=Path(__file__).resolve().parent
DIST=ROOT/'superr-dashboard/dist'
OUT=ROOT/'output/pdf/SupeRR_Selector_Submission_With_Watchlist.pdf'
runpy.run_path(str(ROOT/'redesign_submission.py'),init_globals={'WATCHLIST_EDITION':True})
base=ROOT/'tmp/pdfs/watchlist_base.pdf'
players=json.loads((DIST/'data.json').read_text())['uncapped']
W,H=landscape(A4);M=32;CW=W-64
navy=colors.HexColor('#14243C');pink=colors.HexColor('#D82C75');pale=colors.HexColor('#FCECF3')
pdfmetrics.registerFont(TTFont('WatchSans','C:/Windows/Fonts/arial.ttf'))
pdfmetrics.registerFont(TTFont('WatchBold','C:/Windows/Fonts/arialbd.ttf'))
pdfmetrics.registerFontFamily('WatchSans',normal='WatchSans',bold='WatchBold')
body=ParagraphStyle('b',fontName='WatchSans',fontSize=8.2,leading=10.7,textColor=navy)
tiny=ParagraphStyle('t',parent=body,fontSize=7.5,leading=10)
head=ParagraphStyle('h',parent=body,textColor=colors.white,fontSize=7.5,leading=9.5)
buf=io.BytesIO();c=canvas.Canvas(buf,pagesize=(W,H))
c.setFillColor(navy);c.rect(0,H-83,W,83,fill=1,stroke=0)
c.setFont('WatchBold',9);c.setFillColor(colors.HexColor('#F489BC'));c.drawString(M,H-25,'SupeRR Selector Season 2')
c.setFillColor(colors.white);c.setFont('WatchBold',25);c.drawString(M,H-58,'Uncapped Indian watchlist')
def para(text,x,top,w,style=body):
 p=Paragraph(text,style);_,h=p.wrap(w,1000);p.drawOn(c,x,top-h);return top-h
para('<b>Supplemental scouting order:</b> existing within-role consensus indices, highest first; not a validated cross-role potential score. No India playing-XI appearances are recorded in the supplied dataset. Complete senior ODI/Test/T20I cap histories still need verification.',M,H-94,CW,tiny)
widths=[22,43,107,46,69,58,44,CW-389]
headers=['Rk','Photo','Player','Role','HP rate /<br/>outs or wickets','HP balls /<br/>matches','Index','Possible RR role / evidence strength']
rows=[[Paragraph(h,head) for h in headers]]
for p in players:
 role=p['role'];metric=f"{p['high_strike_rate']:.1f} SR" if role=='batter' else f"{p['high_economy']:.2f} econ"
 image=RLImage(str(DIST/p['photo']),width=36,height=33,kind='proportional')
 values=[str(p['watchlist_rank']),image,'<b>'+html.escape(p['player_name'])+'</b>',role.title(),metric+f"<br/>{int(p['high_dismissals'])} "+('outs' if role=='batter' else 'wickets'),f"{int(p['high_units'])} / {int(p['high_matches'])}",f"{p['consensus_index']:.2f}",html.escape(p['fit'])+'<br/><font color="#A91D59">'+p['status']+'</font>']
 rows.append([v if isinstance(v,RLImage) else Paragraph(v,body) for v in values])
table=Table(rows,colWidths=widths,rowHeights=[26]+[34]*10)
commands=[('BACKGROUND',(0,0),(-1,0),navy),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(-1,-1),4),('RIGHTPADDING',(0,0),(-1,-1),4),('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0)]
for i in range(1,11):commands += [('BACKGROUND',(0,i),(-1,i),pale if i%2 else colors.white),('LINEBELOW',(0,i),(-1,i),.3,colors.HexColor('#DCE3EB'))]
table.setStyle(TableStyle(commands));_,th=table.wrap(CW,1000);table.drawOn(c,M,H-130-th)
para('<b>Read cautiously:</b> Badoni and Suyash have the stronger model evidence; ranks 8-10 are monitoring options. The index is relative to eligible peers within batting or bowling, not a success probability or an identical skill scale across roles. All ten meet the original sample thresholds. Auction entry, availability, fitness, price and confirmed RR role need remain unverified.',M,83,CW,tiny)
para('<b>Scope:</b> this page supplements the two required top-ten lists; it does not change them. SR = runs per 100 balls; economy = runs per six legal balls. Portrait providers are linked in the dashboard footer and watchlist_sources.json. Historical kits do not establish 2027 affiliation.',M,48,CW,ParagraphStyle('s',parent=tiny,fontSize=6.9,leading=8.5))
c.save();buf.seek(0)
original_pages=list(PdfReader(base).pages)
writer=PdfWriter();pages=original_pages[:3]+list(PdfReader(buf).pages)+original_pages[3:]
for i,page in enumerate(pages,1):
 stamp=io.BytesIO();sc=canvas.Canvas(stamp,pagesize=(W,H));sc.setFillColor(colors.white);sc.rect(W-80,7,65,19,fill=1,stroke=0);sc.setFillColor(colors.HexColor('#59697C'));sc.setFont('WatchSans',7);sc.drawRightString(W-M,16,f'{i} / 5');sc.save();stamp.seek(0);page.merge_page(PdfReader(stamp).pages[0]);writer.add_page(page)
writer.add_metadata({'/Title':'SupeRR Selector Season 2 - Rankings, Methodology and Uncapped Watchlist'})
with OUT.open('wb') as f:writer.write(f)
shutil.copy2(OUT,DIST/'methodology.pdf')
assert len(PdfReader(OUT).pages)==5
print(OUT)
