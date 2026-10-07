// Package model turns schematic parts into simulation models: it guesses the
// device kind and pin roles, fills parameters from imported datasheets and
// builds a sim.Circuit for the selected sheets.
package model

import (
	"fmt"
	"math"
	"regexp"
	"sort"
	"strconv"
	"strings"

	"icscope/internal/analysis"
	"icscope/internal/datasheet"
	"icscope/internal/netlist"
)

// Param is one model parameter (SI units).
type Param struct {
	Key   string  `json:"key"`
	Label string  `json:"label"`
	Unit  string  `json:"unit"`
	Value float64 `json:"value"`
	Src   string  `json:"src"` // 기본값 / 부품값 / 데이터시트 p.N …
}

// Model is the simulation model of one part.
type Model struct {
	Ref     string         `json:"ref"`
	Value   string         `json:"value"`
	Kind    string         `json:"kind"`
	Gates   int            `json:"gates"`
	Params  []Param        `json:"params"`
	Roles   map[int]string `json:"roles"` // netlist pin index → role(s), comma separated
	Notes   []string       `json:"notes,omitempty"`
	DS      string         `json:"ds,omitempty"`
	User    bool           `json:"user,omitempty"` // edited by the user
	Enabled bool           `json:"enabled"`
}

type pdef struct {
	Key, Label, Unit string
	Def              float64
}

// KindDef describes a model kind for the editor.
type KindDef struct {
	Key    string   `json:"key"`
	Ko     string   `json:"ko"`
	Multi  bool     `json:"multi"` // roles carry a gate/element number
	Roles  []string `json:"roles"` // base role names
	Common []string `json:"common"`
	Params []pdef   `json:"-"`
	PList  []Param  `json:"params"`
}

var Kinds = []*KindDef{
	{Key: "NONE", Ko: "시뮬레이션 제외"},
	{Key: "R", Ko: "저항", Roles: []string{"1", "2"}, Params: []pdef{{"R", "저항", "Ω", 1e3}}},
	{Key: "C", Ko: "커패시터", Roles: []string{"1", "2"}, Params: []pdef{{"C", "정전용량", "F", 1e-9}, {"ESR", "ESR (0=없음)", "Ω", 0}}},
	{Key: "L", Ko: "인덕터", Roles: []string{"1", "2"}, Params: []pdef{{"L", "인덕턴스", "H", 1e-6}, {"Rdc", "직류저항", "Ω", 0.01}}},
	{Key: "BEAD", Ko: "페라이트 비드(저항 근사)", Roles: []string{"1", "2"}, Params: []pdef{{"R", "직류저항", "Ω", 0.1}}},
	{Key: "SHORT", Ko: "단락(퓨즈·0Ω)", Roles: []string{"1", "2"}, Params: []pdef{{"R", "저항", "Ω", 0.001}}},
	{Key: "D", Ko: "다이오드", Multi: true, Roles: []string{"A", "K"}, Params: []pdef{{"Vf", "순방향 전압", "V", 0.7}, {"If", "Vf 측정 전류", "A", 1e-3}, {"N", "이상 계수", "", 1.5}, {"BV", "항복 전압 (0=없음)", "V", 0}, {"Bidir", "양방향 TVS (1/0)", "", 0}}},
	{Key: "NPN", Ko: "NPN 트랜지스터", Multi: true, Roles: []string{"C", "B", "E"}, Params: []pdef{{"Bf", "전류이득 β", "", 200}, {"Is", "포화전류", "A", 1e-14}}},
	{Key: "PNP", Ko: "PNP 트랜지스터", Multi: true, Roles: []string{"C", "B", "E"}, Params: []pdef{{"Bf", "전류이득 β", "", 200}, {"Is", "포화전류", "A", 1e-14}}},
	{Key: "NMOS", Ko: "N채널 MOSFET", Roles: []string{"D", "G", "S"}, Params: []pdef{{"Vth", "게이트 문턱", "V", 2}, {"Rdson", "RDS(on)", "Ω", 0.01}, {"Vgson", "RDS(on) 측정 VGS", "V", 10}, {"Ciss", "Ciss", "F", 0}, {"Coss", "Coss", "F", 0}, {"Crss", "Crss", "F", 0}, {"Vfbd", "바디다이오드 Vf (0=없음)", "V", 0.8}}},
	{Key: "PMOS", Ko: "P채널 MOSFET", Roles: []string{"D", "G", "S"}, Params: []pdef{{"Vth", "게이트 문턱(크기)", "V", 2}, {"Rdson", "RDS(on)", "Ω", 0.05}, {"Vgson", "RDS(on) 측정 |VGS|", "V", 10}, {"Ciss", "Ciss", "F", 0}, {"Coss", "Coss", "F", 0}, {"Crss", "Crss", "F", 0}, {"Vfbd", "바디다이오드 Vf (0=없음)", "V", 0.8}}},
	{Key: "OPAMP", Ko: "연산 증폭기", Multi: true, Roles: []string{"IN+", "IN-", "OUT"}, Common: []string{"V+", "V-"}, Params: []pdef{{"Aol", "개루프 이득", "dB", 110}, {"GBW", "이득 대역폭", "Hz", 1e6}, {"SR", "슬루율", "V/s", 1e6}, {"Vos", "입력 오프셋", "V", 0}, {"Swing", "출력-레일 여유", "V", 0.05}, {"Rout", "출력 저항", "Ω", 50}, {"IQ", "채널당 소비전류", "A", 0}}},
	{Key: "COMP", Ko: "비교기", Multi: true, Roles: []string{"IN+", "IN-", "OUT"}, Common: []string{"V+", "V-"}, Params: []pdef{{"Tpd", "전파 지연", "s", 1e-6}, {"Hyst", "내장 히스테리시스", "V", 0}, {"OpenDrain", "오픈드레인 출력 (1/0)", "", 0}, {"Vos", "입력 오프셋", "V", 0}, {"Rout", "출력 저항", "Ω", 50}}},
	{Key: "INV", Ko: "인버터(슈미트)", Multi: true, Roles: []string{"IN", "OUT"}, Common: []string{"V+", "V-"}, Params: []pdef{{"VTp", "상승 문턱 (전원 비율)", "", 0.58}, {"VTn", "하강 문턱 (전원 비율)", "", 0.38}, {"Tpd", "전파 지연", "s", 15e-9}, {"Rout", "출력 저항", "Ω", 50}}},
	{Key: "BUF", Ko: "버퍼(슈미트)", Multi: true, Roles: []string{"IN", "OUT"}, Common: []string{"V+", "V-"}, Params: []pdef{{"VTp", "상승 문턱 (전원 비율)", "", 0.58}, {"VTn", "하강 문턱 (전원 비율)", "", 0.38}, {"Tpd", "전파 지연", "s", 15e-9}, {"Rout", "출력 저항", "Ω", 50}}},
	{Key: "GATEDRV", Ko: "게이트 드라이버", Multi: true, Roles: []string{"IN", "EN", "OUT"}, Common: []string{"V+", "V-"}, Params: []pdef{{"VIH", "입력 High 문턱", "V", 2.0}, {"VIL", "입력 Low 문턱", "V", 1.2}, {"Tpd", "전파 지연", "s", 20e-9}, {"Rout", "출력 저항", "Ω", 1}}},
	{Key: "CSA", Ko: "전류 감지 증폭기", Roles: []string{"IN+", "IN-", "OUT", "REF"}, Common: []string{"V+", "V-"}, Params: []pdef{{"Gain", "이득", "V/V", 20}, {"BW", "대역폭", "Hz", 400e3}, {"Vos", "입력 오프셋", "V", 0}, {"Swing", "출력-레일 여유", "V", 0.05}, {"Rout", "출력 저항", "Ω", 10}}},
	{Key: "ISOAMP", Ko: "절연 증폭기", Roles: []string{"INP", "INN", "OUTP", "OUTN"}, Common: []string{"V+", "V-"}, Params: []pdef{{"Gain", "차동 이득", "V/V", 8.2}, {"BW", "대역폭", "Hz", 334e3}, {"VCM", "출력 동상 전압", "V", 1.44}, {"Rout", "출력 저항", "Ω", 10}}},
	{Key: "VREF", Ko: "전압 기준/LDO", Roles: []string{"IN", "OUT", "GND"}, Params: []pdef{{"Vout", "출력 전압", "V", 3.0}, {"Dropout", "드롭아웃", "V", 0.05}, {"Rout", "출력 저항", "Ω", 0.1}, {"BW", "응답 대역", "Hz", 100e3}}},
	{Key: "OPTO", Ko: "포토커플러", Multi: true, Roles: []string{"A", "K", "C", "E"}, Params: []pdef{{"CTR", "전류전달비", "%", 100}, {"Vf", "LED 순방향 전압", "V", 1.2}, {"If", "Vf 측정 전류", "A", 10e-3}}},
	{Key: "XFMR", Ko: "변압기/결합 인덕터", Multi: true, Roles: []string{"W+", "W-"}, Params: []pdef{{"L1", "권선1 인덕턴스", "H", 100e-6}, {"L2", "권선2 인덕턴스", "H", 100e-6}, {"L3", "권선3 인덕턴스", "H", 0}, {"L4", "권선4 인덕턴스", "H", 0}, {"k", "결합 계수", "", 0.99}, {"Rdc", "권선 저항", "Ω", 0.01}}},
}

