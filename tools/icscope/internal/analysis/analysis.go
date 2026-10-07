// Package analysis finds op-amp, comparator and inverter circuits in a
// netlist, identifies their topology and suggests IC or MCU replacements.
package analysis

import (
	"fmt"
	"math"
	"regexp"
	"sort"
	"strings"

	"icscope/internal/datasheet"
	"icscope/internal/netlist"
)

// NetView describes one gate pin and what is attached to its net.
type NetView struct {
	Role    string   `json:"role"`
	Pin     string   `json:"pin"`
	Net     string   `json:"net"`
	Members []string `json:"members"`
}

type DSRef struct {
	File  string           `json:"file"`
	Title string           `json:"title"`
	Specs []datasheet.Spec `json:"specs"`
}

type Finding struct {
	Ref      string    `json:"ref"`
	Value    string    `json:"value"`
	Class    string    `json:"class"`
	ClassKo  string    `json:"classKo"`
	Page     string    `json:"page,omitempty"`
	Gate     int       `json:"gate"`
	Gates    int       `json:"gates"`
	PinSrc   string    `json:"pinSrc"`
	Topology string    `json:"topology"`
	TopoKo   string    `json:"topoKo"`
	Gain     string    `json:"gain,omitempty"`
	Calc     []string  `json:"calc,omitempty"`
	Nets     []NetView `json:"nets"`
	Suggest  []string  `json:"suggest,omitempty"`
	Warn     []string  `json:"warn,omitempty"`
	DS       *DSRef    `json:"ds,omitempty"`
}

type Report struct {
	Source   string    `json:"source"`
	Kind     string    `json:"kind"`
	Parts    int       `json:"parts"`
	Nets     int       `json:"nets"`
	Findings []Finding `json:"findings"`
	Others   []string  `json:"others,omitempty"` // CSA / iso-amp / MCU present
	Notes    []string  `json:"notes,omitempty"`
}

type an struct {
	nl   *netlist.Netlist
	ds   []*datasheet.Datasheet
	mcus map[string]bool
	csa  []*netlist.Part
}

// Analyze runs the circuit recognition over a netlist. Datasheets already
// imported are matched by part number for cross-checks.
func Analyze(nl *netlist.Netlist, ds []*datasheet.Datasheet) *Report {
	a := &an{nl: nl, ds: ds, mcus: map[string]bool{}}
	rep := &Report{Source: nl.Source, Kind: nl.Kind, Parts: len(nl.Parts), Nets: len(nl.Nets), Notes: append([]string{}, nl.Notes...)}
	refs := make([]string, 0, len(nl.Parts))
	for r := range nl.Parts {
		refs = append(refs, r)
	}
	sort.Slice(refs, func(i, j int) bool { return netlist.RefLess(refs[i], refs[j]) })
	cls := map[string]string{}
	for _, r := range refs {
		p := nl.Parts[r]
		c := partClass(p)
		cls[r] = c
		switch c {
		case KMCU:
			a.mcus[r] = true
			rep.Others = append(rep.Others, fmt.Sprintf("%s %s (MCU)", r, p.Value))
		case KCSA, KIsoAmp:
			a.csa = append(a.csa, p)
			rep.Others = append(rep.Others, fmt.Sprintf("%s %s (%s)", r, p.Value, ClassKo[c]))
		}
	}
	for _, r := range refs {
		c := cls[r]
		if c != KOpamp && c != KComparator && c != KInverter {
			continue
		}
		p := nl.Parts[r]
		if nl.Kind == "text" {
			rep.Findings = append(rep.Findings, Finding{Ref: r, Value: p.Value, Class: c, ClassKo: ClassKo[c], Page: p.Page,
				Topology: "nonet", TopoKo: "연결 정보 없음 (부품 목록만)", Suggest: []string{genericHint[c]}})
			continue
		}
		gs := gatesOf(p, c)
		if len(gs) == 0 {
			rep.Findings = append(rep.Findings, Finding{Ref: r, Value: p.Value, Class: c, ClassKo: ClassKo[c], Page: p.Page,
				Topology: "unknown", TopoKo: "핀 역할 불명", Warn: []string{"핀 이름/핀 수로 입력·출력 핀을 정하지 못했습니다."}})
			continue
		}
		for _, g := range gs {
			f := a.gate(p, c, g)
			f.Gates = len(gs)
			rep.Findings = append(rep.Findings, f)
		}
	}
	rep.Notes = append(rep.Notes, a.globalChecks()...)
	return rep
}

var genericHint = map[string]string{
	KOpamp:      "회로 형태 판정에는 연결 정보가 필요합니다(OrCAD 넷리스트 또는 OrCAD 색상 PDF). 일반 대안: 션트 차동증폭 → 전류감지 증폭기 IC, ADC 앞 버퍼 → 분압 직결 또는 MCU 내장 OPAMP, 개루프 비교 용도 → MCU 내장 COMP.",
	KComparator: "회로 형태 판정에는 연결 정보가 필요합니다. 일반 대안: 출력이 MCU 로 가면 MCU 내장 비교기(+내부 DAC 문턱), 아니면 내장 히스테리시스 비교기.",
	KInverter:   "회로 형태 판정에는 연결 정보가 필요합니다. 일반 대안: MCU 가 구동/수신하는 신호면 GPIO·타이머 극성 설정으로 삭제, 레벨 변환·구동 목적이면 유지.",
}

// ---- netlist helpers ----

