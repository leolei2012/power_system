"""Redraw the existing power circuits with visible same-sheet connections.
Electrical parts and pin-net contract are preserved from the pre-redraw snapshot.
"""
from redraw_common import *

def P(s,net,*pts):s.path(net,list(pts))
def H(s,net,a,b):s.line(net,a,b)
def wire_to(s,part,pin,target,via=()):P(s,s.net(part.ref,pin),part.pt(pin),*via,target)
def vbus(s,net,x1,x2,y,taps=(),power=False):
    H(s,net,(x1,y),(x2,y))
    for p,pin in taps:
        x,py=p.pt(pin);H(s,net,(x,py),(x,y));s.junction((x,y))
    if power:s.power(net,(x2,y))

def redraw_aux():
    s=Sheet('aux_input');s.section('AUXILIARY INPUT / eFUSE / 12-24 V',20.32,17.78)
    j=s.place('J2',35.56,60.96,mirror='y');f=s.place('F2',76.2,60.96,90)
    u=s.place('U1',210.82,111.76)
    c1=s.place('C1',96.52,86.36);c3=s.place('C3',350.52,134.62)
    r1=s.place('R1',134.62,86.36);r2=s.place('R2',134.62,147.32)
    r3=s.place('R3',165.1,86.36);r4=s.place('R4',165.1,147.32)
    r5=s.place('R5',185.42,154.94);r6=s.place('R6',269.24,154.94);c2=s.place('C2',309.88,154.94)
    r7=s.place('R7',309.88,86.36,180);r8=s.place('R8',111.76,121.92)
    sw=s.place('SW1',111.76,157.48)
    P(s,'AUX_IN',j.pt(1),f.pt(1))
    ground_y=198.12;rtn_y=177.8;input_y=60.96
    # A continuous input rail supplies the chip, UV/OV dividers and reset pullup.
    P(s,'AUX_FUSED',f.pt(2),(198.12,input_y),(198.12,u.pt(1)[1]),u.pt(1))
    for part,pin in [(c1,1),(r1,1),(r3,1),(r8,1)]:
        x,y=part.pt(pin);P(s,'AUX_FUSED',(x,input_y),(x,y));s.junction((x,input_y))
    # The two pin duplicates IN1/2 and OUT15/16 have the same physical position.
    P(s,'AUX_PROTECTED',u.pt(15),(350.52,u.pt(15)[1]),c3.pt(1));s.power('AUX_PROTECTED',(350.52,u.pt(15)[1]))
    P(s,'AUX_UV_DIV',r1.pt(2),r2.pt(1));uv_y=u.pt(3)[1]
    P(s,'AUX_UV_DIV',(134.62,uv_y),u.pt(3));s.junction((134.62,uv_y));s.mark('AUX_UV_DIV',(134.62,uv_y))
    P(s,'AUX_OV_DIV',r3.pt(2),r4.pt(1));ov_y=u.pt(5)[1]
    P(s,'AUX_OV_DIV',(165.1,ov_y),u.pt(5));s.junction((165.1,ov_y));s.mark('AUX_OV_DIV',(165.1,ov_y))
    P(s,'AUX_MODE',u.pt(6),(185.42,u.pt(6)[1]),r5.pt(1))
    P(s,'AUX_ILIM',u.pt(11),(269.24,u.pt(11)[1]),r6.pt(1))
    P(s,'AUX_DVDT',u.pt(12),(309.88,u.pt(12)[1]),c2.pt(1))
    P(s,'AUX_FLT_N',u.pt(14),(309.88,u.pt(14)[1]),r7.pt(1))
    s.label('AUX_FLT_N',(309.88,u.pt(14)[1]));s.junction((309.88,u.pt(14)[1]))
    P(s,'+3V3_INV',r7.pt(2),(309.88,66.04));s.power('+3V3_INV',(309.88,66.04))
    # SHDN is independent of the MCU. Its button returns to RTN, not board GND.
    P(s,'AUX_SHDN_N',r8.pt(2),(111.76,132.08),(190.5,132.08),(190.5,u.pt(7)[1]),u.pt(7))
    P(s,'AUX_SHDN_N',(111.76,132.08),(106.68,132.08),sw.pt(1));s.junction((111.76,132.08))
    H(s,'EFUSE_RTN',(119.38,rtn_y),(309.88,rtn_y))
    for p,pin in [(r2,2),(r4,2),(r5,2),(r6,2),(c2,2),(u,8)]:
        x,y=p.pt(pin);P(s,'EFUSE_RTN',(x,y),(x,rtn_y));s.junction((x,rtn_y))
    P(s,'EFUSE_RTN',sw.pt(2),(119.38,157.48),(119.38,rtn_y));s.mark('EFUSE_RTN',(119.38,rtn_y))
    # Board GND and eFuse RTN remain visibly separate buses.
    H(s,'GND',(50.8,ground_y),(350.52,ground_y))
    P(s,'GND',j.pt(2),(50.8,j.pt(2)[1]),(50.8,ground_y))
    for p,pin in [(c1,2),(c3,2),(u,9)]:
        x,y=p.pt(pin);P(s,'GND',(x,y),(x,ground_y));s.junction((x,ground_y))
    s.gnd((350.52,ground_y))
    s.text('RTN / exposed pad is the eFuse reference island. It is NOT the board GND pin.\nMODE=402k selects latch-off. AUX_RESET resets the auxiliary path; no MCU startup dependency.\nUV / OV / current-limit values remain unchanged; dynamics and surge coordination still require review.',20.32,223.52,1.08)
    s.save()

