package schematic

import (
	"fmt"
	"math"
	"regexp"
	"sort"
	"strconv"
	"strings"

	"icscope/internal/netlist"
	"icscope/internal/pdf"
)

var (
	reRefdes = regexp.MustCompile(`^(R|C|L|D|U|Q|J|T|F|Y|EC|ZD|RV|LS|TH|ISO|TSW|TP|K|SW|X|IC|FB|CN|P|BT|VR|PS)\d{1,3}[A-H]?$`)
	reDigits = regexp.MustCompile(`^\d+$`)
	reFoot   = regexp.MustCompile(`(?i)^(RESC|CAPC|DIOM|SON|SOT|SOP|SOIC|QFN|LQFP|DSO|XFMR|BEADC|MPX|RT0603|XTAL|hdr|RLYRR|HoLR|TSSOP|SOD|SMD|c1608|c3216|CAPRR|CAPCC|USB-C|DQN|DOA|PX|DFN|MSOP|VSSOP|TO-?\d)`)
	reValue  = regexp.MustCompile(`(nF|uF|pF|mH|uH|KF|KB|MF|F|B|M|m|V|VAC|W|K|k|R|Ω)$`)
	reNum    = regexp.MustCompile(`^[\d.]+$`)
	reNet    = regexp.MustCompile(`^/?[A-Z][A-Za-z0-9_+\-]{1,20}$`)
	reLower2 = regexp.MustCompile(`[a-z]{2,}`)
	rePartA  = regexp.MustCompile(`\d{3,}|^\d`)
	rePartB  = regexp.MustCompile(`^[AB]\d{1,2}$|^MH\d$|^[A-Z]+\d+[A-Z]+\d+[A-Z]*$`)
	reIC     = regexp.MustCompile(`^(U|ISO|J|LS|TSW|Y|Q|T|IC)\d`)
	reDigit  = regexp.MustCompile(`\d`)
)

var misc = map[string]bool{}

func init() {
	for _, s := range strings.Fields("NC A3 A4 A2 MicroInv Application Drawn Checked Approved Description Revision Update Size Page of Date Title Sheet Document Number Rev") {
		misc[s] = true
	}
}

func classify(s string) string {
	switch {
	case reRefdes.MatchString(s):
		return "ref"
	case reDigits.MatchString(s):
		return "num"
	case reFoot.MatchString(s):
		return "foot"
	case misc[s]:
		return "misc"
	case reDigit.MatchString(s) && reValue.MatchString(s) || reNum.MatchString(s):
		return "val"
	case rePartA.MatchString(s) || rePartB.MatchString(s):
		return "part"
	case reNet.MatchString(s) && !reLower2.MatchString(s):
		return "name"
	}
	return "other"
}

type comp struct {
	ref   string
	lines []string
	body  int
	sbb   rect
	pins  []netlist.Pin
}

type pageResult struct {
	comps    map[string]*comp
	netNames map[int][]string
	pinNets  [][2]interface{}
	e        *extracted
	unassign int
}