type conn struct {
	p     *netlist.Part
	pin   string
	other string // other net for 2-terminal parts
}

func (a *an) on(net string) []conn {
	var out []conn
	if net == "" {
		return nil
	}
	for _, n := range a.nl.Nets[net] {
		p := a.nl.Parts[n.Ref]
		if p == nil {
			continue
		}
		out = append(out, conn{p, n.Num, p.Other(net)})
	}
	return out
}

func kindOf(p *netlist.Part) byte {
	if len(p.Pins) != 2 {
		return 0
	}
	switch netlist.Prefix(p.Ref) {
	case "R", "RS", "RN":
		return 'R'
	case "C", "EC", "CE":
		return 'C'
	case "L", "FB":
		return 'L'
	case "D", "ZD":
		return 'D'
	}
	return 0
}

var reValTok = regexp.MustCompile(`^\d+(\.\d+)?([pnuµμmkKMGR]\d*)?(Ω|OHM|R|F|H)?[FJGDK]?$`)
var reHasUnit = regexp.MustCompile(`[pnuµμmkKMGRΩFH]`)
var reValGlued = regexp.MustCompile(`^(\d+(?:\.\d+)?[pnuµμmkKMGR]?\d*[FHΩ]?)(RESC|CAPC|CAPAE|INDC|IND|RES|CAP|SMD|DIOM|SOD|MPX|BEAD)`)

// val reads a component value such as "51.1KF", "100nF", "4K7" or the
// "2mR" inside "HoLR2512-3W-2mR-1%".
func val(p *netlist.Part) (float64, bool) {
	for _, s := range append([]string{p.Value}, p.Lines...) {
		toks := strings.FieldsFunc(s, func(r rune) bool { return r == ' ' || r == '-' || r == '_' || r == '/' || r == ',' })
		for _, t := range toks {
			if reValTok.MatchString(t) && reHasUnit.MatchString(t) {
				return netlist.ParseValue(t)
			}
		}
		if t := strings.TrimSpace(s); reValTok.MatchString(t) {
			return netlist.ParseValue(t)
		}
		// value glued to a footprint name in PDF text, e.g. "51.1KFRESC1608"
		if m := reValGlued.FindStringSubmatch(strings.TrimSpace(s)); m != nil {
			return netlist.ParseValue(m[1])
		}
	}
	return 0, false
}

func (a *an) desc(c conn, net string) string {
	p := c.p
	v := p.Value
	if v == "" && len(p.Lines) > 0 {
		v = p.Lines[0]
	}
	if k := kindOf(p); k != 0 {
		o := c.other
		if o == "" {
			o = "(미연결)"
		}
		return fmt.Sprintf("%s %s → %s", p.Ref, v, o)
	}
	nm := ""
	for _, q := range p.Pins {
		if q.Num == c.pin && q.Name != "" && q.Name != q.Num {
			nm = "(" + q.Name + ")"
		}
	}
	extra := ""
	if a.mcus[p.Ref] {
		extra = mcuFuncs(p, c.pin)
	}
	return fmt.Sprintf("%s.%s%s %s%s", p.Ref, c.pin, nm, v, extra)
}

func mcuFuncs(p *netlist.Part, pin string) string {
	v := strings.ToUpper(p.Value + p.PartName)
	if !strings.Contains(v, "STM32G47") && !strings.Contains(v, "STM32G48") {
		return ""
	}
	for _, q := range p.Pins {
		if q.Num == pin {
			if f, ok := stm32g474Analog[strings.ToUpper(q.Name)]; ok {
				return " [" + f + "]"
			}
		}
	}
	return ""
}

func (a *an) view(role, pin, net string, self *netlist.Part) NetView {
	nv := NetView{Role: role, Pin: pin, Net: net}
	if net == "" {
		nv.Net = "(미연결)"
		return nv
	}
	if isNC(net) || isGround(net) || len(a.nl.Nets[net]) > 40 {
		nv.Members = []string{fmt.Sprintf("(%d개 핀 — 목록 생략)", len(a.nl.Nets[net]))}
		return nv
	}
	for _, c := range a.on(net) {
		if c.p == self && c.pin == pin {
			continue
		}
		nv.Members = append(nv.Members, a.desc(c, net))
	}
	return nv
}

// chain follows resistors in series from net through r and returns the
// total resistance, the far-end net and the parts passed.
func (a *an) chain(net string, r conn) (float64, string, []string) {
	total := 0.0
	cur := net
	c := r
	var refs []string
	for i := 0; i < 8; i++ {
		v, ok := val(c.p)
		if !ok {
			return math.NaN(), c.other, append(refs, c.p.Ref)
		}
		total += v
		refs = append(refs, c.p.Ref)
		nxt := c.other
		ms := a.on(nxt)
		if len(ms) != 2 || nxt == "" || isGround(nxt) {
			return total, nxt, refs
		}
		var next *conn
		for k := range ms {
			if ms[k].p != c.p {
				next = &ms[k]
			}
		}
		if next == nil || kindOf(next.p) != 'R' {
			return total, nxt, refs
		}
		cur = nxt
		c = *next
		_ = cur
	}
	return total, c.other, refs
}

type rlink struct {
	r    float64
	to   string
	refs []string
}

func (a *an) resistors(net string, skip map[string]bool) []rlink {
	var out []rlink
	for _, c := range a.on(net) {
		if kindOf(c.p) != 'R' || skip[c.p.Ref] {
			continue
		}
		r, to, refs := a.chain(net, c)
		out = append(out, rlink{r, to, refs})
	}
	return out
}

