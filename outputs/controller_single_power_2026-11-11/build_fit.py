"""All-top-face nominal-body space study for the reduced controller."""
from pathlib import Path
import json,math
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent;DOCS=ROOT/'docs'
width={2:5.75,3:7,4:8.25,5:9.5,6:10.75,8:13.25}
parts=[];spans={}
def add(label,x,y,w,h,kind,geometry='nominal connector body'):
    parts.append(dict(label=label,x=x,y=y,width=w,height=h,kind=kind,geometry=geometry))
def row(side,items):
    span=sum(w for _,w,_ in items)+len(items)-1;spans[side]=span;pos=(60-span)/2
    for label,w,kind in items:
        if side in ['left','right']:add(label,.5 if side=='left' else 54.5,pos,5,w,kind)
        else:add(label,pos,.5 if side=='top' else 54.5,w,5,kind)
        pos+=w+1
row('left',[(f'ADC{i:02}',width[2],'ADC') for i in range(1,6)]+[('ENC',width[5],'DIG')])
row('right',[(f'ADC{i:02}',width[2],'ADC') for i in range(6,11)]+[('I2C',width[4],'DIG')])
row('top',[('PWM',width[8],'PWM'),('CTRL',width[6],'CTRL'),('SPI',width[6],'DIG')])
bottom=[('CAN',7,5,'DIG'),('TTL',7,5,'DIG'),('SWD',9.5,5,'DIG'),('5V_IN',6,6,'POWER'),('RESET',4.4,9.1,'BUTTON'),('BOOT',4.4,9.1,'BUTTON')]
spans['bottom']=sum(x[1] for x in bottom)+len(bottom)-1;pos=(60-spans['bottom'])/2
for label,w,h,kind in bottom:
    add(label,pos,59.75-h if kind=='BUTTON' else 59.5-h,w,h,kind,
        'actual switch courtyard, rotated90deg' if kind=='BUTTON' else 'unselected6x6 power header placeholder' if kind=='POWER' else 'nominal connector body')
    pos+=w+1
add('MCU',23,23,14,14,'MCU','14x14 estimated package/escape area for10x10 LQFP64 body')
holes=[(4,4),(56,4),(4,56),(56,56)];radius=2.8
collisions=[]
for i,a in enumerate(parts):
    assert a['x']>=0 and a['y']>=0 and a['x']+a['width']<=60 and a['y']+a['height']<=60
    for b in parts[i+1:]:
        if a['x']<b['x']+b['width'] and b['x']<a['x']+a['width'] and a['y']<b['y']+b['height'] and b['y']<a['y']+a['height']:collisions.append([a['label'],b['label']])
    for hx,hy in holes:
        dx=max(a['x']-hx,0,hx-a['x']-a['width']);dy=max(a['y']-hy,0,hy-a['y']-a['height'])
        assert math.hypot(dx,dy)>=radius,(a['label'],hx,hy)
assert not collisions
assert len(parts)==22
assert len([x for x in parts if x['kind'] not in ['BUTTON','MCU']])==19
assert max(spans.values())<=45
study={'revision':'G-single-power','status':'All-top-face geometry candidate, not native PCB or routed/DRC-validated placement.',
 'board_mm':[60,60],'connector_count':19,'top_connector_count':19,'bottom_connector_count':0,
 'mounting_holes_mm':holes,'legacy_keepout_radius_mm':radius,'assumed_available_length_each_edge_mm':45,
 'minimum_between_envelopes_mm':1,'edge_spans_mm':spans,'GH_body_width_total_mm':133.5,'power_body_placeholder_width_mm':6,
 'body_width_plus_header_gaps_mm':154.5,'including_two_switch_courtyards_and_gaps_mm':sum(spans.values()),
 'rectangles':parts,'rectangle_overlap_count':0,
 'scope':['GH rectangles represent nominal bodies; actual land/courtyard data for all selected headers still need review.',
  'Buttons use reviewed TS-1101-C-W9.1x4.4 courtyard rotated90deg; both remain MCU/top-face edge buttons.',
  'Power connector is an unselected6x6 placeholder; actual model/footprint may change fit.',
  'MCU14x14 is an estimated escape reservation; decoupling, regulator, clamps, CAN PHY and routing are not placed.',
  'Mating plugs/latches, cables, screw heads, upper power-board clearance and mechanical access are unverified.',
  'No native schematic/PCB/library changes;4-layer remains a planning candidate.'],
 'source_inventory':'controller_connector_inventory.json','image':'../outputs/controller_single_power_2026-11-11/controller_60mm_single_power_study.png'}
(DOCS/'controller_60mm_single_power_fit.json').write_text(json.dumps(study,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
img=Image.new('RGB',(850,820),'#f3f5f8');d=ImageDraw.Draw(img);fontpath='C:/Windows/Fonts/msyh.ttc'
def font(n):return ImageFont.truetype(fontpath,n)
def text(x,y,t,n=16):d.text((x,y),t,font=font(n),fill='#263448')
text(28,15,'60×60mm 单功率口：19个接口均在顶面',24)
text(28,55,'尺寸草排：保留10个ADC、单PWM、单SPI/I²C/ABZ；非PCB布局结果。',16)
S=9;ox=155;oy=120
d.rectangle((ox,oy,ox+60*S,oy+60*S),fill='white',outline='#263448',width=3)
for hx,hy in holes:
    d.ellipse((ox+(hx-radius)*S,oy+(hy-radius)*S,ox+(hx+radius)*S,oy+(hy+radius)*S),fill='#f0f0f0',outline='#b0b7c2')
    rr=1.1*S;d.ellipse((ox+hx*S-rr,oy+hy*S-rr,ox+hx*S+rr,oy+hy*S+rr),fill='#c7cdd5',outline='#607084')
colors={'ADC':'#c8e7dc','DIG':'#c9dced','PWM':'#f3ca9a','CTRL':'#f4d3ac','POWER':'#edc1c9','BUTTON':'#f3e49e','MCU':'#d7d5e8'}
for p in parts:
    x1=ox+p['x']*S;y1=oy+p['y']*S;x2=x1+p['width']*S;y2=y1+p['height']*S
    d.rectangle((x1,y1,x2,y2),fill=colors[p['kind']],outline='#445164')
    label=p['label'];f=font(12)
    if p['kind']=='BUTTON':
        label='RST' if label=='RESET' else'BOOT';f=font(10);cx=(x1+x2)/2;cy=(y1+y2)/2
        d.rectangle((cx-1.85*S,cy-3.025*S,cx+1.85*S,cy+3.025*S),outline='#a18b32')
    if p['kind']=='MCU':label='G431RBT6\n14×14预留';f=font(15)
    box=d.multiline_textbbox((0,0),label,font=f,align='center')
    d.multiline_text(((x1+x2-box[2]+box[0])/2,(y1+y2-box[3]+box[1])/2-2),label,font=f,fill='#1d2a3c',align='center')
text(385,675,'60 mm',15)
text(28,719,'GH仅画名义本体；按键画实际courtyard；5V入口暂用6×6mm占位。',15)
text(28,748,'仍需检查完整封装、插头锁扣、线束弯折、支柱及上下板装配净空。',15)
text(28,777,'顶面跨度：左43.25 / 右42.00 / 上36.75 / 下43.30 mm。',15)
img.save(OUT/'controller_60mm_single_power_study.png')
print(json.dumps({'connector_count':19,'overlaps':0,'top_edge_spans_mm':spans},ensure_ascii=False))
