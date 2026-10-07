package sim

import (
	"math"
)

const vt = 0.025852 // thermal voltage at 27 °C

// ---------------------------------------------------------------- R

type Resistor struct {
	N    string
	A, B int
	R    float64
}

func (e *Resistor) Name() string { return e.N }
func (e *Resistor) Stamp(c *Ctx) { c.G(e.A, e.B, 1/e.R) }
func (e *Resistor) Accept(*Ctx)  {}
func (e *Resistor) StampAC(c *ACCtx) {
	c.Y(e.A, e.B, complex(1/e.R, 0))
}
func (e *Resistor) Current(x []float64) float64 { return (at(x, e.A) - at(x, e.B)) / e.R }

func at(x []float64, i int) float64 {
	if i < 0 {
		return 0
	}
	return x[i]
}

// ---------------------------------------------------------------- C

type Capacitor struct {
	N     string
	A, B  int
	C     float64
	vPrev float64
	iPrev float64
	g     float64
	ieq   float64
	iNow  float64
}

func (e *Capacitor) Name() string { return e.N }
func (e *Capacitor) Stamp(c *Ctx) {
	if c.Mode == ModeDC {
		e.g, e.ieq = 0, 0
		return
	}
	if c.Trap {
		e.g = 2 * e.C / c.H
		e.ieq = e.g*e.vPrev + e.iPrev
	} else {
		e.g = e.C / c.H
		e.ieq = e.g * e.vPrev
	}
	c.G(e.A, e.B, e.g)
	c.I(e.A, e.B, -e.ieq)
}
func (e *Capacitor) Accept(c *Ctx) {
	v := c.V(e.A) - c.V(e.B)
	if c.Mode == ModeDC {
		e.iPrev = 0
	} else {
		e.iPrev = e.g*v - e.ieq
	}
	e.vPrev = v
	e.iNow = e.iPrev
}
func (e *Capacitor) StampAC(c *ACCtx)            { c.Y(e.A, e.B, complex(0, c.W*e.C)) }
func (e *Capacitor) Current(x []float64) float64 { return e.iNow }

// ---------------------------------------------------------------- L / coupled L

// Inductors is one inductor or a set of magnetically coupled windings.
type Inductors struct {
	N     string
	Nodes [][2]int
	L     [][]float64 // inductance matrix (self on the diagonal, mutual off it)
	R     []float64   // winding resistance
	Br    []int       // branch-current unknowns
	iPrev []float64
	vPrev []float64
	Names []string // per-winding probe names
}

func (e *Inductors) Name() string { return e.N }
func (e *Inductors) Stamp(c *Ctx) {
	n := len(e.Nodes)
	if e.iPrev == nil {
		e.iPrev = make([]float64, n)
		e.vPrev = make([]float64, n)
	}
	for k := 0; k < n; k++ {
		a, b, br := e.Nodes[k][0], e.Nodes[k][1], e.Br[k]
		c.Add(a, br, 1)
		c.Add(b, br, -1)
		c.Add(br, a, 1)
		c.Add(br, b, -1)
		c.Add(br, br, -e.R[k])
		if c.Mode == ModeDC {
			continue
		}
		f := 1 / c.H
		if c.Trap {
			f = 2 / c.H
		}
		rhs := 0.0
		for j := 0; j < n; j++ {
			c.Add(br, e.Br[j], -f*e.L[k][j])
			rhs -= f * e.L[k][j] * e.iPrev[j]
		}
		if c.Trap {
			rhs -= e.vPrev[k] - e.R[k]*e.iPrev[k]
		}
		c.B[br] += rhs
	}
}
func (e *Inductors) Accept(c *Ctx) {
	for k := range e.Nodes {
		e.iPrev[k] = c.X[e.Br[k]]
		e.vPrev[k] = c.V(e.Nodes[k][0]) - c.V(e.Nodes[k][1])
	}
}
func (e *Inductors) StampAC(c *ACCtx) {
	n := len(e.Nodes)
	for k := 0; k < n; k++ {
		a, b, br := e.Nodes[k][0], e.Nodes[k][1], e.Br[k]
		c.Add(a, br, 1)
		c.Add(b, br, -1)
		c.Add(br, a, 1)
		c.Add(br, b, -1)
		c.Add(br, br, complex(-e.R[k], 0))
		for j := 0; j < n; j++ {
			c.Add(br, e.Br[j], complex(0, -c.W*e.L[k][j]))
		}
	}
}
func (e *Inductors) Current(x []float64) float64 { return x[e.Br[0]] }

