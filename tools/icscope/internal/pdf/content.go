package pdf

import (
	"bytes"
	"fmt"
	"math"
)

type RGB [3]float64

type Point struct{ X, Y float64 }

// Glyph is one shown character in displayed page coordinates (y down).
type Glyph struct {
	Text      string
	Code      int
	GlyphName string
	Font      *Font
	FontID    string
	Size      float64
	Color     RGB
	X0, Y0    float64
	X1, Y1    float64
	OX, OY    float64 // origin on the baseline
	Dir       Point   // unit advance direction
	Show      int     // index of the text-showing operation
	Invisible bool
	SpaceW    float64 // width of a space in display units, for word splitting
	Adv       float64 // glyph advance in display units (without char/word spacing)
}

type PathItem struct {
	Kind byte // 'l' line, 'c' curve, 'r' rectangle (4 corners)
	P    []Point
}

type Path struct {
	Stroke, Fill bool
	SColor       RGB
	FColor       RGB
	Width        float64
	Items        []PathItem
	X0, Y0       float64
	X1, Y1       float64
}

type gstate struct {
	ctm      Matrix
	fill     RGB
	stroke   RGB
	fillCS   csInfo
	strokeCS csInfo
	lw       float64
	font     *Font
	fontID   string
	size     float64
	tc, tw   float64
	th       float64
	tl, rise float64
	mode     int
}

type csInfo struct {
	n      int // components
	kind   string
	lookup []byte // Indexed
	baseN  int
	hival  int
}

// PageContent is the result of interpreting a page.
type PageContent struct {
	Width, Height float64
	Glyphs        []Glyph
	Paths         []Path
}

type interp struct {
	r     *Reader
	page  *Page
	out   *PageContent
	gs    gstate
	stack []gstate
	tm    Matrix
	tlm   Matrix
	disp  Matrix
	fonts map[string]*Font
	show  int
	path  []PathItem
	cur   Point
	start Point
	depth int
}

// Interpret runs the page content stream.
func (p *Page) Interpret() *PageContent {
	w, h := p.Size()
	ip := &interp{r: p.r, page: p, out: &PageContent{Width: w, Height: h}, fonts: map[string]*Font{}}
	ip.gs = gstate{ctm: Identity, lw: 1, th: 1, fillCS: csInfo{n: 1, kind: "gray"}, strokeCS: csInfo{n: 1, kind: "gray"}}
	ip.disp = p.displayMatrix()
	ip.run(p.Contents(), p.Resources)
	ip.out.Paths = mergeFillStroke(ip.out.Paths)
	return ip.out
}

func (ip *interp) run(data []byte, res Dict) {
	if ip.depth > 12 {
		return
	}
	ip.depth++
	defer func() { ip.depth-- }()
	p := parser{lx: lexer{b: data}}
	var ops []Object
	for {
		o, ok := p.object(0)
		if !ok {
			return
		}
		kw, isOp := o.(Keyword)
		if !isOp {
			ops = append(ops, o)
			if len(ops) > 4096 {
				ops = ops[:0]
			}
			continue
		}
		if kw == "BI" {
			ip.skipInlineImage(&p)
			ops = ops[:0]
			continue
		}
		ip.op(string(kw), ops, res)
		ops = ops[:0]
	}
}

func (ip *interp) skipInlineImage(p *parser) {
	b := p.lx.b
	i := bytes.Index(b[p.lx.pos:], []byte("ID"))
	if i < 0 {
		p.lx.pos = len(b)
		return
	}
	pos := p.lx.pos + i + 3
	for pos < len(b) {
		j := bytes.Index(b[pos:], []byte("EI"))
		if j < 0 {
			p.lx.pos = len(b)
			return
		}
		e := pos + j
		before := e == 0 || isWhite(b[e-1])
		after := e+2 >= len(b) || isWhite(b[e+2])
		if before && after {
			p.lx.pos = e + 2
			return
		}
		pos = e + 2
	}
	p.lx.pos = len(b)
}

func nums(ops []Object, n int) ([]float64, bool) {
	if len(ops) < n {
		return nil, false
	}
	out := make([]float64, n)
	for i := 0; i < n; i++ {
		v, ok := num(ops[len(ops)-n+i])
		if !ok {
			return nil, false
		}
		out[i] = v
	}
	return out, true
}

func (ip *interp) toDisp(x, y float64) Point {
	m := ip.gs.ctm.Mul(ip.disp)
	a, b := m.Apply(x, y)
	return Point{a, b}
}

