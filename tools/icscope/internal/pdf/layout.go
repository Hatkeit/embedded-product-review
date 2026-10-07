package pdf

import (
	"math"
	"sort"
	"strings"
)

// Word is a run of glyphs without a visible gap.
type Word struct {
	Text           string
	X0, Y0, X1, Y1 float64
	Size           float64
	Color          RGB
	Dir            Point
	Bold           bool
}

// Line is a set of words sharing a baseline, ordered along the text direction.
type Line struct {
	Words          []Word
	X0, Y0, X1, Y1 float64
	Size           float64
}

func (l Line) Text() string {
	var b strings.Builder
	for i, w := range l.Words {
		if i > 0 {
			b.WriteByte(' ')
		}
		b.WriteString(w.Text)
	}
	return b.String()
}

// Words groups the glyphs of horizontal (and other) text into words.
func Words(gs []Glyph) []Word {
	var out []Word
	var cur *Word
	var last Glyph
	flush := func() {
		if cur != nil && strings.TrimSpace(cur.Text) != "" {
			cur.Text = strings.TrimSpace(cur.Text)
			out = append(out, *cur)
		}
		cur = nil
	}
	for _, g := range gs {
		if g.Invisible {
			continue
		}
		t := g.Text
		if t == "" || t == " " {
			t = " "
		}
		if strings.TrimSpace(t) == "" {
			flush()
			last = g
			continue
		}
		if cur != nil {
			same := math.Abs(g.Dir.X-last.Dir.X) < 0.01 && math.Abs(g.Dir.Y-last.Dir.Y) < 0.01
			// distance along the direction from the previous glyph end and across it
			ex, ey := lastEnd(last)
			along := (g.OX-ex)*last.Dir.X + (g.OY-ey)*last.Dir.Y
			across := -(g.OX-last.OX)*last.Dir.Y + (g.OY-last.OY)*last.Dir.X
			tol := 0.18 * math.Max(g.Size, last.Size)
			if last.SpaceW > 0 {
				tol = math.Min(tol, 0.8*last.SpaceW)
			}
			if !same || math.Abs(across) > 0.35*math.Max(g.Size, 1) || along > tol || along < -0.6*math.Max(g.Size, 1) {
				flush()
			}
		}
		if cur == nil {
			cur = &Word{X0: g.X0, Y0: g.Y0, X1: g.X1, Y1: g.Y1, Size: g.Size, Color: g.Color, Dir: g.Dir}
			if g.Font != nil {
				lb := strings.ToLower(g.Font.BaseFont)
				cur.Bold = strings.Contains(lb, "bold") || strings.Contains(lb, "black") || strings.Contains(lb, "heavy")
			}
		}
		cur.Text += t
		cur.X0, cur.Y0 = math.Min(cur.X0, g.X0), math.Min(cur.Y0, g.Y0)
		cur.X1, cur.Y1 = math.Max(cur.X1, g.X1), math.Max(cur.Y1, g.Y1)
		last = g
	}
	flush()
	return out
}

func lastEnd(g Glyph) (float64, float64) {
	// end of the glyph along its direction: project the box extent
	w := (g.X1-g.X0)*math.Abs(g.Dir.X) + (g.Y1-g.Y0)*math.Abs(g.Dir.Y)
	return g.OX + g.Dir.X*w, g.OY + g.Dir.Y*w
}

// Lines groups horizontal words into lines (top to bottom, left to right).
func Lines(ws []Word) []Line {
	var hs []Word
	for _, w := range ws {
		if w.Dir.X > 0.9 {
			hs = append(hs, w)
		}
	}
	sort.Slice(hs, func(i, j int) bool {
		if math.Abs(hs[i].Y1-hs[j].Y1) > 0.5 {
			return hs[i].Y1 < hs[j].Y1
		}
		return hs[i].X0 < hs[j].X0
	})
	var lines []Line
	for _, w := range hs {
		placed := false
		for i := len(lines) - 1; i >= 0 && i >= len(lines)-4; i-- {
			l := &lines[i]
			// same baseline band: vertical centres within ~0.45 of the height
			cy := (w.Y0 + w.Y1) / 2
			ly := (l.Y0 + l.Y1) / 2
			h := math.Max(math.Min(w.Y1-w.Y0, l.Y1-l.Y0), 1)
			if math.Abs(cy-ly) < 0.45*h {
				l.Words = append(l.Words, w)
				l.X0, l.Y0 = math.Min(l.X0, w.X0), math.Min(l.Y0, w.Y0)
				l.X1, l.Y1 = math.Max(l.X1, w.X1), math.Max(l.Y1, w.Y1)
				placed = true
				break
			}
		}
		if !placed {
			lines = append(lines, Line{Words: []Word{w}, X0: w.X0, Y0: w.Y0, X1: w.X1, Y1: w.Y1, Size: w.Size})
		}
	}
	for i := range lines {
		sort.Slice(lines[i].Words, func(a, b int) bool { return lines[i].Words[a].X0 < lines[i].Words[b].X0 })
	}
	sort.SliceStable(lines, func(i, j int) bool { return lines[i].Y0 < lines[j].Y0 })
	return lines
}
