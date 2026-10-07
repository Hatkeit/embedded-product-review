package analysis

import (
	"regexp"
	"strconv"
	"strings"

	"icscope/internal/netlist"
)

// Part classes recognised from the part number.
const (
	KOpamp      = "opamp"
	KComparator = "comparator"
	KInverter   = "inverter"
	KCSA        = "csa"
	KIsoAmp     = "isoamp"
	KMCU        = "mcu"
)

var ClassKo = map[string]string{
	KOpamp:      "연산 증폭기",
	KComparator: "비교기",
	KInverter:   "인버터(로직)",
	KCSA:        "전류 감지 증폭기",
	KIsoAmp:     "절연 증폭기",
	KMCU:        "MCU",
}

// Order matters: comparators before op-amps (TLV3xxx/TLV7xxx vs TLV9xxx).
var partKinds = []struct {
	key string
	re  *regexp.Regexp
}{
	{KComparator, regexp.MustCompile(`^(LM393|LM339|LM311|LM2903|LM2901|LM397|LMV33[19]|LMV393|LMV76\d|TLV3\d{3}|TLV7\d{3}|TLV18\d\d|TLC33\d\d|TLC37\d\d|MAX9\d{2}|MAX40\d{3}|ADCMP\d|LT17\d\d|LTC17\d\d|LTC6702|TS39\d|TS88\d|TS3011|TS3021|NCS2200|NCX2200|MCP65\d\d?|MCP654\d|LMH7\d{3}|BA2903|AS393)`)},
	{KCSA, regexp.MustCompile(`^(INA1[89]\d|INA2[0-4]\d|INA28\d|INA29\d|INA30\d|INA31\d|INA21\d|INA24\d|INA181|MAX40[78]\d|MAX437\d|MAX9918|AD84[01]\d|AD8210|ZXCT\d|LMP86\d\d|LMP8640|TSC\d{3}|MCP6C02|NCS21\d|NCS199)`)},
	{KIsoAmp, regexp.MustCompile(`^(AMC1[0-9]{3}|AMC3[0-9]{3}|ACPL-?C\d|ACPL-?7\d|HCPL-?7\d|SI89\d\d|ISO224|ADUM7\d|AD740\d|ISOAMP)`)},
	{KOpamp, regexp.MustCompile(`^(OPA\d|OPA[A-Z]?\d|TLV9\d|TLV2\d|TLV6\d|TLV4\d|TLV07|TLV8\d|LMV3[0-9]{2}|LMV6\d\d|LMV7[0-6]\d|LM358|LM324|LM2904|LM2902|LM321|LM7321|LM6\d{3}|TL0[678]\d|TLC2\d|TLC27|TLC4|MCP60\d|MCP61\d|MCP62\d|MCP64\d|MCP6V|AD8[0-9]{2}|ADA4\d|OP\d{2}|LT1\d{3}|LT6\d{3}|LTC6\d{3}|LTC20[45]\d|MAX4\d{3}|MAX44\d{3}|NCS\d{3}|TSV\d{3}|TSZ\d{3}|LMC6\d|LMP7\d|THS4\d|TS9\d{2}|TS27\d|TSB\d)`)},
	{KInverter, regexp.MustCompile(`^(SN|MC|NL|M|CD|HEF|U)?74[A-Z]{0,5}(1G|2G|3G)?(U04|04|14|05|06)([A-Z]|$)|^(NC7S|TC7S)[A-Z]{0,2}(U04|04|14)|^(CD|HEF|MC1)40(69|49|106|1G06)|^74[A-Z]{0,5}1G(04|14)`)},
	{KMCU, regexp.MustCompile(`^(STM32|TMS320|F28\d|ESP32|PIC\d|DSPIC|ATSAM|ATMEGA|GD32|RP2040|NRF5|MSP430|MSPM0|R7F|EFM32|LPC\d|MK\d\d|S32K|CY8C|XMC\d)`)},
}

// ClassOf returns the class key of a part number ("" when unknown).
func ClassOf(s string) string {
	for _, tok := range tokens(s) {
		for _, k := range partKinds {
			if k.re.MatchString(tok) {
				return k.key
			}
		}
	}
	return ""
}

func tokens(s string) []string {
	s = strings.ToUpper(s)
	f := strings.FieldsFunc(s, func(r rune) bool { return r == ' ' || r == '_' || r == ',' || r == '/' || r == '(' || r == ')' })
	return f
}

