package sim

import (
	"math"
	"testing"
)

func near(t *testing.T, what string, got, want, tol float64) {
	t.Helper()
	if math.Abs(got-want) > tol {
		t.Errorf("%s = %.6g, want %.6g ± %.3g", what, got, want, tol)
	}
}

func valAt(r *Result, sig string, x float64) float64 {
	xs, ys := r.X, r.Signals[sig]
	for i := 1; i < len(xs); i++ {
		if xs[i] >= x {
			f := (x - xs[i-1]) / (xs[i] - xs[i-1])
			return ys[i-1] + f*(ys[i]-ys[i-1])
		}
	}
	return ys[len(ys)-1]
}

func TestRCStep(t *testing.T) {
	c := NewCircuit()
	in, out := c.Node("in"), c.Node("out")
	c.Add(&VSource{N: "V1", A: in, B: -1, Br: c.Internal("V1"), W: Wave{Kind: "pulse", V1: 0, V2: 1, TD: 0, TR: 1e-9, TF: 1e-9, PW: 1, Per: 2}})
	c.Add(&Resistor{N: "R1", A: in, B: out, R: 1e3})
	c.Add(&Capacitor{N: "C1", A: out, B: -1, C: 1e-6})
	r, err := c.Tran(TranOpts{Stop: 5e-3, MaxStep: 1e-5})
	if err != nil {
		t.Fatal(err)
	}
	near(t, "V(out) at τ", valAt(r, "V(out)", 1e-3), 1-math.Exp(-1), 0.005)
	near(t, "V(out) at 5τ", valAt(r, "V(out)", 5e-3), 1-math.Exp(-5), 0.005)
	near(t, "I(C1) at 0+", valAt(r, "I(C1)", 2e-5), 0.98e-3, 0.03e-3)
}

func TestLCRing(t *testing.T) {
	// series RLC driven by a step: ringing frequency 1/(2π√LC)
	c := NewCircuit()
	in, m, out := c.Node("in"), c.Node("m"), c.Node("out")
	c.Add(&VSource{N: "V1", A: in, B: -1, Br: c.Internal("V1"), W: Wave{Kind: "pulse", V2: 1, TR: 1e-9, TF: 1e-9, PW: 1, Per: 2}})
	c.Add(&Resistor{N: "R1", A: in, B: m, R: 1})
	c.Add(&Inductors{N: "L1", Nodes: [][2]int{{m, out}}, L: [][]float64{{1e-3}}, R: []float64{0}, Br: []int{c.Internal("L1")}})
	c.Add(&Capacitor{N: "C1", A: out, B: -1, C: 1e-6})
	r, err := c.Tran(TranOpts{Stop: 2e-3, MaxStep: 2e-7})
	if err != nil {
		t.Fatal(err)
	}
	// first peak at half period π√LC = 99.3 µs, overshoot ≈ 1 + e^(−ζπ/√(1−ζ²)), ζ = R/2·√(C/L) = 0.0158
	near(t, "first peak", valAt(r, "V(out)", math.Pi*math.Sqrt(1e-9)), 1+math.Exp(-0.0158*math.Pi), 0.02)
}

func TestTransformer(t *testing.T) {
	c := NewCircuit()
	in, p, s := c.Node("in"), c.Node("p"), c.Node("s")
	c.Add(&VSource{N: "V1", A: in, B: -1, Br: c.Internal("V1"), W: Wave{Kind: "sin", VA: 1, Freq: 10e3}})
	c.Add(&Resistor{N: "R1", A: in, B: p, R: 0.01})
	L1, L2, k := 1e-3, 4e-3, 0.999
	M := k * math.Sqrt(L1*L2)
	c.Add(&Inductors{N: "T1", Nodes: [][2]int{{p, -1}, {s, -1}}, L: [][]float64{{L1, M}, {M, L2}}, R: []float64{0, 0}, Br: []int{c.Internal("T1a"), c.Internal("T1b")}})
	c.Add(&Resistor{N: "RL", A: s, B: -1, R: 1e4})
	r, err := c.Tran(TranOpts{Stop: 0.5e-3, MaxStep: 1e-6})
	if err != nil {
		t.Fatal(err)
	}
	mx := 0.0
	for i, x := range r.X {
		if x > 0.3e-3 {
			mx = math.Max(mx, r.Signals["V(s)"][i])
		}
	}
	near(t, "secondary peak (n=2)", mx, 2*0.999, 0.03)
}

