// Package sim is a small SPICE-like circuit simulator: modified nodal
// analysis, Newton-Raphson for nonlinear devices, operating point, DC sweep,
// transient (trapezoidal / backward Euler) and small-signal AC analysis.
package sim

import (
	"errors"
	"fmt"
	"math"
	"math/cmplx"
	"sort"
	"strings"
)

// Elem is a circuit element.
type Elem interface {
	Name() string
	// Stamp adds the linearised companion model around ctx.X.
	Stamp(c *Ctx)
	// Accept is called after a converged time step / operating point.
	Accept(c *Ctx)
}

// ACStamper elements take part in the AC analysis.
type ACStamper interface{ StampAC(c *ACCtx) }

// Breaker elements report times where their waveforms have corners.
type Breaker interface{ Breaks(tstop float64) []float64 }

// Probed elements expose a terminal current for plotting.
type Probed interface {
	Current(x []float64) float64
}

// Mode of the analysis being stamped.
type Mode int

const (
	ModeDC Mode = iota
	ModeTran
)

// Ctx holds the MNA system of one Newton iteration.
type Ctx struct {
	N     int
	A     [][]float64
	B     []float64
	X     []float64 // present iterate
	Mode  Mode
	T, H  float64 // time and step (transient)
	Trap  bool    // trapezoidal (else backward Euler)
	Scale float64 // source scale for source stepping
	Gmin  float64
	// set by elements during Stamp when a device limited its voltages
	Limited bool
	// Event: an element changed a discrete state in Accept
	Event bool
}

// G stamps a conductance g between unknowns i and j (-1 = ground).
func (c *Ctx) G(i, j int, g float64) {
	if i >= 0 {
		c.A[i][i] += g
	}
	if j >= 0 {
		c.A[j][j] += g
	}
	if i >= 0 && j >= 0 {
		c.A[i][j] -= g
		c.A[j][i] -= g
	}
}

// Add adds v at A[i][j].
func (c *Ctx) Add(i, j int, v float64) {
	if i >= 0 && j >= 0 {
		c.A[i][j] += v
	}
}

// I stamps a current i flowing from node a to node b through the element
// (leaving a, entering b) as a right-hand-side source.
func (c *Ctx) I(a, b int, i float64) {
	if a >= 0 {
		c.B[a] -= i
	}
	if b >= 0 {
		c.B[b] += i
	}
}

// V returns the iterate value of unknown i (0 for ground).
func (c *Ctx) V(i int) float64 {
	if i < 0 {
		return 0
	}
	return c.X[i]
}

// ACCtx is the complex MNA system of one AC frequency.
type ACCtx struct {
	N     int
	A     [][]complex128
	B     []complex128
	W     float64   // angular frequency
	OP    []float64 // operating point
	Ctx   *Ctx      // operating point context (for device state)
	Input string    // name of the source with AC magnitude 1
}

func (c *ACCtx) Y(i, j int, y complex128) {
	if i >= 0 {
		c.A[i][i] += y
	}
	if j >= 0 {
		c.A[j][j] += y
	}
	if i >= 0 && j >= 0 {
		c.A[i][j] -= y
		c.A[j][i] -= y
	}
}

func (c *ACCtx) Add(i, j int, v complex128) {
	if i >= 0 && j >= 0 {
		c.A[i][j] += v
	}
}

// Circuit is a set of elements over named nodes.
type Circuit struct {
	nodes  map[string]int
	Names  []string // unknown names: node names, then "#branch" names
	IsNode []bool
	Elems  []Elem
}

func NewCircuit() *Circuit { return &Circuit{nodes: map[string]int{}} }

// IsGround tells whether a net name is the reference node.
func IsGround(n string) bool {
	u := strings.ToUpper(strings.TrimSpace(n))
	return u == "0" || u == "GND" || u == "AGND" || u == "PGND" || u == "DGND" || u == "SGND" || u == "GROUND"
}

