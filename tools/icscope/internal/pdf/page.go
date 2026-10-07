package pdf

import "errors"

type Page struct {
	r         *Reader
	Dict      Dict
	Resources Dict
	MediaBox  [4]float64
	Rotate    int
	Index     int
}

func (r *Reader) NumPages() int    { return len(r.pages) }
func (r *Reader) Page(i int) *Page { return r.pages[i] }

func (r *Reader) loadPages() error {
	root, _ := r.resolve(r.trailer["Root"]).(Dict)
	if root == nil {
		return errors.New("no document catalog")
	}
	var walk func(o Object, inh Dict, depth int)
	visited := map[int]bool{}
	walk = func(o Object, inh Dict, depth int) {
		if depth > 64 {
			return
		}
		if ref, ok := o.(Ref); ok {
			if visited[ref.Num] {
				return
			}
			visited[ref.Num] = true
		}
		d, _ := r.resolve(o).(Dict)
		if d == nil {
			return
		}
		next := Dict{}
		for k, v := range inh {
			next[k] = v
		}
		for _, k := range []Name{"Resources", "MediaBox", "CropBox", "Rotate"} {
			if v, ok := d[k]; ok {
				next[k] = v
			}
		}
		kids, isTree := r.resolve(d["Kids"]).(Array)
		if d.Name("Type") == "Pages" || (isTree && d.Name("Type") != "Page") {
			for _, k := range kids {
				walk(k, next, depth+1)
			}
			return
		}
		pg := &Page{r: r, Dict: d, Index: len(r.pages)}
		pg.Resources, _ = r.resolve(next["Resources"]).(Dict)
		box := next["CropBox"]
		if box == nil {
			box = next["MediaBox"]
		}
		pg.MediaBox = [4]float64{0, 0, 612, 792}
		if a, ok := r.resolve(box).(Array); ok && len(a) == 4 {
			for i := range a {
				pg.MediaBox[i] = numOr(r.resolve(a[i]), 0)
			}
			if pg.MediaBox[0] > pg.MediaBox[2] {
				pg.MediaBox[0], pg.MediaBox[2] = pg.MediaBox[2], pg.MediaBox[0]
			}
			if pg.MediaBox[1] > pg.MediaBox[3] {
				pg.MediaBox[1], pg.MediaBox[3] = pg.MediaBox[3], pg.MediaBox[1]
			}
		}
		pg.Rotate = ((intOr(r.resolve(next["Rotate"]), 0) % 360) + 360) % 360
		r.pages = append(r.pages, pg)
	}
	walk(root["Pages"], Dict{}, 0)
	if len(r.pages) == 0 {
		return errors.New("no pages")
	}
	return nil
}

// Contents returns the concatenated, decoded content streams of the page.
func (p *Page) Contents() []byte {
	var out []byte
	add := func(o Object) {
		if s, ok := p.r.resolve(o).(*Stream); ok {
			if d, err := p.r.StreamData(s); err == nil {
				out = append(out, d...)
				out = append(out, '\n')
			}
		}
	}
	switch c := p.r.resolve(p.Dict["Contents"]).(type) {
	case Array:
		for _, x := range c {
			add(x)
		}
	case *Stream:
		add(c)
	}
	return out
}

// Size returns the displayed width and height (after rotation).
func (p *Page) Size() (float64, float64) {
	w := p.MediaBox[2] - p.MediaBox[0]
	h := p.MediaBox[3] - p.MediaBox[1]
	if p.Rotate == 90 || p.Rotate == 270 {
		return h, w
	}
	return w, h
}

// displayMatrix maps default user space to displayed space: origin top-left,
// y down, page rotation applied. Matches what viewers (and MuPDF) show.
func (p *Page) displayMatrix() Matrix {
	x0, y0, x1, y1 := p.MediaBox[0], p.MediaBox[1], p.MediaBox[2], p.MediaBox[3]
	// flip to y-down with origin at the top-left of the box
	m := Matrix{1, 0, 0, -1, -x0, y1}
	w, h := x1-x0, y1-y0
	switch p.Rotate {
	case 90:
		m = m.Mul(Matrix{0, 1, -1, 0, h, 0})
	case 180:
		m = m.Mul(Matrix{-1, 0, 0, -1, w, h})
	case 270:
		m = m.Mul(Matrix{0, -1, 1, 0, 0, w})
	}
	return m
}