func TestDiodeRectifier(t *testing.T) {
	c := NewCircuit()
	in, out := c.Node("in"), c.Node("out")
	c.Add(&VSource{N: "V1", A: in, B: -1, Br: c.Internal("V1"), W: Wave{Kind: "sin", VA: 5, Freq: 1e3}})
	c.Add(&Diode{N: "D1", A: in, K: out, Is: 1e-14, Nf: 1})
	c.Add(&Resistor{N: "R1", A: out, B: -1, R: 1e3})
	r, err := c.Tran(TranOpts{Stop: 2e-3, MaxStep: 5e-6})
	if err != nil {
		t.Fatal(err)
	}
	near(t, "peak", valAt(r, "V(out)", 0.25e-3), 5-0.68, 0.08)
	near(t, "negative half", valAt(r, "V(out)", 0.75e-3), 0, 1e-3)
}

func opamp(c *Circuit, name string, p, m, out, vp, vn int) *Amp {
	return &Amp{N: name, P: p, M: m, Out: out, VP: vp, VN: vn, X: c.InternalNode(name + ".x"),
		Gain: 1e5, Wp: 2 * math.Pi * 1e6 / 1e5, SR: 1e6, Rout: 10, SwingHi: 0.02, SwingLo: 0.02}
}

func TestOpampInverting(t *testing.T) {
	c := NewCircuit()
	in, m, out, vcc, vee := c.Node("in"), c.Node("m"), c.Node("out"), c.Node("vcc"), c.Node("vee")
	c.Add(&VSource{N: "VCC", A: vcc, B: -1, Br: c.Internal("VCC"), W: Wave{Kind: "dc", DC: 5}})
	c.Add(&VSource{N: "VEE", A: vee, B: -1, Br: c.Internal("VEE"), W: Wave{Kind: "dc", DC: -5}})
	c.Add(&VSource{N: "VIN", A: in, B: -1, Br: c.Internal("VIN"), W: Wave{Kind: "sin", VA: 0.1, Freq: 1e3}})
	c.Add(&Resistor{N: "R1", A: in, B: m, R: 1e3})
	c.Add(&Resistor{N: "R2", A: m, B: out, R: 10e3})
	c.Add(opamp(c, "U1", -1, m, out, vcc, vee))
	r, err := c.Tran(TranOpts{Stop: 2e-3, MaxStep: 2e-6})
	if err != nil {
		t.Fatal(err)
	}
	near(t, "gain -10", valAt(r, "V(out)", 0.25e-3), -1, 0.01)
	// overdrive saturates at the rail
	c2 := NewCircuit()
	in, m, out, vcc, vee = c2.Node("in"), c2.Node("m"), c2.Node("out"), c2.Node("vcc"), c2.Node("vee")
	c2.Add(&VSource{N: "VCC", A: vcc, B: -1, Br: c2.Internal("VCC"), W: Wave{Kind: "dc", DC: 5}})
	c2.Add(&VSource{N: "VEE", A: vee, B: -1, Br: c2.Internal("VEE"), W: Wave{Kind: "dc", DC: -5}})
	c2.Add(&VSource{N: "VIN", A: in, B: -1, Br: c2.Internal("VIN"), W: Wave{Kind: "dc", DC: -1}})
	c2.Add(&Resistor{N: "R1", A: in, B: m, R: 1e3})
	c2.Add(&Resistor{N: "R2", A: m, B: out, R: 10e3})
	c2.Add(opamp(c2, "U1", -1, m, out, vcc, vee))
	op, _, err := c2.OPResult()
	if err != nil {
		t.Fatal(err)
	}
	near(t, "saturated", op.Signals["V(out)"][0], 4.98, 0.03)
}

