package schematic

import (
	"bytes"
	"fmt"
	"html"
	"math"

	"icscope/internal/pdf"
)

func hexColor(c pdf.RGB) string {
	return fmt.Sprintf("#%02x%02x%02x", int(math.Round(c[0]*255)), int(math.Round(c[1]*255)), int(math.Round(c[2]*255)))
}

// SVG draws a page (paths and glyphs) in display coordinates.
func (d *Doc) SVG(i int) []byte {
	pc := d.Page(i)
	var b bytes.Buffer
	fmt.Fprintf(&b, `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %.1f %.1f" width="%.0f" height="%.0f">`, pc.Width, pc.Height, pc.Width, pc.Height)
	fmt.Fprintf(&b, `<rect width="100%%" height="100%%" fill="#fff"/>`)
	for _, p := range pc.Paths {
		var dd bytes.Buffer
		var last pdf.Point
		first := true
		for _, it := range p.Items {
			if len(it.P) == 0 {
				continue
			}
			s := it.P[0]
			if first || math.Abs(s.X-last.X) > 0.01 || math.Abs(s.Y-last.Y) > 0.01 {
				fmt.Fprintf(&dd, "M%.2f %.2f", s.X, s.Y)
			}
			first = false
			switch it.Kind {
			case 'l':
				e := it.P[len(it.P)-1]
				fmt.Fprintf(&dd, "L%.2f %.2f", e.X, e.Y)
				last = e
			case 'c':
				if len(it.P) == 4 {
					fmt.Fprintf(&dd, "C%.2f %.2f %.2f %.2f %.2f %.2f", it.P[1].X, it.P[1].Y, it.P[2].X, it.P[2].Y, it.P[3].X, it.P[3].Y)
					last = it.P[3]
				}
			case 'r':
				for _, q := range it.P[1:] {
					fmt.Fprintf(&dd, "L%.2f %.2f", q.X, q.Y)
				}
				dd.WriteString("Z")
				last = it.P[0]
			}
		}
		if dd.Len() == 0 {
			continue
		}
		fill, stroke := "none", "none"
		if p.Fill {
			fill = hexColor(p.FColor)
		}
		sw := ""
		if p.Stroke {
			stroke = hexColor(p.SColor)
			w := math.Max(0.25, math.Min(p.Width, 3))
			sw = fmt.Sprintf(` stroke-width="%.2f"`, w)
		}
		fmt.Fprintf(&b, `<path d="%s" fill="%s" stroke="%s"%s/>`, dd.String(), fill, stroke, sw)
	}
	b.WriteString(`<g font-family="Arial,Helvetica,sans-serif">`)
	for _, g := range pc.Glyphs {
		if g.Invisible || g.Text == "" || g.Text == " " {
			continue
		}
		h := g.Y1 - g.Y0
		w := g.X1 - g.X0
		rot := ""
		size := h
		// rotated glyph boxes are wider than tall
		if math.Abs(g.Dir.Y) > 0.7 && w > h*1.2 {
			size = w
			cx, cy := (g.X0+g.X1)/2, (g.Y0+g.Y1)/2
			rot = fmt.Sprintf(` transform="rotate(-90 %.2f %.2f)"`, cx, cy)
			fmt.Fprintf(&b, `<text x="%.2f" y="%.2f" font-size="%.2f" fill="%s" text-anchor="middle" dominant-baseline="central"%s>%s</text>`, cx, cy, size*0.85, hexColor(g.Color), rot, html.EscapeString(g.Text))
			continue
		}
		fmt.Fprintf(&b, `<text x="%.2f" y="%.2f" font-size="%.2f" fill="%s">%s</text>`, g.X0, g.Y1-0.2*h, size*0.85, hexColor(g.Color), html.EscapeString(g.Text))
	}
	b.WriteString(`</g></svg>`)
	return b.Bytes()
}
