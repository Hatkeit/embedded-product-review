// Package datasheet extracts characteristics tables, pin tables and key
// specifications from component datasheet PDFs.
package datasheet

import (
	"math"
	"regexp"
	"sort"
	"strings"

	"icscope/internal/pdf"
)

// Row is one sub-row of a characteristics table.
type Row struct {
	Page   int    `json:"page"`
	Table  string `json:"table"`
	Param  string `json:"param"`
	Symbol string `json:"symbol,omitempty"`
	Cond   string `json:"cond,omitempty"`
	Min    string `json:"min,omitempty"`
	Typ    string `json:"typ,omitempty"`
	Max    string `json:"max,omitempty"`
	Unit   string `json:"unit,omitempty"`
}

type column struct {
	kind   string // param, symbol, cond, min, typ, max, unit, other
	x0, x1 float64
}

type hrule struct{ y, x0, x1 float64 }

var (
	reMin  = regexp.MustCompile(`(?i)^min\.?$`)
	reTyp  = regexp.MustCompile(`(?i)^(typ|nom)\.?$`)
	reMax  = regexp.MustCompile(`(?i)^max\.?$`)
	reUnit = regexp.MustCompile(`(?i)^units?$`)
)

func headerKind(t string) string {
	switch {
	case reMin.MatchString(t):
		return "min"
	case reTyp.MatchString(t):
		return "typ"
	case reMax.MatchString(t):
		return "max"
	case reUnit.MatchString(t):
		return "unit"
	}
	l := strings.ToLower(strings.Trim(t, ":"))
	switch l {
	case "parameter", "parameters", "characteristics", "characteristic", "description", "item", "rating":
		return "param"
	case "symbol", "sym":
		return "symbol"
	case "conditions", "condition", "test", "note", "notes":
		return "cond"
	}
	return ""
}

// pageRules returns horizontal rule segments drawn on the page.
func pageRules(c *pdf.PageContent) []hrule {
	var out []hrule
	for _, p := range c.Paths {
		for _, it := range p.Items {
			switch it.Kind {
			case 'l':
				a, b := it.P[0], it.P[1]
				if math.Abs(a.Y-b.Y) < 0.6 && math.Abs(a.X-b.X) > 4 {
					out = append(out, hrule{(a.Y + b.Y) / 2, math.Min(a.X, b.X), math.Max(a.X, b.X)})
				}
			case 'r':
				x0, y0, x1, y1 := bbox(it.P)
				if y1-y0 < 1.6 && x1-x0 > 4 {
					out = append(out, hrule{(y0 + y1) / 2, x0, x1})
				}
			}
		}
	}
	return out
}

func bbox(ps []pdf.Point) (x0, y0, x1, y1 float64) {
	x0, y0 = math.Inf(1), math.Inf(1)
	x1, y1 = math.Inf(-1), math.Inf(-1)
	for _, p := range ps {
		x0, y0 = math.Min(x0, p.X), math.Min(y0, p.Y)
		x1, y1 = math.Max(x1, p.X), math.Max(y1, p.Y)
	}
	return
}

type header struct {
	y0, y1 float64 // vertical extent of the header lines
	cols   []column
	title  string
}

