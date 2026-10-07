// Package orcad reads the OrCAD Capture "PST" netlist files
// (pstxnet.dat, pstxprt.dat, pstchip.dat) into the common netlist model.
package orcad

import (
	"bufio"
	"bytes"
	"fmt"
	"regexp"
	"strings"

	"icscope/internal/netlist"
)

// Files groups the three PST files; Net is required, the others enrich it.
type Files struct {
	Net, Prt, Chip []byte
	Names          []string
}

// Kind recognises a PST file from its header.
func Kind(b []byte) string {
	h := b
	if len(h) > 200 {
		h = h[:200]
	}
	switch {
	case bytes.Contains(h, []byte("EXPANDEDNETLIST")):
		return "net"
	case bytes.Contains(h, []byte("EXPANDEDPARTLIST")):
		return "prt"
	case bytes.Contains(h, []byte("LIBRARY_PARTS")):
		return "chip"
	}
	return ""
}

var (
	reQuoted = regexp.MustCompile(`'((?:[^']|'')*)'`)
	rePage   = regexp.MustCompile(`(?i):page(\d+)_`)
	reNums   = regexp.MustCompile(`\(([^)]*)\)`)
)

func unq(s string) string {
	m := reQuoted.FindStringSubmatch(s)
	if m == nil {
		return strings.TrimSpace(s)
	}
	return strings.ReplaceAll(m[1], "''", "'")
}

type prim struct {
	partName, jedec, value string
	pins                   map[string][]string // pin name -> number per section
}

func parseChip(b []byte) map[string]*prim {
	out := map[string]*prim{}
	var cur *prim
	var pinName string
	inPin := false
	sc := bufio.NewScanner(bytes.NewReader(b))
	sc.Buffer(make([]byte, 1<<20), 1<<20)
	for sc.Scan() {
		t := strings.TrimSpace(sc.Text())
		switch {
		case strings.HasPrefix(t, "primitive "):
			cur = &prim{pins: map[string][]string{}}
			out[unq(t)] = cur
		case cur == nil:
		case t == "pin":
			inPin = true
		case t == "end_pin;":
			inPin = false
		case inPin && strings.HasPrefix(t, "'") && strings.HasSuffix(t, ":"):
			pinName = unq(t)
		case inPin && strings.HasPrefix(t, "PIN_NUMBER="):
			if m := reNums.FindStringSubmatch(unq(t[len("PIN_NUMBER="):])); m != nil {
				var nums []string
				for _, x := range strings.Split(m[1], ",") {
					nums = append(nums, strings.TrimSpace(x))
				}
				cur.pins[pinName] = nums
			}
		case strings.HasPrefix(t, "PART_NAME="):
			cur.partName = unq(t[10:])
		case strings.HasPrefix(t, "JEDEC_TYPE="):
			cur.jedec = unq(t[11:])
		case strings.HasPrefix(t, "VALUE="):
			cur.value = unq(t[6:])
		}
	}
	return out
}

type prtInfo struct {
	prim  string
	pages map[string]bool
}

func parsePrt(b []byte) map[string]*prtInfo {
	out := map[string]*prtInfo{}
	var cur *prtInfo
	lines := strings.Split(strings.ReplaceAll(string(b), "\r", ""), "\n")
	for i := 0; i < len(lines); i++ {
		t := strings.TrimSpace(lines[i])
		if t == "PART_NAME" && i+1 < len(lines) {
			i++
			l := strings.TrimSpace(lines[i])
			sp := strings.IndexByte(l, ' ')
			if sp < 0 {
				continue
			}
			cur = &prtInfo{prim: unq(l[sp:]), pages: map[string]bool{}}
			out[l[:sp]] = cur
			continue
		}
		if cur != nil && strings.HasPrefix(t, "P_PATH=") {
			if m := rePage.FindStringSubmatch(t); m != nil {
				cur.pages[m[1]] = true
			}
		}
	}
	return out
}

// Read builds the netlist. Pin names come from pstxnet; part value,
// footprint and gate numbers from pstxprt + pstchip when given.
func Read(f Files) (*netlist.Netlist, error) {
	if f.Net == nil {
		return nil, fmt.Errorf("pstxnet.dat 가 필요합니다")
	}
	nl := netlist.New(strings.Join(f.Names, ", "), "orcad")
	lines := strings.Split(strings.ReplaceAll(string(f.Net), "\r", ""), "\n")
	net := ""
	for i := 0; i < len(lines); i++ {
		t := strings.TrimSpace(lines[i])
		switch {
		case t == "NET_NAME" && i+1 < len(lines):
			i++
			net = unq(lines[i])
		case strings.HasPrefix(t, "NODE_NAME"):
			fs := strings.Fields(t[len("NODE_NAME"):])
			if len(fs) < 2 {
				continue
			}
			ref, num := fs[0], fs[1]
			name := ""
			if i+2 < len(lines) && strings.HasPrefix(strings.TrimSpace(lines[i+2]), "'") {
				name = unq(lines[i+2])
				i += 2
			}
			p := nl.Parts[ref]
			if p == nil {
				p = &netlist.Part{Ref: ref}
				nl.Parts[ref] = p
			}
			p.Pins = append(p.Pins, netlist.Pin{Num: num, Name: name, Net: net})
		}
	}
	if len(nl.Parts) == 0 {
		return nil, fmt.Errorf("pstxnet.dat 에서 NODE_NAME 을 찾지 못했습니다")
	}
	var chips map[string]*prim
	if f.Chip != nil {
		chips = parseChip(f.Chip)
	}
	if f.Prt != nil {
		for ref, info := range parsePrt(f.Prt) {
			p := nl.Parts[ref]
			if p == nil { // part with no connected pin
				p = &netlist.Part{Ref: ref}
				nl.Parts[ref] = p
			}
			var pg []string
			for k := range info.pages {
				pg = append(pg, k)
			}
			p.Page = strings.Join(pg, ",")
			pr := chips[info.prim]
			if pr == nil {
				p.PartName = info.prim
				continue
			}
			p.PartName, p.Footprint, p.Value = pr.partName, pr.jedec, pr.value
			// Gate number of each pin number, plus the pins left unconnected.
			for name, nums := range pr.pins {
				for s, num := range nums {
					found := false
					for k := range p.Pins {
						if p.Pins[k].Num == num {
							found = true
							if len(nums) > 1 {
								p.Pins[k].Section = s + 1
							}
						}
					}
					if !found {
						sec := 0
						if len(nums) > 1 {
							sec = s + 1
						}
						p.Pins = append(p.Pins, netlist.Pin{Num: num, Name: name, Section: sec})
					}
				}
			}
		}
	} else {
		nl.Notes = append(nl.Notes, "pstxprt.dat·pstchip.dat 없이 읽어 부품값·풋프린트가 비어 있습니다.")
	}
	for _, p := range nl.Parts {
		if p.Value == "" && p.PartName != "" {
			p.Value = p.PartName
		}
	}
	nl.Index()
	return nl, nil
}
