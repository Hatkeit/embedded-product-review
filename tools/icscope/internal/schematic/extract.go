// Package schematic rebuilds a netlist from an OrCAD Capture schematic PDF
// using the default OrCAD drawing colours (wire blue, junction red, pin
// brown, body orange, power/port black). The result is heuristic.
package schematic

import (
	"math"
	"sort"
	"strings"

	"icscope/internal/pdf"
)

var (
	cBlue   = pdf.RGB{0.26, 0, 1}
	cRed    = pdf.RGB{1, 0, 0}
	cBrown  = pdf.RGB{0.67, 0.54, 0.27}
	cOrange = pdf.RGB{0.8, 0.5, 0.02}
	cBlack  = pdf.RGB{0, 0, 0}
)

func sameColor(a, b pdf.RGB) bool {
	return math.Abs(a[0]-b[0]) < 0.011 && math.Abs(a[1]-b[1]) < 0.011 && math.Abs(a[2]-b[2]) < 0.011
}

type seg struct{ x1, y1, x2, y2 float64 }
type rect struct{ x0, y0, x1, y1 float64 }
type pt struct{ x, y float64 }

func (s seg) ends() [2]pt { return [2]pt{{s.x1, s.y1}, {s.x2, s.y2}} }
func (s seg) length() float64 {
	return math.Hypot(s.x2-s.x1, s.y2-s.y1)
}
func (s seg) axis() bool { return math.Abs(s.x1-s.x2) < 0.3 || math.Abs(s.y1-s.y2) < 0.3 }
func (s seg) rect() rect {
	return rect{math.Min(s.x1, s.x2), math.Min(s.y1, s.y2), math.Max(s.x1, s.x2), math.Max(s.y1, s.y2)}
}

func segPtDist(s seg, p pt) float64 {
	dx, dy := s.x2-s.x1, s.y2-s.y1
	l2 := dx*dx + dy*dy
	if l2 == 0 {
		return math.Hypot(p.x-s.x1, p.y-s.y1)
	}
	t := ((p.x-s.x1)*dx + (p.y-s.y1)*dy) / l2
	t = math.Max(0, math.Min(1, t))
	return math.Hypot(p.x-(s.x1+t*dx), p.y-(s.y1+t*dy))
}

func rectDist(a, b rect) float64 {
	dx := math.Max(math.Max(a.x0-b.x1, b.x0-a.x1), 0)
	dy := math.Max(math.Max(a.y0-b.y1, b.y0-a.y1), 0)
	return math.Hypot(dx, dy)
}

func ptRect(p pt) rect { return rect{p.x, p.y, p.x, p.y} }

func union(a, b rect) rect {
	return rect{math.Min(a.x0, b.x0), math.Min(a.y0, b.y0), math.Max(a.x1, b.x1), math.Max(a.y1, b.y1)}
}

type uf struct{ p []int }

func newUF(n int) *uf {
	u := &uf{p: make([]int, n)}
	for i := range u.p {
		u.p[i] = i
	}
	return u
}
func (u *uf) add() int { u.p = append(u.p, len(u.p)); return len(u.p) - 1 }
func (u *uf) f(x int) int {
	for u.p[x] != x {
		u.p[x] = u.p[u.p[x]]
		x = u.p[x]
	}
	return x
}
func (u *uf) u(a, b int) {
	ra, rb := u.f(a), u.f(b)
	if ra != rb {
		u.p[ra] = rb
	}
}

// text is a merged run of glyphs.
type text struct {
	t      string
	bb     rect
	col    int // 0xRRGGBB
	size   float64
	horiz  bool
	near   float64 // distance to nearest net (-1 none)
	nearID int
	cls    string
}

func colInt(c pdf.RGB) int {
	r := int(math.Round(c[0] * 255))
	g := int(math.Round(c[1] * 255))
	b := int(math.Round(c[2] * 255))
	return r<<16 | g<<8 | b
}

const colRed = 0xFF0000

func isPinNameCol(c int) bool { return c&0xFF >= 0x80 && c>>16 == 0 }