def redraw_12v():
    s=Sheet('supply_12v');s.section('12 V DRIVER RAIL / TPS55165 BUCK-BOOST',20.32,17.78)
    u=s.place('U2',190.5,111.76)
    l=s.place('L1',190.5,55.88,90)
    c4=s.place('C4',154.94,86.36);c5=s.place('C5',231.14,96.52)
    c6=s.place('C6',60.96,111.76);c7=s.place('C7',88.9,111.76)
    c8=s.place('C8',309.88,170.18);c9=s.place('C9',345.44,170.18)
    c10=s.place('C10',264.16,190.5);r9=s.place('R9',144.78,162.56)
    r10=s.place('R10',299.72,121.92);r11=s.place('R11',299.72,190.5);r12=s.place('R12',299.72,215.9)
    t1=s.place('TP1',370.84,162.56);t2=s.place('TP2',264.16,213.36);t3=s.place('TP3',340.36,203.2)
    # Inductor and both bootstrap capacitors form the visible switching cell.
    P(s,'BB_L1',u.pt(2),(139.7,u.pt(2)[1]),(139.7,55.88),l.pt(1))
    P(s,'BB_L2',l.pt(2),(251.46,55.88),(251.46,u.pt(20)[1]),u.pt(20))
    P(s,'BB_BST1',u.pt(3),(160.02,u.pt(3)[1]),(160.02,76.2),(154.94,76.2),c4.pt(1))
    P(s,'BB_L1',c4.pt(2),(139.7,c4.pt(2)[1]));s.junction((139.7,c4.pt(2)[1]))
    P(s,'BB_BST2',u.pt(19),(220.98,u.pt(19)[1]),(220.98,86.36),(231.14,86.36),c5.pt(1))
    P(s,'BB_L2',c5.pt(2),(251.46,c5.pt(2)[1]));s.junction((251.46,c5.pt(2)[1]))
    # Input bypass and the three fixed-input control pins.
    input_y=86.36;gy=236.22
    H(s,'AUX_PROTECTED',(40.64,input_y),(121.92,input_y));s.power('AUX_PROTECTED',(40.64,input_y))
    for c in [c6,c7]:P(s,'AUX_PROTECTED',(c.x,input_y),c.pt(1));s.junction((c.x,input_y))
    for pin in [4,5,6]:
        x,y=u.pt(pin);P(s,'AUX_PROTECTED',(x,y),(149.86,y));s.junction((149.86,y))
    P(s,'AUX_PROTECTED',(149.86,u.pt(4)[1]),(149.86,u.pt(6)[1]))
    P(s,'AUX_PROTECTED',(121.92,input_y),(121.92,u.pt(4)[1]),(149.86,u.pt(4)[1]))
    # All grounds share a bottom return; VREG is a separate, closed feedback loop.
    H(s,'GND',(60.96,gy),(370.84,gy));s.gnd((370.84,gy))
    for c in [c6,c7,c8,c9,c10]:P(s,'GND',c.pt(2),(c.x,gy));s.junction((c.x,gy))
    P(s,'GND',u.pt(1),(129.54,u.pt(1)[1]),(129.54,gy));s.junction((129.54,gy))
    for pin in [7,8,9]:P(s,'GND',u.pt(pin),(165.1,u.pt(pin)[1]));s.junction((165.1,u.pt(pin)[1]))
    P(s,'GND',(165.1,u.pt(7)[1]),(165.1,gy));s.junction((165.1,gy))
    for pin,x in [(13,355.6),(18,360.68),(21,365.76)]:P(s,'GND',u.pt(pin),(x,u.pt(pin)[1]),(x,gy));s.junction((x,gy))
    P(s,'BB_PG_DLY',u.pt(10),(144.78,u.pt(10)[1]),r9.pt(1));P(s,'GND',r9.pt(2),(144.78,gy));s.junction((144.78,gy))
    P(s,'BB_VREG',u.pt(12),(226.06,u.pt(12)[1]),(226.06,190.5),(154.94,190.5),(154.94,u.pt(11)[1]),u.pt(11))
    P(s,'BB_VREG',u.pt(14),(226.06,u.pt(14)[1]));s.junction((226.06,u.pt(14)[1]))
    P(s,'BB_VREG',(226.06,177.8),(264.16,177.8),c10.pt(1));s.junction((226.06,177.8))
    P(s,'BB_VREG',(226.06,190.5),(226.06,213.36),t2.pt(1));s.junction((226.06,190.5));s.mark('BB_VREG',(226.06,177.8))
    # Output rail and sense pin tie explicitly to the output capacitors.
    oy=142.24
    P(s,'+12V_DRV',u.pt(16),(213.36,u.pt(16)[1]),(213.36,oy),(370.84,oy))
    P(s,'+12V_DRV',u.pt(17),(215.9,u.pt(17)[1]),(215.9,oy));s.junction((215.9,oy))
    for c in [c8,c9]:P(s,'+12V_DRV',(c.x,oy),c.pt(1));s.junction((c.x,oy))
    P(s,'+12V_DRV',(370.84,oy),t1.pt(1));s.power('+12V_DRV',(370.84,oy))
    # PG level conversion is a separate module; names bridge the module boundary.
    P(s,'DRV_PG_NOM',u.pt(15),(218.44,u.pt(15)[1]),(218.44,137.16));s.label('DRV_PG_NOM',(218.44,137.16),180)
    P(s,'DRV_PG_NOM',(279.4,172.72),(299.72,172.72),r11.pt(1));s.label('DRV_PG_NOM',(279.4,172.72),180)
    P(s,'DRV_PG_NOM',r10.pt(2),(299.72,172.72));s.junction((299.72,172.72))
    P(s,'+5V_INV',r10.pt(1),(299.72,101.6));s.power('+5V_INV',(299.72,101.6))
    P(s,'DRV_PG_LOGIC',r11.pt(2),r12.pt(1));P(s,'DRV_PG_LOGIC',(299.72,203.2),t3.pt(1));s.junction((299.72,203.2));s.label('DRV_PG_LOGIC',t3.pt(1))
    P(s,'GND',r12.pt(2),(299.72,gy));s.junction((299.72,gy))
    s.text('VREG_Q and VOS_FB return to VREG; VREG is not a load rail. VOUT_SENSE is tied to the 12 V output.\nInput/output/bootstrap wiring is shown directly. PG high is about 2.5 V with the fitted pullup/divider.\nInductor model, startup, worst-case gate voltage and thermal capability remain review items.',20.32,254,1.05)
    s.save()