func (a *an) caps(net string) []conn {
	var out []conn
	for _, c := range a.on(net) {
		if kindOf(c.p) == 'C' {
			out = append(out, c)
		}
	}
	return out
}

func par(rs ...float64) float64 {
	s := 0.0
	for _, r := range rs {
		if r > 0 {
			s += 1 / r
		}
	}
	if s == 0 {
		return 0
	}
	return 1 / s
}

func ohm(v float64) string {
	if math.IsNaN(v) {
		return "?"
	}
	return netlist.SI(v, "Ω")
}

// otherMembers counts connections on net other than the listed pins of self.
func (a *an) otherMembers(net string, self *netlist.Part, pins ...string) int {
	n := 0
	for _, c := range a.on(net) {
		mine := false
		if c.p == self {
			for _, q := range pins {
				if q == c.pin {
					mine = true
				}
			}
		}
		if !mine {
			n++
		}
	}
	return n
}

func isRail(net string) bool {
	if _, ok := railVolts(net); ok {
		return true
	}
	return reRail.MatchString(net)
}

// railOf resolves a supply net, following a series resistor (<= 100 Ω),
// inductor or ferrite bead to a named rail.
func (a *an) railOf(net string) (string, float64, bool) {
	if v, ok := railVolts(net); ok {
		return net, v, true
	}
	for _, c := range a.on(net) {
		k := kindOf(c.p)
		if k == 'L' || k == 'R' {
			if r, ok := val(c.p); k == 'R' && (!ok || r > 100) {
				continue
			}
			if v, ok := railVolts(c.other); ok {
				return c.other, v, true
			}
		}
	}
	return net, 0, false
}

// reach collects the MCU pins on net and on nets one or two series
// resistors (<= 1 kΩ) away, without crossing rails, ground or NC nets.
func (a *an) reach(net string, skip map[string]bool) []string {
	var out []string
	seen := map[string]bool{net: true}
	frontier := []string{net}
	for depth := 0; depth < 3 && len(frontier) > 0; depth++ {
		var next []string
		for _, n := range frontier {
			out = append(out, a.mcuPins(n)...)
			for _, c := range a.on(n) {
				if skip[c.p.Ref] || seen[c.other] || c.other == "" {
					continue
				}
				k := kindOf(c.p)
				if k != 'R' && k != 'L' {
					continue
				}
				if r, ok := val(c.p); k == 'R' && (!ok || r > 1000) {
					continue
				}
				if isGround(c.other) || isRail(c.other) || isNC(c.other) {
					continue
				}
				seen[c.other] = true
				next = append(next, c.other)
			}
		}
		frontier = next
	}
	return uniq(out)
}

func (a *an) fixedLevel(net string) bool {
	if net == "" || isNC(net) || isGround(net) {
		return true
	}
	if _, ok := railVolts(net); ok {
		return true
	}
	return false
}

func (a *an) mcuPins(net string) []string {
	var out []string
	if isNC(net) {
		return nil
	}
	for _, c := range a.on(net) {
		if a.mcus[c.p.Ref] {
			out = append(out, a.desc(c, net))
		}
	}
	return out
}

// downstream follows the output through one series resistor and reports
// the MCU pins reached, the output filters and other drivers of the node.
func (a *an) downstream(out string, self *netlist.Part, skip map[string]bool) (string, []string, []string) {
	var path []string
	var calc []string
	mcu := a.reach(out, skip)
	if isNC(out) {
		return "", nil, nil
	}
	for _, c := range a.on(out) {
		if c.p == self || skip[c.p.Ref] || kindOf(c.p) != 'R' {
			continue
		}
		y := c.other
		if y == "" || isGround(y) || isRail(y) || isNC(y) {
			continue
		}
		r, _ := val(c.p)
		path = append(path, fmt.Sprintf("%s %s → %s", c.p.Ref, c.p.Value, y))
		for _, cc := range a.caps(y) {
			if isGround(cc.other) {
				cv, ok := val(cc.p)
				if ok && r > 0 {
					calc = append(calc, fmt.Sprintf("출력 RC 필터 %s·%s: fc = 1/(2π·%s·%s) = %s", c.p.Ref, cc.p.Ref, ohm(r), netlist.SI(cv, "F"), netlist.SI(1/(2*math.Pi*r*cv), "Hz")))
				}
			}
		}
		// another active output driving the same ADC node directly or through a resistor
		if len(a.reach(y, nil)) == 0 {
			continue
		}
		for _, d := range a.on(y) {
			if d.p == c.p {
				continue
			}
			if kindOf(d.p) == 0 && d.p != self && pinRole(pinName(d.p, d.pin)) == "out" {
				calc = append(calc, fmt.Sprintf("⚠ %s 노드를 %s.%s 출력도 직접 구동", y, d.p.Ref, d.pin))
			}
			if kindOf(d.p) == 'R' && d.other != "" && d.other != out {
				for _, e := range a.on(d.other) {
					if kindOf(e.p) == 0 && e.p != self && pinRole(pinName(e.p, e.pin)) == "out" {
						calc = append(calc, fmt.Sprintf("⚠ %s 노드를 %s %s 출력(%s.%s)도 %s 를 거쳐 구동 → 이중 드라이버", y, e.p.Ref, e.p.Value, e.p.Ref, e.pin, d.p.Ref))
					}
				}
			}
		}
	}
	return strings.Join(path, ", "), mcu, calc
}