func (ip *interp) op(op string, ops []Object, res Dict) {
	g := &ip.gs
	switch op {
	case "q":
		ip.stack = append(ip.stack, *g)
	case "Q":
		if n := len(ip.stack); n > 0 {
			*g = ip.stack[n-1]
			ip.stack = ip.stack[:n-1]
		}
	case "cm":
		if v, ok := nums(ops, 6); ok {
			g.ctm = Matrix{v[0], v[1], v[2], v[3], v[4], v[5]}.Mul(g.ctm)
		}
	case "w":
		if v, ok := nums(ops, 1); ok {
			g.lw = v[0]
		}
	case "gs":
		if len(ops) > 0 {
			if egs, ok := ip.r.resolve(ip.resDict(res, "ExtGState")[nameOf(ops[len(ops)-1])]).(Dict); ok {
				if lw, ok := num(ip.r.resolve(egs["LW"])); ok {
					g.lw = lw
				}
				if fa, ok := ip.r.resolve(egs["Font"]).(Array); ok && len(fa) == 2 {
					g.font = ip.r.loadFont(fa[0])
					g.fontID = fmt.Sprint(fa[0])
					g.size = numOr(ip.r.resolve(fa[1]), g.size)
				}
			}
		}
	// colour
	case "g", "G", "rg", "RG", "k", "K":
		n := map[string]int{"g": 1, "G": 1, "rg": 3, "RG": 3, "k": 4, "K": 4}[op]
		if v, ok := nums(ops, n); ok {
			c := toRGB(v)
			cs := csInfo{n: n}
			if op[0] >= 'a' {
				g.fill, g.fillCS = c, cs
			} else {
				g.stroke, g.strokeCS = c, cs
			}
		}
	case "cs", "CS":
		if len(ops) > 0 {
			cs := ip.colorSpace(ops[len(ops)-1], res)
			init := RGB{}
			if cs.kind == "indexed" || cs.kind == "sep" {
				init = ip.csColor(cs, []float64{0})
			}
			if op == "cs" {
				g.fillCS, g.fill = cs, init
			} else {
				g.strokeCS, g.stroke = cs, init
			}
		}
	case "sc", "scn", "SC", "SCN":
		var vals []float64
		for _, o := range ops {
			if v, ok := num(o); ok {
				vals = append(vals, v)
			}
		}
		if len(vals) == 0 {
			return
		}
		if op[0] == 's' {
			g.fill = ip.csColor(g.fillCS, vals)
		} else {
			g.stroke = ip.csColor(g.strokeCS, vals)
		}
	// path construction
	case "m":
		if v, ok := nums(ops, 2); ok {
			ip.cur = ip.toDisp(v[0], v[1])
			ip.start = ip.cur
		}
	case "l":
		if v, ok := nums(ops, 2); ok {
			p := ip.toDisp(v[0], v[1])
			ip.path = append(ip.path, PathItem{'l', []Point{ip.cur, p}})
			ip.cur = p
		}
	case "c":
		if v, ok := nums(ops, 6); ok {
			p1, p2, p3 := ip.toDisp(v[0], v[1]), ip.toDisp(v[2], v[3]), ip.toDisp(v[4], v[5])
			ip.path = append(ip.path, PathItem{'c', []Point{ip.cur, p1, p2, p3}})
			ip.cur = p3
		}
	case "v":
		if v, ok := nums(ops, 4); ok {
			p2, p3 := ip.toDisp(v[0], v[1]), ip.toDisp(v[2], v[3])
			ip.path = append(ip.path, PathItem{'c', []Point{ip.cur, ip.cur, p2, p3}})
			ip.cur = p3
		}
	case "y":
		if v, ok := nums(ops, 4); ok {
			p1, p3 := ip.toDisp(v[0], v[1]), ip.toDisp(v[2], v[3])
			ip.path = append(ip.path, PathItem{'c', []Point{ip.cur, p1, p3, p3}})
			ip.cur = p3
		}
	case "h":
		if math.Abs(ip.cur.X-ip.start.X) > 1e-6 || math.Abs(ip.cur.Y-ip.start.Y) > 1e-6 {
			ip.path = append(ip.path, PathItem{'l', []Point{ip.cur, ip.start}})
		}
		ip.cur = ip.start
	case "re":
		if v, ok := nums(ops, 4); ok {
			x, y, w, h := v[0], v[1], v[2], v[3]
			pts := []Point{ip.toDisp(x, y), ip.toDisp(x+w, y), ip.toDisp(x+w, y+h), ip.toDisp(x, y+h)}
			ip.path = append(ip.path, PathItem{'r', pts})
			ip.cur = pts[0]
			ip.start = pts[0]
		}
	case "S", "s", "f", "F", "f*", "B", "B*", "b", "b*":
		stroke := op == "S" || op == "s" || op[0] == 'B' || op[0] == 'b'
		fill := op != "S" && op != "s"
		ip.emitPath(stroke, fill)
	case "n":
		ip.path = nil
	case "W", "W*":
	// text
	case "BT":
		ip.tm, ip.tlm = Identity, Identity
	case "ET":
	case "Tc":
		if v, ok := nums(ops, 1); ok {
			g.tc = v[0]
		}
	case "Tw":
		if v, ok := nums(ops, 1); ok {
			g.tw = v[0]
		}
	case "Tz":
		if v, ok := nums(ops, 1); ok {
			g.th = v[0] / 100
		}
	case "TL":
		if v, ok := nums(ops, 1); ok {
			g.tl = v[0]
		}
	case "Ts":
		if v, ok := nums(ops, 1); ok {
			g.rise = v[0]
		}
	case "Tr":
		if v, ok := nums(ops, 1); ok {
			g.mode = int(v[0])
		}
	case "Tf":
		if len(ops) >= 2 {
			name := nameOf(ops[len(ops)-2])
			g.size = numOr(ops[len(ops)-1], 0)
			fd := ip.resDict(res, "Font")
			fo := fd[name]
			key := fmt.Sprint(fo)
			if _, isRef := fo.(Ref); !isRef {
				key = fmt.Sprintf("%p/%s", res, name)
			}
			f, ok := ip.fonts[key]
			if !ok {
				f = ip.r.loadFont(fo)
				ip.fonts[key] = f
			}
			g.font, g.fontID = f, key
		}
	case "Td":
		if v, ok := nums(ops, 2); ok {
			ip.tlm = Matrix{1, 0, 0, 1, v[0], v[1]}.Mul(ip.tlm)
			ip.tm = ip.tlm
		}
	case "TD":
		if v, ok := nums(ops, 2); ok {
			g.tl = -v[1]
			ip.tlm = Matrix{1, 0, 0, 1, v[0], v[1]}.Mul(ip.tlm)
			ip.tm = ip.tlm
		}
	case "Tm":
		if v, ok := nums(ops, 6); ok {
			ip.tlm = Matrix{v[0], v[1], v[2], v[3], v[4], v[5]}
			ip.tm = ip.tlm
		}
	case "T*":
		ip.tlm = Matrix{1, 0, 0, 1, 0, -g.tl}.Mul(ip.tlm)
		ip.tm = ip.tlm
	case "Tj":
		if len(ops) > 0 {
			if s, ok := ops[len(ops)-1].(String); ok {
				ip.showText(Array{s})
			}
		}
	case "'":
		ip.tlm = Matrix{1, 0, 0, 1, 0, -g.tl}.Mul(ip.tlm)
		ip.tm = ip.tlm
		if len(ops) > 0 {
			if s, ok := ops[len(ops)-1].(String); ok {
				ip.showText(Array{s})
			}
		}
	case "\"":
		if len(ops) >= 3 {
			g.tw = numOr(ops[len(ops)-3], g.tw)
			g.tc = numOr(ops[len(ops)-2], g.tc)
			ip.tlm = Matrix{1, 0, 0, 1, 0, -g.tl}.Mul(ip.tlm)
			ip.tm = ip.tlm
			if s, ok := ops[len(ops)-1].(String); ok {
				ip.showText(Array{s})
			}
		}
	case "TJ":
		if len(ops) > 0 {
			if a, ok := ops[len(ops)-1].(Array); ok {
				ip.showText(a)
			}
		}
	case "Do":
		if len(ops) == 0 {
			return
		}
		xo, ok := ip.r.resolve(ip.resDict(res, "XObject")[nameOf(ops[len(ops)-1])]).(*Stream)
		if !ok || xo.Dict.Name("Subtype") != "Form" {
			return
		}
		data, err := ip.r.StreamData(xo)
		if err != nil {
			return
		}
		saved := *g
		savedStack := len(ip.stack)
		if m, ok := ip.r.resolve(xo.Dict["Matrix"]).(Array); ok {
			g.ctm = matrixFrom(resolveArr(ip.r, m)).Mul(g.ctm)
		}
		sub, _ := ip.r.resolve(xo.Dict["Resources"]).(Dict)
		if sub == nil {
			sub = res
		}
		savedPath := ip.path
		ip.path = nil
		ip.run(data, sub)
		ip.path = savedPath
		ip.stack = ip.stack[:min(savedStack, len(ip.stack))]
		*g = saved
	}
}