// ---------------------------------------------------------------- sources

// Wave is a source waveform (SPICE DC / SIN / PULSE / PWL).
type Wave struct {
	Kind string  `json:"kind"` // dc, sin, pulse, pwl
	DC   float64 `json:"dc"`
	// SIN
	VO, VA, Freq, TD, Theta, Phase float64
	// PULSE
	V1, V2, TR, TF, PW, Per float64
	// PWL
	T, V  []float64
	ACMag float64 `json:"acmag"`
}

func (w Wave) At(t float64) float64 {
	switch w.Kind {
	case "sin":
		if t < w.TD {
			return w.VO + w.VA*math.Sin(w.Phase*math.Pi/180)
		}
		d := t - w.TD
		return w.VO + w.VA*math.Exp(-d*w.Theta)*math.Sin(2*math.Pi*w.Freq*d+w.Phase*math.Pi/180)
	case "pulse":
		if t < w.TD {
			return w.V1
		}
		d := t - w.TD
		if w.Per > 0 {
			d = math.Mod(d, w.Per)
		}
		tr, tf := math.Max(w.TR, 1e-12), math.Max(w.TF, 1e-12)
		switch {
		case d < tr:
			return w.V1 + (w.V2-w.V1)*d/tr
		case d < tr+w.PW:
			return w.V2
		case d < tr+w.PW+tf:
			return w.V2 + (w.V1-w.V2)*(d-tr-w.PW)/tf
		}
		return w.V1
	case "pwl":
		if len(w.T) == 0 {
			return 0
		}
		if t <= w.T[0] {
			return w.V[0]
		}
		for i := 1; i < len(w.T); i++ {
			if t <= w.T[i] {
				f := (t - w.T[i-1]) / math.Max(w.T[i]-w.T[i-1], 1e-30)
				return w.V[i-1] + f*(w.V[i]-w.V[i-1])
			}
		}
		return w.V[len(w.V)-1]
	}
	return w.DC
}

func (w Wave) Breaks(tstop float64) []float64 {
	var out []float64
	switch w.Kind {
	case "pulse":
		tr, tf := math.Max(w.TR, 1e-12), math.Max(w.TF, 1e-12)
		for base := w.TD; base < tstop; base += w.Per {
			out = append(out, base, base+tr, base+tr+w.PW, base+tr+w.PW+tf)
			if w.Per <= 0 || len(out) > 200000 {
				break
			}
		}
	case "pwl":
		out = append(out, w.T...)
	case "sin":
		if w.TD > 0 {
			out = append(out, w.TD)
		}
	}
	return out
}

type VSource struct {
	N    string
	A, B int // + and - terminals
	Br   int
	W    Wave
}

func (e *VSource) Name() string { return e.N }
func (e *VSource) Stamp(c *Ctx) {
	c.Add(e.A, e.Br, 1)
	c.Add(e.B, e.Br, -1)
	c.Add(e.Br, e.A, 1)
	c.Add(e.Br, e.B, -1)
	v := e.W.DC
	if c.Mode == ModeTran {
		v = e.W.At(c.T)
	} else if e.W.Kind != "dc" {
		v = e.W.At(0)
	}
	c.B[e.Br] += v * c.Scale
}
func (e *VSource) Accept(*Ctx) {}
func (e *VSource) StampAC(c *ACCtx) {
	c.Add(e.A, e.Br, 1)
	c.Add(e.B, e.Br, -1)
	c.Add(e.Br, e.A, 1)
	c.Add(e.Br, e.B, -1)
	if c.Input == e.N {
		c.B[e.Br] += 1
	}
}
func (e *VSource) Breaks(t float64) []float64 { return e.W.Breaks(t) }

// Current is the current delivered by the source (out of + terminal).
func (e *VSource) Current(x []float64) float64 { return -x[e.Br] }

