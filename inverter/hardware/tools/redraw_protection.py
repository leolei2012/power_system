"""Redraw protection / PWM-gating pages without changing their electrical contract."""
from redraw_common import Sheet


def connect(s, net, *points):
    s.path(net, list(points))


def fault_logic():
    s = Sheet('fault_logic')
    s.section('HARDWARE HEALTH CHAIN / EVERY INPUT MUST REMAIN HIGH', 20.32, 17.78)

    # Two left-to-right rows.  The single, visibly wired return between rows
    # makes the aggregation order traceable without repeated internal labels.
    stages = [
        ('U22', 1, 1, 2, 3), ('U22', 2, 4, 5, 6),
        ('U22', 3, 9, 10, 8), ('U22', 4, 12, 13, 11),
        ('U23', 1, 1, 2, 3), ('U23', 2, 4, 5, 6),
        ('U23', 3, 9, 10, 8), ('U23', 4, 12, 13, 11),
        ('U24', 1, 1, 2, 3), ('U24', 2, 4, 5, 6),
    ]
    gates = []
    for i, (ref, unit, pa, pb, po) in enumerate(stages):
        x = 76.2 + (i % 5) * 66.04
        y = 43.18 if i < 5 else 93.98
        gate = s.place(ref, x, y, unit=unit)
        gates.append(gate)
        # Each independently generated health signal enters its own gate.
        net = s.net(ref, pb)
        anchor = (x-17.78, y+17.78)
        connect(s, net, gate.pt(pb), (anchor[0], gate.pt(pb)[1]), anchor)
        s.label(net, anchor, 180)
        if i == 0:
            net = s.net(ref, pa)
            anchor = (50.8, gate.pt(pa)[1])
            connect(s, net, anchor, gate.pt(pa))
            s.label(net, anchor, 180)
        elif i == 5:
            prev = gates[i-1]
            net = s.net(ref, pa)
            connect(s, net, prev.pt(stages[i-1][4]), (388.62, 43.18),
                    (388.62, 76.2), (25.4, 76.2),
                    (25.4, gate.pt(pa)[1]), gate.pt(pa))
            s.mark(net, (134.62, 76.2))
        else:
            prev = gates[i-1]
            net = s.net(ref, pa)
            bend_x = prev.pt(stages[i-1][4])[0] + 20.32
            connect(s, net, prev.pt(stages[i-1][4]),
                    (bend_x, prev.y), (bend_x, gate.pt(pa)[1]), gate.pt(pa))
            s.mark(net, (bend_x+2.54, gate.pt(pa)[1]))

    # The aggregation chain is one block.  Its result enters the separate
    # reset/memory and permission/output blocks through page-local labels.
    all_out = gates[-1].pt(6)
    connect(s, 'HEALTH_ALL', all_out, (375.92, all_out[1]))
    s.label('HEALTH_ALL', (375.92, all_out[1]), global_=False)

    s.section('FAULT MEMORY / DELIBERATE DISABLE-TO-RESET / PERMISSION', 20.32, 134.62)
    inv = s.place('U27', 60.96, 165.1, unit=1)
    reset = s.place('U24', 121.92, 165.1, unit=3)
    r73 = s.place('R73', 167.64, 165.1, angle=90)
    c55 = s.place('C55', 198.12, 189.23)
    latch = s.place('U28', 236.22, 165.1, unit=1)
    latch.field('Reference', 231.14, 144.78)
    latch.field('Value', 231.14, 147.32)
    tp = s.place('TP14', 269.24, 153.67)
    permit_health = s.place('U24', 304.8, 185.42, unit=4)
    permit = s.place('U25', 360.68, 185.42, unit=1)
    fault = s.place('U27', 304.8, 220.98, unit=2)
    r74 = s.place('R74', 335.28, 220.98, angle=90)
    q8 = s.place('Q8', 365.76, 220.98)
    r75 = s.place('R75', 350.52, 234.95)

    # Tied NAND inputs remain visibly connected inside the reset block.
    connect(s, 'ENABLE_IN', (25.4, 165.1), (48.26, 165.1))
    s.label('ENABLE_IN', (25.4, 165.1), 180)
    connect(s, 'ENABLE_IN', inv.pt(1), (48.26, inv.pt(1)[1]),
            (48.26, inv.pt(2)[1]), inv.pt(2))
    s.junction((48.26, 165.1))
    connect(s, 'ENABLE_IN', (345.44, 198.12),
            (345.44, permit.pt(2)[1]), permit.pt(2))
    s.label('ENABLE_IN', (345.44, 198.12))
    connect(s, 'ENABLE_N', inv.pt(3), (95.25, 165.1),
            (95.25, reset.pt(10)[1]), reset.pt(10))
    s.mark('ENABLE_N', (73.66, 165.1))
    connect(s, 'HEALTH_ALL', (106.68, 148.59),
            (106.68, reset.pt(9)[1]), reset.pt(9))
    connect(s, 'HEALTH_ALL', (106.68, 148.59), (236.22, 148.59), latch.pt(4))
    s.label('HEALTH_ALL', (106.68, 148.59), global_=False)
    s.junction((106.68, 148.59))
    connect(s, 'RESET_REQUEST', reset.pt(8), r73.pt(1))
    s.mark('RESET_REQUEST', (134.62, 165.1))

    # The RC is part of the reset-clock route, rather than a labelled island.
    connect(s, 'RESET_CLK', r73.pt(2), (182.88, 165.1),
            (182.88, 180.34), (226.06, 180.34),
            (226.06, latch.pt(3)[1]), latch.pt(3))
    connect(s, 'RESET_CLK', (198.12, 180.34), c55.pt(1))
    s.junction((198.12, 180.34))
    s.mark('RESET_CLK', (200.66, 180.34))
    connect(s, 'GND', c55.pt(2), (198.12, 196.85))
    s.gnd((198.12, 196.85))
    connect(s, 'GND', latch.pt(2), (215.9, latch.pt(2)[1]))
    s.gnd((215.9, latch.pt(2)[1]))
    connect(s, '+3V3_INV', latch.pt(1), (236.22, 187.96), (246.38, 187.96))
    s.power('+3V3_INV', (246.38, 187.96))
    connect(s, 'FAULT_LATCH', latch.pt(5), (261.62, latch.pt(5)[1]),
            (261.62, tp.pt(1)[1]), tp.pt(1))
    s.mark('FAULT_LATCH', (246.38, latch.pt(5)[1]))

    # Keep fan-out within the permission/output block as actual wires; the
    # memory block's result crosses the block boundary by a local label.
    connect(s, 'NO_LATCH', latch.pt(6), (261.62, latch.pt(6)[1]))
    s.label('NO_LATCH', (261.62, latch.pt(6)[1]), global_=False)
    connect(s, 'NO_LATCH', (276.86, permit_health.pt(13)[1]),
            (276.86, fault.pt(5)[1]), fault.pt(5))
    connect(s, 'NO_LATCH', (276.86, permit_health.pt(13)[1]), permit_health.pt(13))
    s.junction((276.86, permit_health.pt(13)[1]))
    s.label('NO_LATCH', (276.86, 201.93), global_=False)
    connect(s, 'HEALTH_ALL', (289.56, 172.72),
            (289.56, fault.pt(4)[1]), fault.pt(4))
    connect(s, 'HEALTH_ALL', (289.56, permit_health.pt(12)[1]), permit_health.pt(12))
    s.label('HEALTH_ALL', (289.56, 172.72), global_=False)
    s.junction((289.56, permit_health.pt(12)[1]))
    connect(s, 'HEALTH_UNLATCHED', permit_health.pt(11), (330.2, 185.42),
            (330.2, permit.pt(1)[1]), permit.pt(1))
    s.mark('HEALTH_UNLATCHED', (314.96, 185.42))
    connect(s, 'DRIVE_PERMIT', permit.pt(3), (388.62, 185.42))
    s.label('DRIVE_PERMIT', (388.62, 185.42))

    connect(s, 'FAULT_ACTIVE', fault.pt(6), r74.pt(1))
    s.mark('FAULT_ACTIVE', (314.96, 220.98))
    connect(s, 'FAULT_BASE', r74.pt(2), q8.pt(1))
    connect(s, 'FAULT_BASE', (350.52, 220.98), r75.pt(1))
    s.junction((350.52, 220.98))
    s.mark('FAULT_BASE', (342.9, 220.98))
    connect(s, 'GND', r75.pt(2), (350.52, 242.57))
    s.gnd((350.52, 242.57))
    connect(s, 'GND', q8.pt(2), (q8.pt(2)[0], 237.49))
    s.gnd((q8.pt(2)[0], 237.49))
    connect(s, 'FAULT_N', q8.pt(3), (q8.pt(3)[0], 213.36), (388.62, 213.36))
    s.label('FAULT_N', (388.62, 213.36))

    s.text('/S=HEALTH_ALL; /R held HIGH; D=0. Fault asynchronously sets Q.\n'
           'RESET_REQUEST = HEALTH_ALL AND NOT ENABLE_IN.\n'
           '10k / 10n delays the rising reset clock; hold ENABLE low >=1 ms after recovery.\n'
           'Fault or invalid supplies block DRIVE_PERMIT directly.\n'
           'Recovery with ENABLE high cannot clear the latch or restart PWM.\n'
           'FAULT_N is open collector; a fully unpowered inverter cannot assert LOW.\n'
           'Very short faults during reset may require a fresh disable cycle.',
           20.32, 222.25, 1.1)
    s.save()