// findHeaders locates MIN/TYP/MAX/UNIT header rows (one or two lines).
func findHeaders(lines []pdf.Line) []header {
	var out []header
	for i := 0; i < len(lines); i++ {
		ws := append([]pdf.Word(nil), lines[i].Words...)
		y0, y1 := lines[i].Y0, lines[i].Y1
		kinds := map[string]bool{}
		for _, w := range ws {
			kinds[headerKind(w.Text)] = true
		}
		// Infineon style: Min./Typ./Max. on the line below the main header
		if !(kinds["min"] && kinds["max"]) && i+1 < len(lines) && lines[i+1].Y0-lines[i].Y1 < 2*(lines[i].Y1-lines[i].Y0)+2 {
			k2 := map[string]bool{}
			for _, w := range lines[i+1].Words {
				k2[headerKind(w.Text)] = true
			}
			if k2["min"] && k2["max"] && (kinds["param"] || kinds["unit"] || kinds["symbol"]) {
				ws = append(ws, lines[i+1].Words...)
				y1 = lines[i+1].Y1
				for k := range k2 {
					kinds[k] = true
				}
				i++
			}
		}
		if !(kinds["max"] && (kinds["min"] || kinds["typ"])) {
			continue
		}
		var cols []column
		for _, w := range ws {
			k := headerKind(w.Text)
			if k == "" {
				// multi-word headers: TEST CONDITIONS, Note or Test Condition
				l := strings.ToLower(w.Text)
				if l == "test" || strings.HasPrefix(l, "condition") || l == "note" {
					k = "cond"
				} else {
					continue
				}
			}
			// merge with an existing column of the same kind that is adjacent
			merged := false
			for j := range cols {
				if cols[j].kind == k && w.X0-cols[j].x1 < 30 && math.Abs((w.Y0+w.Y1)/2-(y0+y1)/2) < 30 {
					cols[j].x1 = math.Max(cols[j].x1, w.X1)
					cols[j].x0 = math.Min(cols[j].x0, w.X0)
					merged = true
				}
			}
			if !merged {
				cols = append(cols, column{k, w.X0, w.X1})
			}
		}
		sort.Slice(cols, func(a, b int) bool { return cols[a].x0 < cols[b].x0 })
		if len(cols) > 0 && isValueKind(cols[0].kind) {
			cols = append([]column{{"param", 0, 0}}, cols...)
		}
		out = append(out, header{y0: y0, y1: y1, cols: cols})
	}
	return out
}

func isValueKind(k string) bool { return k == "min" || k == "typ" || k == "max" || k == "unit" }

// boundaries turns header columns into contiguous x ranges, using vertical
// splits of the rule under/over the header when the table is ruled.
func (h *header) boundaries(rules []hrule, words []pdf.Word, pageW float64) []column {
	// rule splits near the header
	var splits []float64
	for _, r := range rules {
		if r.y >= h.y0-6 && r.y <= h.y1+6 {
			splits = append(splits, r.x0, r.x1)
		}
	}
	sort.Float64s(splits)
	splits = dedup(splits, 2)
	cols := make([]column, len(h.cols))
	copy(cols, h.cols)
	if cols[0].kind == "param" && cols[0].x1 == 0 && len(splits) > 0 {
		cols[0].x0, cols[0].x1 = splits[0], splits[0]+1
	}
	if len(splits) >= len(cols)+1 {
		// assign each header to the split interval containing its centre
		for i := range cols {
			c := (cols[i].x0 + cols[i].x1) / 2
			for k := 0; k+1 < len(splits); k++ {
				if c >= splits[k] && c <= splits[k+1] {
					cols[i].x0, cols[i].x1 = splits[k], splits[k+1]
					break
				}
			}
		}
		// leading gap folds into the first column; a header-less gap in front of
		// a value column is a conditions column
		cols[0].x0 = splits[0] - 1
		var out []column
		for i := range cols {
			if i > 0 && cols[i].x0-cols[i-1].x1 > 2 {
				gap := column{"cond", cols[i-1].x1, cols[i].x0}
				if !isValueKind(cols[i].kind) {
					cols[i].x0 = cols[i-1].x1
				} else if isValueKind(cols[i-1].kind) {
					cols[i].x0 = cols[i-1].x1
				} else {
					out = append(out, gap)
				}
			}
			out = append(out, cols[i])
		}
		out[len(out)-1].x1 = splits[len(splits)-1] + 1
		cols = out
		return cols
	}
	// unruled table: left-aligned columns start at their header, centred ones
	// split at the midpoint between headers
	out := make([]column, len(cols))
	for i := range cols {
		out[i] = cols[i]
		if i == 0 {
			out[i].x0 = 0
			continue
		}
		left := cols[i-1].x1
		aligned := 0
		for _, w := range words {
			if w.Y0 > h.y1 && w.Y0 < h.y1+120 && math.Abs(w.X0-cols[i].x0) < 3.5 {
				aligned++
			}
		}
		b := (left + cols[i].x0) / 2
		if aligned >= 2 {
			b = cols[i].x0 - 3
		}
		out[i].x0 = b
		out[i-1].x1 = b
	}
	out[len(out)-1].x1 = pageW
	return out
}

