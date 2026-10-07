package analysis

import (
	"strings"
	"testing"

	"icscope/internal/netlist"
)

func part(nl *netlist.Netlist, ref, value string, pins ...string) {
	p := &netlist.Part{Ref: ref, Value: value}
	for i := 0; i+2 < len(pins)+1; i += 3 {
		p.Pins = append(p.Pins, netlist.Pin{Num: pins[i], Name: pins[i+1], Net: pins[i+2]})
	}
	nl.Parts[ref] = p
}

func res(nl *netlist.Netlist, ref, value, a, b string) {
	part(nl, ref, value, "1", "", a, "2", "", b)
}

func find(t *testing.T, r *Report, ref string, gate int) Finding {
	for _, f := range r.Findings {
		if f.Ref == ref && f.Gate == gate {
			return f
		}
	}
	t.Fatalf("%s gate %d not found", ref, gate)
	return Finding{}
}

func has(list []string, sub string) bool {
	for _, s := range list {
		if strings.Contains(s, sub) {
			return true
		}
	}
	return false
}

func TestTopologies(t *testing.T) {
	nl := netlist.New("test", "orcad")
	// U1: dual op-amp, gate 1 = buffer of a 1M/20k divider into an MCU ADC pin,
	// gate 2 = low-side shunt difference amplifier with gain 50.
	part(nl, "U1", "TLV9062", "3", "IN1+", "DIV", "2", "IN1-", "BUF", "1", "OUT1", "BUF",
		"5", "IN2+", "P2", "6", "IN2-", "N2", "7", "OUT2", "O2", "8", "V+", "VDD_3V3", "4", "V-", "GND")
	res(nl, "R1", "1M", "VIN", "DIV")
	res(nl, "R2", "20K", "DIV", "GND")
	part(nl, "C1", "10nF", "1", "", "DIV", "2", "", "GND")
	res(nl, "R3", "510", "BUF", "ADC_V")
	part(nl, "U9", "STM32G474QET6", "27", "PA0", "ADC_V", "24", "PC2", "ADC_I", "121", "PB6", "ZC")
	res(nl, "RS", "2m", "SH_P", "GND")
	res(nl, "R10", "1K", "SH_P", "N2")
	res(nl, "R11", "50K", "N2", "O2")
	res(nl, "R12", "1K", "GND", "P2")
	res(nl, "R13", "50K", "P2", "GND")
	res(nl, "R14", "510", "O2", "ADC_I")
	// U2: comparator with positive feedback 100k / 10k from a 1.65 V reference.
	part(nl, "U2", "TLV7041DBVR", "3", "IN+", "HP", "4", "IN-", "SIG", "1", "OUT", "ZC", "5", "VCC", "VDD_3V3", "2", "VEE", "GND")
	res(nl, "R20", "10K", "REF", "HP")
	res(nl, "R21", "100K", "HP", "ZC")
	res(nl, "R22", "10K", "VDD_3V3", "SIG")
	// U3: hex inverter, gate 1 driven by the MCU
	part(nl, "U3", "SN74HC14PWR", "1", "1A", "ZC", "2", "1Y", "DRV", "3", "2A", "", "4", "2Y", "", "7", "GND", "GND", "14", "VCC", "VDD_3V3")
	part(nl, "U4", "INA240A2PWR", "3", "IN+", "SH_P", "4", "IN-", "GND", "7", "OUT", "X")
	part(nl, "NC1", "TP", "1", "", "NC", "2", "", "NC")
	nl.Index()
	r := Analyze(nl, nil)

	f := find(t, r, "U1", 1)
	if f.Topology != "follower" || !has(f.Calc, "VIN×0.01961") || !has(f.Suggest, "버퍼 생략") {
		t.Errorf("U1 gate 1: %+v", f)
	}
	f = find(t, r, "U1", 2)
	if f.Topology != "difference" || f.Gain != "50 V/V" || !has(f.Calc, "0.1 V/A") || !has(f.Warn, "U4") {
		t.Errorf("U1 gate 2: %+v", f)
	}
	f = find(t, r, "U2", 1)
	if f.Topology != "comparator" || !has(f.Calc, "300 mV") || !has(f.Calc, "PB6") {
		t.Errorf("U2: %+v", f)
	}
	f = find(t, r, "U3", 1)
	if f.Topology != "inverter" || !has(f.Suggest, "극성") {
		t.Errorf("U3 gate 1: %+v", f)
	}
	if find(t, r, "U3", 2).Topology != "unused" {
		t.Errorf("U3 gate 2 should be unused")
	}
	if !has(r.Notes, "'NC'") {
		t.Errorf("NC net not flagged: %v", r.Notes)
	}
}

func TestClassOf(t *testing.T) {
	for s, want := range map[string]string{
		"TLV9062D": KOpamp, "OPA2387D": KOpamp, "LM358": KOpamp, "TLV7041DBVR": KComparator, "LM393": KComparator,
		"SN74HC14PWR": KInverter, "SN74LVC1G04DBVR": KInverter, "HEF40106B": KInverter, "INA240A2PWR": KCSA,
		"AMC3301QDWERQ1": KIsoAmp, "STM32G474QET6": KMCU, "LM5156H": "", "SN74HC4051": "",
	} {
		if got := ClassOf(s); got != want {
			t.Errorf("ClassOf(%s) = %q, want %q", s, got, want)
		}
	}
}
