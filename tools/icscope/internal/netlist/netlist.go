// Package netlist is the common circuit model shared by the OrCAD netlist
// reader and the schematic PDF extractor.
package netlist

import (
	"regexp"
	"sort"
	"strconv"
	"strings"
)

type Pin struct {
	Num     string `json:"num"`
	Name    string `json:"name,omitempty"`
	Net     string `json:"net"`
	Section int    `json:"section,omitempty"` // 1-based gate number for multi-section parts
}

type Part struct {
	Ref       string `json:"ref"`
	Value     string `json:"value,omitempty"`
	PartName  string `json:"partName,omitempty"`
	Footprint string `json:"footprint,omitempty"`
	Page      string `json:"page,omitempty"`
	Pins      []Pin  `json:"pins"`
	// Lines holds raw text found next to the reference designator (PDF source).
	Lines []string `json:"lines,omitempty"`
}

type Node struct {
	Ref  string `json:"ref"`
	Num  string `json:"num"`
	Name string `json:"name,omitempty"`
}

type Netlist struct {
	Source string            `json:"source"`
	Kind   string            `json:"kind"` // "orcad" exact, "pdf" heuristic
	Parts  map[string]*Part  `json:"parts"`
	Nets   map[string][]Node `json:"nets"`
	Notes  []string          `json:"notes,omitempty"`
}

func New(source, kind string) *Netlist {
	return &Netlist{Source: source, Kind: kind, Parts: map[string]*Part{}, Nets: map[string][]Node{}}
}

// Index rebuilds Nets from the part pins.
func (n *Netlist) Index() {
	n.Nets = map[string][]Node{}
	for _, p := range n.Parts {
		for _, pin := range p.Pins {
			if pin.Net == "" {
				continue
			}
			n.Nets[pin.Net] = append(n.Nets[pin.Net], Node{p.Ref, pin.Num, pin.Name})
		}
	}
	for k := range n.Nets {
		sort.Slice(n.Nets[k], func(i, j int) bool {
			a, b := n.Nets[k][i], n.Nets[k][j]
			if a.Ref != b.Ref {
				return RefLess(a.Ref, b.Ref)
			}
			return NumLess(a.Num, b.Num)
		})
	}
}

// PinNet returns the net of a pin number ("" when unconnected).
func (p *Part) PinNet(num string) string {
	for _, q := range p.Pins {
		if q.Num == num {
			return q.Net
		}
	}
	return ""
}

// Other returns the net on the other side of a two-terminal part.
func (p *Part) Other(net string) string {
	if len(p.Pins) != 2 {
		return ""
	}
	if p.Pins[0].Net == net {
		return p.Pins[1].Net
	}
	if p.Pins[1].Net == net {
		return p.Pins[0].Net
	}
	return ""
}

var reRef = regexp.MustCompile(`^([A-Za-z_]+)(\d*)(.*)$`)

func RefLess(a, b string) bool {
	ma, mb := reRef.FindStringSubmatch(a), reRef.FindStringSubmatch(b)
	if ma == nil || mb == nil {
		return a < b
	}
	if ma[1] != mb[1] {
		return ma[1] < mb[1]
	}
	ia, _ := strconv.Atoi(ma[2])
	ib, _ := strconv.Atoi(mb[2])
	if ia != ib {
		return ia < ib
	}
	return ma[3] < mb[3]
}

func NumLess(a, b string) bool {
	ia, ea := strconv.Atoi(a)
	ib, eb := strconv.Atoi(b)
	if ea == nil && eb == nil {
		return ia < ib
	}
	if (ea == nil) != (eb == nil) {
		return ea == nil
	}
	return a < b
}

// Prefix is the letter part of a reference designator.
func Prefix(ref string) string {
	m := reRef.FindStringSubmatch(ref)
	if m == nil {
		return ref
	}
	return strings.ToUpper(m[1])
}

var reVal = regexp.MustCompile(`(?i)^\s*([0-9]*\.?[0-9]+)\s*([pnuµμmkKMGR]?)([0-9]*)\s*(ohm|Ω|r|f|h|v)?`)

// ParseValue converts "4.7k", "4K7", "100nF", "20mR", "1M" into a float.
// Returns ok=false when no leading number exists.
func ParseValue(s string) (float64, bool) {
	s = strings.TrimSpace(strings.ReplaceAll(s, ",", ""))
	m := reVal.FindStringSubmatch(s)
	if m == nil {
		return 0, false
	}
	v, err := strconv.ParseFloat(m[1], 64)
	if err != nil {
		return 0, false
	}
	mult := 1.0
	switch m[2] {
	case "p":
		mult = 1e-12
	case "n":
		mult = 1e-9
	case "u", "µ", "μ":
		mult = 1e-6
	case "m":
		mult = 1e-3
	case "k", "K":
		mult = 1e3
	case "M":
		mult = 1e6
	case "G":
		mult = 1e9
	case "R":
		mult = 1
	}
	if m[3] != "" { // 4K7 style
		frac, _ := strconv.ParseFloat("0."+m[3], 64)
		if !strings.Contains(m[1], ".") {
			v += frac
		}
	}
	return v * mult, true
}

// SI formats a value with an engineering prefix.
func SI(v float64, unit string) string {
	if v == 0 {
		return "0 " + unit
	}
	av := v
	if av < 0 {
		av = -av
	}
	pf := []struct {
		m float64
		p string
	}{{1e9, "G"}, {1e6, "M"}, {1e3, "k"}, {1, ""}, {1e-3, "m"}, {1e-6, "µ"}, {1e-9, "n"}, {1e-12, "p"}}
	for _, x := range pf {
		if av >= x.m*0.9995 {
			return strconv.FormatFloat(roundSig(v/x.m, 3), 'f', -1, 64) + " " + x.p + unit
		}
	}
	return strconv.FormatFloat(v, 'g', 3, 64) + " " + unit
}

func roundSig(v float64, n int) float64 {
	s := strconv.FormatFloat(v, 'g', n, 64)
	f, _ := strconv.ParseFloat(s, 64)
	return f
}
