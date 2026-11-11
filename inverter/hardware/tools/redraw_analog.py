"""Redraw the three analog sheets without changing the snapshot electrical contract."""
from redraw_common import Sheet


def rail(s, net, xs, y):
    xs = sorted(set(xs))
    for a, b in zip(xs, xs[1:]):
        s.line(net, (a, y), (b, y))


def horizontal_fields(p):
    p.field('Reference', p.x, p.y-5.08, angle=90)
    p.field('Value', p.x, p.y-2.54, angle=90)


def supply_pair(s, u, supply_pin, ground_pin, c, top, bottom):
    """Show a device supply and its bypass as one local loop."""
    a, b = u.pt(supply_pin), u.pt(ground_pin)
    cp, cn = c.pt(1), c.pt(2)
    rail(s, '+3V3_INV', [a[0], cp[0]], top)
    s.line('+3V3_INV', a, (a[0], top))
    s.line('+3V3_INV', cp, (cp[0], top))
    s.power('+3V3_INV', (a[0], top))
    rail(s, 'GND', [b[0], cn[0]], bottom)
    s.line('GND', b, (b[0], bottom))
    s.line('GND', cn, (cn[0], bottom))
    s.gnd((cn[0], bottom))


def current_sheet():
    s = Sheet('current_sense')
    s.section('THREE LOW-SIDE KELVIN CURRENT CHANNELS', 20.32, 15.24)
    for k, x in enumerate([80.01, 205.74, 331.47]):
        phase = 'UVW'[k]
        u = s.place('U' + str(10+k), x, 76.2)
        u.field('Reference', x+17.78, 59.69)
        u.field('Value', x+17.78, 62.23)
        r = s.place('R' + str(37+k), x+29.21, 76.2, angle=90)
        horizontal_fields(r)
        c = s.place('C' + str(37+k), x-25.4, 45.72)
        tp = s.place('TP' + str(11+k), x+12.7, 91.44)
        tp.field('Reference', x+26.67, 91.44)
        tp.field('Value', x+26.67, 93.98)
        # Kelvin input, output series resistor and test point are actual wires.
        source = u.pt(8)
        s.path(phase+'_SOURCE', [(x-30.48, source[1]), source])
        s.label(phase+'_SOURCE', (x-30.48, source[1]), 180)
        n = 'I_'+phase
        s.line(n, u.pt(5), r.pt(1))
        s.line(n, (x+12.7, 76.2), tp.pt(1))
        s.junction((x+12.7, 76.2))
        s.mark(n, (x+12.7, 76.2))
        out = (x+46.99, 76.2)
        s.line(n+'_PORT', r.pt(2), out)
        s.label(n+'_PORT', out)
        # Supply bypass shares the supply conductor; ground input and return join.
        vp = u.pt(6)
        rail(s, '+3V3_INV', [vp[0], c.pt(1)[0]], 33.02)
        s.line('+3V3_INV', vp, (vp[0], 33.02))
        s.line('+3V3_INV', c.pt(1), (c.pt(1)[0], 33.02))
        s.power('+3V3_INV', (vp[0], 33.02))
        s.line('GND', c.pt(2), (c.pt(2)[0], 53.34))
        s.gnd((c.pt(2)[0], 53.34))
        minus, g = u.pt(1), u.pt(2)
        s.path('GND', [minus, (x-13.97, minus[1]), (x-13.97, 93.98), (g[0], 93.98), g])
        s.gnd((x-13.97, 93.98))
        for pin in [3, 7]:
            pt = u.pt(pin)
            s.line('VBIAS_1V65', pt, (pt[0], 101.6))
        s.line('VBIAS_1V65', (u.pt(3)[0], 101.6), (u.pt(7)[0], 101.6))
        s.label('VBIAS_1V65', (u.pt(3)[0], 101.6))
    s.text('Each channel uses the buffered VBIAS_1V65 generated below.', 55.88, 114.3)

    s.section('BUFFERED BIAS AND CURRENT WINDOW REFERENCES', 20.32, 137.16)
    rt = s.place('R40', 35.56, 172.72)
    rb = s.place('R41', 35.56, 205.74)
    cf = s.place('C40', 60.96, 205.74)
    ub = s.place('U13', 101.6, 193.04)
    ub.field('Reference', 113.03, 177.8)
    ub.field('Value', 113.03, 180.34)
    cb = s.place('C41', 127, 167.64)
    s.line('+3V3_INV', rt.pt(1), (35.56, 160.02))
    s.power('+3V3_INV', (35.56, 160.02))
    s.path('VBIAS_DIV', [rt.pt(2), (35.56, 190.5), (ub.pt(1)[0], 190.5), ub.pt(1)])
    s.line('VBIAS_DIV', (35.56, 190.5), rb.pt(1))
    s.line('VBIAS_DIV', (60.96, 190.5), cf.pt(1))
    s.junction((35.56, 190.5)); s.junction((60.96, 190.5))
    s.mark('VBIAS_DIV', (66.04, 190.5))
    for part in [rb, cf]:
        s.line('GND', part.pt(2), (part.pt(2)[0], 220.98))
    rail(s, 'GND', [35.56, 60.96], 220.98)
    s.line('GND', ub.pt(2), (ub.pt(2)[0], 208.28))
    s.gnd((ub.pt(2)[0], 208.28))
    s.gnd((35.56, 220.98))
    out = ub.pt(4)
    s.line('VBIAS_1V65', out, (144.78, out[1]))
    s.label('VBIAS_1V65', (144.78, out[1]))
    s.path('VBIAS_1V65', [out, (121.92, out[1]), (121.92, 215.9), (91.44, 215.9), (91.44, ub.pt(3)[1]), ub.pt(3)])
    s.junction((121.92, out[1]))
    rail(s, '+3V3_INV', [ub.pt(5)[0], cb.pt(1)[0]], 154.94)
    s.line('+3V3_INV', ub.pt(5), (ub.pt(5)[0], 154.94))
    s.line('+3V3_INV', cb.pt(1), (cb.pt(1)[0], 154.94))
    s.power('+3V3_INV', (ub.pt(5)[0], 154.94))
    s.line('GND', cb.pt(2), (cb.pt(2)[0], 175.26)); s.gnd((cb.pt(2)[0], 175.26))
    for x, rs, output, middle in [(223.52, [42,43,44], 'OC_LOW_REF', 'OC_LO_MID'), (314.96, [45,46,47], 'OC_HIGH_REF', 'OC_HI_MID')]:
        p = [s.place('R'+str(r), x, y) for r,y in zip(rs,[170.18,190.5,210.82])]
        s.line('+3V3_INV', p[0].pt(1), (x,154.94)); s.power('+3V3_INV',(x,154.94))
        a = middle if rs[0]==42 else output
        b = output if rs[0]==42 else middle
        s.line(a, p[0].pt(2), p[1].pt(1)); s.mark(a,(x,180.34))
        s.line(b, p[1].pt(2), p[2].pt(1)); s.mark(b,(x,200.66))
        s.line('GND', p[2].pt(2), (x,220.98)); s.gnd((x,220.98))

    # Keep the spare DFF and its physical supply unit on this original sheet.
    spare=s.place('U28',69.85,248.92,unit=2)
    spare.field('Reference',82.55,238.76); spare.field('Value',115.57,248.92)
    power=s.place('U28',139.7,248.92,unit=3)
    power.field('Reference',139.7,226.06); power.field('Value',139.7,228.6)
    cc=s.place('C62',165.1,248.92)
    rail(s,'+3V3_INV',[69.85,95.25,139.7,165.1],233.68)
    s.line('+3V3_INV',spare.pt(10),(69.85,233.68))
    s.path('+3V3_INV',[spare.pt(13),(95.25,spare.pt(13)[1]),(95.25,233.68)])
    s.line('+3V3_INV',power.pt(14),(139.7,233.68))
    s.line('+3V3_INV',cc.pt(1),(165.1,233.68));s.power('+3V3_INV',(165.1,233.68))
    for pin in [11,12]:
        s.path('GND',[spare.pt(pin),(49.53,spare.pt(pin)[1]),(49.53,264.16)])
    rail(s,'GND',[49.53,139.7,165.1],264.16)
    s.line('GND',power.pt(7),(139.7,264.16));s.line('GND',cc.pt(2),(165.1,264.16));s.gnd((165.1,264.16))
    s.text('SPARE U28B / FIXED INPUTS',20.32,226.06,1.0)
    s.text('I = 1.65 V + 50 mV/A; nominal current trips +/-20 A. Low-side shunts have switching-state blind intervals.\nReferences track the local 3.3 V rail; phase-current sign and sampling windows require bench validation.',20.32,279.4,1.0)
    s.save()