func dedup(v []float64, tol float64) []float64 {
	var out []float64
	for _, x := range v {
		if len(out) == 0 || x-out[len(out)-1] > tol {
			out = append(out, x)
		}
	}
	return out
}

func colOf(cols []column, w pdf.Word) int {
	c := (w.X0 + w.X1) / 2
	for i, col := range cols {
		if c >= col.x0 && c < col.x1 {
			return i
		}
	}
	return -1
}

var reHeading = regexp.MustCompile(`^(\d+(\.\d+){0,3}|Table\s+\d+|\d+\.)\s+\S`)

// tableTitle finds the nearest heading line above y.
func tableTitle(lines []pdf.Line, y float64) string {
	for i := len(lines) - 1; i >= 0; i-- {
		l := lines[i]
		if l.Y1 > y || y-l.Y1 > 160 {
			continue
		}
		t := l.Text()
		if reHeading.MatchString(t) && len(t) < 90 {
			return t
		}
	}
	return ""
}

// extractTables pulls every characteristics row from a page.
func extractTables(page int, c *pdf.PageContent, lines []pdf.Line, words []pdf.Word, carry *header) ([]Row, *header) {
	hs := findHeaders(lines)
	rules := pageRules(c)
	var rows []Row
	// a table continued from the previous page without a repeated header
	if len(hs) == 0 && carry != nil {
		h := *carry
		h.y0, h.y1 = 40, 60
		hs = []header{h}
	}
	for hi, h := range hs {
		if h.title == "" {
			h.title = tableTitle(lines, h.y0)
		}
		cols := h.boundaries(rules, words, c.Width)
		if hi > 0 || carry == nil || h.y0 > 60 {
			carry = &header{cols: h.cols, title: h.title}
		}
		end := c.Height - 50
		if hi+1 < len(hs) {
			end = hs[hi+1].y0 - 1
		}
		rows = append(rows, readTable(page, h, cols, rules, lines, end)...)
	}
	return rows, carry
}

type cellLine struct {
	y     float64
	cells map[string][]string
}

func readTable(page int, h header, cols []column, rules []hrule, lines []pdf.Line, end float64) []Row {
	left, right := cols[0].x0, cols[len(cols)-1].x1
	// a ruled table ends at the last rule of the chain that starts under the header
	var ys []float64
	for _, r := range rules {
		if r.y > h.y1-2 && r.y < end && r.x1 > left+5 && r.x0 < right-5 {
			ys = append(ys, r.y)
		}
	}
	sort.Float64s(ys)
	ys = dedup(ys, 1.2)
	ruledEnd := -1.0
	prev := h.y1
	for _, y := range ys {
		if y-prev > 70 {
			break
		}
		ruledEnd, prev = y, y
	}
	if ruledEnd > h.y1+5 {
		end = ruledEnd + 0.5
	}
	var cls []cellLine
	lastY := h.y1
	for _, l := range lines {
		if l.Y0 <= h.y1+0.5 || l.Y1 >= end {
			continue
		}
		t := l.Text()
		if len(cls) > 0 && reHeading.MatchString(t) && l.Words[0].X0 < left+40 && !hasValue(l, cols) && len(t) < 60 {
			break
		}
		if ruledEnd < 0 && len(cls) > 0 {
			if l.Y0-lastY > 40 {
				break
			}
			if (reHeading.MatchString(t) || strings.HasPrefix(t, "(1)") || strings.HasPrefix(strings.ToUpper(t), "NOTE")) && l.Words[0].X0 < left+40 && !hasValue(l, cols) {
				break
			}
		}
		if strings.HasPrefix(t, "(1)") && !hasValue(l, cols) {
			continue
		}
		cl := cellLine{y: (l.Y0 + l.Y1) / 2, cells: map[string][]string{}}
		for _, w := range l.Words {
			i := colOf(cols, w)
			if i < 0 {
				continue
			}
			cl.cells[cols[i].kind] = append(cl.cells[cols[i].kind], w.Text)
		}
		cls = append(cls, cl)
		lastY = l.Y1
	}
	if len(cls) == 0 {
		return nil
	}
	// row bands from rules spanning the parameter column, sub-rows from rules
	// spanning the value columns
	paramX := (cols[0].x0 + cols[0].x1) / 2
	var valX float64
	for _, c := range cols {
		if c.kind == "typ" || (valX == 0 && (c.kind == "min" || c.kind == "max")) {
			valX = (c.x0 + c.x1) / 2
		}
	}
	bandsP := bandsFor(rules, paramX, h.y1, end)
	bandsV := bandsFor(rules, valX, h.y1, end)
	if len(bandsP) >= 2 && len(bandsV) >= 2 {
		return ruledRows(page, h, cls, bandsP, bandsV)
	}
	return unruledRows(page, h, cls)
}

