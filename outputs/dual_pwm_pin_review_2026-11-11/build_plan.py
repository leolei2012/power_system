"""Create a reviewable LQFP100 planning proposal; never edits native KiCad files."""
from pathlib import Path
import csv
import hashlib
import io
import json

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
DOCS = ROOT / "docs"

# DS12589 Rev6 Figure13, package top view. Pin mapping is cross-checked against
# KiCad's independently maintained STM32G431V_6-8-B_Tx symbol by the reviewer.
names = (
    "PE2 PE3 PE4 PE5 PE6 VBAT PC13 PC14 PC15 PF9 PF10 PF0 PF1 PG10 "
    "PC0 PC1 PC2 PC3 PF2 PA0 PA1 PA2 VSS VDD PA3 "
    "PA4 PA5 PA6 PA7 PC4 PC5 PB0 PB1 PB2 VSSA VREF+ VDDA PE7 PE8 PE9 "
    "PE10 PE11 PE12 PE13 PE14 PE15 PB10 VSS VDD PB11 "
    "PB12 PB13 PB14 PB15 PD8 PD9 PD10 PD11 PD12 PD13 PD14 PD15 VSS VDD "
    "PC6 PC7 PC8 PC9 PA8 PA9 PA10 PA11 PA12 VSS VDD "
    "PA13 PA14 PA15 PC10 PC11 PC12 PD0 PD1 PD2 PD3 PD4 PD5 PD6 PD7 "
    "PB3 PB4 PB5 PB6 PB7 PB8 PB9 PE0 PE1 VSS VDD"
).split()
assert len(names) == 100
pin_map = {n: i for i, n in enumerate(names, 1) if n.startswith("P")}
assert len(pin_map) == 86
review_map = json.loads((OUT / "review_lqfp100_pin_map.json").read_text(encoding="utf-8"))
assert {str(i): n for i, n in enumerate(names, 1)} == review_map

bindings = []

def bind(group, signal, gpio, function, af=None, status="planned", notes=""):
    bindings.append(dict(group=group, signal=signal, gpio=gpio,
                         mcu_pin=pin_map[gpio], function=function, af=af,
                         status=status, notes=notes))

ports = []
for port, timer, pins, af in [
    ("PWM_A", "TIM1", ["PE9", "PE8", "PE11", "PE10", "PE13", "PE12"], 2),
    ("PWM_B", "TIM8", ["PC6", "PC10", "PC7", "PC11", "PC8", "PC12"], 4),
]:
    contacts = [dict(pin=1, signal="GND", gpio=None, mcu_pin=None, function="GND", af=None)]
    for i, (gpio, ch) in enumerate(zip(pins, ["CH1", "CH1N", "CH2", "CH2N", "CH3", "CH3N"]), 2):
        signal = f"{port}_{ch}"
        bind(port, signal, gpio, f"{timer}_{ch}", af,
             notes="3.3V logic; external hardware permission gate required; not a MOSFET gate connection.")
        contacts.append(dict(pin=i, signal=signal, gpio=gpio, mcu_pin=pin_map[gpio],
                             function=f"{timer}_{ch}", af=af))
    contacts.append(dict(pin=8, signal="GND", gpio=None, mcu_pin=None, function="GND", af=None))
    ports.append(dict(name=port, timer=timer, contacts=contacts))

