"""Dimensioned connector-space study, NOT a KiCad placement or routing result."""
from pathlib import Path
import json
import math
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
DOCS = ROOT / "docs"
widths = {2: 5.75, 3: 7.0, 4: 8.25, 5: 9.5, 6: 10.75, 8: 13.25}
parts = []

def add(label, face, x, y, w, h, kind, geometry="nominal body"):
    parts.append(dict(label=label, face=face, x=x, y=y, width=w, height=h,
                      kind=kind, geometry=geometry))

def row(items, face, side, gap=1.0):
    span = sum(w for _, w, _ in items) + gap * (len(items)-1)
    pos = (60-span)/2
    for label, along, kind in items:
        if side in ("left", "right"):
            add(label, face, .5 if side=="left" else 54.5, pos, 5, along, kind)
        else:
            add(label, face, pos, .5 if side=="top" else 54.5, along, 5, kind)
        pos += along+gap
    return span

front_spans = {}
front_spans['left'] = row([(f'ADC{i:02}', widths[2], 'ADC') for i in range(1,6)] + [('CTRL_A', widths[6], 'CTRL')], 'front', 'left')
front_spans['right'] = row([(f'ADC{i:02}', widths[2], 'ADC') for i in range(6,11)] + [('CTRL_B', widths[6], 'CTRL')], 'front', 'right')
front_spans['top'] = row([('SPI_A',widths[6],'DIG'),('SPI_B',widths[6],'DIG'),('ENC_A',widths[5],'DIG'),('ENC_B',widths[5],'DIG')], 'front', 'top')
# Buttons use the actual library courtyard, rotated 90 degrees. Their solder
# lands span 8.6mm, so treating them as only 6.05mm-wide bodies would be misleading.
bottom = [('PWM_A',widths[8],5,'PWM'),('RESET',4.4,9.1,'BUTTON'),('BOOT',4.4,9.1,'BUTTON'),('PWM_B',widths[8],5,'PWM')]
front_spans['bottom'] = sum(x[1] for x in bottom) + 3
pos = (60-front_spans['bottom'])/2
for label, w, h, kind in bottom:
    add(label,'front',pos,59.75-h if kind=='BUTTON' else 54.5,w,h,kind,
        "reviewed switch courtyard, 90deg rotation" if kind=='BUTTON' else "nominal body")
    pos += w+1

back_spans = {}
back_spans['top'] = row([('I2C_A',widths[4],'DIG'),('I2C_B',widths[4],'DIG'),('CAN',widths[3],'DIG'),('TTL',widths[3],'DIG')], 'back', 'top')
back_spans['bottom'] = row([('SWD',widths[5],'DIG'),('5V_IN',6,'POWER')], 'back', 'bottom',gap=2)
# Replace the unspecified supply header's body with an explicitly provisional
# 6x6mm placeholder. Its actual part and footprint remain unselected.
next(x for x in parts if x['label']=='5V_IN').update(y=53.5,height=6,geometry='unselected power connector 6x6mm placeholder')
add('MCU', 'front',21,21,18,18,'MCU','18x18mm estimated package/escape reservation; body14x14')

holes=[(4,4),(56,4),(4,56),(56,56)]
radius=2.8
def overlap(a,b):
    return a['x']<b['x']+b['width'] and b['x']<a['x']+a['width'] and a['y']<b['y']+b['height'] and b['y']<a['y']+a['height']
collisions=[]
for i,a in enumerate(parts):
    assert min(a['x'],a['y'])>=0 and a['x']+a['width']<=60 and a['y']+a['height']<=60
    for b in parts[i+1:]:
        if a['face']==b['face'] and overlap(a,b):collisions.append([a['label'],b['label']])
    for hx,hy in holes:
        dx=max(a['x']-hx,0,hx-(a['x']+a['width']))
        dy=max(a['y']-hy,0,hy-(a['y']+a['height']))
        assert math.hypot(dx,dy)>=radius, (a['label'],hx,hy)
assert not collisions, collisions
headers=[x for x in parts if x['kind'] not in ('BUTTON','MCU')]
assert len(headers)==24
assert len([x for x in headers if x['face']=='front'])==18
assert len([x for x in headers if x['face']=='back'])==6
assert {x['label'] for x in headers} == ({f'ADC{i:02}' for i in range(1,11)} | {'PWM_A','PWM_B','SPI_A','SPI_B','I2C_A','I2C_B','ENC_A','ENC_B','CAN','TTL','SWD','CTRL_A','CTRL_B','5V_IN'})