func init() {
	for _, k := range Kinds {
		for _, p := range k.Params {
			k.PList = append(k.PList, Param{Key: p.Key, Label: p.Label, Unit: p.Unit, Value: p.Def, Src: "기본값"})
		}
	}
}

func KindOf(key string) *KindDef {
	for _, k := range Kinds {
		if k.Key == key {
			return k
		}
	}
	return Kinds[0]
}

func (m *Model) P(key string) float64 {
	for _, p := range m.Params {
		if p.Key == key {
			return p.Value
		}
	}
	for _, p := range KindOf(m.Kind).Params {
		if p.Key == key {
			return p.Def
		}
	}
	return 0
}

func (m *Model) Set(key string, v float64, src string) {
	for i := range m.Params {
		if m.Params[i].Key == key {
			m.Params[i].Value, m.Params[i].Src = v, src
			return
		}
	}
}

// SetKind resets parameters to the defaults of a kind.
func (m *Model) SetKind(kind string) {
	m.Kind = kind
	k := KindOf(kind)
	m.Params = append([]Param(nil), k.PList...)
	if m.Gates == 0 {
		m.Gates = 1
	}
}

// ---------------------------------------------------------------- auto model

var (
	reBead    = regexp.MustCompile(`(?i)BLM|BEAD|MPZ|MMZ|\d+R@|601|121SN|FERRITE`)
	reHenry   = regexp.MustCompile(`(?i)^\d+(\.\d+)?\s*[munp]?H$`)
	reSchot   = regexp.MustCompile(`(?i)^(PMEG|BAT|BAS40|BAS70|SS\d|MBR|SK\d|STPS|RB\d|CUS|PMEG)`)
	reSiC     = regexp.MustCompile(`(?i)^(SCS|C3D|C4D|IDH|IDW)`)
	reTVS     = regexp.MustCompile(`(?i)^(SM[ABCF]J|P[46]KE|SMAJ|SMBJ|SMCJ|1\.5KE|PESD|PTVS|ESD|TPD|SMF)`)
	reTVSV    = regexp.MustCompile(`(?i)^(?:SM[ABCF]J|SMAJ|SMBJ|SMCJ|P[46]KE|1\.5KE)(\d+(?:\.\d+)?)|PTVS(\d+)V(\d+)|PESD\d?[A-Z]*(\d+)`)
	reBidir   = regexp.MustCompile(`(?i)\d(CA|C)(L|-|$|,|_)|BIDIR|PESD`)
	reNPN     = regexp.MustCompile(`(?i)^(BC8[45][6-9]|BC547|BC548|MMBT3904|2N3904|2N2222|MMBT2222|PMBT3904|BCX56|BCP56)`)
	rePNP     = regexp.MustCompile(`(?i)^(BC85[6-9]|BC557|MMBT3906|2N3906|2N2907|BCX53|BCP53|PMBT3906)`)
	reDualBJT = regexp.MustCompile(`(?i)^BC8[45]\dB?S|^BC847B?PN|^BC847$`)
	reMOS     = regexp.MustCompile(`(?i)^(2N7002|BSS138|IAUC|IPB|IPD|IPP|IPW|BSC|BSZ|OSG|SI[2-9]\d|AO\d|IRF|IRL|FD[SDPM]|NTD|NVM|DMN|STP|STD|TK\d|RJK|CSD)`)
	rePMOSv   = regexp.MustCompile(`(?i)^(SI23[0-9][13]|AO34|DMP|FDS[69]|IRF9|BSS84|NTR2101)`)
	reDrv     = regexp.MustCompile(`(?i)^(2EDN|1EDN|2EDF|1EDI|UCC27|UCC21|IR21|IR44|MIC44|LM5114|ADuM4)`)
	reRef     = regexp.MustCompile(`(?i)^(REF30|REF31|REF33|REF50|REF60|ADR\d|LM4050|MCP1501|LT6656|TLV7\d{2}P|AP2112|TLV7\d{2}|AMS1117|LP5907|MCP1700|XC6206|LDK|TPS7A)`)
	reOpto    = regexp.MustCompile(`(?i)^(FOD8|PC817|EL817|LTV|ELD2|EL2|TLP\d|HCPL-?[0-9]|CNY17|VO61|SFH6)`)
	reOptoDu  = regexp.MustCompile(`(?i)^(ELD207|EL827|LTV-?827|PC827|TLP\d+-2)`)
	reTriac   = regexp.MustCompile(`(?i)^MOC30`)
	reSchmitt = regexp.MustCompile(`14|40106|1G17|2G17`)
	reCSAgain = regexp.MustCompile(`(?i)INA(240|181|186|185|199|210|211|212|213|214|215|180|190)A?(\d)`)
)