adc = [
    ("PC0", ["ADC1_IN6", "ADC2_IN6"], "I_A_U"),
    ("PC1", ["ADC1_IN7", "ADC2_IN7"], "I_A_V"),
    ("PC2", ["ADC1_IN8", "ADC2_IN8"], "I_A_W"),
    ("PC3", ["ADC1_IN9", "ADC2_IN9"], "I_B_U"),
    ("PA0", ["ADC1_IN1", "ADC2_IN1"], "I_B_V"),
    ("PA1", ["ADC1_IN2", "ADC2_IN2"], "I_B_W"),
    ("PA4", ["ADC2_IN17"], "V_DC_A"),
    ("PB0", ["ADC1_IN15"], "V_DC_B"),
    ("PB1", ["ADC1_IN12"], "NTC_A"),
    ("PB2", ["ADC2_IN12"], "NTC_B"),
]
unallocated_analog = [
    ("PC4", ["ADC2_IN5"], None),
    ("PC5", ["ADC2_IN11"], None),
    ("PA2", ["ADC1_IN3"], None),
    ("PA3", ["ADC1_IN4"], None),
    ("PB11", ["ADC1_IN14", "ADC2_IN14"], None),
    ("PB12", ["ADC1_IN11"], None),
    ("PB14", ["ADC1_IN5"], None),
    ("PB15", ["ADC2_IN15"], None),
]
adc_inputs = []
vienna_roles = ["I_L1", "I_L2", "I_L3", "V_AC1", "V_AC2", "V_AC3", "V_BUS_UPPER", "V_BUS_LOWER", "NTC", "SPARE"]
single_motor_roles = ["I_U", "I_V", "I_W", "V_U_PHASE", "V_V_PHASE", "V_W_PHASE", "V_DC", "SPARE", "POWER_BOARD_NTC", "SPARE"]
boost_roles = ["I_L", "SPARE", "SPARE", "V_RECTIFIED_INPUT", "SPARE", "SPARE", "V_OUTPUT", "SPARE", "POWER_BOARD_NTC", "SPARE"]
for i, (gpio, channels, example_role) in enumerate(adc, 1):
    status = "planned"
    signal = f"ADC_{i:02}"
    bind("ADC", signal, gpio, "/".join(channels), status=status,
         notes=f"Generic ADC port. Single motor: {single_motor_roles[i-1]}; dual motor: {example_role}; Boost: {boost_roles[i-1]}; Vienna: {vienna_roles[i-1]}. Alternative applications, usage examples only.")
    adc_inputs.append(dict(name=signal, gpio=gpio, mcu_pin=pin_map[gpio],
                           supported_channels=channels, dual_motor_example_role=example_role,
                           single_motor_example_role=single_motor_roles[i-1],
                           Boost_example_role=boost_roles[i-1],
                           Vienna_example_role=vienna_roles[i-1],
                           status=status))

for group, entries in [
    ("ENC_A", [("A", "PD3", "TIM2_CH1", 2), ("B", "PD4", "TIM2_CH2", 2), ("Z", "PD5", "GPIO_EXTI5", None)]),
    ("ENC_B", [("A", "PB6", "TIM4_CH1", 2), ("B", "PB7", "TIM4_CH2", 2), ("Z", "PD6", "GPIO_EXTI6", None)]),
    ("SPI_A", [("SCK", "PA5", "SPI1_SCK", 5), ("MISO", "PA6", "SPI1_MISO", 5), ("MOSI", "PA7", "SPI1_MOSI", 5), ("CS_N", "PE0", "GPIO_Output", None)]),
    ("SPI_B", [("SCK", "PB3", "SPI3_SCK", 6), ("MISO", "PB4", "SPI3_MISO", 6), ("MOSI", "PB5", "SPI3_MOSI", 6), ("CS_N", "PE1", "GPIO_Output", None)]),
    ("I2C_A", [("SCL", "PA15", "I2C1_SCL", 4), ("SDA", "PB9", "I2C1_SDA", 4)]),
    ("I2C_B", [("SCL", "PA9", "I2C2_SCL", 4), ("SDA", "PA8", "I2C2_SDA", 4)]),
    ("TTL", [("TX", "PD8", "USART3_TX", 7), ("RX", "PD9", "USART3_RX", 7)]),
    ("CAN", [("RX", "PA11", "FDCAN1_RX", 9), ("TX", "PA12", "FDCAN1_TX", 9)]),
    ("SWD", [("DIO", "PA13", "SWDIO", 0), ("CLK", "PA14", "SWCLK", 0)]),
    ("CORE", [("HSE_IN", "PF0", "OSC_IN", None), ("HSE_OUT", "PF1", "OSC_OUT", None),
              ("NRST", "PG10", "NRST", None), ("BOOT0", "PB8", "BOOT0", None)]),
    ("LED", [("RUN", "PE2", "GPIO_Output", None), ("FAULT", "PE3", "GPIO_Output", None),
             ("COMM", "PE4", "GPIO_Output", None), ("AUX", "PE5", "GPIO_Output", None)]),
]:
    for signal, gpio, function, af in entries:
        bind(group, f"{group}_{signal}", gpio, function, af,
             notes="Current optional CAN transceiver supports classic CAN; no CAN-FD PHY claim." if group == "CAN" else "")