def voltage_sheet():
    s=Sheet('voltage_sense')
    s.section('FOUR 50:1 VOLTAGE CHANNELS / COMPLETE DIVIDER TO BUFFER',20.32,15.24)
    for k,x in enumerate([30.48,121.92,213.36,304.8]):
        phase=['DC','U','V','W'][k];root='V_'+phase
        rs=[s.place('R'+str(48+5*k+i),x,y) for i,y in enumerate([45.72,66.04,86.36,132.08])]
        filt=s.place('C'+str(42+2*k),x+12.7,132.08)
        u=s.place('U'+str(14+k),x+35.56,116.84)
        u.field('Reference',x+53.34,101.6);u.field('Value',x+53.34,104.14)
        out=s.place('R'+str(52+5*k),x+60.96,116.84,angle=90)
        horizontal_fields(out)
        bypass=s.place('C'+str(43+2*k),x+49.53,93.98)
        inp=s.net(rs[0].ref,1)
        s.line(inp,rs[0].pt(1),(x,30.48));s.label(inp,(x,30.48))
        for a,b,n,y in [(rs[0],rs[1],root+'_DIV1',55.88),(rs[1],rs[2],root+'_DIV2',76.2)]:
            s.line(n,a.pt(2),b.pt(1));s.mark(n,(x,y))
        div=root+'_DIV'
        s.path(div,[rs[2].pt(2),(x,114.3),u.pt(1)])
        s.line(div,(x,114.3),rs[3].pt(1));s.line(div,(x+12.7,114.3),filt.pt(1))
        s.junction((x,114.3));s.junction((x+12.7,114.3));s.mark(div,(x+17.78,114.3))
        for p in [rs[3],filt]:s.line('GND',p.pt(2),(p.pt(2)[0],142.24))
        rail(s,'GND',[x,x+12.7],142.24);s.gnd((x,142.24))
        s.line(root,u.pt(4),out.pt(1))
        s.path(root,[(x+50.8,116.84),(x+50.8,147.32),(x+25.4,147.32),(x+25.4,u.pt(3)[1]),u.pt(3)])
        s.junction((x+50.8,116.84));s.mark(root,(x+30.48,147.32))
        ep=(x+76.2,116.84);s.line(root+'_PORT',out.pt(2),ep);s.label(root+'_PORT',ep)
        rail(s,'+3V3_INV',[u.pt(5)[0],bypass.pt(1)[0]],86.36)
        s.line('+3V3_INV',u.pt(5),(u.pt(5)[0],86.36))
        s.line('+3V3_INV',bypass.pt(1),(bypass.pt(1)[0],86.36))
        s.power('+3V3_INV',(u.pt(5)[0],86.36))
        s.line('GND',u.pt(2),(u.pt(2)[0],132.08));s.gnd((u.pt(2)[0],132.08))
        s.line('GND',bypass.pt(2),(bypass.pt(2)[0],99.06));s.gnd((bypass.pt(2)[0],99.06))
    s.section('BUS OVERVOLTAGE REFERENCE / EXTERNAL NTC',20.32,170.18)
    top=s.place('R68',45.72,190.5);bottom=s.place('R69',45.72,218.44)
    s.line('+3V3_INV',top.pt(1),(45.72,180.34));s.power('+3V3_INV',(45.72,180.34))
    s.line('OV_REF_1V30',top.pt(2),bottom.pt(1))
    s.line('OV_REF_1V30',(45.72,205.74),(83.82,205.74));s.junction((45.72,205.74));s.label('OV_REF_1V30',(83.82,205.74))
    s.line('GND',bottom.pt(2),(45.72,231.14));s.gnd((45.72,231.14))
    s.text('20k / 13k gives 1.30 V\n65 V nominal bus trip at 50:1.',76.2,222.25,1.0)
    pull=s.place('R70',254,190.5);cap=s.place('C50',279.4,223.52);j=s.place('J8',330.2,208.28)
    j.field('Reference',340.36,201.93);j.field('Value',340.36,204.47)
    s.line('+3V3_INV',pull.pt(1),(254,180.34));s.power('+3V3_INV',(254,180.34))
    s.path('TEMP_NTC',[pull.pt(2),(254,208.28),j.pt(1)])
    s.line('TEMP_NTC',(279.4,208.28),cap.pt(1));s.junction((279.4,208.28));s.mark('TEMP_NTC',(287.02,208.28))
    s.path('GND',[j.pt(2),(314.96,j.pt(2)[1]),(314.96,236.22),(279.4,236.22),cap.pt(2)])
    s.gnd((279.4,236.22))
    s.text('Raw phase sense is measured before an external LC filter. Bus RC ~0.98 us; phase RC ~9.8 us.\nExternal NTC nominal 10k; beta, physical placement and cable protection remain to be selected.',20.32,259.08,1.0)
    s.save()