// pageTexts merges glyphs into strings (port of decode.page_texts plus the
// display-level merge of extract.extract).
func pageTexts(pc *pdf.PageContent) []*text {
	type item struct {
		t      string
		bb     rect
		col    int
		size   float64
		dx, dy float64
		stack  float64
	}
	var items []*item
	var cur *item
	var last pdf.Glyph
	for _, g := range pc.Glyphs {
		if g.Invisible {
			continue
		}
		col := colInt(g.Color)
		dx, dy := math.Round(g.Dir.X), math.Round(g.Dir.Y)
		b := rect{g.X0, g.Y0, g.X1, g.Y1}
		if cur != nil && cur.col == col && cur.dx == dx && cur.dy == dy && math.Abs(g.Size-last.Size) < 0.2 {
			// continue the run when this origin follows the previous glyph
			ex, ey := last.OX+last.Adv*last.Dir.X, last.OY+last.Adv*last.Dir.Y
			vx, vy := g.OX-last.OX, g.OY-last.OY
			along := vx*g.Dir.X + vy*g.Dir.Y
			across := vx*g.Dir.Y - vy*g.Dir.X
			run := math.Hypot(g.OX-ex, g.OY-ey) < 0.35*g.Size
			// Rotated OrCAD text: the origin moves by the advance width at
			// right angles to the glyph direction.
			stack := math.Abs(along) < 0.3*g.Size && math.Abs(math.Abs(across)-last.Adv) < 0.3*g.Size && math.Abs(across) > 0.1 &&
				(cur.stack == 0 || cur.stack == math.Copysign(1, across))
			if run || stack {
				if stack {
					cur.stack = math.Copysign(1, across)
				}
				cur.t += g.Text
				cur.bb = union(cur.bb, b)
				last = g
				continue
			}
		}
		cur = &item{t: g.Text, bb: b, col: col, size: math.Round(g.Size*10) / 10, dx: dx, dy: dy}
		items = append(items, cur)
		last = g
	}
	proj := func(b rect, dx, dy float64) (float64, float64) {
		cs := []float64{b.x0*dx + b.y0*dy, b.x1*dx + b.y0*dy, b.x0*dx + b.y1*dy, b.x1*dx + b.y1*dy}
		mn, mx := cs[0], cs[0]
		for _, c := range cs {
			mn, mx = math.Min(mn, c), math.Max(mx, c)
		}
		return mn, mx
	}
	perp := func(b rect, dx, dy float64) float64 {
		cs := []float64{-b.x0*dy + b.y0*dx, -b.x1*dy + b.y0*dx, -b.x0*dy + b.y1*dx, -b.x1*dy + b.y1*dx}
		mn, mx := cs[0], cs[0]
		for _, c := range cs {
			mn, mx = math.Min(mn, c), math.Max(mx, c)
		}
		return (mn + mx) / 2
	}
	sort.SliceStable(items, func(i, j int) bool {
		a, b := items[i], items[j]
		if a.dx != b.dx {
			return a.dx < b.dx
		}
		if a.dy != b.dy {
			return a.dy < b.dy
		}
		pa, _ := proj(a.bb, a.dx, a.dy)
		pb, _ := proj(b.bb, b.dx, b.dy)
		return pa < pb
	})
	var merged []*item
	for _, it := range items {
		done := false
		for _, pr := range merged {
			if pr.dx != it.dx || pr.dy != it.dy || pr.col != it.col || math.Abs(pr.size-it.size) > 0.2 {
				continue
			}
			if math.Abs(perp(it.bb, it.dx, it.dy)-perp(pr.bb, it.dx, it.dy)) > 1.5 {
				continue
			}
			a, _ := proj(it.bb, it.dx, it.dy)
			_, b := proj(pr.bb, it.dx, it.dy)
			gap := a - b
			if gap >= -1.0 && gap < 1.0 {
				pr.t += it.t
				pr.bb = union(pr.bb, it.bb)
				done = true
				break
			}
		}
		if !done {
			merged = append(merged, it)
		}
	}
	// display-level merge of split fragments
	sort.SliceStable(merged, func(i, j int) bool {
		if merged[i].bb.x0 != merged[j].bb.x0 {
			return merged[i].bb.x0 < merged[j].bb.x0
		}
		return merged[i].bb.y0 < merged[j].bb.y0
	})
	var out []*text
	for _, it := range merged {
		s := it.t
		if strings.TrimSpace(s) == "" {
			continue
		}
		bb := it.bb
		horiz := (bb.x1-bb.x0) >= (bb.y1-bb.y0) || len(strings.TrimSpace(s)) == 1
		done := false
		for _, m := range out {
			if m.col != it.col || math.Abs(m.size-it.size) > 0.2 {
				continue
			}
			mb, mh := m.bb, m.horiz
			lm, ls := len([]rune(strings.TrimSpace(m.t))), len([]rune(strings.TrimSpace(s)))
			if lm > 1 && ls > 1 && mh != horiz {
				continue
			}
			if lm == 1 && ls > 1 {
				mh = horiz
				m.horiz = horiz
			}
			if mh {
				if math.Abs((mb.y0+mb.y1)/2-(bb.y0+bb.y1)/2) > 1.5 {
					continue
				}
				gap, gap2 := bb.x0-mb.x1, mb.x0-bb.x1
				if gap >= -1.8 && gap < 1.0 {
					m.t += s
				} else if gap2 >= -1.8 && gap2 < 1.0 {
					m.t = s + m.t
				} else {
					continue
				}
			} else {
				if math.Abs((mb.x0+mb.x1)/2-(bb.x0+bb.x1)/2) > 1.5 {
					continue
				}
				gap, gap2 := mb.y0-bb.y1, bb.y0-mb.y1
				if gap >= -1.8 && gap < 1.0 {
					m.t += s
				} else if gap2 >= -1.8 && gap2 < 1.0 {
					m.t = s + m.t
				} else {
					continue
				}
			}
			m.bb = union(mb, bb)
			done = true
			break
		}
		if !done {
			out = append(out, &text{t: s, bb: bb, col: it.col, size: it.size, horiz: horiz, near: -1})
		}
	}
	return out
}