func pinName(p *netlist.Part, num string) string {
	for _, q := range p.Pins {
		if q.Num == num {
			return q.Name
		}
	}
	return ""
}

// ---- gate analysis ----

func (a *an) gate(p *netlist.Part, class string, g Gate) Finding {
	f := Finding{Ref: p.Ref, Value: p.Value, Class: class, ClassKo: ClassKo[class], Page: p.Page, Gate: g.N, PinSrc: g.Source}
	if f.Value == "" && len(p.Lines) > 0 {
		f.Value = p.Lines[0]
	}
	P, N, O := p.PinNet(g.InP), p.PinNet(g.InN), p.PinNet(g.Out)
	if class == KInverter {
		f.Nets = []NetView{a.view("IN", g.InP, P, p), a.view("OUT", g.Out, O, p)}
		a.inverter(p, &f, P, O)
	} else {
		f.Nets = []NetView{a.view("IN+", g.InP, P, p), a.view("IN−", g.InN, N, p), a.view("OUT", g.Out, O, p)}
		a.amp(p, class, &f, P, N, O)
	}
	// supply pins
	var vp, vn string
	for _, q := range p.Pins {
		switch pinRole(q.Name) {
		case "v+":
			vp = q.Net
		case "v-":
			vn = q.Net
		}
	}
	if vp != "" || vn != "" {
		if r, _, ok := a.railOf(vp); ok && r != vp {
			vp = vp + "→" + r
		}
		f.Nets = append(f.Nets, NetView{Role: "전원", Net: strings.TrimSpace(vp + " / " + vn)})
	}
	a.datasheet(p, &f, vp, vn)
	return f
}

