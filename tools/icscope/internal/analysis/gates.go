package analysis

import (
	"sort"
	"strconv"
	"strings"

	"icscope/internal/netlist"
)

// Gate is one amplifier/comparator/inverter section of a part.
type Gate struct {
	N        int    // 1-based
	InP, InN string // pin numbers ("" for inverters' InN)
	Out      string
	Source   string // how the pins were assigned: "name", "section", "pinout"
}

// Standard pinouts {in+, in-, out} by pin count; used only when pin names
// do not identify the sections.
var stdAmp = map[int][][3]string{
	5:  {{"3", "4", "1"}},
	8:  {{"3", "2", "1"}, {"5", "6", "7"}},
	14: {{"3", "2", "1"}, {"5", "6", "7"}, {"10", "9", "8"}, {"12", "13", "14"}},
}

var stdLM339 = [][3]string{{"5", "4", "2"}, {"7", "6", "1"}, {"9", "8", "14"}, {"11", "10", "13"}}

// {in, out}
var stdInv = map[int][][2]string{
	5:  {{"2", "4"}},
	6:  {{"1", "6"}, {"3", "4"}},
	14: {{"1", "2"}, {"3", "4"}, {"5", "6"}, {"9", "8"}, {"11", "10"}, {"13", "12"}},
}

func pinCount(p *netlist.Part) int {
	m := map[string]bool{}
	max := 0
	for _, q := range p.Pins {
		n, err := strconv.Atoi(q.Num)
		if err != nil {
			continue
		}
		m[q.Num] = true
		if n > max {
			max = n
		}
	}
	if max > len(m) {
		return max
	}
	return len(m)
}

func gatesOf(p *netlist.Part, class string) []Gate {
	inv := class == KInverter
	type slot struct{ inp, inn, out string }
	group := map[string]*slot{}
	var order []string
	dup := false
	hasSec := false
	for _, q := range p.Pins {
		if q.Section > 0 {
			hasSec = true
		}
	}
	for _, q := range p.Pins {
		r := pinRole(q.Name)
		if inv && r == "in" {
			r = "in+"
		}
		if r != "in+" && r != "in-" && r != "out" {
			continue
		}
		key := ""
		if hasSec {
			key = strconv.Itoa(q.Section)
		} else {
			key = tagOf(q.Name)
		}
		s := group[key]
		if s == nil {
			s = &slot{}
			group[key] = s
			order = append(order, key)
		}
		var dst *string
		switch r {
		case "in+":
			dst = &s.inp
		case "in-":
			dst = &s.inn
		case "out":
			dst = &s.out
		}
		if *dst != "" && *dst != q.Num {
			dup = true
		}
		*dst = q.Num
	}
	// a single gate whose pins carry inconsistent tags (IN1+, IN1-, OUT)
	if len(order) > 1 && !hasSec {
		var one slot
		cnt := map[string]int{}
		for _, k := range order {
			s := group[k]
			for r, v := range map[string]string{"in+": s.inp, "in-": s.inn, "out": s.out} {
				if v != "" {
					cnt[r]++
					switch r {
					case "in+":
						one.inp = v
					case "in-":
						one.inn = v
					case "out":
						one.out = v
					}
				}
			}
		}
		if cnt["in+"] == 1 && cnt["out"] == 1 && cnt["in-"] <= 1 && !dup {
			group = map[string]*slot{"": &one}
			order = []string{""}
		}
	}
	var gs []Gate
	src := "name"
	if hasSec {
		src = "section"
	}
	if !dup && len(order) > 0 {
		sort.Strings(order)
		ok := true
		for _, k := range order {
			s := group[k]
			if s.inp == "" || s.out == "" || (!inv && s.inn == "") {
				ok = false
			}
		}
		if ok {
			for i, k := range order {
				s := group[k]
				gs = append(gs, Gate{N: i + 1, InP: s.inp, InN: s.inn, Out: s.out, Source: src})
			}
			return gs
		}
	}
	// Fall back to the standard pinout of the package (hidden power pins
	// make the visible pin count smaller than the package).
	n := pinCount(p)
	switch {
	case inv && n == 6:
	case n > 5 && n <= 8:
		n = 8
	case n > 8 && n <= 14:
		n = 14
	}
	if inv {
		for i, g := range stdInv[n] {
			gs = append(gs, Gate{N: i + 1, InP: g[0], Out: g[1], Source: "pinout"})
		}
		return gs
	}
	tbl := stdAmp[n]
	if n == 14 && class == KComparator && strings.Contains(strings.ToUpper(p.Value+p.PartName), "339") {
		tbl = stdLM339
	}
	if n == 8 && single8(p) {
		tbl = [][3]string{{"3", "2", "6"}}
	}
	for i, g := range tbl {
		gs = append(gs, Gate{N: i + 1, InP: g[0], InN: g[1], Out: g[2], Source: "pinout"})
	}
	return gs
}

// single8 detects a single amplifier in an 8-pin package (OUT on pin 6).
func single8(p *netlist.Part) bool {
	v := strings.ToUpper(p.Value + " " + p.PartName)
	for _, s := range []string{"OPA387", "OPA388", "OPA333", "TLV9061", "OPA180", "OPA189", "OPA277", "OP07", "OPA1611"} {
		if strings.Contains(v, s) {
			return true
		}
	}
	return false
}

func tagOf(name string) string {
	n := strings.ToUpper(name)
	n = strings.NewReplacer("OUT", "", "IN", "", "+", "", "-", "", "V", "").Replace(n)
	if n == "P" || n == "N" {
		return ""
	}
	n = strings.TrimSuffix(strings.TrimSuffix(n, "P"), "N")
	if len(n) > 1 {
		if m := reTag.FindString(n); m != "" {
			return m
		}
	}
	if n == "Y" || n == "A" {
		return ""
	}
	return strings.Trim(n, "AY_")
}