func firstNum(s string) (float64, bool) {
	for _, f := range strings.FieldsFunc(s, func(r rune) bool { return r == ' ' || r == '_' || r == '-' || r == '/' || r == ',' }) {
		if v, ok := netlist.ParseValue(f); ok && regexp.MustCompile(`^\d`).MatchString(f) {
			if strings.ContainsAny(f, "pnuµmkKMGRFHΩ") || regexp.MustCompile(`^\d+(\.\d+)?$`).MatchString(f) {
				return v, true
			}
		}
	}
	return 0, false
}

func valueOf(p *netlist.Part) string {
	v := p.Value
	if v == "" && len(p.Lines) > 0 {
		v = p.Lines[0]
	}
	return v
}

// Auto guesses the model of a part. geo supplies symbol hints (diode
// apex, pin directions) for parts whose pin numbers are not printed.
func Auto(p *netlist.Part, geo *Hints) *Model {
	m := &Model{Ref: p.Ref, Value: valueOf(p), Roles: map[int]string{}, Enabled: true, Gates: 1}
	pre := netlist.Prefix(p.Ref)
	val := strings.ToUpper(strings.TrimSpace(m.Value + " " + strings.Join(p.Lines, " ")))
	tok := strings.Fields(strings.ToUpper(m.Value))
	first := ""
	if len(tok) > 0 {
		first = tok[0]
	}
	two := func() {
		k := 0
		for i := range p.Pins {
			if k < 2 {
				m.Roles[i] = strconv.Itoa(k + 1)
				k++
			}
		}
	}
	setVal := func(key string) {
		if v, ok := firstNum(m.Value + " " + strings.Join(p.Lines, " ")); ok {
			m.Set(key, v, "부품값 "+m.Value)
		} else {
			m.Notes = append(m.Notes, "부품값을 읽지 못해 기본값을 씁니다.")
		}
	}
	switch {
	case pre == "R" || pre == "TH":
		m.SetKind("R")
		setVal("R")
		if m.P("R") < 0.0005 {
			m.SetKind("SHORT")
		}
		two()
	case pre == "RV":
		m.SetKind("NONE")
		m.Notes = append(m.Notes, "배리스터는 시뮬레이션에서 제외(개방).")
	case pre == "C" || pre == "EC" || pre == "CE":
		m.SetKind("C")
		setVal("C")
		two()
	case pre == "F":
		m.SetKind("SHORT")
		two()
	case pre == "L" || pre == "FB":
		switch {
		case len(p.Pins) > 2:
			m.SetKind("NONE")
			m.Notes = append(m.Notes, "4단자 인덕터(공통모드 초크 등) — 필요하면 '변압기/결합 인덕터'로 바꾸고 권선 핀을 지정하세요.")
		case reBead.MatchString(val):
			m.SetKind("BEAD")
			two()
		default:
			m.SetKind("L")
			setVal("L")
			two()
		}
	case pre == "D" || pre == "ZD":
		m.SetKind("D")
		switch {
		case reSiC.MatchString(first):
			m.Set("Vf", 1.4, "기본값(SiC)")
			m.Set("If", 5, "기본값(SiC)")
			m.Set("N", 2, "기본값(SiC)")
		case reSchot.MatchString(first):
			m.Set("Vf", 0.38, "기본값(쇼트키)")
			m.Set("If", 0.1, "기본값(쇼트키)")
			m.Set("N", 1.05, "기본값(쇼트키)")
		}
		if reTVS.MatchString(first) || pre == "ZD" {
			if mm := reTVSV.FindStringSubmatch(first); mm != nil {
				v := 0.0
				switch {
				case mm[1] != "":
					v, _ = strconv.ParseFloat(mm[1], 64)
					v *= 1.11 // VBR(min) ≈ 1.11 × VRWM
				case mm[2] != "":
					v, _ = strconv.ParseFloat(mm[2]+"."+mm[3], 64)
					v *= 1.2
				case mm[4] != "":
					v, _ = strconv.ParseFloat(mm[4], 64)
					v *= 1.1
				}
				if v > 0 {
					m.Set("BV", round3(v), "품번 추정 "+first)
				}
			}
			if reBidir.MatchString(first) {
				m.Set("Bidir", 1, "품번 추정 (CA=양방향)")
			}
		}
		m.diodeRoles(p, geo)
	case pre == "Q":
		m.transistor(p, first, geo)
	case pre == "U" || pre == "IC" || pre == "ISO":
		m.ic(p, first, val)
	case pre == "T":
		m.SetKind("NONE")
		m.Notes = append(m.Notes, "변압기는 권선 정보가 회로도에 없어 제외했습니다. '변압기/결합 인덕터'로 바꾸고 권선 핀·인덕턴스를 지정하면 시뮬레이션됩니다.")
	default:
		m.SetKind("NONE")
	}
	if m.Kind == "NONE" {
		m.Enabled = false
	}
	return m
}