func (a *an) amp(p *netlist.Part, class string, f *Finding, P, N, O string) {
	// Unused section: no signal reaches either input or the output.
	gp := []string{f.Nets[0].Pin, f.Nets[1].Pin, f.Nets[2].Pin}
	oUsed := a.otherMembers(O, p, gp...) > 0 && O != N && O != P
	pFloat := P == "" || a.otherMembers(P, p, gp...) == 0
	nFloat := N == "" || a.otherMembers(N, p, gp...) == 0
	if !oUsed && (a.fixedLevel(P) || pFloat) && (a.fixedLevel(N) || nFloat || N == O) {
		f.Topology, f.TopoKo = "unused", "미사용 섹션"
		if pFloat || isNC(P) {
			f.Warn = append(f.Warn, "IN+ 가 부유(미연결/NC)입니다. 미사용 섹션은 팔로워(OUT–IN−) + IN+ 를 공통모드 범위 안의 고정 전위(예: 중간 전위)에 연결하는 것이 일반 권장입니다.")
		}
		if nFloat && N != O {
			f.Warn = append(f.Warn, "IN− 가 부유입니다.")
		}
		f.Suggest = append(f.Suggest, "다른 섹션만 쓰면 단일 채널 품번으로 바꾸거나, 다른 섹션도 대체되면 IC 삭제.")
		return
	}
	if pFloat {
		f.Warn = append(f.Warn, "IN+ 넷에 다른 연결이 없습니다(부유 입력).")
	}
	if nFloat && N != O {
		f.Warn = append(f.Warn, "IN− 넷에 다른 연결이 없습니다(부유 입력).")
	}
	skip := map[string]bool{}
	// feedback elements between OUT and IN-, OUT and IN+
	var rf, cf, rpos []conn
	for _, c := range a.on(N) {
		if c.p == p {
			continue
		}
		if c.other == O && O != "" {
			switch kindOf(c.p) {
			case 'R':
				rf = append(rf, c)
			case 'C':
				cf = append(cf, c)
			}
		}
	}
	for _, c := range a.on(P) {
		if c.p != p && c.other == O && O != "" && kindOf(c.p) == 'R' {
			rpos = append(rpos, c)
		}
	}
	for _, c := range append(append(rf, cf...), rpos...) {
		skip[c.p.Ref] = true
	}
	direct := O != "" && O == N
	negFB := direct || len(rf) > 0 || len(cf) > 0
	outPath, mcu, dcalc := a.downstream(O, p, skip)

	if !negFB || class == KComparator && !direct && len(rf) == 0 {
		a.comparator(p, f, P, N, O, rpos, mcu)
		if class == KOpamp && a.nl.Kind == "pdf" {
			f.Warn = append(f.Warn, "PDF 에서 복원한 넷리스트라 귀환 저항·커패시터의 핀이 누락됐을 수 있습니다. 회로도에서 OUT–IN− 사이 소자를 확인하세요.")
		}
		f.Calc = append(f.Calc, dcalc...)
		return
	}
	pR := a.resistors(P, skip)
	nR := a.resistors(N, skip)
	var rfv float64 = math.NaN()
	if len(rf) == 1 {
		rfv, _ = val(rf[0].p)
	}
	pole := func() {
		if len(cf) == 1 && len(rf) == 1 {
			c, _ := val(cf[0].p)
			if c > 0 && rfv > 0 {
				f.Calc = append(f.Calc, fmt.Sprintf("피드백 극 %s∥%s: fp = 1/(2π·%s·%s) = %s", rf[0].p.Ref, cf[0].p.Ref, ohm(rfv), netlist.SI(c, "F"), netlist.SI(1/(2*math.Pi*rfv*c), "Hz")))
			}
		}
	}
	switch {
	case direct:
		f.Topology, f.TopoKo, f.Gain = "follower", "전압 팔로워(버퍼)", "1"
		a.follower(p, f, P, pR, mcu, outPath)
	case len(nR) == 0 && len(rf) > 0:
		f.Topology, f.TopoKo, f.Gain = "follower", "팔로워(피드백 저항 있음)", "1"
		a.follower(p, f, P, pR, mcu, outPath)
	default:
		var rgGnd, rgSig []rlink
		for _, l := range nR {
			if isGround(l.to) || a.fixedLevel(l.to) {
				rgGnd = append(rgGnd, l)
			} else {
				rgSig = append(rgSig, l)
			}
		}
		var pSig, pRef []rlink
		for _, l := range pR {
			if isGround(l.to) || a.fixedLevel(l.to) {
				pRef = append(pRef, l)
			} else {
				pSig = append(pSig, l)
			}
		}
		pFixed := a.fixedLevel(P)
		if len(rgSig) > 0 && len(pSig) == 0 && len(pRef) >= 2 {
			// one input of the difference amplifier sits on ground: the IN+
			// resistor matching Rg is the input, the one matching Rf the reference
			rg := rgSig[0].r
			bi := 0
			for i, l := range pRef {
				if math.Abs(math.Log(l.r/rg)) < math.Abs(math.Log(pRef[bi].r/rg)) {
					bi = i
				}
			}
			pSig = []rlink{pRef[bi]}
			pRef = append(append([]rlink{}, pRef[:bi]...), pRef[bi+1:]...)
		}
		switch {
		case len(rgSig) > 0 && len(pSig) > 0:
			f.Topology, f.TopoKo = "difference", "차동 증폭기"
			rg := rgSig[0].r
			f.Gain = gainStr(rfv / rg)
			f.Calc = append(f.Calc, fmt.Sprintf("이득 = Rf/Rg = %s/%s = %s V/V (%s, %s)", ohm(rfv), ohm(rg), fmtF(rfv/rg), names(rf), strings.Join(rgSig[0].refs, "+")))
			if len(pRef) > 0 {
				rp, rq := pSig[0].r, pRef[0].r
				gp := rq / rp
				f.Calc = append(f.Calc, fmt.Sprintf("IN+ 측 분압비 = %s/%s = %s (%s, %s)", ohm(rq), ohm(rp), fmtF(gp), strings.Join(pRef[0].refs, "+"), strings.Join(pSig[0].refs, "+")))
				if math.Abs(gp-rfv/rg)/(rfv/rg) > 0.01 {
					f.Warn = append(f.Warn, fmt.Sprintf("IN− 측 이득 %s 와 IN+ 측 분압비 %s 가 다릅니다 → 공통모드 제거 저하·이득 오차.", fmtF(rfv/rg), fmtF(gp)))
				}
			}
			a.shunt(p, f, rgSig[0].to, pSig[0].to, rfv/rg)
		case len(rgSig) > 0:
			f.Topology, f.TopoKo = "inverting", "반전 증폭기"
			rg := rgSig[0].r
			f.Gain = gainStr(-rfv / rg)
			f.Calc = append(f.Calc, fmt.Sprintf("이득 = −Rf/Rg = −%s/%s = %s V/V", ohm(rfv), ohm(rg), fmtF(-rfv/rg)))
			if !pFixed && len(pSig) == 0 {
				f.Calc = append(f.Calc, "IN+ 기준: "+P)
			}
		case len(rgGnd) > 0:
			f.Topology, f.TopoKo = "noninverting", "비반전 증폭기"
			rg := rgGnd[0].r
			f.Gain = gainStr(1 + rfv/rg)
			f.Calc = append(f.Calc, fmt.Sprintf("이득 = 1 + Rf/Rg = 1 + %s/%s = %s V/V", ohm(rfv), ohm(rg), fmtF(1+rfv/rg)))
		default:
			if len(cf) > 0 && len(rf) == 0 {
				f.Topology, f.TopoKo = "integrator", "적분기/보상 회로"
			} else {
				f.Topology, f.TopoKo = "other", "기타 귀환 회로"
			}
		}
		pole()
		if f.Topology == "inverting" || f.Topology == "noninverting" {
			if len(mcu) > 0 {
				f.Suggest = append(f.Suggest, "출력이 MCU 에 들어갑니다. MCU 내장 OPAMP(PGA 모드) 핀에 신호를 연결할 수 있으면 외부 증폭기를 없앨 수 있습니다(이득 단계·입력 핀 확인 필요).")
			}
			f.Suggest = append(f.Suggest, "고정 이득·정밀 저항이 필요하면 내장 저항 이득 증폭기(예: INA/고정이득 차동앰프)로 저항 정합 오차를 없앨 수 있습니다.")
		}
	}
	if outPath != "" {
		f.Calc = append(f.Calc, "출력 경로: "+outPath)
	}
	f.Calc = append(f.Calc, dcalc...)
	if len(mcu) > 0 {
		f.Calc = append(f.Calc, "MCU 입력: "+strings.Join(uniq(mcu), "; "))
	}
}

func names(cs []conn) string {
	var s []string
	for _, c := range cs {
		s = append(s, c.p.Ref)
	}
	return strings.Join(s, ",")
}

func uniq(s []string) []string {
	m := map[string]bool{}
	var out []string
	for _, x := range s {
		if !m[x] {
			m[x] = true
			out = append(out, x)
		}
	}
	return out
}