type pinRec struct {
	s     seg
	net   int // union-find id, -1 none
	body  int
	inner pt
	num   string
	name  string
}

type extracted struct {
	segs   []seg
	kinds  []byte // 'w' or 'b'
	u      *uf
	pins   []*pinRec
	bodies []rect
	items  [][]rect
	texts  []*text
}

const tol = 1.2

func extractPage(pc *pdf.PageContent) *extracted {
	var wires, pins, black []seg
	var junc []pt
	var bodyItems []rect
	for _, p := range pc.Paths {
		var c, f *pdf.RGB
		if p.Stroke {
			c = &p.SColor
		}
		if p.Fill {
			f = &p.FColor
		}
		is := func(x *pdf.RGB, ref pdf.RGB) bool { return x != nil && sameColor(*x, ref) }
		pr := rect{p.X0, p.Y0, p.X1, p.Y1}
		for _, it := range p.Items {
			switch it.Kind {
			case 'l':
				a, b := it.P[0], it.P[len(it.P)-1]
				s := seg{round2(a.X), round2(a.Y), round2(b.X), round2(b.Y)}
				switch {
				case is(c, cBlue):
					wires = append(wires, s)
				case is(c, cBrown):
					pins = append(pins, s)
				case is(c, cOrange) || is(f, cOrange):
					bodyItems = append(bodyItems, s.rect())
				case is(c, cBlack) || is(f, cBlack):
					if s.length() < 30 {
						black = append(black, s)
					}
				}
			case 'c':
				switch {
				case is(c, cRed) && is(f, cRed):
					junc = append(junc, pt{(pr.x0 + pr.x1) / 2, (pr.y0 + pr.y1) / 2})
				case is(c, cOrange) || is(f, cOrange) || is(c, cBrown):
					bodyItems = append(bodyItems, pr)
				}
			case 'r':
				if is(c, cOrange) || is(f, cOrange) {
					bodyItems = append(bodyItems, pr)
				}
			}
		}
	}
	pins = mergePins(pins)
	e := &extracted{}
	for _, s := range wires {
		e.segs = append(e.segs, s)
		e.kinds = append(e.kinds, 'w')
	}
	for _, s := range black {
		e.segs = append(e.segs, s)
		e.kinds = append(e.kinds, 'b')
	}
	n := len(e.segs)
	u := newUF(n)
	e.u = u
	for k := 0; k < n; k++ {
		s, t := e.segs[k], e.kinds[k]
		for _, ep := range s.ends() {
			for m := 0; m < n; m++ {
				if m == k {
					continue
				}
				s2, t2 := e.segs[m], e.kinds[m]
				if t == 'w' && t2 == 'w' {
					if math.Min(math.Hypot(ep.x-s2.x1, ep.y-s2.y1), math.Hypot(ep.x-s2.x2, ep.y-s2.y2)) <= tol {
						u.u(k, m)
					}
					continue
				}
				tl := 2.0
				if t == 'b' && t2 == 'b' {
					tl = 1.5
				}
				if (t == 'w' || s.axis()) && (t2 == 'w' || s2.axis()) && segPtDist(s2, ep) <= tl {
					u.u(k, m)
				}
			}
		}
	}
	// ground symbol bars
	var bl []int
	for k := 0; k < n; k++ {
		s := e.segs[k]
		if e.kinds[k] == 'b' && math.Abs(s.y1-s.y2) < 0.3 && math.Abs(s.x1-s.x2) >= 3.0 {
			bl = append(bl, k)
		}
	}
	for i := 0; i < len(bl); i++ {
		sa := e.segs[bl[i]]
		for j := i + 1; j < len(bl); j++ {
			sb := e.segs[bl[j]]
			if math.Abs((sa.x1+sa.x2)/2-(sb.x1+sb.x2)/2) <= 1.0 && math.Abs(sa.y1-sb.y1) <= 2.6 {
				u.u(bl[i], bl[j])
			}
		}
	}
	for _, jp := range junc {
		first := -1
		for k := 0; k < n; k++ {
			if segPtDist(e.segs[k], jp) <= 2.0 {
				if first < 0 {
					first = k
				} else {
					u.u(first, k)
				}
			}
		}
	}
	// pins -> nets
	for _, s := range pins {
		r := &pinRec{s: s, net: -1, body: -1}
		for _, ep := range s.ends() {
			for m := 0; m < n; m++ {
				if segPtDist(e.segs[m], ep) <= tol {
					r.net = m
					break
				}
			}
			if r.net >= 0 {
				break
			}
		}
		e.pins = append(e.pins, r)
	}
	// pins joined directly without a wire
	for a := 0; a < len(pins); a++ {
		for b := a + 1; b < len(pins); b++ {
			for _, ep := range pins[a].ends() {
				if segPtDist(pins[b], ep) <= tol {
					pa, pb := e.pins[a], e.pins[b]
					switch {
					case pa.net < 0 && pb.net < 0:
						id := u.add()
						pa.net, pb.net = id, id
					case pa.net < 0:
						pa.net = pb.net
					case pb.net < 0:
						pb.net = pa.net
					default:
						u.u(pa.net, pb.net)
					}
				}
			}
		}
	}
	// bodies: cluster orange items
	e.bodies, e.items = cluster(bodyItems, 2.5)
	e.texts = pageTexts(pc)
	e.labels()
	return e
}