func round3(v float64) float64 { return math.Round(v*1000) / 1000 }

// Hints are drawing-based hints for one part (from the schematic geometry).
type Hints struct {
	// Apex points of diode triangles (cathode side)
	Apex [][2]float64
	// Inner end and direction of each netlist pin index
	Inner map[int][2]float64
	Horiz map[int]bool
}

func (m *Model) diodeRoles(p *netlist.Part, h *Hints) {
	n := len(p.Pins)
	if n == 2 {
		a, k := 0, 1
		if h != nil && len(h.Apex) > 0 {
			ap := h.Apex[0]
			d := func(i int) float64 {
				q, ok := h.Inner[i]
				if !ok {
					return 1e9
				}
				return math.Hypot(q[0]-ap[0], q[1]-ap[1])
			}
			if d(0) < d(1) {
				a, k = 1, 0
			}
			m.Notes = append(m.Notes, "애노드/캐소드는 심볼 삼각형 방향으로 추정했습니다(확인 필요).")
		} else {
			m.Notes = append(m.Notes, "애노드/캐소드를 정하지 못했습니다 — 핀 역할을 확인하세요.")
		}
		m.Roles[a], m.Roles[k] = "A1", "K1"
		return
	}
	// 3-pin arrays by pin number
	num := map[string]int{}
	for i, q := range p.Pins {
		num[q.Num] = i
	}
	set := func(pn, role string) {
		if i, ok := num[pn]; ok {
			m.Roles[i] = role
		}
	}
	v := strings.ToUpper(m.Value)
	switch {
	case strings.HasPrefix(v, "BAV70") || strings.Contains(v, "-05"):
		m.Gates = 2
		set("1", "A1")
		set("2", "A2")
		set("3", "K1,K2")
	case strings.HasPrefix(v, "BAV99") || strings.Contains(v, "-04"):
		m.Gates = 2
		set("1", "A1")
		set("2", "K2")
		set("3", "K1,A2")
	case strings.HasPrefix(v, "BAW56") || strings.Contains(v, "-06"):
		m.Gates = 2
		set("1", "K1")
		set("2", "K2")
		set("3", "A1,A2")
	default:
		m.Enabled = false
		m.Notes = append(m.Notes, "다이오드 어레이의 핀 배치를 모릅니다 — 데이터시트를 가져오거나 핀 역할을 지정하세요.")
	}
}