func hasValue(l pdf.Line, cols []column) bool {
	for _, w := range l.Words {
		if i := colOf(cols, w); i >= 0 && isValueKind(cols[i].kind) && cols[i].kind != "unit" {
			return true
		}
	}
	return false
}

func bandsFor(rules []hrule, x, y0, y1 float64) []float64 {
	var ys []float64
	for _, r := range rules {
		if r.y > y0-4 && r.y < y1+4 && r.x0-1 <= x && r.x1+1 >= x {
			ys = append(ys, r.y)
		}
	}
	sort.Float64s(ys)
	return dedup(ys, 1.2)
}

func bandIndex(b []float64, y float64) int {
	for i := 0; i+1 < len(b); i++ {
		if y >= b[i] && y < b[i+1] {
			return i
		}
	}
	return -1
}

func join(s []string) string { return strings.TrimSpace(strings.Join(s, " ")) }

func ruledRows(page int, h header, cls []cellLine, bandsP, bandsV []float64) []Row {
	type acc struct {
		param, symbol, cond, unit []string
		min, typ, max             []string
		pband                     int
		hasVal                    bool
	}
	pText := map[int]*acc{}
	vRows := map[int]*acc{}
	for _, cl := range cls {
		pb := bandIndex(bandsP, cl.y)
		vb := bandIndex(bandsV, cl.y)
		if pb < 0 && vb < 0 {
			continue
		}
		if pb >= 0 {
			a := pText[pb]
			if a == nil {
				a = &acc{}
				pText[pb] = a
			}
			a.param = append(a.param, cl.cells["param"]...)
			a.symbol = append(a.symbol, cl.cells["symbol"]...)
		}
		if vb >= 0 {
			a := vRows[vb]
			if a == nil {
				a = &acc{pband: pb}
				vRows[vb] = a
			}
			a.cond = append(a.cond, cl.cells["cond"]...)
			a.unit = append(a.unit, cl.cells["unit"]...)
			a.min = append(a.min, cl.cells["min"]...)
			a.typ = append(a.typ, cl.cells["typ"]...)
			a.max = append(a.max, cl.cells["max"]...)
			if len(cl.cells["min"])+len(cl.cells["typ"])+len(cl.cells["max"]) > 0 {
				a.hasVal = true
			}
		}
	}
	var keys []int
	for k := range vRows {
		keys = append(keys, k)
	}
	sort.Ints(keys)
	var out []Row
	// a unit cell may span several value sub-rows: remember the band's last unit
	bandUnits := map[int]map[string]bool{}
	for _, k := range keys {
		a := vRows[k]
		if u := join(a.unit); u != "" {
			if bandUnits[a.pband] == nil {
				bandUnits[a.pband] = map[string]bool{}
			}
			bandUnits[a.pband][u] = true
		}
	}
	lastUnit := map[int]string{}
	for b, us := range bandUnits {
		if len(us) == 1 {
			for u := range us {
				lastUnit[b] = u
			}
		}
	}
	for _, k := range keys {
		a := vRows[k]
		if !a.hasVal {
			continue
		}
		p := pText[a.pband]
		row := Row{Page: page, Table: h.title, Min: join(a.min), Typ: join(a.typ), Max: join(a.max), Cond: join(a.cond), Unit: join(a.unit)}
		if p != nil {
			row.Param, row.Symbol = splitSymbol(join(p.param), join(p.symbol))
		}
		if row.Unit == "" && !strings.Contains(row.Min+row.Typ+row.Max, "%") {
			row.Unit = lastUnit[a.pband]
		}
		out = append(out, row)
	}
	return out
}