func partClass(p *netlist.Part) string {
	if c := ClassOf(p.Value + " " + p.PartName + " " + strings.Join(p.Lines, " ")); c != "" {
		return c
	}
	// Generic amplifier symbol: IN+/IN-/OUT pins on a U part.
	if netlist.Prefix(p.Ref) == "U" || netlist.Prefix(p.Ref) == "IC" {
		var ip, in, out bool
		for _, q := range p.Pins {
			switch pinRole(q.Name) {
			case "in+":
				ip = true
			case "in-":
				in = true
			case "out":
				out = true
			}
		}
		if ip && in && out {
			return KOpamp
		}
	}
	return ""
}

var (
	reInP  = regexp.MustCompile(`^(\+IN[A-D1-4]?|IN[A-D1-4]?\+|\+|INP[A-D1-4]?|IN[A-D1-4]?P|VIN\+|VINP|NONINV.*|\+IN_?[A-D1-4])$`)
	reInN  = regexp.MustCompile(`^(-IN[A-D1-4]?|IN[A-D1-4]?-|-|INN[A-D1-4]?|IN[A-D1-4]?N|VIN-|VINN|INV.*|-IN_?[A-D1-4])$`)
	reOut  = regexp.MustCompile(`^(V?OUT[A-D1-4]?|OUT_?[A-D1-4]|[1-6]?Y|Y[1-6]?|O|OUTPUT)$`)
	reVP   = regexp.MustCompile(`^(V\+|VCC[A-Z0-9]*|VDD[A-Z0-9]*|VS\+?|\+VS|V\+S|VPOS|AVDD)$`)
	reVN   = regexp.MustCompile(`^(V-|VEE|VSS|GND|AGND|VS-|-VS|VNEG)$`)
	reLin  = regexp.MustCompile(`^([1-6]?A|A[1-6]?|IN|I|INPUT)$`)
	reTag  = regexp.MustCompile(`([A-D1-4])`)
	reGnd  = regexp.MustCompile(`(?i)(^|[_/])([ADPSHIEFCLM]|ISO|SYS)?GND([0-9_]|$)|^VSS[A-Z]?$|^0V$|^GND`)
	reNC   = regexp.MustCompile(`(?i)^(NC|N\.C\.?|NOCONNECT|NO_CONNECT)$`)
	reV1   = regexp.MustCompile(`(?i)(\d+)V(\d+)`)
	reV2   = regexp.MustCompile(`(?i)(^|[^A-Z0-9.])\+?(\d+(\.\d+)?)V([^A-Z0-9]|$|_)`)
	reV3   = regexp.MustCompile(`(?i)^\+?(\d+(\.\d+)?)V`)
	reRail = regexp.MustCompile(`(?i)^\+?(VDD|VCC|VDDA|AVDD|DVDD|VBUS|VIN|VBAT|VREF|VS)([_A-Z0-9]*)$`)
)

func pinRole(name string) string {
	n := strings.ToUpper(strings.TrimSpace(name))
	n = strings.ReplaceAll(n, " ", "")
	switch {
	case n == "":
		return ""
	case reVP.MatchString(n):
		return "v+"
	case reVN.MatchString(n):
		return "v-"
	case reInP.MatchString(n):
		return "in+"
	case reInN.MatchString(n):
		return "in-"
	case reOut.MatchString(n):
		return "out"
	case reLin.MatchString(n):
		return "in"
	}
	return ""
}

func isGround(net string) bool { return net != "" && reGnd.MatchString(net) }
func isNC(net string) bool     { return reNC.MatchString(strings.TrimSpace(net)) }

// railVolts guesses a supply voltage from a net name such as 3V3, +5V, VDD_15V.
func railVolts(net string) (float64, bool) {
	if m := reV1.FindStringSubmatch(net); m != nil {
		v, _ := strconv.ParseFloat(m[1]+"."+m[2], 64)
		return v, true
	}
	if m := reV3.FindStringSubmatch(net); m != nil {
		v, _ := strconv.ParseFloat(m[1], 64)
		return v, true
	}
	if m := reV2.FindStringSubmatch(net); m != nil {
		v, _ := strconv.ParseFloat(m[2], 64)
		return v, true
	}
	return 0, false
}