// Node returns the unknown index of a net (-1 for ground).
func (c *Circuit) Node(name string) int {
	if name == "" {
		return c.Internal("nc")
	}
	if IsGround(name) {
		return -1
	}
	if i, ok := c.nodes[name]; ok {
		return i
	}
	i := len(c.Names)
	c.nodes[name] = i
	c.Names = append(c.Names, name)
	c.IsNode = append(c.IsNode, true)
	return i
}

// HasNode reports whether the net is part of the circuit.
func (c *Circuit) HasNode(name string) bool {
	_, ok := c.nodes[name]
	return ok || IsGround(name)
}

// Internal allocates an extra unknown (branch current or internal node).
func (c *Circuit) Internal(label string) int {
	i := len(c.Names)
	c.Names = append(c.Names, "#"+label)
	c.IsNode = append(c.IsNode, false)
	return i
}

// InternalNode allocates an internal voltage node (gets gmin to ground).
func (c *Circuit) InternalNode(label string) int {
	i := len(c.Names)
	c.Names = append(c.Names, "#"+label)
	c.IsNode = append(c.IsNode, true)
	return i
}

func (c *Circuit) Add(e Elem) { c.Elems = append(c.Elems, e) }

func (c *Circuit) newCtx() *Ctx {
	n := len(c.Names)
	ctx := &Ctx{N: n, A: make([][]float64, n), B: make([]float64, n), X: make([]float64, n), Scale: 1, Gmin: 1e-12}
	for i := range ctx.A {
		ctx.A[i] = make([]float64, n)
	}
	return ctx
}

func (c *Circuit) assemble(ctx *Ctx) {
	for i := range ctx.A {
		row := ctx.A[i]
		for j := range row {
			row[j] = 0
		}
		ctx.B[i] = 0
	}
	ctx.Limited = false
	for _, e := range c.Elems {
		e.Stamp(ctx)
	}
	for i := 0; i < ctx.N; i++ {
		if c.IsNode[i] {
			ctx.A[i][i] += ctx.Gmin
		}
	}
}

var errSingular = errors.New("행렬이 특이(singular)합니다")

// solve solves A x = b in place by LU with partial pivoting (dense, but
// skips zero entries so sparse MNA matrices stay cheap).
func solve(A [][]float64, b []float64) ([]float64, error) {
	n := len(b)
	for k := 0; k < n; k++ {
		p := k
		mx := math.Abs(A[k][k])
		for i := k + 1; i < n; i++ {
			if v := math.Abs(A[i][k]); v > mx {
				mx, p = v, i
			}
		}
		if mx < 1e-300 {
			return nil, errSingular
		}
		if p != k {
			A[p], A[k] = A[k], A[p]
			b[p], b[k] = b[k], b[p]
		}
		piv := A[k][k]
		rk := A[k]
		nz := make([]int, 0, 8)
		for j := k + 1; j < n; j++ {
			if rk[j] != 0 {
				nz = append(nz, j)
			}
		}
		for i := k + 1; i < n; i++ {
			ri := A[i]
			if ri[k] == 0 {
				continue
			}
			f := ri[k] / piv
			ri[k] = 0
			for _, j := range nz {
				ri[j] -= f * rk[j]
			}
			b[i] -= f * b[k]
		}
	}
	x := make([]float64, n)
	for i := n - 1; i >= 0; i-- {
		s := b[i]
		ri := A[i]
		for j := i + 1; j < n; j++ {
			if ri[j] != 0 {
				s -= ri[j] * x[j]
			}
		}
		x[i] = s / ri[i]
	}
	return x, nil
}

