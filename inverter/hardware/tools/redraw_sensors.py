"""Draw connector-to-conditioning wires for the two ABZ and two SPI ports."""
from redraw_common import Sheet, children, child


def connect(s, net, *points):
    s.path(net, list(points))


def connector_fields(part, x, y):
    part.field('Reference', x, y)
    part.field('Value', x, y+2.54)
    for prop in children(part.item, 'property'):
        if prop[1] == 'Value':
            child(child(prop, 'effects'), 'font')[1][1:] = [0.9, 0.9]


def pullup_fields(part):
    # KiCad reverses the left justification of a 180-degree part.  A centered
    # field beyond the body keeps the upright reference/value beside the part.
    part.field('Reference', part.x+7.62, part.y-1.27)
    part.field('Value', part.x+7.62, part.y+1.27)
    for prop in children(part.item, 'property'):
        if prop[1] in ['Reference', 'Value']:
            effects = child(prop, 'effects')
            for justify in children(effects, 'justify'):
                effects.remove(justify)


def draw():
    s = Sheet('sensors')
    for bank, shift in [('A', 0), ('B', 203.2)]:
        s.section('ABZ ENCODER '+bank+' / 3.3 V SINGLE-ENDED', 20.32+shift, 17.78, 175.26)
        first = 94 if bank == 'A' else 101
        jack = s.place('J9' if bank == 'A' else 'J10', 35.56+shift, 93.98, angle=180)
        connector_fields(jack, 25.4+shift, 76.2)
        for letter, pin, resistor_offset, row, fan_x in [
            ('A', 3, 0, 93.98, None),
            ('B', 4, 2, 71.12, 50.8),
            ('Z', 5, 4, 48.26, 45.72),
        ]:
            rs = s.place('R'+str(first+resistor_offset), 101.6+shift, row, angle=90)
            pu = s.place('R'+str(first+resistor_offset+1), 132.08+shift, row-12.7, angle=180)
            pullup_fields(pu)
            port = 'ENC_'+bank+'_'+letter+'_PORT'
            signal = 'ENC_'+bank+'_'+letter
            if fan_x is None:
                connect(s, port, jack.pt(pin), rs.pt(1))
            else:
                connect(s, port, jack.pt(pin), (fan_x+shift, jack.pt(pin)[1]),
                        (fan_x+shift, row), rs.pt(1))
            s.mark(port, (60.96+shift, row))
            connect(s, signal, rs.pt(2), (160.02+shift, row))
            s.label(signal, (160.02+shift, row))
            connect(s, signal, (132.08+shift, row), pu.pt(1))
            s.junction((132.08+shift, row))
            s.power('+3V3_INV', pu.pt(2))

        supply = s.place('R'+str(first+6), 101.6+shift, 119.38, angle=270)
        vcc = 'ENC_'+bank+'_VCC'
        connect(s, vcc, jack.pt(1), (45.72+shift, jack.pt(1)[1]),
                (45.72+shift, 119.38), supply.pt(2))
        s.mark(vcc, (48.26+shift, 119.38))
        connect(s, '+5V_SENSOR', supply.pt(1), (132.08+shift, 119.38))
        s.power('+5V_SENSOR', (132.08+shift, 119.38))
        s.text('DNP', 88.9+shift, 110.49, 1.0)
        connect(s, 'GND', jack.pt(2), (60.96+shift, jack.pt(2)[1]), (60.96+shift, 111.76))
        s.gnd((60.96+shift, 111.76))
        s.text('100 ohm series / 10k pull-ups to 3.3 V.  5 V supply link DNP.',
               20.32+shift, 128.27, 1.0)

        s.section('SPI SENSOR '+bank+' / 3.3 V SINGLE-ENDED', 20.32+shift, 137.16, 175.26)
        first = 108 if bank == 'A' else 114
        jack = s.place('J11' if bank == 'A' else 'J12', 35.56+shift, 228.6, angle=180)
        connector_fields(jack, 25.4+shift, 213.36)
        for signal_name, pin, resistor_offset, row, fan_x in [
            ('SCK', 3, 0, 228.6, None),
            ('MOSI', 4, 1, 208.28, 55.88),
            ('MISO', 5, 2, 187.96, 50.8),
            ('CS', 6, 3, 167.64, 45.72),
        ]:
            rs = s.place('R'+str(first+resistor_offset), 101.6+shift, row, angle=270)
            signal = 'SPI_'+bank+'_'+signal_name
            port = signal+'_PORT'
            if fan_x is None:
                connect(s, port, jack.pt(pin), rs.pt(2))
            else:
                connect(s, port, jack.pt(pin), (fan_x+shift, jack.pt(pin)[1]),
                        (fan_x+shift, row), rs.pt(2))
            s.mark(port, (60.96+shift, row))
            connect(s, signal, rs.pt(1), (160.02+shift, row))
            s.label(signal, (160.02+shift, row))
            if signal_name == 'CS':
                pu = s.place('R'+str(first+4), 132.08+shift, 154.94, angle=180)
                pullup_fields(pu)
                connect(s, signal, (132.08+shift, row), pu.pt(1))
                s.junction((132.08+shift, row))
                s.power('+3V3_INV', pu.pt(2))

        supply = s.place('R'+str(first+5), 101.6+shift, 248.92, angle=270)
        vcc = 'SPI_'+bank+'_VCC'
        connect(s, vcc, jack.pt(1), (45.72+shift, jack.pt(1)[1]),
                (45.72+shift, 248.92), supply.pt(2))
        s.mark(vcc, (48.26+shift, 248.92))
        connect(s, '+5V_SENSOR', supply.pt(1), (132.08+shift, 248.92))
        s.power('+5V_SENSOR', (132.08+shift, 248.92))
        s.text('DNP', 88.9+shift, 240.03, 1.0)
        connect(s, 'GND', jack.pt(2), (60.96+shift, jack.pt(2)[1]), (60.96+shift, 241.3))
        s.gnd((60.96+shift, 241.3))
    s.text('All external signal pins are 3.3 V single-ended; no 5 V level conversion or cable protection is claimed.\n'
           'R100 / R107 / R113 / R119 are DNP: external sensor-power links remain open by default.',
           20.32, 264.16, 1.0)
    s.save()


if __name__ == '__main__':
    draw()