func fmtF(v float64) string {
	if math.IsNaN(v) || math.IsInf(v, 0) {
		return "?"
	}
	return fmt.Sprintf("%.4g", v)
}

func gainStr(v float64) string {
	if math.IsNaN(v) || math.IsInf(v, 0) {
		return "?"
	}
	return fmt.Sprintf("%.4g V/V", v)
}

func (a *an) follower(p *netlist.Part, f *Finding, P string, pR []rlink, mcu []string, outPath string) {
	var top, bot []rlink
	for _, l := range pR {
		if isGround(l.to) {
			bot = append(bot, l)
		} else {
			top = append(top, l)
		}
	}
	var cs []string
	ctot := 0.0
	for _, c := range a.caps(P) {
		if isGround(c.other) {
			v, _ := val(c.p)
			ctot += v
			cs = append(cs, c.p.Ref+" "+c.p.Value)
		}
	}
	src := ""
	switch {
	case len(top) >= 1:
		var all []float64
		for _, l := range pR {
			all = append(all, l.r)
		}
		rth := par(all...)
		var terms []string
		for _, l := range top {
			terms = append(terms, fmt.Sprintf("%s×%s", l.to, fmtF(rth/l.r)))
		}
		var parts []string
		for _, l := range pR {
			parts = append(parts, fmt.Sprintf("%s %s→%s", strings.Join(l.refs, "+"), ohm(l.r), l.to))
		}
		f.Calc = append(f.Calc, fmt.Sprintf("IN+ = %s  (저항: %s; 테브난 %s)", strings.Join(terms, " + "), strings.Join(parts, ", "), ohm(rth)))
		if len(top) > 1 {
			f.Calc = append(f.Calc, "IN+ 는 여러 신호의 저항 가중 평균입니다(합산/동상전압 검출 회로).")
		}
		for _, l := range pR {
			if l.r < 1 {
				f.Warn = append(f.Warn, fmt.Sprintf("%s %s 가 IN+ 에 직접 연결 — 1 Ω 미만 저항은 입력 보호·절연 저항 역할을 하지 못합니다(값 확인).", strings.Join(l.refs, "+"), ohm(l.r)))
			}
		}
		if ctot > 0 {
			f.Calc = append(f.Calc, fmt.Sprintf("IN+ 커패시터 %s: τ = %s·%s = %s", strings.Join(cs, ", "), ohm(rth), netlist.SI(ctot, "F"), netlist.SI(rth*ctot, "s")))
		}
		ref := false
		if len(top) == 1 && len(bot) >= 1 {
			if _, ok := railVolts(top[0].to); ok || isRail(top[0].to) {
				ref = true
			}
		}
		if ref {
			f.TopoKo = "기준 전압 버퍼"
		}
		if len(mcu) > 0 && len(top) == 1 && len(bot) >= 1 {
			kq := 0.0
			if ctot > 0 {
				kq = 5e-12 / ctot
			}
			s := fmt.Sprintf("버퍼 생략 검토: 분압(테브난 %s)을 ADC 에 직결.", ohm(rth))
			if ctot > 0 {
				s += fmt.Sprintf(" IN+ 커패시터 %s 이면 ADC 샘플 커패시터(가정 5 pF)와의 전하분배 오차 ≈ %s %%.", netlist.SI(ctot, "F"), fmtF(kq*100))
				s += fmt.Sprintf(" 재충전 τ = %s → 12비트 정착(9τ) %s, 채널당 샘플률 상한 ≈ %s.", netlist.SI(rth*ctot, "s"), netlist.SI(9*rth*ctot, "s"), netlist.SI(1/(9*rth*ctot), "Hz"))
			} else {
				s += " 커패시터가 없으면 ADC 샘플 시간이 테브난 저항에 맞게 길어야 합니다(MCU 레퍼런스 매뉴얼의 최대 소스 임피던스 표 확인)."
			}
			f.Suggest = append(f.Suggest, s)
			f.Suggest = append(f.Suggest, "또는 MCU 내장 OPAMP 팔로워 모드(입력이 OPAMPx_VINP 핀이어야 함).")
		}
		if ref {
			f.Suggest = append(f.Suggest, "기준 전압 용도면 MCU 내부 기준(VREFBUF/DAC)이나 전용 기준 IC(REF30xx 등)로 대체 검토.")
		}
	case len(top) == 0 && len(bot) == 0:
		// direct drive from another IC or a single node
		var drv []string
		for _, c := range a.on(P) {
			if c.p != p && kindOf(c.p) == 0 {
				drv = append(drv, a.desc(c, P))
			}
		}
		if len(drv) > 0 {
			f.Calc = append(f.Calc, "IN+ 직접 구동: "+strings.Join(drv, "; "))
		}
		src = "direct"
	default:
		f.Calc = append(f.Calc, fmt.Sprintf("IN+ 는 %s 로 GND 에만 연결", strings.Join(bot[0].refs, "+")))
	}
	_ = src
	_ = outPath
}

