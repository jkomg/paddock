"""Create a presentation-ready Paddock decision flowchart using Pillow."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
helpers = (ROOT / 'docs/render_t3_workflow.py').read_text().split("\ntext(50,52,")[0]
helpers = helpers.replace('W, H, SCALE = 1120, 2750, 2', 'W, H, SCALE = 1120, 1900, 2')
exec(compile(helpers, str(ROOT / 'docs/render_t3_workflow.py'), 'exec'))
OUT = ROOT / 'output'

text(60,65,'PADDOCK',size=44,bold=True)
text(60,115,'How a request becomes an evidence-backed result',size=29,color=MUTED)
text(60,160,'T3 crew workflow · Coordinator judgment + explicit evidence checks',size=23,color=MUTED)

box(60,210,1000,110,'1  You set the goal and boundaries',[
    'Approved AI resources, scope, acceptance criteria and permitted actions.'],fill=PURPLEF,stroke=PURPLE)
arrow([(560,320),(560,355)])
box(60,355,1000,140,'2  Coordinator captures the plan',[
    'Substantial or ambiguous work → fresh instruction adversary.',
    'Resolve contradictions and define what evidence will count as success.'])
arrow([(560,495),(560,530)])
box(60,530,1000,110,'3  Coordinator builds or delegates',[
    'Small task → current session. Larger task → one bounded builder.'])
arrow([(560,640),(560,680)])
diamond(560,755,['Approved, available','provider binding?'])
arrow([(750,755),(820,755)],color=RED)
text(775,729,'No',size=22,bold=True,color=RED)
box(820,687,250,135,'Stop dispatch',[
    'Explain the gap.', 'No silent fallback.'],fill=REDF,stroke=RED)
arrow([(560,830),(560,870)],color=GREEN)
text(580,851,'Yes',size=21,bold=True,color=GREEN)
box(60,870,1000,110,'4  Build → integrate → run actual project checks',[
    'Keep command output, test counts, failures and host receipts.'])
arrow([(560,980),(560,1020)])
diamond(560,1095,['Verification','complete?'])
arrow([(750,1095),(820,1095)],color=RED)
text(775,1069,'No',size=22,bold=True,color=RED)
box(820,1027,250,135,'Repair / report',[
    'Missing evidence', 'stays incomplete.'],fill=REDF,stroke=RED)
arrow([(560,1170),(560,1210)],color=GREEN)
text(580,1191,'Yes',size=21,bold=True,color=GREEN)
box(60,1210,1000,100,'5  Freeze source + create an evidence packet',[
    'Bind source, original requirements, checks, receipts and proposed claims.'])
arrow([(560,1310),(560,1340),(300,1340),(300,1370)])
arrow([(560,1340),(820,1340),(820,1370)])
box(60,1370,480,150,'Fresh code reviewer',[
    'Is the implementation correct?', 'Does it meet the requirements?'],fill=GREENF,stroke=GREEN)
box(580,1370,480,150,'Separate process adversary',[
    'Did the agent follow instructions?', 'Does evidence support its claims?'],fill=PURPLEF,stroke=PURPLE)
arrow([(300,1520),(300,1550),(560,1550),(560,1580)])
arrow([(820,1520),(820,1550),(560,1550)])
box(60,1580,1000,140,'6  Resolve findings and audit the records',[
    'Repair → new packet + fresh reviews. At most two automatic repair rounds.',
    'Unresolved findings → return to you with evidence.'])
arrow([(560,1720),(560,1755)],color=GREEN)
rect(60,1755,1000,75,GREENF,GREEN)
text(560,1793,'Report: checks · reviews · host controls · CI · deployment',size=26,bold=True,center=True)
text(60,1864,'Complete records are not proof of correctness or enforced permissions.',size=24,color=MUTED)

svg.append('</svg>')
(OUT/'paddock-flowchart.svg').write_text('\n'.join(svg),encoding='utf-8')
img.save(OUT/'paddock-flowchart.png',optimize=True)
print(OUT/'paddock-flowchart.png')