def comparator_sheet():
    s=Sheet('comparators')
    s.section('HARDWARE WINDOWS / EACH OUTPUT IS HEALTHY HIGH',20.32,15.24)
    for k,x in enumerate([80.01,205.74,331.47]):
        phase='UVW'[k];ref='U'+str(18+k)
        hi=s.place(ref,x,66.04,unit=1);lo=s.place(ref,x,101.6,unit=2)
        hi.field('Reference',x,50.8);hi.field('Value',x,53.34)
        lo.field('Reference',x,86.36);lo.field('Value',x,88.9)
        inp='I_'+phase;branch=x-35.56
        s.path(inp,[hi.pt(2),(branch,hi.pt(2)[1]),(branch,lo.pt(5)[1]),lo.pt(5)])
        s.line(inp,(branch,83.82),(branch-10.16,83.82));s.junction((branch,83.82));s.label(inp,(branch-10.16,83.82),180)
        hx=x-22.86;lx=x-22.86
        s.line('OC_HIGH_REF',hi.pt(3),(hx,hi.pt(3)[1]));s.label('OC_HIGH_REF',(hx,hi.pt(3)[1]),180)
        s.line('OC_LOW_REF',lo.pt(6),(lx,lo.pt(6)[1]));s.label('OC_LOW_REF',(lx,lo.pt(6)[1]),180)
        for u,pin,name in [(hi,1,'OC_'+phase+'_HIGH_OK'),(lo,7,'OC_'+phase+'_LOW_OK')]:
            end=(x+15.24,u.pt(pin)[1]);s.line(name,u.pt(pin),end);s.label(name,end)
        p=s.place(ref,x,152.4,unit=3)
        p.field('Reference',x+8.89,144.78);p.field('Value',x+11.43,147.32)
        c=s.place('C'+str(51+k),x+27.94,152.4)
        supply_pair(s,p,8,4,c,134.62,165.1)

    s.section('BUS OVERVOLTAGE / DRIVER RAIL UNDERVOLTAGE',20.32,175.26)
    ov=s.place('U21',100.33,220.98,unit=1);uv=s.place('U21',320.04,220.98,unit=2)
    ov.field('Reference',100.33,205.74);ov.field('Value',100.33,208.28)
    uv.field('Reference',320.04,205.74);uv.field('Value',320.04,208.28)
    s.line('OV_REF_1V30',ov.pt(3),(63.5,ov.pt(3)[1]));s.label('OV_REF_1V30',(63.5,ov.pt(3)[1]),180)
    s.line('OV_REF_1V30',uv.pt(6),(290.83,uv.pt(6)[1]));s.label('OV_REF_1V30',(290.83,uv.pt(6)[1]),180)
    vd=(63.5,ov.pt(2)[1]);s.line('V_DC',vd,ov.pt(2));s.label('V_DC',vd,180)
    for p,pin,n in [(ov,1,'BUS_OV_OK'),(uv,7,'DRV_UV_OK')]:
        end=(p.pt(pin)[0]+10.16,p.pt(pin)[1]);s.line(n,p.pt(pin),end);s.label(n,end)
    top=s.place('R71',259.08,207.01);bottom=s.place('R72',259.08,242.57)
    s.line('+12V_DRV',top.pt(1),(259.08,198.12));s.power('+12V_DRV',(259.08,198.12))
    node=(259.08,uv.pt(5)[1])
    s.path('DRV_UV_DIV',[top.pt(2),node,bottom.pt(1)])
    s.line('DRV_UV_DIV',node,uv.pt(5));s.junction(node);s.mark('DRV_UV_DIV',(266.7,node[1]))
    s.line('GND',bottom.pt(2),(259.08,254));s.gnd((259.08,254))
    p=s.place('U21',175.26,251.46,unit=3);p.field('Reference',188.0,240.03);p.field('Value',195.58,242.57)
    c=s.place('C54',210.82,251.46)
    supply_pair(s,p,8,4,c,233.68,266.7)
    s.text('Healthy = HIGH. Window violation, bus >~65 V or driver rail <~11.193 V drives its own output LOW.\nPush-pull outputs enter separate AND inputs. No wired-AND; no intentional hysteresis; first event is latched.',20.32,279.4,1.0)
    s.save()


if __name__ == '__main__':
    current_sheet()
    voltage_sheet()
    comparator_sheet()