type ISource struct {
	N    string
	A, B int // current flows from A through the source to B
	W    Wave
}

func (e *ISource) Name() string { return e.N }
func (e *ISource) Stamp(c *Ctx) {
	v := e.W.DC
	if c.Mode == ModeTran {
		v = e.W.At(c.T)
	}
	c.I(e.A, e.B, v*c.Scale)
}
func (e *ISource) Accept(*Ctx) {}
func (e *ISource) StampAC(c *ACCtx) {
	if c.Input == e.N {
		if e.A >= 0 {
			c.B[e.A] -= 1
		}
		if e.B >= 0 {
			c.B[e.B] += 1
		}
	}
}
func (e *ISource) Breaks(t float64) []float64 { return e.W.Breaks(t) }

// ---------------------------------------------------------------- diode

type Diode struct {
	N    string
	A, K int
	Is   float64
	Nf   float64
	BV   float64 // reverse breakdown (0 = none)
	IBV  float64
	vOld float64
	g    float64
	iNow float64
}

func (e *Diode) Name() string { return e.N }

func pnjlim(vnew, vold, vtn, vcrit float64) (float64, bool) {
	if vnew > vcrit && math.Abs(vnew-vold) > 2*vtn {
		if vold > 0 {
			arg := 1 + (vnew-vold)/vtn
			if arg > 0 {
				return vold + vtn*math.Log(arg), true
			}
			return vcrit, true
		}
		return vtn * math.Log(vnew/vtn), true
	}
	return vnew, false
}

func (e *Diode) iv(v float64) (float64, float64) {
	nv := e.Nf * vt
	ex := math.Exp(math.Min(v/nv, 80))
	i := e.Is * (ex - 1)
	g := e.Is * ex / nv
	if e.BV > 0 {
		x := math.Exp(math.Min(-(v+e.BV)/vt, 80))
		ib := e.IBV * x
		i -= ib
		g += ib / vt
	}
	return i, g + 1e-12
}

func (e *Diode) Stamp(c *Ctx) {
	v := c.V(e.A) - c.V(e.K)
	nv := e.Nf * vt
	vcrit := nv * math.Log(nv/(math.Sqrt2*e.Is))
	v2, lim := pnjlim(v, e.vOld, nv, vcrit)
	if e.BV > 0 && -v > e.BV {
		// limit the breakdown side as well
		w, l2 := pnjlim(-v-e.BV, -e.vOld-e.BV, vt, vt*math.Log(vt/(math.Sqrt2*e.IBV)))
		if l2 {
			v2, lim = -(w + e.BV), true
		}
	}
	if lim {
		c.Limited = true
	}
	e.vOld = v2
	i, g := e.iv(v2)
	e.g = g
	c.G(e.A, e.K, g)
	c.I(e.A, e.K, i-g*v2)
}
func (e *Diode) Accept(c *Ctx) {
	v := c.V(e.A) - c.V(e.K)
	e.vOld = v
	e.iNow, e.g = e.iv(v)
}
func (e *Diode) StampAC(c *ACCtx)          { c.Y(e.A, e.K, complex(e.g, 0)) }
func (e *Diode) Current([]float64) float64 { return e.iNow }

// ---------------------------------------------------------------- BJT

type BJT struct {
	N          string
	C, B, E    int
	PNP        bool
	Is         float64
	Bf, Br     float64
	vbeO, vbcO float64
	jac        [3][3]float64
	ic         float64
}

func (e *BJT) Name() string { return e.N }

func (e *BJT) eval(vbe, vbc float64) (ic, ib float64, j [2][2]float64) {
	ebe := math.Exp(math.Min(vbe/vt, 80))
	ebc := math.Exp(math.Min(vbc/vt, 80))
	ict := e.Is * (ebe - ebc)
	ic = ict - e.Is/e.Br*(ebc-1)
	ib = e.Is/e.Bf*(ebe-1) + e.Is/e.Br*(ebc-1)
	gbe := e.Is * ebe / vt
	gbc := e.Is * ebc / vt
	// d/dvbe, d/dvbc
	j[0] = [2]float64{gbe, -gbc - gbc/e.Br}   // ic
	j[1] = [2]float64{gbe / e.Bf, gbc / e.Br} // ib
	return
}