for signal, gpio, function, af, status, notes in [
    ("FAULT_A_N", "PE15", "TIM1_BKIN", 2, "planned", "Independent active-low break; also locally gates the power board; no automatic restart."),
    ("FAULT_B_N", "PD2", "TIM8_BKIN", 4, "planned", "Uses primary BKIN, independent from port A."),
    ("ENABLE_A", "PD10", "GPIO_Output", None, "planned", "External pulldown, default disabled."),
    ("ENABLE_B", "PD11", "GPIO_Output", None, "planned", "External pulldown, default disabled."),
    ("BASE_READY_A", "PC13", "GPIO_Input", None, "planned", "PC13 input only; receiver protection and reference must be designed."),
    ("BASE_READY_B", "PC14", "GPIO_Input", None, "planned", "PC14 input only; LSE cannot be used on this pad concurrently."),
    ("RUN_ARM", "PE7", "GPIO_Output", None, "planned", "Local pulldown; AND with reset supervisor to produce CTRL_READY; ARM is not a ROM UART pad."),
    ("BRAKE_A", "PF9", "TIM15_CH1", 3, "planned", "Independent from bridge FAULT/ENABLE; reset/ARM startup gate required."),
    ("BRAKE_B", "PF10", "TIM15_CH2", 3, "pin_reserve_only", "Optional second brake; same TIM15 frequency/counter as BRAKE_A, independent duty; no second power circuit implied."),
]:
    bind("POWER_CTRL", signal, gpio, function, af, status, notes)

assert len(bindings) == 63
assert len({r['gpio'] for r in bindings}) == 63
assert len({r['mcu_pin'] for r in bindings}) == 63
unallocated = [{"gpio": g, "mcu_pin": p} for g, p in sorted(pin_map.items(), key=lambda item: item[1])
               if g not in {r['gpio'] for r in bindings}]
assert len(unallocated) == 23
power_rails = {"VBAT": "+3V3_MCU", "VDD": "+3V3_MCU", "VSS": "GND",
               "VSSA": "GND", "VDDA": "+3V3_A_MCU", "VREF+": "VREF_MCU"}
power_pads = [dict(mcu_pin=i, pad=n, proposed_rail=power_rails[n])
              for i, n in enumerate(names, 1) if n in power_rails]
assert len(power_pads) == 14