func (ip *interp) resDict(res Dict, key Name) Dict {
	d, _ := ip.r.resolve(res[key]).(Dict)
	if d == nil {
		return Dict{}
	}
	return d
}

func toRGB(v []float64) RGB {
	switch len(v) {
	case 1:
		return RGB{v[0], v[0], v[0]}
	case 3:
		return RGB{v[0], v[1], v[2]}
	case 4:
		c, m, y, k := v[0], v[1], v[2], v[3]
		return RGB{(1 - c) * (1 - k), (1 - m) * (1 - k), (1 - y) * (1 - k)}
	}
	return RGB{}
}

func (ip *interp) colorSpace(o Object, res Dict) csInfo {
	n := nameOf(o)
	switch n {
	case "DeviceGray", "G", "CalGray":
		return csInfo{n: 1}
	case "DeviceRGB", "RGB", "CalRGB":
		return csInfo{n: 3}
	case "DeviceCMYK", "CMYK":
		return csInfo{n: 4}
	case "Pattern":
		return csInfo{n: 0, kind: "pattern"}
	}
	def := ip.r.resolve(ip.resDict(res, "ColorSpace")[n])
	return ip.csFromDef(def, res, 0)
}

func (ip *interp) csFromDef(def Object, res Dict, depth int) csInfo {
	if depth > 4 {
		return csInfo{n: 3}
	}
	switch v := def.(type) {
	case Name:
		return ip.colorSpace(v, Dict{})
	case Array:
		if len(v) == 0 {
			return csInfo{n: 3}
		}
		switch nameOf(ip.r.resolve(v[0])) {
		case "ICCBased":
			if len(v) > 1 {
				if s, ok := ip.r.resolve(v[1]).(*Stream); ok {
					return csInfo{n: intOr(ip.r.resolve(s.Dict["N"]), 3)}
				}
			}
		case "CalRGB", "Lab":
			return csInfo{n: 3}
		case "CalGray":
			return csInfo{n: 1}
		case "Indexed", "I":
			if len(v) >= 4 {
				base := ip.csFromDef(ip.r.resolve(v[1]), res, depth+1)
				var lut []byte
				switch l := ip.r.resolve(v[3]).(type) {
				case String:
					lut = l
				case *Stream:
					lut, _ = ip.r.StreamData(l)
				}
				return csInfo{n: 1, kind: "indexed", lookup: lut, baseN: base.n, hival: intOr(ip.r.resolve(v[2]), 255)}
			}
		case "Separation", "DeviceN":
			return csInfo{n: 1, kind: "sep"}
		case "Pattern":
			return csInfo{n: 0, kind: "pattern"}
		}
	}
	return csInfo{n: 3}
}