func (m *Model) transistor(p *netlist.Part, first string, h *Hints) {
	switch {
	case rePNP.MatchString(first):
		m.SetKind("PNP")
	case reNPN.MatchString(first) || reDualBJT.MatchString(first):
		m.SetKind("NPN")
	case reMOS.MatchString(first):
		m.SetKind("NMOS")
		if rePMOSv.MatchString(first) {
			m.SetKind("PMOS")
		}
	default:
		m.SetKind("NONE")
		m.Notes = append(m.Notes, "트랜지스터 종류를 품번으로 정하지 못했습니다.")
		return
	}
	num := map[string]int{}
	numbered := true
	for i, q := range p.Pins {
		num[q.Num] = i
		if q.Num == "?" || q.Num == "" {
			numbered = false
		}
	}
	isMOS := m.Kind == "NMOS" || m.Kind == "PMOS"
	// dual BJT in SOT-363 (BC847BS): 1 E1, 2 B1, 3 C2, 4 E2, 5 B2, 6 C1
	if !isMOS && len(p.Pins) == 6 && numbered {
		m.Gates = 2
		for pn, r := range map[string]string{"1": "E1", "2": "B1", "3": "C2", "4": "E2", "5": "B2", "6": "C1"} {
			if i, ok := num[pn]; ok {
				m.Roles[i] = r
			}
		}
		m.Notes = append(m.Notes, "SOT-363 듀얼 트랜지스터 표준 핀배치(1 E1, 2 B1, 3 C2, 4 E2, 5 B2, 6 C1)를 가정했습니다 — 데이터시트로 확인하세요.")
		return
	}
	suf := ""
	if !isMOS {
		suf = "1"
	}
	// group pins by net: power MOSFETs repeat D and S pins
	groups := map[string][]int{}
	for i, q := range p.Pins {
		groups[q.Net] = append(groups[q.Net], i)
	}
	if isMOS && len(p.Pins) >= 4 && len(groups) == 3 {
		type g struct {
			net string
			idx []int
		}
		var gs []g
		for n, idx := range groups {
			gs = append(gs, g{n, idx})
		}
		sort.Slice(gs, func(i, j int) bool { return len(gs[i].idx) < len(gs[j].idx) })
		roles := []string{"G", "S", "D"}
		for k, gg := range gs {
			for _, i := range gg.idx {
				m.Roles[i] = roles[k]
			}
		}
		m.Notes = append(m.Notes, "핀 수로 G(1핀)·S·D(가장 많은 핀)를 추정했습니다.")
		return
	}
	if len(p.Pins) == 3 && numbered {
		// SOT-23: 1 G/B, 2 S/E, 3 D/C
		for pn, r := range map[string]string{"1": "G", "2": "S", "3": "D"} {
			if !isMOS {
				r = map[string]string{"G": "B", "S": "E", "D": "C"}[r]
			}
			if i, ok := num[pn]; ok {
				m.Roles[i] = r + suf
			}
		}
		m.Notes = append(m.Notes, "SOT-23 표준 핀배치(1 G/B, 2 S/E, 3 D/C)를 가정했습니다.")
		return
	}
	if len(p.Pins) == 3 && h != nil && len(h.Horiz) == 3 {
		// the control pin runs in the other direction than the two power pins
		var hz, vt []int
		for i := 0; i < 3; i++ {
			if h.Horiz[i] {
				hz = append(hz, i)
			} else {
				vt = append(vt, i)
			}
		}
		var gate int
		var others []int
		switch {
		case len(hz) == 1:
			gate, others = hz[0], vt
		case len(vt) == 1:
			gate, others = vt[0], hz
		default:
			m.Notes = append(m.Notes, "핀 방향으로 단자를 정하지 못했습니다 — 핀 역할을 지정하세요.")
			m.Enabled = false
			return
		}
		top, bot := others[0], others[1]
		a, b := h.Inner[top], h.Inner[bot]
		if a[1]+a[0]*1e-6 > b[1]+b[0]*1e-6 {
			top, bot = bot, top
		}
		g, d, s := "G", "D", "S"
		if !isMOS {
			g, d, s = "B"+suf, "C"+suf, "E"+suf
		}
		upper, lower := d, s
		if m.Kind == "PMOS" || m.Kind == "PNP" {
			upper, lower = s, d
		}
		m.Roles[gate], m.Roles[top], m.Roles[bot] = g, upper, lower
		m.Notes = append(m.Notes, "심볼 모양(제어 핀 방향, 위=드레인/컬렉터)으로 단자를 추정했습니다 — 확인하세요.")
		return
	}
	m.Enabled = false
	m.Notes = append(m.Notes, "트랜지스터 단자를 정하지 못했습니다 — 핀 역할을 지정하세요.")
}

func (m *Model) ic(p *netlist.Part, first, val string) {
	cls := analysis.ClassOf(val)
	switch {
	case reTriac.MatchString(first):
		m.SetKind("NONE")
		m.Notes = append(m.Notes, "트라이악 드라이버(MOC30xx)는 모델이 없습니다.")
		return
	case reOpto.MatchString(first):
		m.SetKind("OPTO")
		m.optoRoles(p, first)
		return
	case reDrv.MatchString(first):
		m.SetKind("GATEDRV")
		m.Gates = 2
	case cls == analysis.KOpamp:
		m.SetKind("OPAMP")
	case cls == analysis.KComparator:
		m.SetKind("COMP")
		if strings.Contains(first, "TLV7041") || strings.Contains(first, "TLV7021") || strings.Contains(first, "LM393") || strings.Contains(first, "LM339") || strings.Contains(first, "LM2903") {
			m.Set("OpenDrain", 1, "품번 추정(오픈드레인/컬렉터 출력)")
		}
	case cls == analysis.KInverter:
		m.SetKind("INV")
		if !reSchmitt.MatchString(first) {
			m.Set("VTp", 0.5, "기본값(일반 인버터)")
			m.Set("VTn", 0.49, "기본값(일반 인버터)")
		}
	case cls == analysis.KCSA:
		m.SetKind("CSA")
		if mm := reCSAgain.FindStringSubmatch(first); mm != nil {
			g := map[string]float64{"1": 20, "2": 50, "3": 100, "4": 200}[mm[2]]
			if g > 0 {
				m.Set("Gain", g, "품번 "+first)
			}
		}
	case cls == analysis.KIsoAmp:
		m.SetKind("ISOAMP")
		if strings.Contains(first, "AMC3302") || strings.Contains(first, "AMC1302") {
			m.Set("Gain", 41, "품번 추정(±50 mV 입력형)")
		}
	case reRef.MatchString(first):
		m.SetKind("VREF")
		if mm := regexp.MustCompile(`REF3(\d)(\d\d)`).FindStringSubmatch(first); mm != nil {
			v, _ := strconv.ParseFloat(mm[1]+"."+mm[2], 64)
			if mm[2] == "12" || mm[2] == "25" || mm[2] == "30" || mm[2] == "33" || mm[2] == "40" || mm[2] == "20" {
				v, _ = strconv.ParseFloat(mm[2][:1]+"."+mm[2][1:], 64)
			}
			m.Set("Vout", v, "품번 "+first)
		}
	default:
		m.SetKind("NONE")
		if cls == analysis.KMCU {
			m.Notes = append(m.Notes, "MCU 는 시뮬레이션하지 않습니다. MCU 출력 핀 넷에 신호원(PWM 등)을 지정하세요.")
		} else {
			m.Notes = append(m.Notes, "이 IC 의 동작 모델이 없습니다(제외).")
		}
		return
	}
	m.icRoles(p, cls)
}