func TestACLowpass(t *testing.T) {
	c := NewCircuit()
	in, out := c.Node("in"), c.Node("out")
	c.Add(&VSource{N: "V1", A: in, B: -1, Br: c.Internal("V1"), W: Wave{Kind: "dc"}})
	c.Add(&Resistor{N: "R1", A: in, B: out, R: 1e3})
	c.Add(&Capacitor{N: "C1", A: out, B: -1, C: 159.155e-9})
	r, err := c.AC("V1", 10, 100e3, 50)
	if err != nil {
		t.Fatal(err)
	}
	near(t, "|H| at 1 kHz (dB)", valAt(r, "V(out)|db", 1e3), -3.01, 0.05)
	near(t, "phase at 1 kHz", valAt(r, "V(out)|ph", 1e3), -45, 0.5)
}

func TestSchmittHysteresis(t *testing.T) {
	c := NewCircuit()
	in, out, vcc := c.Node("in"), c.Node("out"), c.Node("vcc")
	c.Add(&VSource{N: "VCC", A: vcc, B: -1, Br: c.Internal("VCC"), W: Wave{Kind: "dc", DC: 3.3}})
	c.Add(&VSource{N: "VIN", A: in, B: -1, Br: c.Internal("VIN"), W: Wave{Kind: "pwl", T: []float64{0, 1e-3, 2e-3}, V: []float64{0, 3.3, 0}}})
	c.Add(&Gate{N: "U1", In: in, VP: vcc, VN: -1, Out: out, X: c.InternalNode("U1.x"), VTp: 0.6, VTn: 0.4, Frac: true, Invert: true, Tau: 10e-9, Rout: 25})
	c.Add(&Resistor{N: "RL", A: out, B: -1, R: 1e5})
	r, err := c.Tran(TranOpts{Stop: 2e-3, MaxStep: 1e-6})
	if err != nil {
		t.Fatal(err)
	}
	// rising input switches at 0.6·3.3 = 1.98 V (t = 0.6 ms), falling at 1.32 V (t = 1.6 ms)
	near(t, "before rising threshold", valAt(r, "V(out)", 0.58e-3), 3.3, 0.01)
	near(t, "after rising threshold", valAt(r, "V(out)", 0.62e-3), 0, 0.01)
	near(t, "between thresholds falling", valAt(r, "V(out)", 1.5e-3), 0, 0.01)
	near(t, "after falling threshold", valAt(r, "V(out)", 1.62e-3), 3.3, 0.01)
}

func TestMOSandBJT(t *testing.T) {
	// NMOS low-side switch driving a 10 Ω load, Rds(on) set by K
	c := NewCircuit()
	g, d, vdd := c.Node("g"), c.Node("d"), c.Node("vdd")
	c.Add(&VSource{N: "VDD", A: vdd, B: -1, Br: c.Internal("VDD"), W: Wave{Kind: "dc", DC: 10}})
	c.Add(&VSource{N: "VG", A: g, B: -1, Br: c.Internal("VG"), W: Wave{Kind: "dc", DC: 10}})
	c.Add(&Resistor{N: "RL", A: vdd, B: d, R: 10})
	c.Add(&MOS{N: "Q1", D: d, G: g, S: -1, Vth: 2, K: 1 / (0.01 * 8)})
	op, _, err := c.OPResult()
	if err != nil {
		t.Fatal(err)
	}
	near(t, "Vds on", op.Signals["V(d)"][0], 10*0.01/10.01, 0.002)
	// NPN common emitter: Ic = β·Ib
	c2 := NewCircuit()
	b, col, vcc := c2.Node("b"), c2.Node("c"), c2.Node("vcc")
	c2.Add(&VSource{N: "VCC", A: vcc, B: -1, Br: c2.Internal("VCC"), W: Wave{Kind: "dc", DC: 5}})
	c2.Add(&Resistor{N: "RB", A: vcc, B: b, R: 430e3})
	c2.Add(&Resistor{N: "RC", A: vcc, B: col, R: 1e3})
	c2.Add(&BJT{N: "Q2", C: col, B: b, E: -1, Is: 1e-14, Bf: 200, Br: 2})
	op2, _, err := c2.OPResult()
	if err != nil {
		t.Fatal(err)
	}
	ib := (5 - 0.65) / 430e3
	near(t, "Vc", op2.Signals["V(c)"][0], 5-200*ib*1e3, 0.1)
}