func (ip *interp) csColor(cs csInfo, vals []float64) RGB {
	switch cs.kind {
	case "indexed":
		i := int(vals[0])
		if cs.baseN <= 0 || (i+1)*cs.baseN > len(cs.lookup) {
			return RGB{}
		}
		comp := make([]float64, cs.baseN)
		for k := range comp {
			comp[k] = float64(cs.lookup[i*cs.baseN+k]) / 255
		}
		return toRGB(comp)
	case "sep":
		t := 1 - vals[0]
		return RGB{t, t, t}
	case "pattern":
		return RGB{}
	}
	switch {
	case cs.n == 4 && len(vals) >= 4:
		return toRGB(vals[:4])
	case cs.n == 3 && len(vals) >= 3:
		return toRGB(vals[:3])
	}
	return toRGB(vals[:1])
}

func (ip *interp) emitPath(stroke, fill bool) {
	if len(ip.path) == 0 {
		return
	}
	p := Path{Stroke: stroke, Fill: fill, Items: ip.path}
	if stroke {
		p.SColor = ip.gs.stroke
		p.Width = ip.gs.lw * ip.gs.ctm.Mul(ip.disp).Scale()
	}
	if fill {
		p.FColor = ip.gs.fill
	}
	p.X0, p.Y0 = math.Inf(1), math.Inf(1)
	p.X1, p.Y1 = math.Inf(-1), math.Inf(-1)
	for _, it := range p.Items {
		for _, q := range it.P {
			p.X0, p.Y0 = math.Min(p.X0, q.X), math.Min(p.Y0, q.Y)
			p.X1, p.Y1 = math.Max(p.X1, q.X), math.Max(p.Y1, q.Y)
		}
	}
	ip.out.Paths = append(ip.out.Paths, p)
	ip.path = nil
}