func (m *Model) optoRoles(p *netlist.Part, first string) {
	num := map[string]int{}
	for i, q := range p.Pins {
		num[q.Num] = i
	}
	pin := map[string]string{"1": "A1", "2": "K1", "3": "E1", "4": "C1"}
	if reOptoDu.MatchString(first) {
		m.Gates = 2
		pin = map[string]string{"1": "A1", "2": "K1", "3": "A2", "4": "K2", "5": "E2", "6": "C2", "7": "E1", "8": "C1"}
	}
	for pn, r := range pin {
		if i, ok := num[pn]; ok {
			m.Roles[i] = r
		}
	}
	m.Notes = append(m.Notes, "포토커플러 표준 핀배치를 가정했습니다 — 데이터시트 핀 표로 확인하세요.")
}

// icRoles maps IC pins from their names, falling back to standard pinouts.
func (m *Model) icRoles(p *netlist.Part, cls string) {
	byName := func(name string) string {
		n := strings.ToUpper(strings.ReplaceAll(name, " ", ""))
		switch m.Kind {
		case "CSA":
			switch {
			case n == "IN+" || n == "+IN" || n == "INP":
				return "IN+"
			case n == "IN-" || n == "-IN" || n == "INN":
				return "IN-"
			case n == "OUT" || n == "VOUT":
				return "OUT"
			case strings.HasPrefix(n, "REF"):
				return "REF"
			case n == "VS" || n == "VCC" || n == "VDD" || n == "V+":
				return "V+"
			case n == "GND" || n == "V-":
				return "V-"
			}
		case "ISOAMP":
			switch n {
			case "INP", "IN+", "VINP":
				return "INP"
			case "INN", "IN-", "VINN":
				return "INN"
			case "OUTP", "VOUTP":
				return "OUTP"
			case "OUTN", "VOUTN":
				return "OUTN"
			case "VDD", "VDD2", "AVDD":
				return "V+"
			case "GND", "GND2":
				return "V-"
			}
		case "GATEDRV":
			switch n {
			case "INA", "IN_A", "INA+":
				return "IN1"
			case "INB", "IN_B", "INB+":
				return "IN2"
			case "ENA", "EN_A":
				return "EN1"
			case "ENB", "EN_B":
				return "EN2"
			case "OUTA", "OUT_A":
				return "OUT1"
			case "OUTB", "OUT_B":
				return "OUT2"
			case "VDD", "VCC":
				return "V+"
			case "GND", "VSS":
				return "V-"
			}
		case "VREF":
			switch n {
			case "IN", "VIN":
				return "IN"
			case "OUT", "VOUT":
				return "OUT"
			case "GND":
				return "GND"
			}
		}
		switch analysis.PinRole(name) {
		case "v+":
			return "V+"
		case "v-":
			return "V-"
		}
		return ""
	}
	named := false
	for i, q := range p.Pins {
		if r := byName(q.Name); r != "" {
			m.Roles[i] = r
			named = true
		}
	}
	switch m.Kind {
	case "OPAMP", "COMP", "INV", "BUF":
		c := cls
		if m.Kind == "INV" || m.Kind == "BUF" {
			c = analysis.KInverter
		}
		gs := analysis.GatesOf(p, c)
		num := map[string][]int{}
		for i, q := range p.Pins {
			num[q.Num] = append(num[q.Num], i)
		}
		for _, g := range gs {
			n := strconv.Itoa(g.N)
			for _, i := range num[g.InP] {
				if m.Kind == "INV" || m.Kind == "BUF" {
					m.Roles[i] = "IN" + n
				} else {
					m.Roles[i] = "IN+" + n
				}
			}
			for _, i := range num[g.InN] {
				m.Roles[i] = "IN-" + n
			}
			for _, i := range num[g.Out] {
				m.Roles[i] = "OUT" + n
			}
		}
		if len(gs) > 0 {
			m.Gates = len(gs)
		}
		// supplies by standard pinout when unnamed
		pc := 0
		for _, q := range p.Pins {
			if v, err := strconv.Atoi(q.Num); err == nil && v > pc {
				pc = v
			}
		}
		std := map[int][2]string{5: {"5", "2"}, 8: {"8", "4"}, 14: {"4", "11"}}
		if m.Kind == "INV" || m.Kind == "BUF" {
			std = map[int][2]string{5: {"5", "3"}, 6: {"5", "2"}, 14: {"14", "7"}}
		}
		if pc > 8 {
			pc = 14
		} else if pc > 5 && m.Kind != "INV" {
			pc = 8
		}
		if s, ok := std[pc]; ok {
			for _, i := range num[s[0]] {
				if m.Roles[i] == "" {
					m.Roles[i] = "V+"
				}
			}
			for _, i := range num[s[1]] {
				if m.Roles[i] == "" {
					m.Roles[i] = "V-"
				}
			}
		}
		if len(gs) > 0 && gs[0].Source == "pinout" {
			m.Notes = append(m.Notes, fmt.Sprintf("핀 이름이 없어 표준 핀배치(%d핀)로 섹션을 정했습니다.", pc))
		}
	case "VREF":
		if !named {
			num := map[string]int{}
			for i, q := range p.Pins {
				num[q.Num] = i
			}
			for pn, r := range map[string]string{"1": "IN", "2": "OUT", "3": "GND"} {
				if i, ok := num[pn]; ok {
					m.Roles[i] = r
				}
			}
			m.Notes = append(m.Notes, "SOT-23-3 기준전압 표준 핀배치(1 IN, 2 OUT, 3 GND)를 가정했습니다.")
		}
	default:
		if !named {
			m.Enabled = false
			m.Notes = append(m.Notes, "핀 이름이 없어 단자를 정하지 못했습니다 — 데이터시트를 가져오거나 핀 역할을 지정하세요.")
		}
	}
}

