"""Regenerate the shareable workflow SVG/PNG: python -m pip install Pillow; python docs/render_workflow.py.

Pillow is only a documentation rendering dependency. Paddock itself uses the standard library.
"""
from pathlib import Path
from html import escape
import math
import os
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent
W, H, SCALE = 1120, 2540, 2
img = Image.new("RGB", (W*SCALE, H*SCALE), "#ffffff")
draw = ImageDraw.Draw(img)
svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
       '<title>Paddock: from a query in a new repo to completed work</title>',
       '<desc>Set the repo account rule, select an allowed login, work directly or through an optional herdr crew, verify, and review. Qwen is optional and off by default in sample crews.</desc>',
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


text(50,52,'PADDOCK',size=35,bold=True)
text(50,96,'From a query in a new repo to completed work',size=27,color=MUTED)
box(310,140,500,90,'You ask a question in a new repo',fill=PURPLEF,stroke=PURPLE)
rect(30,260,1040,805,'#f7f9fc','#cbd5e3',r=24,width=2)
text(60,302,'01  REPO OWNERSHIP & LOGIN',size=22,bold=True,color=MUTED)
box(165,340,790,130,'Give the repo an account rule',[
    'Use an existing account folder, or add a rule for this repo.',
    'Manual setup: a repo outside all rules is unrestricted.'])
arrow([(560,230),(560,340)])
arrow([(560,470),(560,495),(310,495),(310,520)])
arrow([(560,495),(810,495),(810,520)])
box(90,520,440,120,'Terminal: wrapper chooses',[
    'The folder picks the login.', 'An allowed explicit login is kept.'])
box(590,520,440,120,'T3: you choose the instance',[
    'One provider instance per account.', 'Set its home; install its guard.'])
arrow([(310,640),(310,670),(560,670),(560,700)])
arrow([(810,640),(810,670),(560,670)])
diamond(560,775,['Account allowed','in this folder?'])
arrow([(750,775),(820,775)],color=RED)
text(776,749,'No',size=22,bold=True,color=RED)
box(820,710,235,145,'Stop & correct',[
    'Select the right', 'account; retry.'],fill=REDF,stroke=RED)
arrow([(560,850),(560,905)],color=GREEN)
text(580,877,'Yes',size=22,bold=True,color=GREEN)
box(165,905,790,130,'Guarded session',[
    'Claude: tool hook. T3 Codex: configured proxy.',
    'Linked worktrees must satisfy both repo and location rules.'])
rect(30,1090,1040,1320,'#f7f9fc','#cbd5e3',r=24,width=2)
text(60,1124,'02  WORK & VERIFICATION',size=22,bold=True,color=MUTED)
arrow([(560,1035),(560,1150)])
diamond(560,1225,['Use a herdr','crew?'])
arrow([(370,1225),(310,1225),(310,1370)])
text(115,1294,'No · work directly',size=24,bold=True)
arrow([(750,1225),(810,1225),(810,1370)],color=GREEN)
text(835,1294,'Yes',size=24,bold=True,color=GREEN)
box(90,1370,440,130,'Work in this session',[
    'The agent edits and runs checks.', 'A crew is not required.'])
box(590,1370,440,130,'Coordinator / project lead',[
    'Same account as the coordinator.', 'Writes a bounded task brief.'],fill=GREENF,stroke=GREEN)
arrow([(810,1500),(810,1560)],color=GREEN)
box(590,1560,440,260,'Use only enabled helpers',[
    'Codex: implementation / review',
    'Gemini: large reads, if enabled',
    'LiteLLM: optional paid reviewer',
    'Qwen: optional small local tasks',
    'Qwen is OFF in sample crews.',
    'Returns result.md + changes.'],fill=GREENF,stroke=GREEN)
arrow([(310,1500),(310,1870),(560,1870),(560,1910)])
arrow([(810,1820),(810,1870),(560,1870)])
box(310,1910,500,115,'Verify the work',[
    'Inspect changes and run relevant tests.'])
arrow([(560,2025),(560,2075)])
diamond(560,2150,['You review:', 'Query satisfied?'])
arrow([(750,2150),(1090,2150),(1090,1225),(750,1225)],color=PURPLE,dashed=True)
text(808,2115,'No · revise / retry',size=23,bold=True,color=PURPLE)
arrow([(560,2225),(560,2280)],color=GREEN)
text(580,2252,'Yes',size=23,bold=True,color=GREEN)
rect(310,2280,500,80,'#c1ecd7',GREEN,r=40)
text(560,2320,'Work complete',size=29,bold=True,center=True)
text(50,2454,'Guard coverage depends on the host and installed integration; it is not a sandbox.',size=23,color=MUTED)
text(50,2491,'Native Windows: portable Claude hook installer. Unix launcher / crew support is separate.',size=22,color=MUTED)
svg.append('</svg>')
(OUT/'paddock-workflow.svg').write_text('\n'.join(svg),encoding='utf-8')
img.save(OUT/'paddock-workflow.png',optimize=True)
print(OUT/'paddock-workflow.png')
