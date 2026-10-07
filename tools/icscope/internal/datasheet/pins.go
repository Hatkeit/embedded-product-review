package datasheet

import (
	"math"
	"regexp"
	"sort"
	"strings"

	"icscope/internal/pdf"
)

var (
	rePinNum   = regexp.MustCompile(`^(\d{1,3}|[A-K]\d{1,2}|\d{1,3}(,\s*\d{1,3})+|\d{1,3}\s*[-–]\s*\d{1,3}|EP|PAD|—|–|-)$`)
	rePinName  = regexp.MustCompile(`^[A-Za-z~/][A-Za-z0-9_+\-–/#~()]{0,15}$`)
	rePinTitle = regexp.MustCompile(`(?i)(pin|terminal)\s+(functions?|descriptions?|configuration|assignments?|definitions?)`)
)

type pinCol struct {
	kind string // name, num, type, desc
	pkg  string
	x0   float64
}

// extractPins reads a pin-function table (NAME / NO. / TYPE / DESCRIPTION).
func extractPins(page int, c *pdf.PageContent, lines []pdf.Line, words []pdf.Word) []Pin {
	rules := pageRules(c)
	for i := range lines {
		// header: NAME and DESCRIPTION within three consecutive lines
		var hdr []pdf.Word
		hasName, hasDesc, hasNum := false, false, false
		last := i
		for k := i; k < len(lines) && k < i+4 && lines[k].Y0-lines[i].Y0 < 40; k++ {
			for _, w := range lines[k].Words {
				t := strings.ToUpper(strings.Trim(w.Text, ".:()"))
				switch {
				case t == "NAME" || t == "SYMBOL":
					hasName = true
					hdr = append(hdr, w)
					last = k
				case t == "DESCRIPTION" || t == "FUNCTION":
					hasDesc = true
					hdr = append(hdr, w)
					last = k
				case t == "NO" || t == "NUMBER" || t == "PIN#" || t == "NO#":
					hasNum = true
					hdr = append(hdr, w)
					last = k
				case t == "TYPE" || t == "I/O" || t == "TYPE(1)" || strings.HasPrefix(t, "TYPE"):
					hdr = append(hdr, w)
					last = k
				case len(t) <= 4 && regexp.MustCompile(`^(PW|D|DBV|DCK|DGK|DRL|DDF|DSG|DRV|DBZ|DWE|DW|RGY|RGT|PWP|DSBGA|YZF|SOIC|TSSOP|SOT|VSSOP|MSOP|QFN|SON)$`).MatchString(t):
					hdr = append(hdr, w)
					last = k
				}
			}
		}
		if !(hasName && hasDesc) {
			continue
		}
		var cols []pinCol
		for _, w := range hdr {
			t := strings.ToUpper(strings.Trim(w.Text, ".:()"))
			k := "num"
			switch {
			case t == "NAME" || t == "SYMBOL":
				k = "name"
			case t == "DESCRIPTION" || t == "FUNCTION":
				k = "desc"
			case strings.HasPrefix(t, "TYPE") || t == "I/O":
				k = "type"
			}
			pkg := ""
			if k == "num" && t != "NO" && t != "NUMBER" {
				pkg = t
			}
			cols = append(cols, pinCol{k, pkg, w.X0})
		}
		if !hasNum {
			found := false
			for _, c := range cols {
				if c.kind == "num" {
					found = true
				}
			}
			if !found {
				continue
			}
		}
		sort.Slice(cols, func(a, b int) bool { return cols[a].x0 < cols[b].x0 })
		// ruled tables: column intervals from the rule splits around the header
		var splits []float64
		for _, r := range rules {
			if r.y >= lines[i].Y0-8 && r.y <= lines[last].Y1+8 {
				splits = append(splits, r.x0, r.x1)
			}
		}
		sort.Float64s(splits)
		splits = dedup(splits, 2)
		type iv struct{ a, b float64 }
		var ivs []iv
		if len(splits) >= len(cols)+1 {
			ok := true
			for _, c := range cols {
				// header centre (approx.) must fall in some interval
				x := c.x0 + 6
				found := false
				for k := 0; k+1 < len(splits); k++ {
					if x >= splits[k] && x <= splits[k+1] {
						ivs = append(ivs, iv{splits[k], splits[k+1]})
						found = true
						break
					}
				}
				if !found {
					ok = false
				}
			}
			if !ok {
				ivs = nil
			}
		}
		colAt := func(w pdf.Word) int {
			if ivs != nil {
				cx := (w.X0 + w.X1) / 2
				for j, v := range ivs {
					if cx >= v.a-1 && cx <= v.b+1 {
						return j
					}
				}
			}
			best := 0
			for j, c := range cols {
				if w.X0 >= c.x0-8 {
					best = j
				}
			}
			// centred number columns: pick the nearest number-column anchor
			if rePinNum.MatchString(w.Text) {
				bd := math.Inf(1)
				for j, c := range cols {
					if c.kind != "num" {
						continue
					}
					if d := math.Abs((w.X0+w.X1)/2 - (c.x0 + 6)); d < bd && d < 25 {
						bd, best = d, j
					}
				}
			}
			return best
		}
		type rowAcc struct {
			y    float64
			pin  Pin
			desc []string
			typ  []string
		}
		var rows []*rowAcc
		var rest []pdf.Line
		lastY := lines[last].Y1
		for _, bl := range lines[last+1:] {
			if bl.Y0-lastY > 45 {
				break
			}
			t := bl.Text()
			if (reHeading.MatchString(t) && bl.Words[0].Bold) || strings.HasPrefix(t, "(1)") || strings.HasPrefix(t, "Copyright") {
				break
			}
			var name, num, typ, desc []string
			numPkgs := map[string]string{}
			for _, w := range bl.Words {
				j := colAt(w)
				switch cols[j].kind {
				case "name":
					name = append(name, w.Text)
				case "num":
					num = append(num, w.Text)
					if cols[j].pkg != "" && rePinNum.MatchString(w.Text) {
						numPkgs[cols[j].pkg] = w.Text
					}
				case "type":
					typ = append(typ, w.Text)
				case "desc":
					desc = append(desc, w.Text)
				}
			}
			nm := strings.Join(name, " ")
			nb := ""
			if len(num) > 0 {
				nb = num[0]
			}
			if nm != "" && nb != "" && rePinName.MatchString(nm) && rePinNum.MatchString(nb) {
				ra := &rowAcc{y: (bl.Y0 + bl.Y1) / 2, pin: Pin{Name: nm, Num: strings.Join(num, " "), Page: page}}
				if len(numPkgs) > 0 {
					ra.pin.Nums = numPkgs
				}
				ra.typ = typ
				ra.desc = desc
				rows = append(rows, ra)
			} else {
				rest = append(rest, bl)
			}
			lastY = bl.Y1
		}
		if len(rows) < 2 {
			continue
		}
		// distribute the remaining lines' type/description to the nearest row
		for _, bl := range rest {
			cy := (bl.Y0 + bl.Y1) / 2
			var best *rowAcc
			bd := 22.0
			for _, ra := range rows {
				if d := math.Abs(ra.y - cy); d < bd {
					bd, best = d, ra
				}
			}
			if best == nil {
				continue
			}
			for _, w := range bl.Words {
				switch cols[colAt(w)].kind {
				case "type":
					best.typ = append(best.typ, w.Text)
				case "desc":
					best.desc = append(best.desc, w.Text)
				}
			}
		}
		var out []Pin
		for _, ra := range rows {
			ra.pin.Type = strings.Join(ra.typ, " ")
			ra.pin.Desc = strings.Join(ra.desc, " ")
			out = append(out, ra.pin)
		}
		return out
	}
	return nil
}