func (a *an) comparator(p *netlist.Part, f *Finding, P, N, O string, rpos []conn, mcu []string) {
	f.Topology, f.TopoKo = "comparator", "비교기"
	if f.Class == KOpamp {
		f.TopoKo = "비교기(Op-amp 개루프)"
		f.Warn = append(f.Warn, "Op-amp 을 귀환 없이 비교기로 쓰고 있습니다. 포화 복귀 지연·입력 차동전압 한계를 데이터시트로 확인하세요.")
	}
	skip := map[string]bool{}
	for _, c := range rpos {
		skip[c.p.Ref] = true
	}
	if len(rpos) > 0 {
		rfb, _ := val(rpos[0].p)
		pR := a.resistors(P, skip)
		var rs []float64
		var refs []string
		for _, l := range pR {
			rs = append(rs, l.r)
			refs = append(refs, strings.Join(l.refs, "+")+"→"+l.to)
		}
		rth := par(rs...)
		if rth > 0 && rfb > 0 {
			k := rth / (rth + rfb)
			s := fmt.Sprintf("양귀환 %s %s, IN+ 측 테브난 %s (%s) → 히스테리시스 = ΔVout × %s", rpos[0].p.Ref, ohm(rfb), ohm(rth), strings.Join(refs, ", "), fmtF(k))
			vcc := 0.0
			for _, q := range p.Pins {
				if pinRole(q.Name) == "v+" {
					_, vcc, _ = a.railOf(q.Net)
				}
			}
			if vcc > 0 {
				s += fmt.Sprintf(" ≈ %s (출력 0↔%sV 레일투레일 가정)", netlist.SI(vcc*k, "V"), fmtF(vcc))
			}
			f.Calc = append(f.Calc, s)
		}
	} else {
		f.Calc = append(f.Calc, "양귀환 저항 없음 → 히스테리시스 없음(내장 히스테리시스는 데이터시트 vhys 확인).")
	}
	for _, net := range []string{P, N} {
		for _, c := range a.caps(net) {
			if isGround(c.other) {
				f.Calc = append(f.Calc, fmt.Sprintf("%s 커패시터 %s %s", net, c.p.Ref, c.p.Value))
			}
		}
	}
	mcu = uniq(mcu)
	if len(mcu) > 0 {
		f.Calc = append(f.Calc, "출력 → MCU: "+strings.Join(mcu, "; "))
		f.Suggest = append(f.Suggest, "출력이 MCU 로 들어갑니다. MCU 내장 비교기(STM32G4 COMP1~7 / TMS320F28x CMPSS 등)로 대체 가능: 비교 대상 신호를 COMPx_INP 가능 핀에 연결하고 문턱은 내부 DAC, 히스테리시스는 내장 설정 사용.")
		var comp []string
		for _, net := range []string{P, N} {
			for _, m := range a.mcuPins(net) {
				if strings.Contains(m, "COMP") {
					comp = append(comp, m)
				}
			}
		}
		if len(comp) > 0 {
			f.Suggest = append(f.Suggest, "입력 넷이 이미 COMP 가능 MCU 핀에 닿아 있음: "+strings.Join(comp, "; "))
		}
	}
	f.Suggest = append(f.Suggest, "외부 비교기를 유지할 경우 내장 히스테리시스 품번(예: TLV3201/TLV7031 계열 데이터시트 확인)으로 양귀환 저항 삭제 가능.")
}

func (a *an) inverter(p *netlist.Part, f *Finding, in, out string) {
	f.Topology, f.TopoKo, f.Gain = "inverter", "논리 반전", "−"
	if in == "" || a.otherMembers(in, p, f.Nets[0].Pin) == 0 {
		if out == "" || a.otherMembers(out, p, f.Nets[1].Pin) == 0 {
			f.Topology, f.TopoKo = "unused", "미사용 게이트"
			f.Warn = append(f.Warn, "입력이 부유이면 CMOS 입력 관통전류·발진 위험 → GND/VCC 로 고정하세요.")
			return
		}
		f.Warn = append(f.Warn, "입력 넷에 다른 연결이 없습니다(부유 입력).")
	}
	mi := a.reach(in, nil)
	mo := a.reach(out, nil)
	for _, c := range a.caps(in) {
		if isGround(c.other) {
			f.Calc = append(f.Calc, fmt.Sprintf("입력 커패시터 %s %s (RC 지연/디바운스)", c.p.Ref, c.p.Value))
		}
	}
	isSchmitt := strings.Contains(strings.ToUpper(p.Value+p.PartName), "14")
	switch {
	case len(mi) > 0 && len(mo) > 0:
		f.Suggest = append(f.Suggest, "입력·출력 모두 MCU 에 연결: 소프트웨어 극성 반전으로 삭제 가능.")
	case len(mi) > 0:
		f.Calc = append(f.Calc, "MCU 출력 → 인버터: "+strings.Join(mi, "; "))
		f.Suggest = append(f.Suggest, "MCU 가 구동하는 신호: GPIO 출력 반전 또는 타이머 출력 극성(CCxP/OCxPOL, ePWM AQ 설정)으로 대체 가능. 단 리셋·부팅 중 핀 상태(풀업/풀다운)가 반전 전과 같은 안전 상태인지 확인.")
	case len(mo) > 0:
		f.Calc = append(f.Calc, "인버터 → MCU 입력: "+strings.Join(uniq(mo), "; "))
		f.Suggest = append(f.Suggest, "MCU 입력 신호: 소프트웨어에서 극성 반전, 또는 인터럽트 엣지 반대로 설정해 삭제 가능.")
		if isSchmitt {
			f.Suggest = append(f.Suggest, "슈미트 입력 용도면 MCU GPIO 입력의 슈미트 트리거 사양(VHYS)을 데이터시트로 확인 후 대체.")
		}
	default:
		f.Suggest = append(f.Suggest, "MCU 와 직접 연결되지 않은 반전 — 전압 영역(레벨 변환)이나 구동 전류 목적인지 확인. 단일 게이트면 1G 계열, 여러 개면 다채널 IC 로 통합 검토.")
	}
}

