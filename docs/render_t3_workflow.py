"""Regenerate the shareable workflow SVG/PNG: python -m pip install Pillow; python docs/render_workflow.py.

Pillow is only a documentation rendering dependency. Paddock itself uses the standard library.
"""
from pathlib import Path
from html import escape
import math
import os
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parents[1] / "t3"
W, H, SCALE = 1120, 2750, 2
img = Image.new("RGB", (W*SCALE, H*SCALE), "#ffffff")
draw = ImageDraw.Draw(img)
svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
       '<title>Paddock T3 crew: instruction, code and process review</title>',
       '<desc>Onboard approved resources, clarify instructions, build and verify, then obtain separate code and process reviews. Errors and missing data are never success.</desc>',
       f'<rect width="{W}" height="{H}" fill="white"/>']
INK, MUTED, LINE = '#172b44', '#586b85', '#45566e'
BLUE, BLUEF = '#3076df', '#e0ecff'
GREEN, GREENF = '#23865e', '#e3f5eb'
PURPLE, PURPLEF = '#7762d5', '#ece7ff'
GOLD, GOLDF = '#d49408', '#fff4d6'
RED, REDF = '#c94b38', '#ffebe6'


def font(size, bold=False):
    names = ([os.environ.get('PADDOCK_DIAGRAM_FONT_BOLD')] if bold else [os.environ.get('PADDOCK_DIAGRAM_FONT')])
    names += [f'/System/Library/Fonts/Supplemental/Arial{" Bold" if bold else ""}.ttf',
              f'C:/Windows/Fonts/arial{"bd" if bold else ""}.ttf',
              f'/usr/share/fonts/truetype/dejavu/DejaVuSans{"-Bold" if bold else ""}.ttf']
    return ImageFont.truetype(next(p for p in names if p and Path(p).exists()), size*SCALE)


def text(x, y, value, size=25, bold=False, color=INK, center=False):
    f = font(size, bold)
    draw.text((x*SCALE, y*SCALE), value, font=f, fill=color, anchor='mm' if center else 'lm')
    svg.append(f'<text x="{x}" y="{y}" fill="{color}" font-family="Arial, sans-serif" font-size="{size}" font-weight="{700 if bold else 400}" dominant-baseline="central" text-anchor="{"middle" if center else "start"}">{escape(value)}</text>')


def rect(x,y,w,h,fill,stroke,r=18,width=3):
    draw.rounded_rectangle((x*SCALE,y*SCALE,(x+w)*SCALE,(y+h)*SCALE),radius=r*SCALE,fill=fill,outline=stroke,width=width*SCALE)
    svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{width}"/>')


def box(x,y,w,h,title,lines=(),fill=BLUEF,stroke=BLUE):
    rect(x,y,w,h,fill,stroke)
    text(x+24,y+34,title,bold=True,size=27)
    for i,line in enumerate(lines): text(x+24,y+73+i*33,line,size=24,color=MUTED)


def arrow(points,color=LINE,dashed=False):
    pts=[(x*SCALE,y*SCALE) for x,y in points]
    if dashed:
        for (x1,y1),(x2,y2) in zip(pts,pts[1:]):
            length=math.hypot(x2-x1,y2-y1)
            for s in range(0,int(length),20*SCALE):
                e=min(s+11*SCALE,length)
                draw.line((x1+(x2-x1)*s/length,y1+(y2-y1)*s/length,x1+(x2-x1)*e/length,y1+(y2-y1)*e/length),fill=color,width=3*SCALE)
    else: draw.line(pts,fill=color,width=3*SCALE)
    (ax,ay),(bx,by)=points[-2:]; angle=math.atan2(by-ay,bx-ax)
    tri=[(bx,by),(bx-17*math.cos(angle)+8*math.sin(angle),by-17*math.sin(angle)-8*math.cos(angle)),
         (bx-17*math.cos(angle)-8*math.sin(angle),by-17*math.sin(angle)+8*math.cos(angle))]
    draw.polygon([(x*SCALE,y*SCALE) for x,y in tri],fill=color)
    svg.append(f'<polyline points="{" ".join(f"{x},{y}" for x,y in points)}" fill="none" stroke="{color}" stroke-width="3"'+(' stroke-dasharray="11 9"' if dashed else '')+'/>')
    svg.append(f'<polygon points="{" ".join(f"{x},{y}" for x,y in tri)}" fill="{color}"/>')


def diamond(cx,cy,lines):
    points=[(cx,cy-75),(cx+190,cy),(cx,cy+75),(cx-190,cy)]
    draw.polygon([(x*SCALE,y*SCALE) for x,y in points], fill=GOLDF)
    draw.line([(x*SCALE,y*SCALE) for x,y in points+[points[0]]],fill=GOLD,width=3*SCALE)
    svg.append(f'<polygon points="{" ".join(f"{x},{y}" for x,y in points)}" fill="{GOLDF}" stroke="{GOLD}" stroke-width="3"/>')
    for i,line in enumerate(lines): text(cx,cy+(i-(len(lines)-1)/2)*32,line,size=26,bold=True,center=True)