func unruledRows(page int, h header, cls []cellLine) []Row {
	var out []Row
	var cur *Row
	var pendingParam []string
	for _, cl := range cls {
		vals := len(cl.cells["min"]) + len(cl.cells["typ"]) + len(cl.cells["max"])
		if vals == 0 {
			// continuation of a parameter name or condition
			if cur != nil && len(cl.cells["param"]) > 0 && len(pendingParam) == 0 {
				cur.Param = strings.TrimSpace(cur.Param + " " + join(cl.cells["param"]))
			} else if len(cl.cells["param"]) > 0 {
				pendingParam = append(pendingParam, cl.cells["param"]...)
			}
			if cur != nil {
				if c := join(cl.cells["cond"]); c != "" {
					cur.Cond = strings.TrimSpace(cur.Cond + " " + c)
				}
				if s := join(cl.cells["symbol"]); s != "" && cur.Symbol != "" {
					cur.Symbol += s
				}
			}
			continue
		}
		r := Row{Page: page, Table: h.title, Min: join(cl.cells["min"]), Typ: join(cl.cells["typ"]), Max: join(cl.cells["max"]), Unit: join(cl.cells["unit"]), Cond: join(cl.cells["cond"])}
		p := join(cl.cells["param"])
		switch {
		case len(pendingParam) > 0:
			p = strings.TrimSpace(join(pendingParam) + " " + p)
			pendingParam = nil
		case p == "" && cur != nil:
			p = cur.Param
		case p != "" && cur != nil && looksLikeVariant(p):
			// MOC3061/MOC3062 sub-rows under one parameter
			r.Cond = strings.TrimSpace(p + " " + r.Cond)
			p = cur.Param
		}
		r.Param, r.Symbol = splitSymbol(p, join(cl.cells["symbol"]))
		if r.Symbol == "" && cur != nil && r.Param == cur.Param {
			r.Symbol = cur.Symbol
		}
		if r.Unit == "" && cur != nil && r.Param == cur.Param {
			r.Unit = cur.Unit
		}
		out = append(out, r)
		cur = &out[len(out)-1]
	}
	return out
}

var reVariant = regexp.MustCompile(`^[A-Z]{2,}[0-9]{3,}[A-Z0-9-]*$`)

func looksLikeVariant(p string) bool { return reVariant.MatchString(p) }

var reSymLead = regexp.MustCompile(`^([A-Za-zΔ][A-Za-z0-9_+\-/()]{0,12})\s+([A-Z][a-z].*)$`)

// splitSymbol separates a TI-style leading symbol ("VOS Offset voltage").
func splitSymbol(param, symbol string) (string, string) {
	if symbol != "" {
		return param, symbol
	}
	if m := reSymLead.FindStringSubmatch(param); m != nil {
		s := m[1]
		if strings.ToUpper(s[:1]) == s[:1] && (strings.ContainsAny(s, "0123456789/") || strings.ToUpper(s) == s || len(s) <= 6) {
			return m[2], s
		}
	}
	return param, ""
}