func round2(v float64) float64 { return math.Round(v*100) / 100 }

func cluster(items []rect, d float64) ([]rect, [][]rect) {
	u := newUF(len(items))
	for a := range items {
		for b := a + 1; b < len(items); b++ {
			if rectDist(items[a], items[b]) <= d {
				u.u(a, b)
			}
		}
	}
	idx := map[int]int{}
	var bbs []rect
	var groups [][]rect
	for a := range items {
		r := u.f(a)
		k, ok := idx[r]
		if !ok {
			k = len(bbs)
			idx[r] = k
			bbs = append(bbs, items[a])
			groups = append(groups, nil)
		}
		bbs[k] = union(bbs[k], items[a])
		groups[k] = append(groups[k], items[a])
	}
	return bbs, groups
}

func mergePins(in []seg) []seg {
	ps := append([]seg{}, in...)
	for changed := true; changed; {
		changed = false
	outer:
		for a := 0; a < len(ps); a++ {
			for b := a + 1; b < len(ps); b++ {
				sa, sb := ps[a], ps[b]
				ha, hb := math.Abs(sa.y1-sa.y2) < 0.3, math.Abs(sb.y1-sb.y2) < 0.3
				va, vb := math.Abs(sa.x1-sa.x2) < 0.3, math.Abs(sb.x1-sb.x2) < 0.3
				if ha && hb && math.Abs(sa.y1-sb.y1) < 0.3 {
					xa0, xa1 := math.Min(sa.x1, sa.x2), math.Max(sa.x1, sa.x2)
					xb0, xb1 := math.Min(sb.x1, sb.x2), math.Max(sb.x1, sb.x2)
					if xa1 >= xb0-0.6 && xb1 >= xa0-0.6 {
						ps[a] = seg{math.Min(xa0, xb0), sa.y1, math.Max(xa1, xb1), sa.y1}
						ps = append(ps[:b], ps[b+1:]...)
						changed = true
						break outer
					}
				} else if va && vb && math.Abs(sa.x1-sb.x1) < 0.3 {
					ya0, ya1 := math.Min(sa.y1, sa.y2), math.Max(sa.y1, sa.y2)
					yb0, yb1 := math.Min(sb.y1, sb.y2), math.Max(sb.y1, sb.y2)
					if ya1 >= yb0-0.6 && yb1 >= ya0-0.6 {
						ps[a] = seg{sa.x1, math.Min(ya0, yb0), sa.x1, math.Max(ya1, yb1)}
						ps = append(ps[:b], ps[b+1:]...)
						changed = true
						break outer
					}
				}
			}
		}
	}
	return ps
}