func buildPage(pc *pdf.PageContent) *pageResult {
	e := extractPage(pc)
	var blk []*text
	for _, t := range e.texts {
		if t.col == 0 && strings.TrimSpace(t.t) != "" {
			t.cls = classify(strings.TrimSpace(t.t))
			blk = append(blk, t)
		}
	}
	sort.SliceStable(blk, func(i, j int) bool {
		a, b := math.Round(blk[i].bb.x0), math.Round(blk[j].bb.x0)
		if a != b {
			return a < b
		}
		return blk[i].bb.y0 < blk[j].bb.y0
	})
	used := map[int]bool{}
	var stacks [][]*text
	stackOK := map[string]bool{"val": true, "foot": true, "part": true, "other": true, "misc": true, "name": true}
	for a, t := range blk {
		if used[a] || t.cls != "ref" {
			continue
		}
		st := []*text{t}
		used[a] = true
		cur := t
		for changed := true; changed; {
			changed = false
			for b, u := range blk {
				if used[b] {
					continue
				}
				if math.Abs(u.bb.x0-cur.bb.x0) < 2.5 && u.bb.y0-cur.bb.y1 >= 0 && u.bb.y0-cur.bb.y1 < 3.5 && stackOK[u.cls] {
					st = append(st, u)
					used[b] = true
					cur = u
					changed = true
					break
				}
			}
		}
		stacks = append(stacks, st)
	}
	for i, st := range stacks {
		t := st[0]
		for b, u := range blk {
			if used[b] {
				continue
			}
			if math.Abs(u.bb.y0-t.bb.y0) < 1.5 && u.bb.x0-t.bb.x1 > 0 && u.bb.x0-t.bb.x1 < 12 && (u.cls == "val" || u.cls == "foot" || u.cls == "part") {
				stacks[i] = append(stacks[i], u)
				used[b] = true
			}
		}
	}
	sbbox := func(st []*text) rect {
		r := st[0].bb
		for _, x := range st[1:] {
			r = union(r, x.bb)
		}
		return r
	}
	bodies := e.bodies
	items := e.items
	var comps map[string]*comp
	var bodyRef map[int][]string
	// One body per reference designator, nearest first. OrCAD puts the
	// reference and value above (or right of) the body, so a body above
	// its text is penalised.
	assign := func() {
		comps = map[string]*comp{}
		bodyRef = map[int][]string{}
		type cand struct {
			d  float64
			si int
			bi int
		}
		var cs []cand
		sbs := make([]rect, len(stacks))
		for si, st := range stacks {
			sbs[si] = sbbox(st)
			ref := strings.TrimSpace(st[0].t)
			c := &comp{ref: ref, body: -1, sbb: sbs[si]}
			for _, x := range st[1:] {
				c.lines = append(c.lines, strings.TrimSpace(x.t))
			}
			comps[ref] = c
			for bi, bb := range bodies {
				d := rectDist(sbs[si], bb)
				if d > 25 {
					continue
				}
				if (bb.y0+bb.y1)/2 < (sbs[si].y0+sbs[si].y1)/2-1 {
					d += 4
				}
				cs = append(cs, cand{d, si, bi})
			}
		}
		sort.SliceStable(cs, func(i, j int) bool { return cs[i].d < cs[j].d })
		doneS := map[int]bool{}
		for _, c := range cs {
			if doneS[c.si] || len(bodyRef[c.bi]) > 0 {
				continue
			}
			doneS[c.si] = true
			ref := strings.TrimSpace(stacks[c.si][0].t)
			comps[ref].body = c.bi
			bodyRef[c.bi] = append(bodyRef[c.bi], ref)
		}
	}
	assign()
	for iter := 0; iter < 3; iter++ {
		multi := map[int]bool{}
		for bi, v := range bodyRef {
			if len(v) > 1 {
				multi[bi] = true
			}
		}
		if len(multi) == 0 {
			break
		}
		var nb []rect
		var ni [][]rect
		for bi := range bodies {
			if multi[bi] {
				sb, si := cluster(items[bi], 0.6)
				if len(sb) > 1 {
					nb = append(nb, sb...)
					ni = append(ni, si...)
					continue
				}
			}
			nb = append(nb, bodies[bi])
			ni = append(ni, items[bi])
		}
		bodies, items = nb, ni
		assign()
	}
	refs := make([]string, 0, len(comps))
	for r := range comps {
		refs = append(refs, r)
	}
	sort.Strings(refs)
	for _, ref := range refs {
		c := comps[ref]
		if c.body >= 0 {
			continue
		}
		best, bi := -1.0, -1
		for k, bb := range bodies {
			if _, taken := bodyRef[k]; taken {
				continue
			}
			d := rectDist(c.sbb, bb)
			if d <= 60 && (best < 0 || d < best) {
				best, bi = d, k
			}
		}
		if bi >= 0 {
			c.body = bi
			bodyRef[bi] = append(bodyRef[bi], ref)
		}
	}
	// transformers absorb refdes-less bodies within 15 pt
	absorbed := map[int]string{}
	for _, ref := range refs {
		c := comps[ref]
		if !strings.HasPrefix(ref, "T") || c.body < 0 {
			continue
		}
		grp := map[int]bool{c.body: true}
		for changed := true; changed; {
			changed = false
			for bi, bb := range bodies {
				if grp[bi] {
					continue
				}
				if _, taken := bodyRef[bi]; taken {
					continue
				}
				for g := range grp {
					if rectDist(bb, bodies[g]) <= 15 {
						grp[bi] = true
						changed = true
						break
					}
				}
			}
		}
		for g := range grp {
			absorbed[g] = ref
		}
	}
	// pin numbers and names
	var nums, names []*text
	for _, t := range e.texts {
		s := strings.TrimSpace(t.t)
		if t.col == 0 && reDigits.MatchString(s) {
			nums = append(nums, t)
		}
		if isPinNameCol(t.col) && s != "" {
			names = append(names, t)
		}
	}
	for _, pr := range e.pins {
		bn := -1.0
		for _, t := range nums {
			c := pt{(t.bb.x0 + t.bb.x1) / 2, (t.bb.y0 + t.bb.y1) / 2}
			d := segPtDist(pr.s, c)
			if d <= 4.5 && (bn < 0 || d < bn) {
				bn = d
				pr.num = strings.TrimSpace(t.t)
			}
		}
		best := -1.0
		for _, ep := range pr.s.ends() {
			for bi, bb := range bodies {
				d := rectDist(ptRect(ep), bb)
				if best < 0 || d < best {
					best, pr.body, pr.inner = d, bi, ep
				}
			}
		}
		if best < 0 || best > 7.0 {
			pr.body = -1
		}
		if best < 0 {
			pr.inner = pr.s.ends()[0]
		}
		bm := -1.0
		for _, t := range names {
			d := rectDist(ptRect(pr.inner), t.bb)
			if d <= 6 && (bm < 0 || d < bm) {
				bm = d
				pr.name = strings.TrimSpace(t.t)
			}
		}
	}
	// net names
	netNames := map[int][]string{}
	for _, t := range e.texts {
		s := strings.TrimSpace(t.t)
		if s == "" || isPinNameCol(t.col) || t.size > 8 || t.near < 0 {
			continue
		}
		lim := 3.0
		if t.col == colRed {
			lim = 24.0
		}
		if t.near > lim {
			continue
		}
		if t.col == colRed || classify(s) == "name" {
			if misc[s] {
				continue
			}
			id := e.u.f(t.nearID)
			if !contains(netNames[id], s) {
				netNames[id] = append(netNames[id], s)
			}
		}
	}
	res := &pageResult{comps: comps, netNames: netNames, e: e}
	near := func(p pt, r rect) float64 { return rectDist(ptRect(p), r) }
	for _, pr := range e.pins {
		ep := pr.inner
		ref := ""
		if pr.body >= 0 {
			if a, ok := absorbed[pr.body]; ok {
				ref = a
			} else {
				rs := bodyRef[pr.body]
				if len(rs) == 1 {
					ref = rs[0]
				} else if len(rs) > 1 {
					var ic []string
					for _, r := range rs {
						if reIC.MatchString(r) {
							ic = append(ic, r)
						}
					}
					n, _ := strconv.Atoi(pr.num)
					cand := rs
					if (pr.name != "" || n > 2) && len(ic) > 0 {
						cand = ic
					}
					ref = cand[0]
					for _, r := range cand[1:] {
						if near(ep, comps[r].sbb) < near(ep, comps[ref].sbb) {
							ref = r
						}
					}
				}
			}
		}
		if ref == "" {
			best, bi := -1.0, -1
			for k := range bodies {
				_, a := absorbed[k]
				_, b := bodyRef[k]
				if !a && !b {
					continue
				}
				d := near(ep, bodies[k])
				if d <= 25 && (best < 0 || d < best) {
					best, bi = d, k
				}
			}
			if bi >= 0 {
				if a, ok := absorbed[bi]; ok {
					ref = a
				} else {
					rs := bodyRef[bi]
					ref = rs[0]
					for _, r := range rs[1:] {
						if near(ep, comps[r].sbb) < near(ep, comps[ref].sbb) {
							ref = r
						}
					}
				}
			}
		}
		netID := -1
		if pr.net >= 0 {
			netID = e.u.f(pr.net)
		}
		if ref == "" {
			res.unassign++
			continue
		}
		res.pinNets = append(res.pinNets, [2]interface{}{ref, netID})
		comps[ref].pins = append(comps[ref].pins, netlist.Pin{Num: pr.num, Name: pr.name, Net: strconv.Itoa(netID)})
	}
	return res
}

