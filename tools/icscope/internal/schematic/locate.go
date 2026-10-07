package schematic

import (
	"fmt"
	"math"
	"regexp"
	"strings"

	"icscope/internal/netlist"
	"icscope/internal/pdf"
)

// Loc is where a reference designator is printed.
type Loc struct {
	Page int        `json:"page"` // 0-based
	Box  [4]float64 `json:"box"`
}

// Doc keeps an interpreted schematic PDF for location lookup and drawing.
type Doc struct {
	Name  string
	R     *pdf.Reader
	pages map[int]*pdf.PageContent
	texts map[int][]*text
	OrCAD bool
	Geo   map[int]*PageGeo
}

func NewDoc(name string, r *pdf.Reader) *Doc {
	d := &Doc{Name: name, R: r, pages: map[int]*pdf.PageContent{}, texts: map[int][]*text{}}
	for i := 0; i < r.NumPages() && i < 3; i++ {
		if Detect(d.Page(i)) {
			d.OrCAD = true
		}
	}
	return d
}

func (d *Doc) Page(i int) *pdf.PageContent {
	if pc, ok := d.pages[i]; ok {
		return pc
	}
	pc := d.R.Page(i).Interpret()
	d.pages[i] = pc
	return pc
}

func (d *Doc) Texts(i int) []*text {
	if t, ok := d.texts[i]; ok {
		return t
	}
	t := pageTexts(d.Page(i))
	d.texts[i] = t
	return t
}

var reSecSuffix = regexp.MustCompile(`^(.*\d)([A-H])$`)

// Locate finds the printed reference designator (or its sections U2A, U2B).
func (d *Doc) Locate(ref string) []Loc {
	var out []Loc
	for i := 0; i < d.R.NumPages(); i++ {
		for _, t := range d.Texts(i) {
			s := strings.TrimSpace(t.t)
			if s == ref {
				out = append(out, Loc{i, [4]float64{t.bb.x0, t.bb.y0, t.bb.x1, t.bb.y1}})
			} else if m := reSecSuffix.FindStringSubmatch(s); m != nil && m[1] == ref {
				out = append(out, Loc{i, [4]float64{t.bb.x0, t.bb.y0, t.bb.x1, t.bb.y1}})
			}
		}
	}
	return out
}

// RefCount counts reference-designator-like strings on the first pages,
// used to tell a schematic from a datasheet.
func (d *Doc) RefCount() int {
	n := 0
	for i := 0; i < d.R.NumPages() && i < 4; i++ {
		for _, t := range d.Texts(i) {
			for _, w := range strings.Fields(t.t) {
				if reRefdes.MatchString(w) && !strings.HasPrefix(w, "P") {
					n++
				}
			}
		}
	}
	return n
}

// TextParts builds a part list (no connectivity) for schematics that are not
// OrCAD-coloured: each reference designator takes the nearest text below or
// to its right as its value lines.
func (d *Doc) TextParts(classOf func(string) string) *netlist.Netlist {
	nl := netlist.New(d.Name, "text")
	for i := 0; i < d.R.NumPages(); i++ {
		ts := d.Texts(i)
		var words []*text
		for _, t := range ts {
			// split merged runs into words, keeping the run box
			for _, w := range strings.Fields(t.t) {
				words = append(words, &text{t: w, bb: t.bb, col: t.col, size: t.size})
			}
		}
		for _, w := range words {
			if !reRefdes.MatchString(w.t) {
				continue
			}
			best := ""
			bd := math.Inf(1)
			isIC := strings.HasPrefix(w.t, "U") || strings.HasPrefix(w.t, "IC")
			var lines []string
			for _, v := range words {
				if v == w || reRefdes.MatchString(v.t) {
					continue
				}
				dx := v.bb.x0 - w.bb.x0
				dy := v.bb.y0 - w.bb.y0
				if dx < -10 || dx > 40 || dy < -2 || dy > 25 {
					continue
				}
				dist := math.Hypot(dx, dy)
				if dist < 30 && isIC {
					lines = append(lines, v.t)
				}
				if isIC && classOf(v.t) != "" && dist < bd {
					bd, best = dist, v.t
				}
			}
			ref := w.t
			if m := reSection.FindStringSubmatch(ref); m != nil {
				ref = m[1]
			}
			p := nl.Parts[ref]
			if p == nil {
				p = &netlist.Part{Ref: ref, Page: fmt.Sprint(i + 1)}
				nl.Parts[ref] = p
			}
			if best != "" && p.Value == "" {
				p.Value = best
			}
			if len(p.Lines) == 0 && len(lines) > 0 {
				if len(lines) > 4 {
					lines = lines[:4]
				}
				p.Lines = lines
			}
		}
	}
	nl.Notes = append(nl.Notes, "OrCAD 기본 색상이 아닌 회로도라 연결(넷) 정보 없이 부품 목록만 읽었습니다. 회로 형태 판정은 OrCAD 넷리스트(pstxnet.dat 등)를 함께 넣으면 가능합니다.")
	return nl
}