var powerPrefixes = []string{"GND", "PGND", "FGND", "AGND", "VDD", "VCC", "VDDA", "PHV", "VSS", "PV_"}

// labels associates net label texts with nets.
func (e *extracted) labels() {
	type sg struct {
		k int
		s seg
	}
	byNet := map[int][]sg{}
	for k := range e.segs {
		byNet[e.u.f(k)] = append(byNet[e.u.f(k)], sg{k, e.segs[k]})
	}
	for _, t := range e.texts {
		s := strings.TrimSpace(t.t)
		t.near = -1
		if s == "" || reDigits.MatchString(s) || reRefdes.MatchString(s) {
			continue
		}
		bb := t.bb
		horiz := (bb.x1 - bb.x0) >= (bb.y1 - bb.y0)
		best, bestNet := -1.0, -1
		try := func(d float64, net int) {
			if best < 0 || d < best {
				best, bestNet = d, net
			}
		}
		if t.col == colRed {
			cx, cy := (bb.x0+bb.x1)/2, (bb.y0+bb.y1)/2
			for k, ws := range e.segs {
				if e.kinds[k] != 'w' {
					continue
				}
				for _, ep := range ws.ends() {
					if horiz {
						if math.Abs(ep.y-cy) <= 3.5 && ((bb.x1-0.5 <= ep.x && ep.x <= bb.x1+12.5) || (bb.x0-12.5 <= ep.x && ep.x <= bb.x0+0.5)) {
							try(math.Min(math.Abs(ep.x-bb.x1), math.Abs(ep.x-bb.x0))+3*math.Abs(ep.y-cy), e.u.f(k))
						}
					} else {
						if math.Abs(ep.x-cx) <= 3.5 && ((bb.y1-0.5 <= ep.y && ep.y <= bb.y1+12.5) || (bb.y0-12.5 <= ep.y && ep.y <= bb.y0+0.5)) {
							try(math.Min(math.Abs(ep.y-bb.y1), math.Abs(ep.y-bb.y0))+3*math.Abs(ep.x-cx), e.u.f(k))
						}
					}
				}
			}
		} else {
			power := false
			for _, p := range powerPrefixes {
				if strings.HasPrefix(s, p) {
					power = true
				}
			}
			for net, ss := range byNet {
				for _, x := range ss {
					sgm := x.s
					var d float64
					if e.kinds[x.k] == 'w' {
						hs, vs := math.Abs(sgm.y1-sgm.y2) < 0.3, math.Abs(sgm.x1-sgm.x2) < 0.3
						if horiz && hs {
							if !(math.Min(sgm.x1, sgm.x2)-1 <= bb.x1 && math.Max(sgm.x1, sgm.x2)+1 >= bb.x0) {
								continue
							}
							dy := sgm.y1 - bb.y1
							if dy < -0.6 || dy > 2.8 {
								continue
							}
							d = math.Abs(dy)
						} else if !horiz && vs {
							if !(math.Min(sgm.y1, sgm.y2)-1 <= bb.y1 && math.Max(sgm.y1, sgm.y2)+1 >= bb.y0) {
								continue
							}
							dx := math.Min(math.Abs(bb.x0-sgm.x1), math.Abs(sgm.x1-bb.x1))
							if dx > 2.8 {
								continue
							}
							d = dx
						} else {
							continue
						}
					} else {
						if !power {
							continue
						}
						d = rectDist(bb, sgm.rect())
						if d > 3.0 {
							continue
						}
					}
					try(d, net)
				}
			}
		}
		t.near, t.nearID = best, bestNet
	}
}