def redraw_logic():
    s=Sheet('supply_logic');s.section('5 V BUCK / AP63205',20.32,17.78,190.5);s.section('3.3 V MCU / ANALOG SUPPLY',238.76,17.78,152.4)
    u3=s.place('U3',101.6,71.12);c11=s.place('C11',55.88,81.28);c12=s.place('C12',139.7,55.88,90);l2=s.place('L2',154.94,68.58,90)
    c13=s.place('C13',185.42,91.44);c14=s.place('C14',215.9,91.44)
    gy=111.76;iy=u3.pt(3)[1]
    P(s,'AUX_PROTECTED',(40.64,iy),u3.pt(3));s.power('AUX_PROTECTED',(40.64,iy))
    P(s,'AUX_PROTECTED',u3.pt(2),(81.28,u3.pt(2)[1]),(81.28,iy));s.junction((81.28,iy))
    P(s,'AUX_PROTECTED',(55.88,iy),c11.pt(1));s.junction((55.88,iy))
    P(s,'BUCK_SW',u3.pt(5),l2.pt(1));P(s,'BUCK_SW',c12.pt(2),(151.13,c12.pt(2)[1]),(151.13,iy));s.junction((151.13,iy))
    P(s,'BUCK_BST',u3.pt(6),(124.46,u3.pt(6)[1]),(124.46,55.88),c12.pt(1))
    P(s,'+5V_INV',l2.pt(2),(215.9,iy));s.power('+5V_INV',(215.9,iy))
    P(s,'+5V_INV',u3.pt(1),(185.42,u3.pt(1)[1]),(185.42,iy));s.junction((185.42,iy))
    for c in [c13,c14]:P(s,'+5V_INV',(c.x,iy),c.pt(1));s.junction((c.x,iy))
    H(s,'GND',(55.88,gy),(215.9,gy));s.gnd((215.9,gy))
    for p,pin in [(u3,4),(c11,2),(c13,2),(c14,2)]:P(s,'GND',p.pt(pin),(p.pt(pin)[0],gy));s.junction((p.pt(pin)[0],gy))
    u4=s.place('U4',279.4,71.12);c15=s.place('C15',243.84,81.28);c16=s.place('C16',335.28,81.28)
    iy=u4.pt(1)[1];gy=106.68
    P(s,'+5V_INV',(243.84,iy),u4.pt(1));s.power('+5V_INV',(243.84,iy))
    P(s,'+5V_INV',u4.pt(3),(264.16,u4.pt(3)[1]),(264.16,iy));s.junction((264.16,iy))
    P(s,'+5V_INV',(243.84,iy),c15.pt(1))
    P(s,'+3V3_INV',u4.pt(5),(335.28,iy),c16.pt(1));s.power('+3V3_INV',(335.28,iy))
    H(s,'GND',(243.84,gy),(335.28,gy));s.gnd((335.28,gy))
    for p,pin in [(u4,2),(c15,2),(c16,2)]:P(s,'GND',p.pt(pin),(p.pt(pin)[0],gy));s.junction((p.pt(pin)[0],gy))
    s.section('3.3 V SUPERVISOR / LOCAL MCU RESET',238.76,121.92,152.4)
    u6=s.place('U6',279.4,157.48);c17=s.place('C17',243.84,162.56);r13=s.place('R13',325.12,147.32,180)
    vy=142.24;gy=182.88
    H(s,'+3V3_INV',(243.84,vy),(325.12,vy));s.power('+3V3_INV',(243.84,vy))
    P(s,'+3V3_INV',u6.pt(6),(279.4,vy));s.junction((279.4,vy))
    for pin,x in [(3,259.08),(5,264.16)]:P(s,'+3V3_INV',u6.pt(pin),(x,u6.pt(pin)[1]),(x,vy));s.junction((x,vy))
    P(s,'+3V3_INV',(243.84,vy),c17.pt(1));P(s,'+3V3_INV',(325.12,vy),r13.pt(2))
    P(s,'LOGIC_POWER_OK',u6.pt(1),(365.76,157.48));P(s,'LOGIC_POWER_OK',r13.pt(1),(325.12,157.48));s.junction((325.12,157.48));s.label('LOGIC_POWER_OK',(365.76,157.48))
    H(s,'GND',(243.84,gy),(279.4,gy));s.gnd((279.4,gy))
    for p,pin in [(u6,2),(c17,2)]:P(s,'GND',p.pt(pin),(p.pt(pin)[0],gy));s.junction((p.pt(pin)[0],gy))
    s.section('PROTECTED OPTIONAL SENSOR POWER / TOTAL TARGET 0.5 A',20.32,132.08,190.5)
    u5=s.place('U5',111.76,218.44);r14=s.place('R14',172.72,238.76);r15=s.place('R15',205.74,185.42,180)
    c18=s.place('C18',251.46,238.76);j7=s.place('J7',307.34,220.98);tp=s.place('TP4',205.74,210.82)
    gy=256.54
    P(s,'+5V_INV',(50.8,u5.pt(1)[1]),u5.pt(1));s.power('+5V_INV',(50.8,u5.pt(1)[1]))
    P(s,'+5V_INV',u5.pt(3),(81.28,u5.pt(3)[1]),(81.28,u5.pt(1)[1]));s.junction((81.28,u5.pt(1)[1]))
    P(s,'GND',u5.pt(2),(88.9,u5.pt(2)[1]),(88.9,gy))
    P(s,'SENSOR_ILIM',u5.pt(5),(172.72,u5.pt(5)[1]),r14.pt(1))
    P(s,'SENSOR_PWR_FLT_N',u5.pt(4),(205.74,u5.pt(4)[1]),r15.pt(1));P(s,'SENSOR_PWR_FLT_N',tp.pt(1),(205.74,u5.pt(4)[1]));s.junction((205.74,u5.pt(4)[1]));s.mark('SENSOR_PWR_FLT_N',(205.74,u5.pt(4)[1]))
    P(s,'+3V3_INV',r15.pt(2),(205.74,170.18));s.power('+3V3_INV',(205.74,170.18))
    P(s,'+5V_SENSOR',u5.pt(6),j7.pt(1));P(s,'+5V_SENSOR',(251.46,u5.pt(6)[1]),c18.pt(1));s.junction((251.46,u5.pt(6)[1]));s.power('+5V_SENSOR',j7.pt(1))
    P(s,'GND',j7.pt(2),(284.48,j7.pt(2)[1]),(284.48,gy));H(s,'GND',(88.9,gy),(284.48,gy));s.gnd((284.48,gy))
    for p,pin in [(r14,2),(c18,2)]:P(s,'GND',p.pt(pin),(p.pt(pin)[0],gy));s.junction((p.pt(pin)[0],gy))
    s.text('J7 / external power links default DNP. The branch current target is total, not per connector.\nThe 3.3 V LDO is shared by MCU, analog, logic and optional CAN; budget and temperature still require verification.',20.32,274.32,.98)
    s.save()