func (e *BJT) Stamp(c *Ctx) {
	p := 1.0
	if e.PNP {
		p = -1
	}
	vbe := p * (c.V(e.B) - c.V(e.E))
	vbc := p * (c.V(e.B) - c.V(e.C))
	vcrit := vt * math.Log(vt/(math.Sqrt2*e.Is))
	var l1, l2 bool
	vbe, l1 = pnjlim(vbe, e.vbeO, vt, vcrit)
	vbc, l2 = pnjlim(vbc, e.vbcO, vt, vcrit)
	if l1 || l2 {
		c.Limited = true
	}
	e.vbeO, e.vbcO = vbe, vbc
	ic, ib, j := e.eval(vbe, vbc)
	// terminal currents into the device: C: ic, B: ib, E: -(ic+ib), times p
	// partials wrt node voltages (vb, vc, ve): dvbe = p(dvb - dve), dvbc = p(dvb - dvc)
	type row struct {
		i    float64
		dbe  float64
		dbc  float64
		node int
	}
	rows := []row{{ic, j[0][0], j[0][1], e.C}, {ib, j[1][0], j[1][1], e.B}, {-(ic + ib), -(j[0][0] + j[1][0]), -(j[0][1] + j[1][1]), e.E}}
	vb, vc, ve := c.V(e.B), c.V(e.C), c.V(e.E)
	_ = vb
	for _, r := range rows {
		// current entering device at terminal r.node = p*r.i ; as "leaving node" = p*r.i
		I := p * r.i
		dB := p * (r.dbe + r.dbc) * p
		dC := p * (-r.dbc) * p
		dE := p * (-r.dbe) * p
		if r.node >= 0 {
			c.Add(r.node, e.B, dB)
			c.Add(r.node, e.C, dC)
			c.Add(r.node, e.E, dE)
			lin := dB*c.V(e.B) + dC*vc + dE*ve
			c.B[r.node] -= I - lin
		}
	}
}
func (e *BJT) Accept(c *Ctx) {
	p := 1.0
	if e.PNP {
		p = -1
	}
	e.vbeO = p * (c.V(e.B) - c.V(e.E))
	e.vbcO = p * (c.V(e.B) - c.V(e.C))
	ic, _, j := e.eval(e.vbeO, e.vbcO)
	e.ic = p * ic
	e.jac[0] = [3]float64{j[0][0], j[0][1], 0}
	e.jac[1] = [3]float64{j[1][0], j[1][1], 0}
}
func (e *BJT) StampAC(c *ACCtx) {
	j := e.jac
	rows := []struct {
		dbe, dbc float64
		node     int
	}{{j[0][0], j[0][1], e.C}, {j[1][0], j[1][1], e.B}, {-(j[0][0] + j[1][0]), -(j[0][1] + j[1][1]), e.E}}
	for _, r := range rows {
		if r.node < 0 {
			continue
		}
		c.Add(r.node, e.B, complex(r.dbe+r.dbc, 0))
		c.Add(r.node, e.C, complex(-r.dbc, 0))
		c.Add(r.node, e.E, complex(-r.dbe, 0))
	}
}
func (e *BJT) Current([]float64) float64 { return e.ic }

// ---------------------------------------------------------------- MOSFET

// MOS is a level-1 style MOSFET with a smooth sub-threshold corner.
type MOS struct {
	N       string
	D, G, S int
	PMOS    bool
	Vth     float64
	K       float64 // transconductance parameter (A/V²)
	Lambda  float64
	vgsO    float64
	gm, gds float64
	id      float64
}

func (e *MOS) Name() string { return e.N }

func (e *MOS) eval(vgs, vds float64) (id, gm, gds float64) {
	n := 1.5 * vt
	u := (vgs - e.Vth) / n
	var veff, dveff float64
	if u > 40 {
		veff, dveff = vgs-e.Vth, 1
	} else {
		veff = n * math.Log1p(math.Exp(u))
		dveff = 1 / (1 + math.Exp(-u))
	}
	cl := 1 + e.Lambda*vds
	if vds < veff {
		id = e.K * (veff*vds - vds*vds/2) * cl
		gm = e.K * vds * cl * dveff
		gds = e.K*(veff-vds)*cl + e.K*(veff*vds-vds*vds/2)*e.Lambda
	} else {
		id = e.K / 2 * veff * veff * cl
		gm = e.K * veff * cl * dveff
		gds = e.K / 2 * veff * veff * e.Lambda
	}
	return id, gm, gds + 1e-12
}