// mergeFillStroke joins a fill immediately followed by a stroke of the same
// geometry into one path (as viewers report "fs" drawings).
func mergeFillStroke(ps []Path) []Path {
	var out []Path
	for i := 0; i < len(ps); i++ {
		p := ps[i]
		if p.Fill && !p.Stroke && i+1 < len(ps) {
			q := ps[i+1]
			if q.Stroke && !q.Fill && sameGeom(p, q) {
				p.Stroke, p.SColor, p.Width = true, q.SColor, q.Width
				i++
			}
		}
		out = append(out, p)
	}
	return out
}

func sameGeom(a, b Path) bool {
	if len(a.Items) != len(b.Items) {
		return false
	}
	for i := range a.Items {
		if a.Items[i].Kind != b.Items[i].Kind || len(a.Items[i].P) != len(b.Items[i].P) {
			return false
		}
		for k := range a.Items[i].P {
			if math.Abs(a.Items[i].P[k].X-b.Items[i].P[k].X) > 0.01 || math.Abs(a.Items[i].P[k].Y-b.Items[i].P[k].Y) > 0.01 {
				return false
			}
		}
	}
	return true
}

func (ip *interp) showText(parts Array) {
	g := &ip.gs
	f := g.font
	if f == nil {
		return
	}
	ip.show++
	full := g.ctm.Mul(ip.disp)
	for _, part := range parts {
		if adj, ok := num(part); ok {
			tx := -adj / 1000 * g.size * g.th
			if f.vertical {
				ip.tm = Matrix{1, 0, 0, 1, 0, -adj / 1000 * g.size}.Mul(ip.tm)
			} else {
				ip.tm = Matrix{1, 0, 0, 1, tx, 0}.Mul(ip.tm)
			}
			continue
		}
		s, ok := part.(String)
		if !ok {
			continue
		}
		codes := f.codes(s)
		for _, code := range codes {
			w0 := f.Width(code)
			trm := Matrix{g.size * g.th, 0, 0, g.size, 0, g.rise}.Mul(ip.tm).Mul(full)
			// glyph box: origin O, advance A and visual "up" U in display space
			ox, oy := trm.Apply(0, 0)
			axx, ayy := trm.Apply(w0, 0)
			ux, uy := trm.Apply(0, 1)
			A := Point{axx - ox, ayy - oy}
			U := Point{ux - ox, uy - oy}
			if A.X*U.Y-A.Y*U.X > 0 { // mirrored text space: make U point visually up
				U = Point{-U.X, -U.Y}
			}
			asc, desc := f.Ascent, f.Descent
			if f.type3 && asc-desc < 0.5 {
				asc, desc = 1, 0
			}
			x0, y0 := math.Inf(1), math.Inf(1)
			x1, y1 := math.Inf(-1), math.Inf(-1)
			for _, c := range [4][2]float64{{0, desc}, {1, desc}, {1, asc}, {0, asc}} {
				x := ox + A.X*c[0] + U.X*c[1]
				y := oy + A.Y*c[0] + U.Y*c[1]
				x0, y0 = math.Min(x0, x), math.Min(y0, y)
				x1, y1 = math.Max(x1, x), math.Max(y1, y)
			}
			ax, ay := trm.Apply(1, 0)
			dx, dy := ax-ox, ay-oy
			l := math.Hypot(dx, dy)
			if l > 0 {
				dx, dy = dx/l, dy/l
			}
			sx, sy := trm.Apply(0.25, 0)
			gl := Glyph{
				Text: f.Text(code), Code: code, GlyphName: f.GlyphName(code), Font: f, FontID: g.fontID,
				Size:  g.size * full.Scale() * math.Sqrt(math.Abs(ip.tm[0]*ip.tm[3]-ip.tm[1]*ip.tm[2])),
				Color: g.fill, X0: x0, Y0: y0, X1: x1, Y1: y1, OX: ox, OY: oy, Dir: Point{dx, dy},
				Show: ip.show, Invisible: g.mode == 3 || g.mode == 7, SpaceW: math.Hypot(sx-ox, sy-oy),
				Adv: l * f.Width(code),
			}
			if g.mode == 1 || g.mode == 5 {
				gl.Color = g.stroke
			}
			ip.out.Glyphs = append(ip.out.Glyphs, gl)
			adv := w0*g.size + g.tc
			if !f.twoByte && code == 32 {
				adv += g.tw
			}
			if f.vertical {
				ip.tm = Matrix{1, 0, 0, 1, 0, -g.size}.Mul(ip.tm)
			} else {
				ip.tm = Matrix{1, 0, 0, 1, adv * g.th, 0}.Mul(ip.tm)
			}
		}
	}
}