proposal = {
    "revision": "F-dual-power-PWM-LQFP100-planning",
    "date": "2026-11-11",
    "status": "Planning proposal; no native schematic, PCB, BOM or library migration performed.",
    "user_decisions": ["Two independent PWM power-control ports, 8P each: 6 PWM plus 2 GND.",
                       "Retain existing ABZ interfaces, independent SPI buses and GPIO indicators; evaluate a larger package.",
                       "Two SPI, two I2C and two ABZ interfaces; one CAN and one TTL UART.",
                       "Exactly ten independent analog connectors in total, not eight plus ten.",
                       "PFC application does not run motor control on the same controller; motor and PFC modes are alternatives."],
    "operating_modes": {
        "motor_and_PFC_simultaneous": False,
        "motor_mode": "One motor or the separately evaluated basic dual-motor option; no PFC loop on the same MCU.",
        "PFC_mode": "One Boost or Vienna power-board application; no motor control on this MCU. No dual-PFC or LLC operating target is implied.",
        "PWM_usage": "Keep both physical PWM ports. Configure only the selected application's required outputs; unused outputs remain disabled.",
        "ADC_usage": "Reuse the same ten generic analog connectors between alternative applications; do not add motor and PFC sensing counts together."
    },
    "recommended_MCU": {"MPN": "STM32G431VBT6", "package": "LQFP100, 14x14 mm body",
                        "selection_status": "Recommended planning candidate, not an implemented part change.",
                        "core_and_memory": "Same G431 class: 170MHz, 128KB Flash, 32KB SRAM, two ADCs.",
                        "domestic_LCSC_code": "C529359", "domestic_LCSC_URL": "https://item.szlcsc.com/549637.html",
                        "domestic_stock_verified": False, "shared_library_model_present": False,
                        "stock_note": "Domestic item mapping verified from LCSC product data; item page challenge prevented domestic stock verification."},
    "package_signal_pad_count": 86,
    "power_reference_ground_pad_count": 14,
    "power_reference_ground_pads": power_pads,
    "power_notes": "All five VDD/VSS pairs require local return/decoupling review; retain separate VDDA/VREF filtering and local bypass. VBAT tied to 3V3 as in the current design. Power rail names are proposed roles, not newly implemented nets.",
    "allocated_or_reserved_signal_pads": 63,
    "existing_features_and_dual_controls_planned_pads": 62,
    "additional_analog_pin_reservations": 0,
    "optional_second_brake_pin_reservations": 1,
    "unallocated_signal_pads": unallocated,
    "PWM_ports": ports,
    "connector_order_status": "Proposed logical order, pin1/pin8 GND. Connector model and mating-view drawing remain unselected.",
    "ADC_inputs": adc_inputs,
    "ADC_usage_examples": {
        "status": "Hypothetical sensor assignments, not frozen power-board circuits or ADC conversion schedules.",
        "counts": {"single_motor": 8, "dual_motor_basic": 10, "single_boost": 4, "single_Vienna": 9},
        "single_motor_spare_options": {"ADC_08": "Possible future DC input current, requiring a new sensing front end.",
                                       "ADC_10": "Possible future motor NTC, requiring a matching excitation/divider front end."},
        "measurement_notes": ["Single-motor phase voltages refer to conditioned PWM phase-node measurements as in the saved inverter; no sinusoidal post-filter output is implied.",
                              "Boost input voltage example is rectified input; confirm the actual sensing point when the topology is selected.",
                              "Vienna upper/lower half-bus inputs are conditioned voltage measurements of the two bus-capacitor sections; do not tie the physical bus midpoint to controller GND just to obtain these measurements.",
                              "All ports receive low-voltage, reference-compatible conditioned signals. An NTC role needs a divider/excitation front end; it does not mean wiring a raw NTC directly across a signal/GND ADC port."]
    },
    "ADC_connector_scope": "Exactly ten independent generic ADC connectors in total. User accepted XUNPU GH1.25 2P signal-plus-GND recommendation for planning; physical pin order and footprint remain to be checked. Dual-motor roles are usage examples, not fixed labels. Eight other ADC-capable pads remain unallocated and have no extra terminals.",
    "connector_inventory_record": "controller_connector_inventory.json",
    "unallocated_analog_capabilities": [{"gpio": g, "mcu_pin": pin_map[g], "supported_channels": c} for g,c,_ in unallocated_analog],
    "analog_input_budget": {
        "assumptions": "Motor and PFC are alternative applications on this controller. Each mode uses the same ten ports. Counts are project interface budgets, not claimed manufacturer mandatory channel counts.",
        "single_motor_full": {"inputs": 8, "description": "Three currents, bus voltage, three phase voltages and one NTC; two ports remain."},
        "dual_motor_basic": {"inputs": 10, "description": "Each motor: 3 phase currents, 1 bus voltage, 1 NTC; no phase-voltage measurements."},
        "dual_motor_with_phase_voltages": {"inputs": 16, "description": "Basic dual-motor set plus three phase voltages per motor."},
        "single_boost_PFC": {"inputs": 4, "description": "Inductor current, input voltage, output voltage and NTC; six ports remain."},
        "single_Vienna_PFC": {"inputs": 9, "description": "Three currents, three input voltages, two half-bus voltages and NTC; one port remains."},
        "excluded_from_target": "Motor plus PFC simultaneously on this MCU; previous 14/17-input combined examples are not requirements.",
        "decision": "Keep exactly ten analog connectors. They cover the defined standalone Boost/Vienna and basic motor-mode examples; no expansion is required for the PFC alternative. Dual-motor phase-voltage sensing remains outside this ten-port example."
    },
    "bindings": bindings,
    "power_control_interface": {
        "PWM_ports_contain": "PWM and GND only; no raw power, ADC, ENABLE, FAULT or READY signals inside the 8P ports.",
        "separate_CTRL_ports": "Proposed A/B 6P each: ENABLE, FAULT_N, BASE_READY, CTRL_READY, BRAKE and GND. Physical pin order pending. CTRL_READY is the shared reset-qualified ARM output, not an extra GPIO; BRAKE_B remains a reserved pin, not an implemented second brake circuit.",
        "startup": "Both boards require default-disabled hardware gating independent of MCU boot output levels. CTRL_READY = CORE_RESET_OK AND RUN_ARM; each board also requires its own ENABLE and local hardware-OK.",
        "ROM_loader": "AN2606 G431 Table116 lists PC10/PC11 as ROM USART3 TX/RX and PC8 as I2C3 SCL: all overlap PWM_B. BOOT/ROM must not obtain ARM permission; hardware gating must suppress any ROM-level activity. PD5/PD6 have USART2 alternate functions, but that ROM table selects PA2/PA3, not PD5/PD6; do not infer ROM use from an AF entry alone.",
        "fault": "Each local power board closes its own hardware protection path and reports FAULT_N to the corresponding advanced-timer BKIN. Do not replace hardware cutoff with software polling.",
        "brake": "TIM15 is separate from TIM1/TIM8 and remains available after bridge fault. Brake startup permission must use reset/ARM; bridge FAULT must not automatically suppress required braking.",
        "electrical": "3.3V logic and conditioned ADC voltages. Gate drivers, high-voltage sensing and any required isolation remain power-board responsibilities. Mains-version isolation is not decided by this pin plan.",
    },
    "firmware_constraints": [
        "Each PWM port is three complementary pairs, not six arbitrary independently timed PWM outputs; port A and port B use separate advanced timers.",
        "TIM1/TIM8 PWM frequency, ADC trigger/sequence and CPU budget must be designed for the selected motor OR PFC application; they do not run together on this controller. Two 20kHz FOC loops plus ThreadX are not validated here.",
        "Two ADC instances remain shared; physical analog pin reservations do not increase simultaneous ADC capacity.",
        "ABZ uses independent TIM2/TIM4 encoder counters; Z inputs are GPIO interrupts, not promised hardware timer-index reset.",
        "SPI_A and SPI_B remain independent hardware SPI1/SPI3 buses; release PB3/PB4 JTAG/SWO while retaining PA13/PA14 SWD.",
        "I2C1 and I2C2 are separate open-drain buses, each with a separately sized 3.3V pullup network. Disable unused UCPD dead-battery pulls affecting PB6 and PA9 before encoder/I2C use; verify option bytes for PB8 BOOT0 and PG10 NRST.",
        "Keep PE2-PE5 trace functions disabled when used for the four GPIO LEDs; power LED uses no GPIO.",
        "CAN keeps current classic-CAN PHY qualification; changing package does not validate CAN-FD operation.",
    ],
    "migration": {"native_MCU": "STM32G431RBT6", "native_interface": "Rev E headers",
                  "native_schematic_changed": False, "native_PCB_changed": False,
                  "native_BOM_changed": False, "shared_library_changed": False,
                  "required_before_drawing": ["Build/review the exact VBT6 library material and LQFP100 footprint.",
                                              "Redraw MCU supply/ground/decoupling for all 100 physical pads; do not rename the 64-pin symbol.",
                                              "Implement terminal receivers, A/B independent controls and revised ARM/brake gates.",
                                              "Verify connector mating views, harnesses and 60x60mm placement in the new PCB."]},
    "sources": {"datasheet_URL": "https://www.st.com/resource/en/datasheet/stm32g431rb.pdf",
                "datasheet_local": "../reference/ST_G431_dual_pwm/original/DS12589_STM32G431_Rev6.pdf",
                "datasheet_sections": "Figure13 p49; Table12 pp51-60; Table13 pp61-66",
                "source_manifest": "../reference/ST_G431_dual_pwm/sources.json",
                "official_part": "https://estore.st.com/en/stm32g431vbt6-cpn.html",
                "ROM_bootloader": "https://www.st.com/resource/en/application_note/an2606-stm32-microcontroller-system-memory-boot-mode-stmicroelectronics.pdf — G431 Table116",
                "Vienna_sensing_reference": "https://www.ti.com/lit/ug/tiducj0g/tiducj0g.pdf — 3 currents, 3 AC voltages and 2 half-bus voltages; NTC is an additional project budgeting assumption."},
}