func (e *MOS) Stamp(c *Ctx) {
	p := 1.0
	if e.PMOS {
		p = -1
	}
	d, s := e.D, e.S
	vds := p * (c.V(d) - c.V(s))
	if vds < 0 { // symmetric device: swap drain and source
		d, s = s, d
		vds = -vds
	}
	vgs := p * (c.V(e.G) - c.V(s))
	if dv := vgs - e.vgsO; math.Abs(dv) > 1 {
		vgs = e.vgsO + math.Copysign(1, dv)
		c.Limited = true
	}
	e.vgsO = vgs
	id, gm, gds := e.eval(vgs, vds)
	// current id flows d -> s (for NMOS); I leaving d = p*id
	I := p * id
	// dI/dvd = gds, dI/dvg = gm, dI/dvs = -(gm+gds) (polarity cancels)
	vd, vg, vs := c.V(d), c.V(e.G), c.V(s)
	lin := gds*vd + gm*vg - (gm+gds)*vs
	if d >= 0 {
		c.Add(d, d, gds)
		c.Add(d, e.G, gm)
		c.Add(d, s, -(gm + gds))
		c.B[d] -= I - lin
	}
	if s >= 0 {
		c.Add(s, d, -gds)
		c.Add(s, e.G, -gm)
		c.Add(s, s, gm+gds)
		c.B[s] += I - lin
	}
}
func (e *MOS) Accept(c *Ctx) {
	p := 1.0
	if e.PMOS {
		p = -1
	}
	vds := p * (c.V(e.D) - c.V(e.S))
	vgs := p * (c.V(e.G) - c.V(e.S))
	sign := 1.0
	if vds < 0 {
		vgs = p * (c.V(e.G) - c.V(e.D))
		vds = -vds
		sign = -1
	}
	e.vgsO = vgs
	id, gm, gds := e.eval(vgs, vds)
	e.id, e.gm, e.gds = p*sign*id, gm, gds
}
func (e *MOS) StampAC(c *ACCtx) {
	gm, gds := complex(e.gm, 0), complex(e.gds, 0)
	if e.D >= 0 {
		c.Add(e.D, e.D, gds)
		c.Add(e.D, e.G, gm)
		c.Add(e.D, e.S, -(gm + gds))
	}
	if e.S >= 0 {
		c.Add(e.S, e.D, -gds)
		c.Add(e.S, e.G, -gm)
		c.Add(e.S, e.S, gm+gds)
	}
}
func (e *MOS) Current([]float64) float64 { return e.id }

// ---------------------------------------------------------------- behavioural amplifier

// Amp is a behavioural amplifier used for op-amps, comparators,
// current-sense / isolation amplifiers and references:
//
//	target = Gain·(V(P) − V(M) + Vos ± Hyst/2) + Offset + V(Ref)
//	dX/dt  = SR·tanh(Wp·(target − X)/SR)        (single pole, slew limited)
//	Vout   = X limited to the supply rails minus the output swing, via Rout
type Amp struct {
	N             string
	P, M, Ref     int // Ref < 0 with HasRef=false means no reference input
	HasRef        bool
	VP, VN        int // supply pins (ground allowed)
	FixedRails    bool
	Hi, Lo        float64 // rails when FixedRails
	Out           int
	X             int // internal state node
	Gain, Offset  float64
	Vos           float64
	Wp, SR        float64
	SwingHi       float64
	SwingLo       float64
	Rout          float64
	OpenDrain     bool
	Hyst          float64
	IQ            float64
	hs            float64 // hysteresis state ±1
	xIter         float64
	iterOK        bool
	xPrev, dxPrev float64
	g             float64
	ieq           float64
	dIdx          float64
	dIdv          [3]float64 // wrt P, M, Ref
	dVo           float64
	vo            float64
	iout          float64
}

func (e *Amp) Name() string { return e.N }