// ---------------------------------------------------------------- datasheet

var reNumber = regexp.MustCompile(`[-–−]?\s*\d+(\.\d+)?([eE][-+]?\d+)?`)

func parseNum(s string) (float64, bool) {
	s = strings.ReplaceAll(strings.ReplaceAll(s, "–", "-"), "−", "-")
	m := reNumber.FindString(strings.ReplaceAll(s, "±", ""))
	if m == "" {
		return 0, false
	}
	v, err := strconv.ParseFloat(strings.ReplaceAll(m, " ", ""), 64)
	return v, err == nil
}

var prefixes = map[string]float64{"p": 1e-12, "n": 1e-9, "u": 1e-6, "µ": 1e-6, "μ": 1e-6, "m": 1e-3, "k": 1e3, "K": 1e3, "M": 1e6, "G": 1e9}

// UnitScale converts a datasheet unit into an SI multiplier.
func UnitScale(unit string) (float64, string) {
	u := strings.ReplaceAll(strings.TrimSpace(unit), " ", "")
	switch strings.ToLower(u) {
	case "db":
		return 1, "dB"
	case "%":
		return 1, "%"
	case "v/v", "":
		return 1, ""
	case "v/mv":
		return 1e3, ""
	case "v/µs", "v/us", "v/μs":
		return 1e6, "V/s"
	case "v/ms":
		return 1e3, "V/s"
	case "v/ns":
		return 1e9, "V/s"
	}
	for _, base := range []string{"Hz", "V", "A", "s", "Ω", "F", "W", "ohm"} {
		if strings.HasSuffix(u, base) {
			pre := strings.TrimSuffix(u, base)
			if pre == "" {
				return 1, base
			}
			if f, ok := prefixes[pre]; ok {
				return f, base
			}
		}
	}
	return 1, u
}

func specVal(s datasheet.Spec, prefer string) (float64, bool) {
	order := []string{s.Typ, s.Min, s.Max}
	switch prefer {
	case "min":
		order = []string{s.Min, s.Typ, s.Max}
	case "max":
		order = []string{s.Max, s.Typ, s.Min}
	}
	for _, x := range order {
		if v, ok := parseNum(x); ok {
			f, _ := UnitScale(s.Unit)
			return v * f, true
		}
	}
	return 0, false
}

