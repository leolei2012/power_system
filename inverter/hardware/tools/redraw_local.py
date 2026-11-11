"""Use direct wires inside functional blocks and named connections between blocks."""
from redraw_common import *

def pinline(s,part,pin,point,mark=False):
    net=s.net(part.ref,pin);s.path(net,[part.pt(pin),point])
    if mark:s.mark(net,point)
def endpoint(s,part,pin,dx=10.16,dy=0):
    a=part.pt(pin);b=(round(a[0]+dx,4),round(a[1]+dy,4));s.line(s.net(part.ref,pin),a,b);s.label(s.net(part.ref,pin),b,180 if dx<0 else 0);return b

def mcu():
    s=Sheet('mcu');s.section('LOCAL STM32G431 / SUPPLY AND DECOUPLING',20.32,17.78)
    u=s.place('U30',142.24,144.78);u.field('Reference',142.24,30.48);u.field('Value',142.24,34.29)
    # Keep the MCU power-pin bus local; its bypass bank is a separate block.
    top=83.82
    vdd_x=[u.pt(pin)[0] for pin in ['1','16','32','48','64']]
    s.line('+3V3_INV',(min(vdd_x),top),(max(vdd_x),top));s.power('+3V3_INV',(min(vdd_x),top))
    for pin in ['1','16','32','48','64']:
        x,y=u.pt(pin);s.line('+3V3_INV',(x,y),(x,top));s.junction((x,top))
    s.text('MCU DECOUPLING / PLACE AT THE SUPPLY PINS',233.68,30.48,1.1,True)
    cap_top=45.72
    s.line('+3V3_INV',(238.76,cap_top),(365.76,cap_top));s.power('+3V3_INV',(238.76,cap_top))
    for ref_,x in zip(['C63','C64','C65','C66','C67','C68'],[238.76,264.16,289.56,314.96,340.36,365.76]):
        c=s.place(ref_,x,60.96)
        s.line('+3V3_INV',c.pt(1),(x,cap_top));s.junction((x,cap_top))
        s.line('GND',c.pt(2),(x,73.66));s.gnd((x,73.66))
    # Analog supply is separate from the digital VDD bus.
    p=u.pt(29);s.path('+3V3_A_MCU',[p,(p[0],83.82),(187.96,83.82)]);s.power('+3V3_A_MCU',(187.96,83.82))
    bottom=205.74
    for pin in ['15','31','47','63','27']:
        x,y=u.pt(pin);s.line('GND',(x,y),(x,bottom))
    s.line('GND',(142.24,bottom),(144.78,bottom));s.junction((142.24,bottom));s.gnd((142.24,bottom))
    powerpins={'1','16','32','48','64','29','15','31','47','63','27'}
    for pin,(x,y,pa) in u.pins.items():
        net=s.net('U30',pin)
        if pin in powerpins or net.startswith('unconnected-'):continue
        endpoint(s,u,pin,-12.7 if pa==0 else 12.7)
    s.text('Decoupling is shown as a separate functional block.\nPlace each 100 nF at its physical VDD or VBAT pin.\nVSSA and VSS return to shunt LOW / DC-.\nNo external VCAP on this package.\nVREF+ uses the external 3.3 V reference rail; VREFBUF OFF.',251.46,93.98,1.15)
    s.text('CROSS-SHEET SIGNALS\nPWM / ENABLE / BRAKE -> local command and gate pages\nADC inputs <- local RC filters\nABZ / SPI <- external sensor interface\nSWD / TTL / CAN / LEDs -> debug interface\nUse labels between blocks and direct wires within each block.',251.46,144.78,1.15)
    s.text('Keep outputs disabled during reset and initialization. BKIN is active-low; disable automatic restart.\nPB15 TIM1_CH3N uses AF4. Three currents share two ADCs: sampling windows still require validation.\nSeven unused GPIOs remain explicit NC. Preserve NRST, SWD and the intended BOOT/UCPD configuration.',20.32,243.84,1.1)
    s.save()