// soft limits v into [lo, hi] with exponential corners of width d.
func soft(v, lo, hi float64) (float64, float64) {
	if hi < lo {
		hi, lo = lo, hi
	}
	d := math.Max(0.02*(hi-lo), 0.01)
	if hi-lo < 2*d {
		d = (hi - lo) / 2
		if d <= 0 {
			return lo, 0
		}
	}
	switch {
	case v > hi-d:
		x := math.Exp(-(v - (hi - d)) / d)
		return hi - d*x, x
	case v < lo+d:
		x := math.Exp((v - (lo + d)) / d)
		return lo + d*x, x
	}
	return v, 1
}

func (e *Amp) rails(c *Ctx) (float64, float64) {
	if e.FixedRails {
		return e.Lo, e.Hi
	}
	return c.V(e.VN), c.V(e.VP)
}

func (e *Amp) target(c *Ctx) float64 {
	vd := c.V(e.P) - c.V(e.M) + e.Vos + e.hs*e.Hyst/2
	raw := e.Gain*vd + e.Offset
	if e.HasRef {
		raw += c.V(e.Ref)
	}
	return raw
}

// softplus clamp current pulling x back inside [xl, xh].
func clampI(x, xl, xh, gc float64) (float64, float64) {
	const d = 0.01
	sp := func(z float64) (float64, float64) { // d·ln(1+e^(z/d)) and derivative
		if z/d > 40 {
			return z, 1
		}
		e := math.Exp(z / d)
		return d * math.Log1p(e), e / (1 + e)
	}
	a, da := sp(x - xh)
	b, db := sp(xl - x)
	return -gc*a + gc*b, -gc*da - gc*db
}

func (e *Amp) Stamp(c *Ctx) {
	lo, hi := e.rails(c)
	if hi-lo < 0.1 { // unpowered: hold the output at the negative rail
		hi = lo + 0.1
	}
	tg := e.target(c)
	// limit the state change per Newton iteration so the iteration does not
	// bounce between the two saturated states
	x := c.X[e.X]
	if e.iterOK {
		step := math.Max(0.5, 0.25*(hi-lo))
		if d := x - e.xIter; math.Abs(d) > step {
			x = e.xIter + math.Copysign(step, d)
			c.Limited = true
		}
	}
	c.X[e.X] = x
	e.xIter, e.iterOK = x, true
	sr := e.SR
	if sr <= 0 {
		sr = 1e8
	}
	u := e.Wp * (tg - x)
	th := math.Tanh(u / sr)
	I := sr * th
	dIdu := 1 - th*th
	// anti-windup: keep the state within the rails (± 0.3 V)
	ic, dic := clampI(x, lo-0.3, hi+0.3, 100*sr)
	I += ic
	dIdx := -dIdu*e.Wp + dic
	dIdt := dIdu * e.Wp
	e.dIdx = dIdx
	e.dIdv = [3]float64{dIdt * e.Gain, -dIdt * e.Gain, dIdt}
	// state node: C·dX/dt = I with C = 1 F (DC: I = 0)
	X := e.X
	if c.Mode == ModeTran {
		// backward Euler: the behavioural state is stiff and must not ring
		e.g = 1 / c.H
		e.ieq = e.g * e.xPrev
		c.A[X][X] += e.g
		c.B[X] += e.ieq
	} else {
		e.g, e.ieq = 0, 0
	}
	// −I moved to the left side
	c.A[X][X] -= dIdx
	lin := dIdx * x
	for k, n := range []int{e.P, e.M, e.Ref} {
		if k == 2 && !e.HasRef {
			continue
		}
		c.Add(X, n, -e.dIdv[k])
		lin += e.dIdv[k] * c.V(n)
	}
	c.B[X] += I - lin
	// output stage
	vo, dvo := soft(x, lo+e.SwingLo, hi-e.SwingHi)
	e.vo, e.dVo = vo, dvo
	vout := c.V(e.Out)
	if e.Out >= 0 {
		if e.OpenDrain {
			// pull-down strength follows how low the output wants to be
			span := math.Max(hi-lo, 1e-3)
			s := (hi - e.SwingHi - vo) / span
			if s < 0 {
				s = 0
			}
			gon := 1 / e.Rout
			i := gon * s * (vout - lo)
			di := gon * s
			dix := -gon * dvo / span * (vout - lo)
			c.A[e.Out][e.Out] += di + 1e-9
			c.A[e.Out][X] += dix
			c.B[e.Out] -= i - di*vout - dix*x
		} else {
			g := 1 / e.Rout
			c.A[e.Out][e.Out] += g
			c.A[e.Out][X] -= g * dvo
			c.B[e.Out] += g * (vo - dvo*x)
		}
	}
	if e.IQ > 0 && !e.FixedRails {
		vs := math.Abs(hi - lo)
		if vs > 0.5 {
			c.G(e.VP, e.VN, e.IQ/vs)
		}
	}
}

