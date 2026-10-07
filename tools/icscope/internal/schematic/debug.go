package schematic

import (
	"fmt"

	"icscope/internal/pdf"
)

// DebugTexts lists merged texts of a page (development aid).
func DebugTexts(pc *pdf.PageContent) []string {
	var out []string
	for _, t := range pageTexts(pc) {
		out = append(out, fmt.Sprintf("%q %06x %.1f [%.1f %.1f %.1f %.1f] h=%v", t.t, t.col, t.size, t.bb.x0, t.bb.y0, t.bb.x1, t.bb.y1, t.horiz))
	}
	return out
}

// DebugComps lists the components of a page with their body and pins.
func DebugComps(pc *pdf.PageContent) []string {
	res := buildPage(pc)
	var out []string
	for ref, c := range res.comps {
		s := fmt.Sprintf("%s body=%d sbb=[%.0f %.0f %.0f %.0f] lines=%v pins:", ref, c.body, c.sbb.x0, c.sbb.y0, c.sbb.x1, c.sbb.y1, c.lines)
		for _, p := range c.pins {
			s += " " + p.Num + "=" + p.Net
		}
		out = append(out, s)
	}
	for _, p := range res.e.pins {
		out = append(out, fmt.Sprintf("PIN [%.1f %.1f %.1f %.1f] body=%d num=%s name=%s net=%d", p.s.x1, p.s.y1, p.s.x2, p.s.y2, p.body, p.num, p.name, p.net))
	}
	for i, b := range res.e.bodies {
		out = append(out, fmt.Sprintf("BODY %d [%.1f %.1f %.1f %.1f] n=%d", i, b.x0, b.y0, b.x1, b.y1, len(res.e.items[i])))
	}
	return out
}