def analog():
    s=Sheet('mcu_analog');s.section('LOCAL ADC FILTERS / SOURCE -> SERIES R -> RC NODE -> MCU',20.32,17.78)
    signals=['I_U','I_V','I_W','V_DC','V_U','V_V','V_W','TEMP_NTC']
    for i,sig in enumerate(signals):
        x=27.94+(i%4)*96.52;y=63.5+(i//4)*68.58
        r=s.place('R'+str(84+i),x+25.4,y,90);c=s.place('C'+str(69+i),x+50.8,y+17.78)
        source=s.net(r.ref,1);dest=s.net(r.ref,2)
        s.line(source,(x,y),r.pt(1));s.label(source,(x,y),180)
        s.line(dest,r.pt(2),(x+76.2,y));s.line(dest,(x+50.8,y),c.pt(1));s.junction((x+50.8,y));s.label(dest,(x+76.2,y))
        s.line('GND',c.pt(2),(x+50.8,y+30.48));s.gnd((x+50.8,y+30.48))
        s.text(sig,x,y-22.86,1.2,True)
    s.section('VDDA AND VREF+ / EXTERNALLY SUPPLIED REFERENCE',20.32,190.5)
    r=s.place('R92',71.12,220.98,90);r2=s.place('R93',228.6,220.98,90)
    s.line('+3V3_INV',(35.56,220.98),r.pt(1));s.power('+3V3_INV',(35.56,220.98))
    s.line('+3V3_A_MCU',r.pt(2),r2.pt(1));s.power('+3V3_A_MCU',(152.4,220.98));s.junction((152.4,220.98))
    s.line('VREF_MCU',r2.pt(2),(360.68,220.98));s.power('VREF_MCU',(360.68,220.98))
    for ref_,x,net in [('C77',109.22,'+3V3_A_MCU'),('C78',177.8,'+3V3_A_MCU'),('C79',274.32,'VREF_MCU'),('C80',337.82,'VREF_MCU')]:
        c=s.place(ref_,x,241.3);s.line(net,c.pt(1),(x,220.98));s.junction((x,220.98));s.line('GND',c.pt(2),(x,254));s.gnd((x,254))
    s.text('Trip comparators remain upstream of the original 47R output isolators. New RC = 100R / 1nF.\nNTC also has 10k / 10nF upstream; select adequate acquisition time. VREFBUF stays OFF.\nThe 1.65 V amplifier bias is not the ADC reference.',20.32,271.78,1.02)
    s.save()

def control():
    s=Sheet('mcu_control');s.section('LOCAL COMMAND SERIES RESISTORS / PAGE-TO-PAGE SIGNALS',20.32,17.78)
    for i in range(8):
        x=73.66+(i%2)*187.96;y=48.26+(i//2)*25.4
        r=s.place('R'+str(135+i),x,y,90)
        endpoint(s,r,1,-25.4);endpoint(s,r,2,25.4)
        if i==6:
            t=s.place('TP17',x+20.32,y-12.7);net='ENABLE_IN'
            s.path(net,[t.pt(1),(x+20.32,y),r.pt(2)]);s.junction((x+20.32,y))
    s.section('FAULT INPUT / LOCAL PULL-UP AND TIMER BKIN',20.32,154.94)
    r=s.place('R143',73.66,180.34,180);t=s.place('TP16',111.76,185.42)
    s.line('+3V3_INV',r.pt(2),(73.66,167.64));s.power('+3V3_INV',(73.66,167.64))
    s.path('FAULT_N',[r.pt(1),(73.66,198.12),(165.1,198.12)]);s.label('FAULT_N',(165.1,198.12));s.path('FAULT_N',[t.pt(1),(111.76,198.12)]);s.junction((111.76,198.12))
    s.text('Q8 open collector -> pull-up -> PB12 / TIM1 BKIN.\nBridge protection remains independent of firmware.\nHold ENABLE low >=1 ms before deliberate re-enable.\nBRAKE remains independent of bridge ENABLE / fault.',215.9,172.72,1.1)
    s.section('HSE OPTION / CRYSTAL AND LOAD CAPACITORS DEFAULT DNP',20.32,220.98)
    y=s.place('Y1',137.16,248.92);ca=s.place('C83',86.36,266.7);cb=s.place('C84',190.5,266.7)
    s.path('HSE_IN',[(35.56,248.92),y.pt(1)]);s.label('HSE_IN',(35.56,248.92),180)
    s.path('HSE_OUT',[y.pt(3),(238.76,248.92)]);s.label('HSE_OUT',(238.76,248.92))
    for c,net in [(ca,'HSE_IN'),(cb,'HSE_OUT')]:
        s.line(net,c.pt(1),(c.x,248.92));s.junction((c.x,248.92));s.line('GND',c.pt(2),(c.x,278.13));s.gnd((c.x,278.13))
    s.line('GND',y.pt(2),(137.16,278.13));s.gnd((137.16,278.13))
    s.text('Y1 8 MHz and load C are candidates.\nSelect actual CL / ESR / drive and\nverify oscillator gain before fitting.\nInitial bring-up can use HSI16 / PLL.',269.24,236.22,1.0)
    s.save()

def debug():
    s=Sheet('debug_comms');s.section('SWD / OPEN-DRAIN RESET / BOOT',20.32,17.78,190.5)
    j=s.place('J13',35.56,55.88,mirror='y')
    # VTREF and ground are actual connector branches, not signal-label jumps.
    a=j.pt(1);s.path('+3V3_INV',[a,(48.26,a[1]),(48.26,35.56)]);s.power('+3V3_INV',(48.26,35.56))
    a=j.pt(4);s.line('GND',a,(a[0]+3.81,a[1]));s.power('GND',(a[0]+3.81,a[1]),90)
    for ref_,pin,y,fan,net in [('R120',2,45.72,66.04,'SWDIO'),('R121',3,68.58,60.96,'SWCLK')]:
        r=s.place(ref_,91.44,y,90);a=j.pt(pin)
        s.path(s.net(j.ref,pin),[a,(fan,a[1]),(fan,y),r.pt(1)]);s.mark(s.net(j.ref,pin),(fan,y))
        endpoint(s,r,2,25.4)
    sw=s.place('SW2',86.36,104.14);c=s.place('C81',139.7,116.84)
    a=j.pt(5);s.path('LOGIC_POWER_OK',[a,(55.88,a[1]),(55.88,91.44),(139.7,91.44),c.pt(1)])
    s.path('LOGIC_POWER_OK',[sw.pt(1),(71.12,104.14),(71.12,91.44)]);s.junction((71.12,91.44));s.mark('LOGIC_POWER_OK',(55.88,91.44))
    s.path('GND',[sw.pt(2),(111.76,104.14),(111.76,129.54),(139.7,129.54),c.pt(2)]);s.gnd((111.76,129.54))
    r=s.place('R122',187.96,111.76);t=s.place('TP15',187.96,86.36)
    s.line('BOOT0',t.pt(1),r.pt(1));s.mark('BOOT0',r.pt(1));s.line('GND',r.pt(2),(187.96,129.54));s.gnd((187.96,129.54))
    s.text('VTREF is sense only. NRST also enters the hardware health chain.\nOrdinary power-stage faults do not reset the MCU.',20.32,139.7,1.02)
    s.section('TTL UART / USART3 / 3.3 V',238.76,17.78,152.4)
    j=s.place('J14',375.92,55.88)
    tx=s.place('R123',297.18,45.72,90);rx=s.place('R124',297.18,71.12,270);rp=s.place('R125',264.16,50.8,180)
    endpoint(s,tx,1,-15.24)
    s.path('UART_TX_PORT',[tx.pt(2),(345.44,45.72),(345.44,j.pt(1)[1]),j.pt(1)]);s.mark('UART_TX_PORT',(345.44,45.72))
    s.path('UART_RX_PORT',[rx.pt(1),(340.36,71.12),(340.36,j.pt(2)[1]),j.pt(2)]);s.mark('UART_RX_PORT',(340.36,71.12))
    s.line('UART_RX',(248.92,71.12),rx.pt(2));s.label('UART_RX',(248.92,71.12),180)
    s.line('UART_RX',rp.pt(1),(264.16,71.12));s.junction((264.16,71.12));s.line('+3V3_INV',rp.pt(2),(264.16,35.56));s.power('+3V3_INV',(264.16,35.56))
    a=j.pt(3);s.path('GND',[a,(360.68,a[1]),(360.68,86.36)]);s.gnd((360.68,86.36))
    s.text('TX/RX relative to this board; no RS-232 levels.\nNo USB and no supply output on TTL connector.',238.76,104.14,1.02)
    s.section('OPTIONAL CLASSIC CAN / COMPLETE PHY BLOCK DNP',20.32,157.48)
    u=s.place('U31',162.56,198.12)
    rt=s.place('R126',93.98,182.88,90);rr=s.place('R127',93.98,210.82,270);rp=s.place('R128',127,173.99,180)
    endpoint(s,rt,1,-25.4);endpoint(s,rr,2,-25.4)
    s.path('CAN_TX_PHY',[rt.pt(2),(127,182.88),(127,u.pt(1)[1]),u.pt(1)])
    s.path('CAN_RX_PHY',[rr.pt(1),(119.38,210.82),(119.38,u.pt(4)[1]),u.pt(4)])
    s.line('CAN_TX_PHY',rp.pt(1),(127,182.88));s.junction((127,182.88));s.mark('CAN_TX_PHY',(127,182.88));s.mark('CAN_RX_PHY',(119.38,210.82))
    # Pull-up rail is below its section title but above signal wiring.
    s.power('+3V3_INV',rp.pt(2))
    c=s.place('C82',193.04,180.34)
    s.path('+3V3_INV',[u.pt(3),(162.56,167.64),(193.04,167.64),c.pt(1)]);s.power('+3V3_INV',(162.56,167.64))
    s.line('GND',c.pt(2),(193.04,187.96));s.gnd((193.04,187.96))
    s.line('GND',u.pt(2),(162.56,218.44));s.gnd((162.56,218.44))
    j=s.place('J15',365.76,203.2);term=s.place('R129',289.56,200.66)
    hy=187.96;ly=218.44
    s.path('CAN_H',[u.pt(7),(231.14,u.pt(7)[1]),(231.14,hy),(350.52,hy),(350.52,j.pt(1)[1]),j.pt(1)])
    s.path('CAN_L',[u.pt(6),(220.98,u.pt(6)[1]),(220.98,ly),(345.44,ly),(345.44,j.pt(2)[1]),j.pt(2)])
    s.line('CAN_H',term.pt(1),(289.56,hy));s.junction((289.56,hy));s.mark('CAN_H',(259.08,hy))
    s.line('CAN_L',term.pt(2),(289.56,ly));s.junction((289.56,ly));s.mark('CAN_L',(259.08,ly))
    a=j.pt(3);s.path('GND',[a,(355.6,a[1]),(355.6,228.6)]);s.gnd((355.6,228.6))
    s.section('FIVE INDICATORS / ONE POWER + FOUR GPIO, ACTIVE LOW',20.32,233.68)
    s.line('+3V3_INV',(25.4,246.38),(256.54,246.38));s.power('+3V3_INV',(25.4,246.38))
    for i in range(5):
        x=43.18+i*53.34;r=s.place('R'+str(130+i),x,254);d=s.place('D'+str(3+i),x,269.24,90)
        s.line('+3V3_INV',r.pt(1),(x,246.38));s.junction((x,246.38))
        net=s.net(r.ref,2);s.line(net,r.pt(2),d.pt(2));s.mark(net,(x,261.62))
        dest=s.net(d.ref,1);end=(x,279.4);s.line(dest,d.pt(1),end)
        if dest=='GND':s.gnd(end)
        else:s.label(dest,end)
        d.field('Reference',x+5.08,266.7);d.field('Value',x+5.08,269.24)
    s.save()

if __name__=='__main__':
    mcu();analog();control();debug()