func solveC(A [][]complex128, b []complex128) ([]complex128, error) {
	n := len(b)
	for k := 0; k < n; k++ {
		p := k
		mx := cmplx.Abs(A[k][k])
		for i := k + 1; i < n; i++ {
			if v := cmplx.Abs(A[i][k]); v > mx {
				mx, p = v, i
			}
		}
		if mx < 1e-300 {
			return nil, errSingular
		}
		A[p], A[k] = A[k], A[p]
		b[p], b[k] = b[k], b[p]
		for i := k + 1; i < n; i++ {
			if A[i][k] == 0 {
				continue
			}
			f := A[i][k] / A[k][k]
			for j := k; j < n; j++ {
				if A[k][j] != 0 {
					A[i][j] -= f * A[k][j]
				}
			}
			b[i] -= f * b[k]
		}
	}
	x := make([]complex128, n)
	for i := n - 1; i >= 0; i-- {
		s := b[i]
		for j := i + 1; j < n; j++ {
			s -= A[i][j] * x[j]
		}
		x[i] = s / A[i][i]
	}
	return x, nil
}

// newton iterates to convergence; returns iterations used.
func (c *Circuit) newton(ctx *Ctx, maxIter int) (int, error) {
	for it := 1; it <= maxIter; it++ {
		c.assemble(ctx)
		A := make([][]float64, ctx.N)
		for i := range A {
			A[i] = append([]float64(nil), ctx.A[i]...)
		}
		b := append([]float64(nil), ctx.B...)
		x, err := solve(A, b)
		if err != nil {
			return it, err
		}
		conv := !ctx.Limited
		for i := range x {
			if math.IsNaN(x[i]) || math.IsInf(x[i], 0) {
				return it, errors.New("수치 발산(NaN)")
			}
			d := math.Abs(x[i] - ctx.X[i])
			tol := 1e-3*math.Max(math.Abs(x[i]), math.Abs(ctx.X[i])) + 1e-6
			if !c.IsNode[i] {
				tol = 1e-3*math.Max(math.Abs(x[i]), math.Abs(ctx.X[i])) + 1e-9
			}
			if d > tol {
				conv = false
			}
		}
		ctx.X = x
		if conv && it > 1 {
			return it, nil
		}
	}
	return maxIter, errors.New("Newton 반복이 수렴하지 않았습니다")
}

// OP solves the DC operating point with gmin and source stepping fallbacks.
func (c *Circuit) OP() (*Ctx, error) {
	if len(c.Names) == 0 {
		return nil, errors.New("해석할 노드가 없습니다")
	}
	ctx := c.newCtx()
	ctx.Mode = ModeDC
	if _, err := c.newton(ctx, 150); err == nil {
		c.accept(ctx)
		return ctx, nil
	}
	// gmin stepping
	ctx.X = make([]float64, ctx.N)
	ok := true
	for g := 1e-2; g >= 1e-12; g /= 10 {
		ctx.Gmin = g
		if _, err := c.newton(ctx, 150); err != nil {
			ok = false
			break
		}
	}
	ctx.Gmin = 1e-12
	if ok {
		if _, err := c.newton(ctx, 150); err == nil {
			c.accept(ctx)
			return ctx, nil
		}
	}
	// source stepping
	ctx.X = make([]float64, ctx.N)
	for s := 0.0; s <= 1.0001; s += 0.05 {
		ctx.Scale = math.Min(s, 1)
		if _, err := c.newton(ctx, 200); err != nil {
			return ctx, fmt.Errorf("동작점(OP)이 수렴하지 않았습니다 (전원 %.0f%%에서 실패)", s*100)
		}
	}
	ctx.Scale = 1
	c.accept(ctx)
	return ctx, nil
}

func (c *Circuit) accept(ctx *Ctx) {
	ctx.Event = false
	for _, e := range c.Elems {
		e.Accept(ctx)
	}
}

// Result holds sampled waveforms.
type Result struct {
	Kind    string               `json:"kind"` // "tran", "dc", "ac", "op"
	X       []float64            `json:"x"`
	XName   string               `json:"xname"`
	Signals map[string][]float64 `json:"-"`
	// AC: magnitude and phase in separate signals "name|db", "name|ph"
	Order []string `json:"signals"`
	Notes []string `json:"notes,omitempty"`
}

func (r *Result) add(name string, v float64) {
	if _, ok := r.Signals[name]; !ok {
		r.Order = append(r.Order, name)
	}
	r.Signals[name] = append(r.Signals[name], v)
}

