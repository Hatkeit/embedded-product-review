package model

import (
	"fmt"
	"math"
	"regexp"
	"sort"
	"strconv"
	"strings"

	"icscope/internal/analysis"
	"icscope/internal/netlist"
	"icscope/internal/sim"
)

// Stim is a source attached to a net.
type Stim struct {
	ID   string   `json:"id"`
	Net  string   `json:"net"`
	Neg  string   `json:"neg,omitempty"` // reference net (default ground)
	Type string   `json:"type"`          // "V" or "I"
	Wave sim.Wave `json:"wave"`
	Auto bool     `json:"auto,omitempty"` // supply rail created automatically
	Off  bool     `json:"off,omitempty"`
}

// Setup is everything needed to build the circuit.
type Setup struct {
	Parts  map[string]bool // parts to include
	Ground string          // net alias used as 0 V
	Stims  []Stim
}

// Aliases splits a merged net name ("I_PV_A+/GND") into its labels.
func Aliases(net string) []string { return strings.Split(net, "/") }

func hasAlias(net, a string) bool {
	for _, x := range Aliases(net) {
		if strings.EqualFold(x, a) {
			return true
		}
	}
	return false
}

// RailOf returns the voltage encoded in one of the net's labels.
func RailOf(net string) (float64, bool) {
	for _, a := range Aliases(net) {
		if regexp.MustCompile(`(?i)ADC|AIN|SENSE|_SNS`).MatchString(a) {
			continue
		}
		if v, ok := analysis.RailVolts(a); ok && v > 0 && v <= 60 {
			return v, true
		}
	}
	return 0, false
}

// Built is a circuit plus the bookkeeping the UI needs.
type Built struct {
	C        *sim.Circuit
	Warnings []string
	Included []string
	Skipped  []string
	NetOf    map[string]string // sim node name → schematic net name
}

// Build creates the simulation circuit.
func Build(nl *netlist.Netlist, models map[string]*Model, s Setup) (*Built, error) {
	c := sim.NewCircuit()
	b := &Built{C: c, NetOf: map[string]string{}}
	gnd := s.Ground
	if gnd == "" {
		gnd = "GND"
	}
	node := func(net string) int {
		if net == "" {
			return c.InternalNode("nc")
		}
		if hasAlias(net, gnd) || sim.IsGround(net) && strings.EqualFold(net, gnd) {
			return -1
		}
		b.NetOf[net] = net
		return c.Node(net)
	}
	refs := make([]string, 0, len(s.Parts))
	for r, ok := range s.Parts {
		if ok {
			refs = append(refs, r)
		}
	}
	sort.Slice(refs, func(i, j int) bool { return netlist.RefLess(refs[i], refs[j]) })
	used := map[string]bool{}
	for _, ref := range refs {
		p := nl.Parts[ref]
		m := models[ref]
		if p == nil || m == nil {
			continue
		}
		if !m.Enabled || m.Kind == "NONE" {
			b.Skipped = append(b.Skipped, ref)
			continue
		}
		if err := addPart(c, p, m, node, b); err != nil {
			b.Warnings = append(b.Warnings, ref+": "+err.Error())
			b.Skipped = append(b.Skipped, ref)
			continue
		}
		b.Included = append(b.Included, ref)
		for _, q := range p.Pins {
			used[q.Net] = true
		}
	}
	// sources
	for _, st := range s.Stims {
		if st.Off {
			continue
		}
		if !used[st.Net] && !st.Auto {
			b.Warnings = append(b.Warnings, fmt.Sprintf("신호원 %s: 넷 %s 에 연결된 포함 부품이 없습니다.", st.ID, st.Net))
		}
		if st.Auto && !used[st.Net] {
			continue
		}
		a, n := node(st.Net), -1
		if st.Neg != "" {
			n = node(st.Neg)
		}
		if a == n {
			continue
		}
		if st.Type == "I" {
			c.Add(&sim.ISource{N: st.ID, A: n, B: a, W: st.Wave})
		} else {
			c.Add(&sim.VSource{N: st.ID, A: a, B: n, Br: c.Internal(st.ID), W: st.Wave})
		}
	}
	if len(b.Included) == 0 {
		return b, fmt.Errorf("시뮬레이션할 부품이 없습니다")
	}
	return b, nil
}

// roleNets collects role → nets (a role may sit on several pins).
func roleNets(p *netlist.Part, m *Model) map[string][]string {
	out := map[string][]string{}
	for i, q := range p.Pins {
		for _, r := range strings.Split(m.Roles[i], ",") {
			r = strings.TrimSpace(r)
			if r != "" {
				out[r] = append(out[r], q.Net)
			}
		}
	}
	return out
}