def control_interface():
    s = Sheet('control_interface')
    s.section('HARDWARE GATING / SIX PWM COMMANDS', 20.32, 17.78, 190.5)
    s.section('LOGIC POWER / LOCAL DECOUPLING', 223.52, 17.78, 170.18)

    commands = [
        ('U25', 2, 4, 5, 6, 'R76'), ('U25', 3, 9, 10, 8, 'R77'),
        ('U25', 4, 12, 13, 11, 'R78'), ('U26', 1, 1, 2, 3, 'R79'),
        ('U26', 2, 4, 5, 6, 'R80'), ('U26', 3, 9, 10, 8, 'R81'),
    ]
    permit_x = 119.38
    for i, (ref, unit, pi, pe, po, pull) in enumerate(commands):
        y = 45.72 + i * 27.94
        gate = s.place(ref, 152.4, y, unit=unit)
        r = s.place(pull, 88.9, y+8.89)
        incoming = s.net(ref, pi)
        outgoing = s.net(ref, po)
        connect(s, incoming, (50.8, gate.pt(pi)[1]), gate.pt(pi))
        s.label(incoming, (50.8, gate.pt(pi)[1]), 180)
        connect(s, incoming, (88.9, gate.pt(pi)[1]), r.pt(1))
        s.junction((88.9, gate.pt(pi)[1]))
        connect(s, 'GND', r.pt(2), (88.9, y+16.51))
        s.gnd((88.9, y+16.51))
        connect(s, 'DRIVE_PERMIT', (permit_x, gate.pt(pe)[1]), gate.pt(pe))
        s.label('DRIVE_PERMIT', (permit_x, gate.pt(pe)[1]), 180)
        connect(s, outgoing, gate.pt(po), (190.5, y))
        s.label(outgoing, (190.5, y))
    s.section('DEFAULT DISABLE / NO PERMISSION', 20.32, 210.82, 190.5)
    r83 = s.place('R83', permit_x, 233.68)
    connect(s, 'DRIVE_PERMIT', (permit_x, 220.98), r83.pt(1))
    s.label('DRIVE_PERMIT', (permit_x, 220.98), 180)
    connect(s, 'GND', r83.pt(2), (permit_x, 241.3))
    s.gnd((permit_x, 241.3))

    r82 = s.place('R82', 50.8, 233.68)
    connect(s, 'ENABLE_IN', (50.8, 220.98), r82.pt(1))
    s.label('ENABLE_IN', (50.8, 220.98), 180)
    connect(s, 'GND', r82.pt(2), (50.8, 241.3))
    s.gnd((50.8, 241.3))
    s.text('R76-R81: hold all six commands LOW while MCU outputs are Hi-Z.\n'
           'R82: default disabled.  R83: default no permission.\n'
           'Logic levels remain 3.3 V; hardware AND gates operate independently of firmware.',
           20.32, 254, 1.1)

    # Each logic package and its bypass capacitor form one short supply loop.
    # Power symbols join independent package blocks without long shared rails.
    for i in range(6):
        col = i % 2
        row = i // 2
        x = 248.92 + col*78.74
        y = 55.88 + row*58.42
        power = s.place('U'+str(22+i), x, y, unit=5)
        cap = s.place('C'+str(56+i), x+25.4, y)
        top = y-12.7
        bottom = y+12.7
        connect(s, '+3V3_INV', power.pt(14), (cap.pt(1)[0], top))
        connect(s, '+3V3_INV', (cap.pt(1)[0], top), cap.pt(1))
        s.power('+3V3_INV', (cap.pt(1)[0], top))
        connect(s, 'GND', power.pt(7), (cap.pt(2)[0], bottom))
        connect(s, 'GND', cap.pt(2), (cap.pt(2)[0], bottom))
        s.gnd((cap.pt(2)[0], bottom))
    s.text('C56-C61: 100 nF local bypass at each logic package.', 223.52, 202.56, 1.1)

    s.section('UNUSED LOGIC / INPUTS TIED LOW', 223.52, 213.36, 170.18)
    for ref, unit, pa, pb, po, x in [
        ('U26', 4, 12, 13, 11, 248.92),
        ('U27', 3, 9, 10, 8, 309.88),
        ('U27', 4, 12, 13, 11, 370.84),
    ]:
        gate = s.place(ref, x, 241.3, unit=unit)
        tie_x = x-15.24
        connect(s, 'GND', gate.pt(pa), (tie_x, gate.pt(pa)[1]),
                (tie_x, gate.pt(pb)[1]), gate.pt(pb))
        connect(s, 'GND', (tie_x, gate.pt(pb)[1]), (tie_x, 248.92))
        s.junction((tie_x, gate.pt(pb)[1]))
        s.gnd((tie_x, 248.92))
        s.nc(ref, po, unit=unit)
    s.save()


if __name__ == '__main__':
    fault_logic()
    control_interface()