func (c *Circuit) record(r *Result, ctx *Ctx) {
	for i, n := range c.Names {
		if c.IsNode[i] && !strings.HasPrefix(n, "#") {
			r.add("V("+n+")", ctx.X[i])
		}
	}
	for _, e := range c.Elems {
		if p, ok := e.(Probed); ok {
			r.add("I("+e.Name()+")", p.Current(ctx.X))
		}
	}
}

// OPResult reports node voltages and device currents of the operating point.
func (c *Circuit) OPResult() (*Result, *Ctx, error) {
	ctx, err := c.OP()
	r := &Result{Kind: "op", Signals: map[string][]float64{}}
	if ctx != nil {
		c.record(r, ctx)
	}
	return r, ctx, err
}

// TranOpts configures a transient run.
type TranOpts struct {
	Stop    float64
	MaxStep float64
	Start   float64 // time from which data is kept
	UIC     bool    // skip operating point: start from zero
	BE      bool    // backward Euler only
}

// Tran runs a transient analysis.
func (c *Circuit) Tran(o TranOpts) (*Result, error) {
	if o.Stop <= 0 {
		return nil, errors.New("종료 시간이 0 입니다")
	}
	if o.MaxStep <= 0 || o.MaxStep > o.Stop/50 {
		o.MaxStep = o.Stop / 500
	}
	var ctx *Ctx
	var err error
	r := &Result{Kind: "tran", XName: "시간 (s)", Signals: map[string][]float64{}}
	if o.UIC {
		ctx = c.newCtx()
		ctx.Mode = ModeDC
		c.accept(ctx) // initialise device histories at zero
	} else {
		ctx, err = c.OP()
		if err != nil {
			r.Notes = append(r.Notes, "동작점 계산 실패 → 0 V 초기조건으로 시작: "+err.Error())
			ctx = c.newCtx()
			ctx.Mode = ModeDC
			c.accept(ctx)
		}
	}
	ctx.Mode = ModeTran
	// breakpoints
	var bps []float64
	for _, e := range c.Elems {
		if b, ok := e.(Breaker); ok {
			bps = append(bps, b.Breaks(o.Stop)...)
		}
	}
	bps = append(bps, o.Stop)
	sort.Float64s(bps)
	t := 0.0
	if o.Start <= 0 {
		r.X = append(r.X, 0)
		c.record(r, ctx)
	}
	h := o.MaxStep / 20
	hmin := o.Stop * 1e-14
	firstAfterBreak := true
	bi := 0
	steps := 0
	const maxPoints = 2_000_000
	for t < o.Stop*(1-1e-12) {
		for bi < len(bps) && bps[bi] <= t*(1+1e-12)+1e-30 {
			bi++
		}
		hh := math.Min(h, o.MaxStep)
		hitBreak := false
		if bi < len(bps) && t+hh >= bps[bi]-hmin {
			hh = bps[bi] - t
			hitBreak = true
		}
		if hh < hmin {
			hh = hmin
		}
		prev := append([]float64(nil), ctx.X...)
		ctx.T = t + hh
		ctx.H = hh
		ctx.Trap = !o.BE && !firstAfterBreak
		it, err := c.newton(ctx, 40)
		if err != nil {
			ctx.X = prev
			h = hh / 8
			if h < hmin {
				return r, fmt.Errorf("t = %.4g s 에서 시간 간격이 너무 작아졌습니다 (수렴 실패: %v)", t, err)
			}
			firstAfterBreak = true
			continue
		}
		t += hh
		c.accept(ctx)
		steps++
		if t >= o.Start {
			r.X = append(r.X, t)
			c.record(r, ctx)
		}
		if len(r.X) > maxPoints {
			r.Notes = append(r.Notes, "데이터 점이 너무 많아 중단했습니다. 최대 간격을 늘리세요.")
			break
		}
		firstAfterBreak = false
		switch {
		case hitBreak || ctx.Event:
			h = o.MaxStep / 50
			firstAfterBreak = true
		case it <= 4:
			h = hh * 2
		case it > 10:
			h = hh / 2
		default:
			h = hh
		}
	}
	return r, nil
}