// shunt reports a difference amplifier measuring across a low-value resistor.
func (a *an) shunt(p *netlist.Part, f *Finding, x1, x2 string, gain float64) {
	var sh *netlist.Part
	for _, c := range a.on(x1) {
		if kindOf(c.p) == 'R' && c.other == x2 {
			if v, ok := val(c.p); ok && v < 1 {
				sh = c.p
			}
		}
	}
	if sh == nil {
		f.Calc = append(f.Calc, fmt.Sprintf("입력 넷: %s / %s (두 넷 사이에 1 Ω 미만 저항 없음)", x1, x2))
		return
	}
	v, _ := val(sh)
	f.TopoKo = "차동 증폭기(션트 전류 검출)"
	f.Calc = append(f.Calc, fmt.Sprintf("션트 %s %s (%s ↔ %s): 감도 = %s × %s = %s V/A", sh.Ref, sh.Value, x1, x2, ohm(v), fmtF(gain), fmtF(v*gain)))
	std := []float64{20, 25, 50, 60, 100, 200, 500}
	best := std[0]
	for _, s := range std {
		if math.Abs(math.Log(s/gain)) < math.Abs(math.Log(best/gain)) {
			best = s
		}
	}
	f.Suggest = append(f.Suggest, fmt.Sprintf("전류 감지 증폭기 IC 1개로 대체 가능(고정 이득 %g V/V 가 가장 가까움; 예: INA240/INA181/INA186 계열 — 공통모드 범위·대역은 데이터시트 확인). 저항 4개 정합 오차가 사라집니다.", best))
	for _, c := range a.csa {
		on := func(net string) int {
			switch {
			case net == "":
				return 0
			case net == x1 || a.nearVia(net, x1):
				return 1
			case net == x2 || a.nearVia(net, x2):
				return 2
			}
			return 0
		}
		var ip, in int
		for _, q := range c.Pins {
			switch pinRole(q.Name) {
			case "in+":
				ip = on(q.Net)
			case "in-":
				in = on(q.Net)
			}
		}
		if ip != 0 && in != 0 && ip != in {
			f.Warn = append(f.Warn, fmt.Sprintf("같은 션트를 이미 %s %s 가 측정하고 있습니다 → 중복, 이 회로 삭제 가능.", c.Ref, c.Value))
		}
	}
}

// nearVia: net reaches target through a single resistor of 100 Ω or less.
func (a *an) nearVia(net, target string) bool {
	if net == "" {
		return false
	}
	for _, c := range a.on(net) {
		if kindOf(c.p) == 'R' && c.other == target {
			if v, ok := val(c.p); ok && v >= 1 && v <= 100 {
				return true
			}
		}
	}
	return false
}

func (a *an) datasheet(p *netlist.Part, f *Finding, vp, vn string) {
	v := strings.ToUpper(p.Value + " " + p.PartName + " " + strings.Join(p.Lines, " "))
	for _, d := range a.ds {
		match := false
		for _, pn := range d.Parts {
			pn = strings.ToUpper(pn)
			if len(pn) >= 5 && (strings.Contains(v, pn) || strings.Contains(pn, firstTok(v))) {
				match = true
			}
		}
		if !match {
			continue
		}
		f.DS = &DSRef{File: d.File, Title: d.Title}
		for _, s := range d.Specs {
			f.DS.Specs = append(f.DS.Specs, s)
		}
		vcc, ok := railVolts(vp)
		if ok && !isGround(vn) {
			if vn2, ok2 := railVolts(vn); ok2 {
				vcc += vn2
			}
		}
		for _, s := range d.Specs {
			if s.Key == "vs" && ok && !strings.Contains(s.Label, "절대최대") {
				lo, okl := netlist.ParseValue(s.Min)
				hi, okh := netlist.ParseValue(s.Max)
				if okh && vcc > hi*1.0001 {
					f.Warn = append(f.Warn, fmt.Sprintf("전원 %s(≈%sV)가 데이터시트 권장 최대 %s %s 초과 (p.%d)", vp, fmtF(vcc), s.Max, s.Unit, s.Page))
				}
				if okl && vcc < lo*0.9999 {
					f.Warn = append(f.Warn, fmt.Sprintf("전원 %s(≈%sV)가 데이터시트 최소 %s %s 미만 (p.%d)", vp, fmtF(vcc), s.Min, s.Unit, s.Page))
				}
			}
		}
		return
	}
}

func firstTok(s string) string {
	f := strings.Fields(s)
	if len(f) == 0 {
		return "\x00"
	}
	if len(f[0]) < 5 {
		return "\x00"
	}
	return f[0]
}

// globalChecks flags netlist issues that affect the analysed circuits.
func (a *an) globalChecks() []string {
	var out []string
	var keys []string
	for k := range a.nl.Nets {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	for _, k := range keys {
		if isNC(k) && len(a.nl.Nets[k]) > 1 {
			refs := map[string]bool{}
			for _, n := range a.nl.Nets[k] {
				refs[n.Ref] = true
			}
			out = append(out, fmt.Sprintf("⚠ 넷 이름 '%s' 에 %d개 핀(%d개 부품)이 묶여 있습니다. 넷 이름 NC 는 무연결이 아니라 하나의 넷으로 연결됩니다 → No-Connect 심볼 사용 권장.", k, len(a.nl.Nets[k]), len(refs)))
		}
	}
	return out
}