def redraw_bus():
    s=Sheet('bus_brake');s.section('MAIN BUS INPUT / BULK CAPACITORS / RAW PWM OUTPUTS',20.32,17.78)
    j3=s.place('J3',35.56,55.88,mirror='y');f=s.place('F1',76.2,55.88,90);d1=s.place('D1',132.08,55.88,180)
    caps=[s.place('C19',185.42,86.36),s.place('C20',231.14,86.36),s.place('C21',276.86,86.36),s.place('C22',322.58,86.36)]
    d2=s.place('D2',365.76,86.36,270);j4=s.place('J4',365.76,147.32)
    gy=116.84;vy=55.88
    P(s,'DC_INPUT_POS',j3.pt(1),f.pt(1))
    P(s,'DC_FUSED',f.pt(2),(116.84,vy),d1.pt(3));P(s,'DC_FUSED',d1.pt(1),(116.84,d1.pt(1)[1]),(116.84,vy));s.junction((116.84,vy))
    P(s,'VBUS',d1.pt(2),(157.48,vy),(391.16,vy));s.power('VBUS',(391.16,vy));s.flag('VBUS',(157.48,vy));s.junction((157.48,vy))
    for c in caps+[d2]:P(s,'VBUS',(c.x,vy),c.pt(1));s.junction((c.x,vy))
    H(s,'GND',(45.72,gy),(365.76,gy));s.gnd((365.76,gy))
    P(s,'GND',j3.pt(2),(45.72,j3.pt(2)[1]),(45.72,gy))
    for c in caps+[d2]:P(s,'GND',c.pt(2),(c.x,gy));s.junction((c.x,gy))
    for pin in [1,2,3]:j4.stub(pin,20.32)
    s.text('D2 is DNP. The input diode / TVS / fuse are still procurement and energy/thermal review items.\nNo main-bus precharge or dedicated bleeder. U/V/W are raw bridge PWM, not LC-filtered sine outputs.',20.32,134.62,1.05)
    s.section('ONE BRAKE BRANCH / EXTERNAL RESISTOR / LOCAL MCU COMMAND',20.32,172.72)
    u=s.place('U29',116.84,218.44);r16=s.place('R16',60.96,241.3);r17=s.place('R17',177.8,218.44,90)
    r18=s.place('R18',226.06,241.3);q=s.place('Q7',251.46,218.44);c23=s.place('C23',66.04,205.74);c24=s.place('C24',88.9,205.74)
    j5=s.place('J5',325.12,198.12)
    gy=261.62;dy=195.58
    H(s,'+12V_DRV',(66.04,dy),(116.84,dy));s.power('+12V_DRV',(66.04,dy))
    for c in [c23,c24]:P(s,'+12V_DRV',(c.x,dy),c.pt(1));s.junction((c.x,dy))
    P(s,'+12V_DRV',u.pt(1),(116.84,dy))
    P(s,'BRAKE_IN',(35.56,u.pt(3)[1]),u.pt(3));s.label('BRAKE_IN',(35.56,u.pt(3)[1]),180)
    P(s,'BRAKE_IN',(60.96,u.pt(3)[1]),r16.pt(1));s.junction((60.96,u.pt(3)[1]))
    P(s,'BR_DRV',u.pt(5),r17.pt(1));P(s,'BR_GATE',r17.pt(2),q.pt(1))
    P(s,'BR_GATE',(226.06,218.44),r18.pt(1));s.junction((226.06,218.44))
    # The resistor connector is visibly in series with the brake MOS drain.
    # Main input and brake are separate functional modules. VBUS joins them by name.
    P(s,'VBUS',(307.34,187.96),(307.34,j5.pt(1)[1]),j5.pt(1));s.power('VBUS',(307.34,187.96))
    P(s,'BR_SW',j5.pt(2),(292.1,j5.pt(2)[1]),(292.1,205.74),(254,205.74),q.pt(2));s.mark('BR_SW',(292.1,205.74))
    H(s,'GND',(60.96,gy),(254,gy));s.gnd((254,gy))
    for p,pin in [(r16,2),(r18,2),(q,3),(c23,2),(c24,2),(u,2)]:P(s,'GND',p.pt(pin),(p.pt(pin)[0],gy));s.junction((p.pt(pin)[0],gy))
    P(s,'GND',u.pt(4),(101.6,u.pt(4)[1]),(101.6,gy));s.junction((101.6,gy))
    s.text('J5: BR+ = VBUS, BR_SW = MOS drain. External resistor goes across these pins; unused port stays OPEN.\nBrake is independent of the bridge ENABLE/fault gates. MCU reset defaults the command low.',20.32,276.86,.98)
    s.save()