func (e *Amp) Accept(c *Ctx) {
	x := c.V(e.X)
	e.xIter = x
	if c.Mode == ModeTran {
		e.dxPrev = e.g*x - e.ieq
	} else {
		e.dxPrev = 0
	}
	e.xPrev = x
	if e.Hyst > 0 {
		lo, hi := e.rails(c)
		mid := (lo + hi) / 2
		ns := -1.0
		if x > mid {
			ns = 1
		}
		if ns != e.hs {
			e.hs = ns
			c.Event = true
		}
	}
	if e.Out >= 0 && !e.OpenDrain {
		e.iout = (e.vo - c.V(e.Out)) / e.Rout
	}
}

func (e *Amp) StampAC(c *ACCtx) {
	X := e.X
	c.A[X][X] += complex(0, c.W) - complex(e.dIdx, 0)
	for k, n := range []int{e.P, e.M, e.Ref} {
		if k == 2 && !e.HasRef {
			continue
		}
		c.Add(X, n, complex(-e.dIdv[k], 0))
	}
	if e.Out >= 0 && !e.OpenDrain {
		g := 1 / e.Rout
		c.A[e.Out][e.Out] += complex(g, 0)
		c.A[e.Out][X] -= complex(g*e.dVo, 0)
	}
}

func (e *Amp) Current([]float64) float64 { return e.iout }

// ---------------------------------------------------------------- logic gate

// Gate is a buffer / inverter with Schmitt thresholds, optional enable and a
// first-order output transition. Thresholds are fractions of the supply when
// Frac is set, volts otherwise.
type Gate struct {
	N        string
	In, En   int
	HasEn    bool
	VP, VN   int
	Out      int
	X        int
	VTp, VTn float64
	Frac     bool
	Invert   bool
	EnVT     float64 // enable threshold (fraction or volts)
	Tau      float64
	Rout     float64
	state    bool
	init     bool
	xPrev    float64
	dxPrev   float64
	g, ieq   float64
	iout     float64
}

func (e *Gate) Name() string { return e.N }

func (e *Gate) levels(c *Ctx) (lo, hi, tp, tn float64) {
	lo, hi = c.V(e.VN), c.V(e.VP)
	tp, tn = e.VTp, e.VTn
	if e.Frac {
		tp = lo + e.VTp*(hi-lo)
		tn = lo + e.VTn*(hi-lo)
	}
	return
}

func (e *Gate) outTarget(c *Ctx) float64 {
	lo, hi, _, _ := e.levels(c)
	high := e.state != e.Invert
	if e.HasEn {
		ev := e.EnVT
		if e.Frac {
			ev = lo + e.EnVT*(hi-lo)
		}
		if c.V(e.En) < ev {
			high = false
		}
	}
	if high {
		return hi
	}
	return lo
}

func (e *Gate) update(c *Ctx) bool {
	_, _, tp, tn := e.levels(c)
	v := c.V(e.In)
	old := e.state
	if !e.init {
		e.state = v > (tp+tn)/2
		e.init = true
		return false
	}
	if v > tp {
		e.state = true
	} else if v < tn {
		e.state = false
	}
	return old != e.state
}