// ApplyDatasheet fills model parameters from a datasheet's key specs and
// pin names from its pin table. It returns a list of what was applied.
func (m *Model) ApplyDatasheet(d *datasheet.Datasheet, p *netlist.Part) []string {
	var log []string
	m.DS = d.File
	get := func(key string) (datasheet.Spec, bool) {
		for _, s := range d.Specs {
			if s.Key == key {
				return s, true
			}
		}
		return datasheet.Spec{}, false
	}
	set := func(param, key, prefer string, conv func(float64, datasheet.Spec) float64) {
		s, ok := get(key)
		if !ok {
			return
		}
		v, ok := specVal(s, prefer)
		if !ok {
			return
		}
		if conv != nil {
			v = conv(v, s)
		}
		if math.IsNaN(v) || v == 0 && param != "Vos" {
			return
		}
		src := fmt.Sprintf("데이터시트 p.%d %s", s.Page, s.Param)
		m.Set(param, v, src)
		log = append(log, fmt.Sprintf("%s = %g (%s)", param, v, src))
	}
	abs := func(v float64, _ datasheet.Spec) float64 { return math.Abs(v) }
	switch m.Kind {
	case "OPAMP":
		set("Aol", "aol", "typ", func(v float64, s datasheet.Spec) float64 {
			if _, u := UnitScale(s.Unit); u != "dB" {
				return 20 * math.Log10(math.Abs(v))
			}
			return v
		})
		set("GBW", "gbw", "typ", nil)
		set("SR", "sr", "typ", abs)
		set("Vos", "vos", "typ", nil)
	case "COMP":
		set("Tpd", "tpd", "typ", nil)
		set("Hyst", "vhys", "typ", abs)
		set("Vos", "vos", "typ", nil)
		t := strings.ToLower(d.Title + " " + d.Text)
		if strings.Contains(t, "open-drain") || strings.Contains(t, "open drain") || strings.Contains(t, "open-collector") || strings.Contains(t, "open collector") {
			if !strings.Contains(t, "push-pull") || strings.Index(t, "open") < strings.Index(t, "push-pull") {
				m.Set("OpenDrain", 1, "데이터시트 본문(open-drain)")
				log = append(log, "OpenDrain = 1 (데이터시트 본문)")
			}
		} else if strings.Contains(t, "push-pull") {
			m.Set("OpenDrain", 0, "데이터시트 본문(push-pull)")
			log = append(log, "OpenDrain = 0 (push-pull)")
		}
	case "INV", "BUF":
		// thresholds are given at several VCC; use the ratio at the test supply
		for _, k := range []string{"vtp", "vtn"} {
			s, ok := get(k)
			if !ok {
				continue
			}
			v, ok := specVal(s, "typ")
			vcc := 0.0
			if mm := regexp.MustCompile(`(\d+(\.\d+)?)\s*V`).FindStringSubmatch(s.Cond); mm != nil {
				vcc, _ = strconv.ParseFloat(mm[1], 64)
			}
			if ok && vcc > 0 && v < vcc {
				key := map[string]string{"vtp": "VTp", "vtn": "VTn"}[k]
				src := fmt.Sprintf("데이터시트 p.%d %s (VCC=%gV 에서 %gV)", s.Page, s.Param, vcc, v)
				m.Set(key, round3(v/vcc), src)
				log = append(log, fmt.Sprintf("%s = %.3g×VCC (%s)", key, v/vcc, src))
			}
		}
		set("Tpd", "tpd", "typ", nil)
	case "GATEDRV":
		set("VIH", "vtp", "typ", nil)
		if _, ok := get("vtp"); !ok {
			set("VIH", "vt", "typ", nil)
		}
		set("VIL", "vtn", "typ", nil)
		set("Tpd", "tpd", "typ", nil)
	case "CSA":
		if s, ok := get("gain"); ok {
			g, ok := specVal(s, "typ")
			up := strings.ToUpper(m.Value)
			for _, v := range append([]string{s.Cond + ": " + s.Typ}, s.Variants...) {
				// variants look like "INA240A2: / 50 / V/V"
				if i := strings.Index(v, ":"); i > 0 && strings.Contains(up, strings.TrimSpace(strings.ToUpper(v[:i]))) {
					if x, ok2 := parseNum(strings.Trim(v[i+1:], " /")); ok2 {
						g, ok = x, true
					}
				}
			}
			if ok && g > 0 {
				m.Set("Gain", g, fmt.Sprintf("데이터시트 p.%d %s", s.Page, s.Param))
				log = append(log, fmt.Sprintf("Gain = %g", g))
			}
		}
		set("BW", "bw", "typ", nil)
		set("Vos", "vos", "typ", nil)
	case "ISOAMP":
		set("Gain", "gain", "typ", nil)
		set("BW", "bw", "typ", nil)
		set("VCM", "vcmout", "typ", nil)
	case "VREF":
		set("Vout", "vout", "typ", nil)
	case "D":
		set("Vf", "vf", "typ", nil)
		if s, ok := get("vf"); ok {
			if mm := regexp.MustCompile(`(?i)I\s*F\s*=\s*(\d+(\.\d+)?)\s*(m|µ|u)?A`).FindStringSubmatch(s.Cond + " " + s.Param); mm != nil {
				v, _ := strconv.ParseFloat(mm[1], 64)
				v *= map[string]float64{"": 1, "m": 1e-3, "µ": 1e-6, "u": 1e-6}[mm[3]]
				m.Set("If", v, fmt.Sprintf("데이터시트 p.%d 조건", s.Page))
				log = append(log, fmt.Sprintf("If = %g A", v))
			}
		}
		set("BV", "vbr", "min", abs)
	case "NMOS", "PMOS":
		set("Vth", "vgsth", "typ", abs)
		if s, ok := get("rdson"); ok {
			best, okb := specVal(s, "typ")
			for _, v := range s.Variants { // pick the lowest typical (highest VGS)
				parts := strings.Split(v, "/")
				if len(parts) >= 2 {
					if x, ok := parseNum(parts[1]); ok {
						f, _ := UnitScale(s.Unit)
						if x*f < best || !okb {
							best, okb = x*f, true
						}
					}
				}
			}
			if okb && best > 0 {
				m.Set("Rdson", best, fmt.Sprintf("데이터시트 p.%d %s", s.Page, s.Param))
				log = append(log, fmt.Sprintf("Rdson = %g Ω", best))
			}
		}
		set("Vfbd", "vf", "typ", abs)
	case "OPTO":
		set("CTR", "ctr", "min", nil)
		set("Vf", "vf", "typ", nil)
	}
	// pin names from the datasheet pin table by pin number
	if len(d.Pins) > 0 && p != nil {
		names := map[string]string{}
		for _, dp := range d.Pins {
			if dp.Num != "" {
				names[dp.Num] = dp.Name
			}
			for _, n := range dp.Nums {
				if _, ok := names[n]; !ok {
					names[n] = dp.Name
				}
			}
		}
		k := 0
		for i := range p.Pins {
			if p.Pins[i].Name == "" {
				if nm, ok := names[p.Pins[i].Num]; ok {
					p.Pins[i].Name = nm
					k++
				}
			}
		}
		if k > 0 {
			log = append(log, fmt.Sprintf("핀 이름 %d개를 데이터시트 핀 표에서 채움", k))
			if m.Kind != "D" && m.Kind != "NPN" && m.Kind != "PNP" && m.Kind != "NMOS" && m.Kind != "PMOS" && m.Kind != "OPTO" {
				old := m.Roles
				m.Roles = map[int]string{}
				m.icRoles(p, analysis.ClassOf(m.Value))
				if len(m.Roles) == 0 {
					m.Roles = old
				}
			}
		}
	}
	if len(log) == 0 {
		log = append(log, "데이터시트에서 이 모델에 쓸 사양을 찾지 못했습니다.")
	}
	return log
}