def redraw_bridge(ph,index):
    s=Sheet('bridge_'+ph.lower());s.section(f'{ph} HALF BRIDGE / VISIBLE GATE, BOOTSTRAP AND SHUNT RETURNS',20.32,17.78)
    qh=s.place('Q'+str(index*2+1),261.62,91.44);ql=s.place('Q'+str(index*2+2),261.62,182.88)
    u=s.place('U'+str(index+7),111.76,137.16)
    start=19+index*6;cs=25+index*4
    rh=s.place('R'+str(start),210.82,91.44,90);rl=s.place('R'+str(start+1),210.82,182.88,90)
    rgh=s.place('R'+str(start+2),236.22,111.76);rgl=s.place('R'+str(start+3),236.22,195.58)
    ri1=s.place('R'+str(start+4),40.64,157.48);ri2=s.place('R'+str(start+5),66.04,167.64)
    cb1=s.place('C'+str(cs),185.42,116.84);cb2=s.place('C'+str(cs+1),210.82,116.84)
    cd1=s.place('C'+str(cs+2),322.58,88.9);cd2=s.place('C'+str(cs+3),353.06,88.9)
    rs=s.place('RS'+str(index+1),264.16,231.14)
    tp1=s.place('TP'+str(5+index*2),307.34,132.08);tp2=s.place('TP'+str(6+index*2),307.34,205.74)
    vb='VBUS';src=ph+'_SOURCE';phase=ph+'_PHASE';boot=ph+'_BOOT'
    H(s,vb,(264.16,45.72),(307.34,45.72));P(s,vb,(264.16,45.72),qh.pt(2));s.power(vb,(307.34,45.72))
    # Main half-bridge and shunt are one continuous vertical power path.
    P(s,phase,qh.pt(3),ql.pt(2));P(s,phase,(264.16,132.08),tp1.pt(1));s.junction((264.16,132.08));s.label(phase,tp1.pt(1))
    sy=205.74;gy=259.08
    P(s,src,ql.pt(3),rs.pt(1));H(s,src,(40.64,sy),(353.06,sy));s.junction((264.16,sy))
    P(s,'GND',rs.pt(2),(264.16,gy));s.gnd((264.16,gy));s.label(src,(353.06,sy))
    # High and low gates are wired to their respective source return, never GND.
    P(s,ph+'_HO',u.pt(7),(154.94,u.pt(7)[1]),(154.94,91.44),rh.pt(1))
    P(s,ph+'_GATE_H',rh.pt(2),qh.pt(1));P(s,ph+'_GATE_H',(236.22,91.44),rgh.pt(1));s.junction((236.22,91.44))
    P(s,phase,rgh.pt(2),(236.22,127),(264.16,127));s.junction((264.16,127))
    P(s,ph+'_LO',u.pt(4),(86.36,u.pt(4)[1]),(86.36,182.88),rl.pt(1))
    P(s,ph+'_GATE_L',rl.pt(2),ql.pt(1));P(s,ph+'_GATE_L',(236.22,182.88),rgl.pt(1));s.junction((236.22,182.88))
    P(s,src,rgl.pt(2),(236.22,sy));s.junction((236.22,sy))
    # Bootstrap is an explicit capacitor pair between VB and the phase node.
    P(s,boot,u.pt(8),(147.32,u.pt(8)[1]),(147.32,106.68),(210.82,106.68))
    for c in [cb1,cb2]:P(s,boot,(c.x,106.68),c.pt(1));s.junction((c.x,106.68))
    H(s,phase,(185.42,127),(264.16,127))
    for c in [cb1,cb2]:P(s,phase,c.pt(2),(c.x,127));s.junction((c.x,127))
    P(s,phase,u.pt(6),(142.24,u.pt(6)[1]),(142.24,132.08),(264.16,132.08));s.junction((264.16,132.08))
    # Local VCC decouplers return to SOURCE above the shunt, including COM.
    vy=66.04;H(s,'+12V_DRV',(137.16,vy),(353.06,vy));s.power('+12V_DRV',(353.06,vy))
    P(s,'+12V_DRV',u.pt(5),(137.16,u.pt(5)[1]),(137.16,vy))
    for c in [cd1,cd2]:
        P(s,'+12V_DRV',(c.x,vy),c.pt(1));s.junction((c.x,vy))
        P(s,src,c.pt(2),(c.x,sy));s.junction((c.x,sy))
    P(s,src,u.pt(3),(81.28,u.pt(3)[1]),(81.28,sy));s.junction((81.28,sy))
    for pin,r,x in [(1,ri1,40.64),(2,ri2,66.04)]:
        sig=ph+('_HIN' if pin==1 else '_LIN');P(s,sig,(x,u.pt(pin)[1]),u.pt(pin));s.label(sig,(x,u.pt(pin)[1]),180)
        P(s,sig,(x,u.pt(pin)[1]),r.pt(1));s.junction((x,u.pt(pin)[1]))
        P(s,src,r.pt(2),(x,sy));s.junction((x,sy))
    # Testpoint 2 is physically on the source rail.
    s.junction(tp2.pt(1))
    s.text('COM, low-gate pulldown, local VCC capacitors and sense high all return to SOURCE above the shunt.\nHigh-gate pulldown and bootstrap capacitors return to PHASE. Common GND/DC- exists only below RS.\nGate R / bootstrap values remain initial values; deadtime, minimum recharge time and waveforms require validation.',20.32,271.78,1.0)
    s.save()

if __name__=='__main__':
    redraw_aux();redraw_12v();redraw_logic();redraw_bus()
    for i,ph in enumerate('UVW'):redraw_bridge(ph,i)