inventory=json.loads((DOCS/'controller_connector_inventory.json').read_text(encoding='utf-8'))
GH_total=sum(g['quantity']*widths[g['pins_each']] for g in inventory['connector_groups'] if g['name']!='5V_IN')
assert GH_total==186
study={
 'date':'2026-11-11','status':'Alternative feasibility study only; not a chosen placement, native PCB, or DRC result.',
 'board_mm':[60,60],'holes_mm':holes,'legacy_mounting_keepout_radius_mm':radius,
 'all_side_entry_single_face':{'GH_header_body_width_sum_mm':GH_total,'estimated_power_header_width_mm':[4,6],
   'total_bodies_mm':[190,192],'inter_header_gaps_at_1mm_mm':20,'total_with_gaps_mm':[210,212],
   'estimated_clear_perimeter_after_corners_mm':[176,184],
   'conclusion':'Insufficient comfortable edge length for all24 single-face, single-row side-entry ports, even before buttons and final footprints.'},
 'two_face_alternative':{'front_connector_count':18,'back_connector_count':6,'front_edge_body_spans_mm':front_spans,
   'back_edge_body_spans_mm':back_spans,'unapproved_back_side_ports':['I2C_A','I2C_B','CAN','TTL','SWD','5V_IN'],
   'buttons':'RESET and BOOT stay on the MCU/top face near an edge, using actual rotated switch courtyards.',
   'coordinate_frame':'Both drawings use the SAME assembly XY frame; rear drawing is not a solder-side mirrored manufacturing view.',
   'rectangles':parts,'same_face_rectangle_overlap_count':len(collisions),
   'conclusion':'Nominal-body geometry has a feasible arrangement with both buttons and MCU reservation. Full footprints, routing, mating plugs, latch access and stack clearances NOT validated.'},
 'limitations':['GH rectangles are bodies only, not checked courtyard/land patterns; other pin-count models still need exact selection.',
   'Power inlet uses an unselected6x6 placeholder.',
   'MCU18x18 reservation is an estimate; decoupling, regulator, protection circuits, CAN PHY and routing are not placed.',
   'Rear-facing connectors require enclosure/feet clearance, and cable/latch access. Existing standoff height is not frozen.',
   'Upper power board, wires, screw heads, tool/finger access and power-device thermal/EMI projections require assembly review.',
   'A 4-layer board is the planning candidate, not a guarantee of a routable layout.'],
 'sources':['controller_connector_inventory.json','controller_signal_connector_candidates.json','pcb_stack_contract_rev_e.json',
   'D:/workspace/kicad_library/footprints/MyFootprints.pretty/XKB_TS-1101-C-W_6.05x3.70mm_Pad1.10x1.00mm.kicad_mod'],
 'native_design_changed':False}
(DOCS/'controller_60mm_fit_study.json').write_text(json.dumps(study,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

S=8
img=Image.new('RGB',(1230,710),'#f3f5f8');d=ImageDraw.Draw(img)
font_path=Path('C:/Windows/Fonts/msyh.ttc')
def font(n):return ImageFont.truetype(str(font_path),n) if font_path.exists() else ImageFont.load_default()
colors={'ADC':'#c8e7dc','CTRL':'#f4d3ac','DIG':'#c9dced','PWM':'#f3ca9a','BUTTON':'#f3e49e','MCU':'#d7d5e8','POWER':'#edc1c9'}
def text(x,y,s,n=15,fill='#243247'):d.text((x,y),s,font=font(n),fill=fill)
text(28,15,'60×60mm 连接器空间估算：18口顶面＋6口底面',23)
text(28,49,'仅做几何可行性比较；不是PCB布局、封装检查或布线结果。',15)
for face,ox,title in [('front',57,'顶面：MCU、按键、18个接口'),('back',675,'底面：另6个接口（同一装配XY坐标）')]:
    oy=124
    text(ox,86,title,18)
    d.rectangle((ox,oy,ox+60*S,oy+60*S),fill='#ffffff',outline='#243247',width=3)
    for hx,hy in holes:
        box=(ox+(hx-radius)*S,oy+(hy-radius)*S,ox+(hx+radius)*S,oy+(hy+radius)*S)
        d.ellipse(box,fill='#f0f0f0',outline='#aab1ba',width=1)
        dr=1.1*S;d.ellipse((ox+hx*S-dr,oy+hy*S-dr,ox+hx*S+dr,oy+hy*S+dr),fill='#c3c9cf',outline='#596673')
    for p in parts:
        if p['face']!=face:continue
        x1=ox+p['x']*S;y1=oy+p['y']*S;x2=x1+p['width']*S;y2=y1+p['height']*S
        d.rectangle((x1,y1,x2,y2),fill=colors[p['kind']],outline='#445164',width=1)
        label=p['label'];f=font(11 if p['width']<6 else 13)
        if p['kind']=='BUTTON':
            label='RST' if label=='RESET' else 'BOOT';f=font(9)
            cx=(x1+x2)/2;cy=(y1+y2)/2
            d.rectangle((cx-1.85*S,cy-3.025*S,cx+1.85*S,cy+3.025*S),outline='#a18b32',width=1)
        if p['kind']=='MCU':label='MCU / 18×18 预留';f=font(14)
        bb=d.textbbox((0,0),label,font=f)
        d.text(((x1+x2-(bb[2]-bb[0]))/2,(y1+y2-(bb[3]-bb[1]))/2-2),label,font=f,fill='#1b283b')
    text(ox+194,oy+60*S+10,'60 mm',14)
text(28,649,'GH仅画本体；按键画实际courtyard；5V入口暂用6×6mm占位。灰圈为M2孔附近Ø5.6mm规划净空。',14)
text(28,675,'底面接口需要额外离地/外壳净空；插头、锁扣、线缆弯折、上下板干涉尚未验证。',14)
img.save(OUT/'controller_60mm_two_face_body_study.png')
print(json.dumps({'connectors':24,'front':18,'back':6,'overlaps':0,'front_spans_mm':front_spans,'single_face_body_plus_gap_mm':[210,212]},ensure_ascii=False))