text(50,52,'PADDOCK · T3 CREW',size=35,bold=True)
text(50,96,'One company. Approved resources. Evidence before claims.',size=27,color=MUTED)
box(310,140,500,90,'You ask for work in a repo',fill=PURPLEF,stroke=PURPLE)
rect(30,270,1040,2340,'#f7f9fc','#cbd5e3',r=24,width=2)
box(165,310,790,135,'Initial interview / project setup',[
 'Which approved AI resources do you have? Bind the four roles.',
 'Preserve project rules; configure real checks. No local model required.'])
arrow([(560,230),(560,310)])
arrow([(560,445),(560,505)])
box(165,505,790,105,'Coordinator captures the request and contract',[
 'Scope, exclusions, acceptance checks and existing authorization.'])
arrow([(560,610),(560,670)])
box(165,670,790,140,'Instruction adversary',[
 'Are instructions consistent, scoped and testable?',
 'Keep the original request; challenge assumptions before building.'],fill=PURPLEF,stroke=PURPLE)
arrow([(560,810),(560,850)])
diamond(560,925,['Clear and','testable?'])
arrow([(750,925),(820,925)],color=RED)
text(777,899,'No',size=22,bold=True,color=RED)
box(820,860,235,140,'Resolve gaps',[
 'Clarify or correct', 'the contract.'],fill=REDF,stroke=RED)
arrow([(1055,925),(1090,925),(1090,555),(955,555)],color=PURPLE,dashed=True)
arrow([(560,1000),(560,1060)],color=GREEN)
text(580,1030,'Yes',size=23,bold=True,color=GREEN)
box(165,1060,790,135,'Coordinator builds or assigns a bounded builder',[
 'One builder by default; current session handles small tasks.',
 'Only approved live instances. Coordinator owns integration.'])
arrow([(560,1195),(560,1255)])
box(165,1255,790,135,'Execute verification and freeze the evidence',[
 'Actual command output, test completion/counts and source digest.',
 'Preserve failures and host receipts; draft the final claims.'])
arrow([(560,1390),(560,1430)])
diamond(560,1505,['Checks genuinely','complete?'])
arrow([(750,1505),(820,1505)],color=RED)
text(777,1479,'No',size=22,bold=True,color=RED)
box(820,1440,235,170,'Report / repair',[
 'Errors, skips and', 'no data are NOT', 'success.'],fill=REDF,stroke=RED)
arrow([(560,1580),(560,1610),(310,1610),(310,1650)],color=GREEN)
arrow([(560,1610),(810,1610),(810,1650)],color=GREEN)
box(90,1650,440,235,'Fresh code reviewer',[
 'Does the implementation work?',
 'Correctness and regressions.',
 'Meaningful tests and edge cases.',
 'Cite concrete code findings.'],fill=GREENF,stroke=GREEN)
box(590,1650,440,235,'Fresh process adversary',[
 'Did the agent follow instructions?',
 'Are claims backed by raw evidence?',
 'Were failures hidden or misreported?',
 'Which rails were actually observed?'],fill=PURPLEF,stroke=PURPLE)
arrow([(310,1885),(310,1920),(560,1920),(560,1950)])
arrow([(810,1885),(810,1920),(560,1920)])
diamond(560,2025,['Evidence current?', 'Findings resolved?'])
arrow([(750,2025),(1090,2025),(1090,1120),(955,1120)],color=PURPLE,dashed=True)
text(795,1980,'No · repair / re-review',size=21,bold=True,color=PURPLE)
text(795,2009,'At most two rounds',size=21,color=PURPLE)
arrow([(560,2100),(560,2170)],color=GREEN)
text(580,2135,'Yes',size=23,bold=True,color=GREEN)
box(165,2170,790,190,'Coordinator audits records and reports separate outcomes',[
 'Verification · code review · adversary review · host controls',
 'Unknown stays unknown. Stale or missing reviews stay incomplete.',
 'Record completeness is not proof that controls were enforced.'])
arrow([(560,2360),(560,2440)],color=GREEN)
rect(260,2440,600,90,'#c1ecd7',GREEN,r=40)
text(560,2485,'Result ready for your review',size=29,bold=True,center=True)
text(50,2660,'The adversary checks evidence and behavior; it does not infer deceptive intent.',size=23,color=MUTED)
text(50,2700,'Public preview · No herdr · Multi-account isolation is a separate optional extension.',size=22,color=MUTED)
svg.append('</svg>')
(OUT/'workflow.svg').write_text('\n'.join(svg),encoding='utf-8')
img.save(OUT/'workflow.png',optimize=True)
print(OUT/'workflow.png')