func (e *Gate) Stamp(c *Ctx) {
	if c.Mode == ModeDC {
		e.update(c) // settle the state during the operating point
	}
	tg := e.outTarget(c)
	X := e.X
	// tau·dX/dt = tg − X
	if c.Mode == ModeTran {
		e.g = e.Tau / c.H // backward Euler (stiff state)
		e.ieq = e.g * e.xPrev
	} else {
		e.g, e.ieq = 0, 0
	}
	c.A[X][X] += e.g + 1
	c.B[X] += e.ieq + tg
	if e.Out >= 0 {
		g := 1 / e.Rout
		c.A[e.Out][e.Out] += g
		c.A[e.Out][X] -= g
	}
}

func (e *Gate) Accept(c *Ctx) {
	x := c.V(e.X)
	if c.Mode == ModeTran && e.Tau > 0 {
		e.dxPrev = (e.g*x - e.ieq) / e.Tau
	} else {
		e.dxPrev = 0
	}
	e.xPrev = x
	if e.update(c) {
		c.Event = true
	}
	if e.Out >= 0 {
		e.iout = (x - c.V(e.Out)) / e.Rout
	}
}

func (e *Gate) StampAC(c *ACCtx) {
	X := e.X
	c.A[X][X] += complex(1, c.W*e.Tau)
	if e.Out >= 0 {
		g := complex(1/e.Rout, 0)
		c.A[e.Out][e.Out] += g
		c.A[e.Out][X] -= g
	}
}
func (e *Gate) Current([]float64) float64 { return e.iout }

// ---------------------------------------------------------------- opto-coupler

// Opto is an LED driving a photo-transistor: Ic = CTR·I_LED·(1 − e^(−Vce/V0)).
type Opto struct {
	N          string
	A, K, C, E int
	Led        Diode
	CTR        float64
	V0         float64
	gl, gc, gx float64
	ic         float64
}

func (e *Opto) Name() string { return e.N }

func (e *Opto) eval(vak, vce float64) (id, gd, ic, dicd, dicv float64) {
	id, gd = e.Led.iv(vak)
	if id < 0 {
		id, gd = 0, 1e-12
	}
	s := 1 - math.Exp(-math.Max(vce, -1)/e.V0)
	ds := math.Exp(-math.Max(vce, -1)/e.V0) / e.V0
	if vce < 0 {
		s, ds = vce/e.V0, 1/e.V0
	}
	ic = e.CTR * id * s
	dicd = e.CTR * gd * s
	dicv = e.CTR * id * ds
	return
}

func (e *Opto) Stamp(c *Ctx) {
	e.Led.A, e.Led.K = e.A, e.K
	e.Led.Stamp(c)
	vak := e.Led.vOld
	vce := c.V(e.C) - c.V(e.E)
	_, _, ic, dd, dv := e.eval(vak, vce)
	// ic leaves C, enters E: depends on vak = va−vk and vce = vc−ve
	lin := dd*(c.V(e.A)-c.V(e.K)) + dv*vce
	for _, t := range []struct {
		n int
		s float64
	}{{e.C, 1}, {e.E, -1}} {
		if t.n < 0 {
			continue
		}
		c.Add(t.n, e.A, t.s*dd)
		c.Add(t.n, e.K, -t.s*dd)
		c.Add(t.n, e.C, t.s*dv+t.s*1e-12)
		c.Add(t.n, e.E, -t.s*dv-t.s*1e-12)
		c.B[t.n] -= t.s * (ic - lin)
	}
}
func (e *Opto) Accept(c *Ctx) {
	e.Led.Accept(c)
	_, gd, ic, dd, dv := e.eval(c.V(e.A)-c.V(e.K), c.V(e.C)-c.V(e.E))
	e.gl, e.gc, e.gx, e.ic = gd, dd, dv, ic
}
func (e *Opto) StampAC(c *ACCtx) {
	c.Y(e.A, e.K, complex(e.gl, 0))
	for _, t := range []struct {
		n int
		s float64
	}{{e.C, 1}, {e.E, -1}} {
		if t.n < 0 {
			continue
		}
		c.Add(t.n, e.A, complex(t.s*e.gc, 0))
		c.Add(t.n, e.K, complex(-t.s*e.gc, 0))
		c.Add(t.n, e.C, complex(t.s*e.gx, 0))
		c.Add(t.n, e.E, complex(-t.s*e.gx, 0))
	}
}
func (e *Opto) Current([]float64) float64 { return e.ic }