func contains(s []string, x string) bool {
	for _, y := range s {
		if y == x {
			return true
		}
	}
	return false
}

// Detect reports whether a page looks like an OrCAD Capture export.
func Detect(pc *pdf.PageContent) bool {
	var blue, brown int
	for _, p := range pc.Paths {
		if !p.Stroke {
			continue
		}
		if sameColor(p.SColor, cBlue) {
			blue++
		}
		if sameColor(p.SColor, cBrown) {
			brown++
		}
	}
	return blue >= 10 && brown >= 10
}

var reSection = regexp.MustCompile(`^((?:U|IC|ISO)\d+)([A-H])$`)

// FromPDF rebuilds the netlist of every OrCAD-coloured page and merges nets
// across pages by name (power symbols, ports, off-page connectors).
func FromPDF(d *Doc) (*netlist.Netlist, error) {
	r := d.R
	nl := netlist.New(d.Name, "pdf")
	var notes []string
	type key struct{ page, id int }
	parent := map[string]string{}
	var find func(string) string
	find = func(x string) string {
		if _, ok := parent[x]; !ok {
			parent[x] = x
		}
		for parent[x] != x {
			parent[x] = parent[parent[x]]
			x = parent[x]
		}
		return x
	}
	join := func(a, b string) {
		ra, rb := find(a), find(b)
		if ra != rb {
			parent[ra] = rb
		}
	}
	names := map[string][]string{}
	type pinRef struct {
		ref  string
		pin  int
		page int
	}
	pages := 0
	for i := 0; i < r.NumPages(); i++ {
		pc := d.Page(i)
		if !Detect(pc) {
			continue
		}
		pages++
		res := buildPage(pc)
		for id, ns := range res.netNames {
			k := fmt.Sprintf("%d:%d", i, id)
			for _, n := range ns {
				join(k, "N:"+n)
				names["N:"+n] = append(names["N:"+n], n)
			}
		}
		refs := make([]string, 0, len(res.comps))
		for r := range res.comps {
			refs = append(refs, r)
		}
		sort.Strings(refs)
		for _, ref := range refs {
			c := res.comps[ref]
			base := ref
			if m := reSection.FindStringSubmatch(ref); m != nil {
				base = m[1]
			}
			p := nl.Parts[base]
			if p == nil {
				p = &netlist.Part{Ref: base, Page: strconv.Itoa(i + 1)}
				nl.Parts[base] = p
			}
			if len(p.Lines) == 0 {
				p.Lines = c.lines
			}
			for _, pin := range c.pins {
				dupe := false
				for _, q := range p.Pins {
					if q.Num == pin.Num && pin.Num != "" && q.Name == pin.Name && q.Net == fmt.Sprintf("%d:%s", i, pin.Net) {
						dupe = true
					}
				}
				if dupe {
					continue
				}
				if pin.Net == "-1" {
					pin.Net = ""
				} else {
					pin.Net = fmt.Sprintf("%d:%s", i, pin.Net)
					find(pin.Net)
				}
				p.Pins = append(p.Pins, pin)
			}
		}
		if res.unassign > 0 {
			notes = append(notes, fmt.Sprintf("p.%d: 부품에 귀속하지 못한 핀 %d개", i+1, res.unassign))
		}
	}
	if pages == 0 {
		return nil, fmt.Errorf("OrCAD 기본 색상(배선 파랑·핀 갈색) 페이지가 없습니다")
	}
	// name every merged net
	label := map[string]string{}
	for k, ns := range names {
		root := find(k)
		cur := label[root]
		for _, n := range ns {
			if cur == "" {
				cur = n
			} else if !strings.Contains("/"+cur+"/", "/"+n+"/") {
				cur += "/" + n
			}
		}
		label[root] = cur
	}
	var roots []string
	seen := map[string]bool{}
	for _, p := range nl.Parts {
		for _, q := range p.Pins {
			if q.Net != "" && !seen[find(q.Net)] && label[find(q.Net)] == "" {
				seen[find(q.Net)] = true
				roots = append(roots, find(q.Net))
			}
		}
	}
	sort.Strings(roots)
	for i, r := range roots {
		label[r] = fmt.Sprintf("N%03d", i+1)
	}
	for _, p := range nl.Parts {
		for k := range p.Pins {
			if p.Pins[k].Net != "" {
				p.Pins[k].Net = label[find(p.Pins[k].Net)]
			}
			if p.Pins[k].Num == "" {
				p.Pins[k].Num = "?"
			}
		}
		p.Value = pickValue(p.Lines)
	}
	nl.Notes = append(notes, fmt.Sprintf("회로도 PDF 에서 그림 색상으로 복원한 넷리스트입니다(%d페이지). 핀 귀속·넷 이름은 추정이므로 원본 회로도로 확인하세요.", pages))
	nl.Index()
	return nl, nil
}

func pickValue(lines []string) string {
	for _, l := range lines {
		c := classify(l)
		if c == "part" || c == "val" || c == "other" {
			return l
		}
	}
	if len(lines) > 0 {
		return lines[0]
	}
	return ""
}
