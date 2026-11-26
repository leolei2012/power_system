import re,xml.etree.ElementTree as ET,sys
t=ET.parse('inverter/hardware/review/inverter.net.xml').getroot()
pins={}
for n in t.iter('net'):
    name=n.get('name').split('/')[-1]
    for nd in n.iter('node'):
        pins[(nd.get('ref'),nd.get('pin'))]=name
md=open('docs/pinmap.md').read()
def table(sec):
    s=md.split(sec)[1].split('###')[0]
    rows={}
    for l in s.splitlines():
        c=[x.strip() for x in l.strip('|').split('|')]
        if len(c)>=4 and c[0].isdigit(): rows[int(c[0])]=c[3]
    return rows
bad=0
for J,sec in (('J101','### 4.1'),('J102','### 4.2')):
    for p,exp in table(sec).items():
        got=pins.get((J,str(p)),'<未连接>')
        e=exp
        if '悬空' in e: ok = got=='<未连接>' or got.startswith('unconnected')
        else: ok = got==e
        if not ok: bad+=1
        print(J,p,exp[:12],'->',got,'' if ok else '  <<< MISMATCH')
print('mismatch',bad)
# components
fp0402=[];emptyfp=[]
for c in t.iter('comp'):
    fp=(c.findtext('footprint') or '')
    if '0402' in fp: fp0402.append(c.get('ref'))
    if not fp: emptyfp.append(c.get('ref'))
print('0402',fp0402); print('emptyFP',emptyfp)
print('ncomp',len(list(t.iter('comp'))))
for r in ['U33','U34','U35','RS4','R71','R216','R217','R218','R219','R42','R43','R44','R45','R46','R47']:
    print(r,[ (p,n) for (rr,p),n in sorted(pins.items()) if rr==r])