def write_csv(path, rows, fields):
    text = io.StringIO(newline="")
    writer = csv.DictWriter(text, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
    path.write_text(text.getvalue(), encoding="utf-8-sig", newline="")

(DOCS / "controller_dual_pwm_pin_plan.json").write_text(json.dumps(proposal, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
write_csv(DOCS / "controller_dual_pwm_pin_plan.csv", bindings,
          ["group", "signal", "gpio", "mcu_pin", "function", "af", "status", "notes"])
example_rows = [dict(port=x['name'], gpio=x['gpio'], mcu_pin=x['mcu_pin'],
                     ADC_channels='/'.join(x['supported_channels']),
                     single_motor=x['single_motor_example_role'],
                     dual_motor=x['dual_motor_example_role'],
                     Boost=x['Boost_example_role'], Vienna=x['Vienna_example_role'])
                for x in adc_inputs]
write_csv(DOCS / "controller_ADC_mode_examples.csv", example_rows,
          ["port", "gpio", "mcu_pin", "ADC_channels", "single_motor", "dual_motor", "Boost", "Vienna"])
port_rows = [dict(port=p['name'], **c) for p in ports for c in p['contacts']]
write_csv(DOCS / "controller_dual_pwm_ports.csv", port_rows,
          ["port", "pin", "signal", "gpio", "mcu_pin", "function", "af"])
by_gpio = {x['gpio']: x for x in bindings}
all_pad_rows = []
for i, n in enumerate(names, 1):
    if n in power_rails:
        row = dict(mcu_pin=i, pad=n, role=power_rails[n], function="power/reference/ground", af=None, status="power")
    elif n in by_gpio:
        x = by_gpio[n]
        row = dict(mcu_pin=i, pad=n, role=x['signal'], function=x['function'], af=x['af'], status=x['status'])
    else:
        row = dict(mcu_pin=i, pad=n, role="Unallocated", function="Reserve", af=None, status="unallocated")
    all_pad_rows.append(row)
write_csv(DOCS / "controller_LQFP100_all_pins.csv", all_pad_rows,
          ["mcu_pin", "pad", "role", "function", "af", "status"])
(OUT / "figure13_pin_map.json").write_text(json.dumps({str(i): n for i, n in enumerate(names, 1)}, indent=2) + "\n", encoding="utf-8")
native_files = ["controller/hardware/g431_core/controller.kicad_sch",
                "controller/hardware/g431_core/controller.kicad_pcb",
                "controller/hardware/g431_core/STM32G431RBT6_pin_plan.csv",
                "inverter/hardware/inverter.kicad_sch", "inverter/hardware/inverter.kicad_pcb"]
hashes = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in native_files}
hash_file = OUT / "native_before.json"
if not hash_file.exists():
    hash_file.write_text(json.dumps(hashes, indent=2) + "\n", encoding="utf-8")
assert hashes == json.loads(hash_file.read_text(encoding="utf-8")), "Native files changed during planning"
print(json.dumps({"plan_rows": len(bindings), "signal_pad_pool": len(pin_map), "free": len(unallocated),
                  "PWM_ports": len(ports), "native_unchanged": True}, ensure_ascii=False))