func addPart(c *sim.Circuit, p *netlist.Part, m *Model, node func(string) int, b *Built) error {
	rn := roleNets(p, m)
	get := func(role string) (int, bool) {
		ns, ok := rn[role]
		if !ok || len(ns) == 0 {
			return 0, false
		}
		return node(ns[0]), true
	}
	need := func(roles ...string) ([]int, error) {
		var out []int
		var miss []string
		for _, r := range roles {
			n, ok := get(r)
			if !ok {
				miss = append(miss, r)
			}
			out = append(out, n)
		}
		if len(miss) > 0 {
			return nil, fmt.Errorf("핀 역할 %s 이(가) 지정되지 않았습니다", strings.Join(miss, ", "))
		}
		return out, nil
	}
	two := func() (int, int, error) {
		n, err := need("1", "2")
		if err != nil {
			return 0, 0, err
		}
		return n[0], n[1], nil
	}
	name := p.Ref
	switch m.Kind {
	case "R", "BEAD", "SHORT":
		a, k, err := two()
		if err != nil {
			return err
		}
		r := m.P("R")
		if r <= 0 {
			r = 1e-3
		}
		c.Add(&sim.Resistor{N: name, A: a, B: k, R: r})
	case "C":
		a, k, err := two()
		if err != nil {
			return err
		}
		if esr := m.P("ESR"); esr > 0 {
			mid := c.InternalNode(name + ".esr")
			c.Add(&sim.Resistor{N: name + ".ESR", A: a, B: mid, R: esr})
			a = mid
		}
		c.Add(&sim.Capacitor{N: name, A: a, B: k, C: m.P("C")})
	case "L":
		a, k, err := two()
		if err != nil {
			return err
		}
		c.Add(&sim.Inductors{N: name, Nodes: [][2]int{{a, k}}, L: [][]float64{{m.P("L")}}, R: []float64{m.P("Rdc")}, Br: []int{c.Internal(name)}})
	case "D":
		vf, ifm, nf := m.P("Vf"), m.P("If"), m.P("N")
		if nf <= 0 {
			nf = 1.5
		}
		is := ifm / (math.Exp(vf/(nf*0.025852)) - 1)
		for g := 1; g <= max(m.Gates, 1); g++ {
			s := strconv.Itoa(g)
			n, err := need("A"+s, "K"+s)
			if err != nil {
				if g == 1 {
					return err
				}
				continue
			}
			dn := name
			if m.Gates > 1 {
				dn = name + "." + s
			}
			if m.P("Bidir") > 0.5 {
				mid := c.InternalNode(dn + ".mid")
				c.Add(&sim.Diode{N: dn, A: n[0], K: mid, Is: is, Nf: nf, BV: m.P("BV"), IBV: 1e-3})
				c.Add(&sim.Diode{N: dn + ".r", A: n[1], K: mid, Is: is, Nf: nf, BV: m.P("BV"), IBV: 1e-3})
			} else {
				c.Add(&sim.Diode{N: dn, A: n[0], K: n[1], Is: is, Nf: nf, BV: m.P("BV"), IBV: 1e-3})
			}
		}
	case "NPN", "PNP":
		for g := 1; g <= max(m.Gates, 1); g++ {
			s := strconv.Itoa(g)
			n, err := need("C"+s, "B"+s, "E"+s)
			if err != nil {
				if g == 1 {
					// single device may use roles without a number
					if n2, err2 := need("C", "B", "E"); err2 == nil {
						n = n2
					} else {
						return err
					}
				} else {
					continue
				}
			}
			dn := name
			if m.Gates > 1 {
				dn = name + "." + s
			}
			c.Add(&sim.BJT{N: dn, C: n[0], B: n[1], E: n[2], PNP: m.Kind == "PNP", Is: m.P("Is"), Bf: m.P("Bf"), Br: 2})
		}
	case "NMOS", "PMOS":
		n, err := need("D", "G", "S")
		if err != nil {
			return err
		}
		vth, rds, vgs := math.Abs(m.P("Vth")), m.P("Rdson"), math.Abs(m.P("Vgson"))
		if vgs <= vth {
			vgs = vth + 5
		}
		k := 1 / (rds * (vgs - vth))
		pm := m.Kind == "PMOS"
		c.Add(&sim.MOS{N: name, D: n[0], G: n[1], S: n[2], PMOS: pm, Vth: vth, K: k, Lambda: 0.001})
		if vf := m.P("Vfbd"); vf > 0 {
			a, kk := n[2], n[0]
			if pm {
				a, kk = n[0], n[2]
			}
			is := 1.0 / (math.Exp(vf/(1.2*0.025852)) - 1) // vf at 1 A
			c.Add(&sim.Diode{N: name + ".bd", A: a, K: kk, Is: is, Nf: 1.2})
		}
		ciss, coss, crss := m.P("Ciss"), m.P("Coss"), m.P("Crss")
		if crss > 0 {
			c.Add(&sim.Capacitor{N: name + ".Cgd", A: n[1], B: n[0], C: crss})
		}
		if ciss > crss {
			c.Add(&sim.Capacitor{N: name + ".Cgs", A: n[1], B: n[2], C: ciss - crss})
		}
		if coss > crss {
			c.Add(&sim.Capacitor{N: name + ".Cds", A: n[0], B: n[2], C: coss - crss})
		}
	case "OPAMP", "COMP":
		vp, okp := get("V+")
		vn, okn := get("V-")
		if !okp || !okn {
			return fmt.Errorf("전원 핀(V+, V-) 역할이 지정되지 않았습니다")
		}
		added := 0
		for g := 1; g <= max(m.Gates, 1); g++ {
			s := strconv.Itoa(g)
			n, err := need("IN+"+s, "IN-"+s, "OUT"+s)
			if err != nil {
				continue
			}
			dn := name
			if m.Gates > 1 {
				dn = name + "." + s
			}
			a := &sim.Amp{N: dn, P: n[0], M: n[1], Out: n[2], VP: vp, VN: vn, X: c.InternalNode(dn + ".x"), Vos: m.P("Vos"), Rout: math.Max(m.P("Rout"), 0.01)}
			if m.Kind == "OPAMP" {
				a.Gain = math.Pow(10, m.P("Aol")/20)
				a.Wp = 2 * math.Pi * m.P("GBW") / a.Gain
				a.SR = m.P("SR")
				a.SwingHi, a.SwingLo = m.P("Swing"), m.P("Swing")
				a.IQ = m.P("IQ")
			} else {
				a.Gain = 1e4
				a.Wp = 2 * math.Pi * 1e9 / a.Gain
				tpd := math.Max(m.P("Tpd"), 1e-9)
				a.SR = 3 / tpd
				a.Hyst = m.P("Hyst")
				a.OpenDrain = m.P("OpenDrain") > 0.5
			}
			c.Add(a)
			added++
		}
		if added == 0 {
			return fmt.Errorf("IN+n / IN-n / OUTn 핀 역할이 없습니다")
		}
	case "INV", "BUF", "GATEDRV":
		vp, okp := get("V+")
		vn, okn := get("V-")
		if !okp || !okn {
			return fmt.Errorf("전원 핀(V+, V-) 역할이 지정되지 않았습니다")
		}
		added := 0
		for g := 1; g <= max(m.Gates, 1); g++ {
			s := strconv.Itoa(g)
			n, err := need("IN"+s, "OUT"+s)
			if err != nil {
				continue
			}
			dn := name
			if m.Gates > 1 {
				dn = name + "." + s
			}
			tpd := math.Max(m.P("Tpd"), 1e-10)
			gt := &sim.Gate{N: dn, In: n[0], Out: n[1], VP: vp, VN: vn, X: c.InternalNode(dn + ".x"), Tau: tpd / 0.69, Rout: math.Max(m.P("Rout"), 0.01)}
			if m.Kind == "GATEDRV" {
				gt.VTp, gt.VTn = m.P("VIH"), m.P("VIL")
				if en, ok := get("EN" + s); ok {
					gt.En, gt.HasEn, gt.EnVT = en, true, m.P("VIH")
				}
			} else {
				gt.VTp, gt.VTn, gt.Frac = m.P("VTp"), m.P("VTn"), true
				gt.Invert = m.Kind == "INV"
			}
			c.Add(gt)
			added++
		}
		if added == 0 {
			return fmt.Errorf("INn / OUTn 핀 역할이 없습니다")
		}
	case "CSA":
		n, err := need("IN+", "IN-", "OUT", "V+", "V-")
		if err != nil {
			return err
		}
		a := &sim.Amp{N: name, P: n[0], M: n[1], Out: n[2], VP: n[3], VN: n[4], X: c.InternalNode(name + ".x"),
			Gain: m.P("Gain"), Wp: 2 * math.Pi * m.P("BW"), SR: 1e8, Vos: m.P("Vos"), SwingHi: m.P("Swing"), SwingLo: m.P("Swing"), Rout: math.Max(m.P("Rout"), 0.01)}
		if r, ok := get("REF"); ok {
			a.Ref, a.HasRef = r, true
		}
		c.Add(a)
	case "ISOAMP":
		n, err := need("INP", "INN", "OUTP", "OUTN", "V+", "V-")
		if err != nil {
			return err
		}
		g := m.P("Gain") / 2
		for k, o := range []struct {
			p, mm, out int
			s          string
		}{{n[0], n[1], n[2], "P"}, {n[1], n[0], n[3], "N"}} {
			_ = k
			c.Add(&sim.Amp{N: name + "." + o.s, P: o.p, M: o.mm, Out: o.out, VP: n[4], VN: n[5], X: c.InternalNode(name + o.s + ".x"),
				Gain: g, Offset: m.P("VCM"), Wp: 2 * math.Pi * m.P("BW"), SR: 1e8, SwingHi: 0.05, SwingLo: 0.05, Rout: math.Max(m.P("Rout"), 0.01)})
		}
	case "VREF":
		n, err := need("IN", "OUT", "GND")
		if err != nil {
			return err
		}
		c.Add(&sim.Amp{N: name, P: n[2], M: n[2], Out: n[1], VP: n[0], VN: n[2], X: c.InternalNode(name + ".x"),
			Gain: 0, Offset: m.P("Vout"), Wp: 2 * math.Pi * math.Max(m.P("BW"), 1), SR: 1e8, SwingHi: m.P("Dropout"), Rout: math.Max(m.P("Rout"), 0.001), HasRef: true, Ref: n[2]})
	case "OPTO":
		vf, ifm := m.P("Vf"), m.P("If")
		is := ifm / (math.Exp(vf/(2*0.025852)) - 1)
		added := 0
		for g := 1; g <= max(m.Gates, 1); g++ {
			s := strconv.Itoa(g)
			n, err := need("A"+s, "K"+s, "C"+s, "E"+s)
			if err != nil {
				continue
			}
			dn := name
			if m.Gates > 1 {
				dn = name + "." + s
			}
			c.Add(&sim.Opto{N: dn, A: n[0], K: n[1], C: n[2], E: n[3], Led: sim.Diode{N: dn + ".led", Is: is, Nf: 2}, CTR: m.P("CTR") / 100, V0: 0.15})
			added++
		}
		if added == 0 {
			return fmt.Errorf("A/K/C/E 핀 역할이 없습니다")
		}
	case "XFMR":
		var nodes [][2]int
		var ls []float64
		for g := 1; g <= 4; g++ {
			s := strconv.Itoa(g)
			n, err := need("W+"+s, "W-"+s)
			if err != nil {
				continue
			}
			l := m.P("L" + s)
			if l <= 0 {
				return fmt.Errorf("권선 %d 인덕턴스가 0 입니다", g)
			}
			nodes = append(nodes, [2]int{n[0], n[1]})
			ls = append(ls, l)
		}
		if len(nodes) < 1 {
			return fmt.Errorf("권선 핀(W+1, W-1 …) 역할이 없습니다")
		}
		k := m.P("k")
		L := make([][]float64, len(ls))
		var br []int
		var rr []float64
		for i := range ls {
			L[i] = make([]float64, len(ls))
			for j := range ls {
				if i == j {
					L[i][j] = ls[i]
				} else {
					L[i][j] = k * math.Sqrt(ls[i]*ls[j])
				}
			}
			br = append(br, c.Internal(fmt.Sprintf("%s.w%d", name, i+1)))
			rr = append(rr, m.P("Rdc"))
		}
		c.Add(&sim.Inductors{N: name, Nodes: nodes, L: L, R: rr, Br: br})
	default:
		return fmt.Errorf("모델 없음")
	}
	return nil
}

// RoleOptions lists the selectable roles for a model.
func RoleOptions(m *Model) []string {
	k := KindOf(m.Kind)
	var out []string
	if k.Multi {
		g := max(m.Gates, 1)
		if m.Kind == "XFMR" {
			g = 4
		}
		for i := 1; i <= g; i++ {
			for _, r := range k.Roles {
				out = append(out, r+strconv.Itoa(i))
			}
		}
	} else {
		out = append(out, k.Roles...)
	}
	return append(out, k.Common...)
}