// DCSweep sweeps the value of a source and records the operating points.
func (c *Circuit) DCSweep(src string, from, to, step float64) (*Result, error) {
	var s *VSource
	var is *ISource
	for _, e := range c.Elems {
		if e.Name() == src {
			switch v := e.(type) {
			case *VSource:
				s = v
			case *ISource:
				is = v
			}
		}
	}
	if s == nil && is == nil {
		return nil, fmt.Errorf("소스 %s 가 없습니다", src)
	}
	if step == 0 || (to-from)/step < 0 {
		return nil, errors.New("스윕 간격이 잘못되었습니다")
	}
	r := &Result{Kind: "dc", XName: src, Signals: map[string][]float64{}}
	n := int(math.Floor((to-from)/step+1e-9)) + 1
	if n > 20000 {
		return nil, errors.New("스윕 점이 너무 많습니다(20000 초과)")
	}
	var ctx *Ctx
	for k := 0; k < n; k++ {
		v := from + float64(k)*step
		if s != nil {
			s.W = Wave{Kind: "dc", DC: v}
		} else {
			is.W = Wave{Kind: "dc", DC: v}
		}
		if ctx == nil {
			var err error
			ctx, err = c.OP()
			if err != nil {
				return r, err
			}
		} else {
			if _, err := c.newton(ctx, 200); err != nil {
				return r, fmt.Errorf("%s = %g 에서 수렴 실패", src, v)
			}
			c.accept(ctx)
		}
		r.X = append(r.X, v)
		c.record(r, ctx)
	}
	return r, nil
}

// AC runs a small-signal sweep (points per decade) driven by the source
// named input (magnitude 1, phase 0).
func (c *Circuit) AC(input string, fstart, fstop float64, perDec int) (*Result, error) {
	if fstart <= 0 || fstop <= fstart {
		return nil, errors.New("주파수 범위가 잘못되었습니다")
	}
	found := false
	for _, e := range c.Elems {
		if e.Name() == input {
			found = true
		}
	}
	if !found {
		return nil, fmt.Errorf("AC 입력 소스 %s 가 없습니다", input)
	}
	op, err := c.OP()
	r := &Result{Kind: "ac", XName: "주파수 (Hz)", Signals: map[string][]float64{}}
	if err != nil {
		r.Notes = append(r.Notes, "동작점 수렴 실패 — 0 V 에서 선형화: "+err.Error())
		op = c.newCtx()
	}
	if perDec <= 0 {
		perDec = 20
	}
	dec := math.Log10(fstop / fstart)
	n := int(math.Ceil(dec*float64(perDec))) + 1
	for k := 0; k < n; k++ {
		f := fstart * math.Pow(10, float64(k)/float64(perDec))
		if f > fstop*1.0001 {
			break
		}
		ac := &ACCtx{N: op.N, W: 2 * math.Pi * f, OP: op.X, Ctx: op, Input: input}
		ac.A = make([][]complex128, op.N)
		for i := range ac.A {
			ac.A[i] = make([]complex128, op.N)
			if c.IsNode[i] {
				ac.A[i][i] += 1e-12
			}
		}
		ac.B = make([]complex128, op.N)
		for _, e := range c.Elems {
			if s, ok := e.(ACStamper); ok {
				s.StampAC(ac)
			}
		}
		x, err := solveC(ac.A, ac.B)
		if err != nil {
			return r, err
		}
		r.X = append(r.X, f)
		for i, nm := range c.Names {
			if c.IsNode[i] && !strings.HasPrefix(nm, "#") {
				r.add("V("+nm+")|db", 20*math.Log10(cmplx.Abs(x[i])+1e-300))
				r.add("V("+nm+")|ph", cmplx.Phase(x[i])*180/math.Pi)
			}
		}
	}
	return r, nil
}

// Unknown returns the index of an unknown by name (node name).
func (c *Circuit) Unknown(name string) (int, bool) {
	i, ok := c.nodes[name]
	return i, ok
}
