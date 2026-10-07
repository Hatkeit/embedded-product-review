package pdf

import (
	"bytes"
	"errors"
	"regexp"
	"strconv"
)

type xrefEntry struct {
	typ    int // 1 = in file at off, 2 = in object stream
	off    int
	stream int
	idx    int
	gen    int
}

type Reader struct {
	b       []byte
	xref    map[int]xrefEntry
	trailer Dict
	cache   map[int]Object
	objStms map[int]*objStm
	crypt   *decrypter
	encRef  int
	pages   []*Page
	loading map[int]bool
}

type objStm struct {
	data  []byte
	offs  map[int]int
	first int
}

// Open parses a PDF held in memory.
func Open(b []byte) (*Reader, error) {
	r := &Reader{b: b, xref: map[int]xrefEntry{}, cache: map[int]Object{}, objStms: map[int]*objStm{}, loading: map[int]bool{}, encRef: -1}
	if err := r.loadXref(); err != nil || len(r.xref) == 0 || r.trailer["Root"] == nil {
		r.xref = map[int]xrefEntry{}
		r.trailer = Dict{}
		r.scan()
	}
	if enc := r.trailer["Encrypt"]; enc != nil {
		if ref, ok := enc.(Ref); ok {
			r.encRef = ref.Num
		}
		ed, _ := r.resolve(enc).(Dict)
		if ed != nil {
			ids, _ := r.resolve(r.trailer["ID"]).(Array)
			if err := r.setupCrypt(ed, ids); err != nil {
				return nil, err
			}
			r.cache = map[int]Object{}
			r.objStms = map[int]*objStm{}
		}
	}
	if err := r.loadPages(); err != nil {
		return nil, err
	}
	return r, nil
}

func (r *Reader) loadXref() error {
	i := bytes.LastIndex(r.b, []byte("startxref"))
	if i < 0 {
		return errors.New("no startxref")
	}
	lx := lexer{b: r.b, pos: i + 9}
	t := lx.next()
	if t.kind != tNum {
		return errors.New("bad startxref")
	}
	off := int(t.num)
	seen := map[int]bool{}
	first := true
	for off > 0 && off < len(r.b) && !seen[off] {
		seen[off] = true
		tr, err := r.readXrefAt(off)
		if err != nil {
			// try to recover a slightly wrong offset
			if j := bytes.Index(r.b[max(0, off-64):min(len(r.b), off+64)], []byte("xref")); j >= 0 && first {
				off = max(0, off-64) + j
				tr, err = r.readXrefAt(off)
			}
			if err != nil {
				return err
			}
		}
		if first {
			r.trailer = tr
			first = false
		}
		if xs, ok := tr["XRefStm"]; ok {
			if o, ok := num(xs); ok {
				r.readXrefAt(int(o))
			}
		}
		p, ok := num(tr["Prev"])
		if !ok {
			break
		}
		off = int(p)
	}
	return nil
}

func (r *Reader) readXrefAt(off int) (Dict, error) {
	lx := lexer{b: r.b, pos: off}
	lx.skipWS()
	if bytes.HasPrefix(r.b[lx.pos:], []byte("xref")) {
		lx.pos += 4
		for {
			p := parser{lx: lx}
			t := p.tok()
			if t.kind == tKeyword && string(t.s) == "trailer" {
				lx = p.lx
				pp := parser{lx: lx, allowRefs: true}
				o, _ := pp.object(0)
				d, _ := o.(Dict)
				return d, nil
			}
			if t.kind != tNum {
				return nil, errors.New("bad xref section")
			}
			t2 := p.tok()
			start, count := int(t.num), int(t2.num)
			lx = p.lx
			for k := 0; k < count; k++ {
				lx.skipWS()
				if lx.pos+18 > len(r.b) {
					return nil, errors.New("truncated xref")
				}
				line := r.b[lx.pos:min(len(r.b), lx.pos+20)]
				f := bytes.Fields(line)
				if len(f) < 3 {
					return nil, errors.New("bad xref entry")
				}
				o, _ := strconv.Atoi(string(f[0]))
				g, _ := strconv.Atoi(string(f[1]))
				n := start + k
				if _, exists := r.xref[n]; !exists {
					if f[2][0] == 'n' {
						r.xref[n] = xrefEntry{typ: 1, off: o, gen: g}
					} else {
						r.xref[n] = xrefEntry{typ: 0}
					}
				}
				// entries are nominally 20 bytes; advance past the type letter
				idx := bytes.IndexAny(line, "nf")
				lx.pos += idx + 1
			}
		}
	}
	// cross-reference stream
	p := parser{lx: lx, allowRefs: true}
	p.tok()
	p.tok()
	kw := p.tok()
	if kw.kind != tKeyword || string(kw.s) != "obj" {
		return nil, errors.New("xref offset does not point to xref")
	}
	o, _ := p.object(0)
	d, ok := o.(Dict)
	if !ok {
		return nil, errors.New("bad xref stream")
	}
	raw := r.streamBytes(&p.lx, d)
	data, err := applyFilters(raw, d, r.resolveNoCrypt)
	if err != nil {
		return nil, err
	}
	w, _ := d["W"].(Array)
	if len(w) < 3 {
		return nil, errors.New("bad /W")
	}
	ws := []int{intOr(w[0], 0), intOr(w[1], 0), intOr(w[2], 0)}
	rowLen := ws[0] + ws[1] + ws[2]
	index, _ := d["Index"].(Array)
	if index == nil {
		index = Array{0.0, numOr(d["Size"], 0)}
	}
	pos := 0
	field := func(n int) int {
		v := 0
		for k := 0; k < n; k++ {
			v = v<<8 | int(data[pos+k])
		}
		pos += n
		return v
	}
	for s := 0; s+1 < len(index); s += 2 {
		start, count := intOr(index[s], 0), intOr(index[s+1], 0)
		for k := 0; k < count && pos+rowLen <= len(data); k++ {
			typ := 1
			if ws[0] > 0 {
				typ = field(ws[0])
			}
			a := field(ws[1])
			b := field(ws[2])
			n := start + k
			if _, exists := r.xref[n]; exists {
				continue
			}
			switch typ {
			case 1:
				r.xref[n] = xrefEntry{typ: 1, off: a, gen: b}
			case 2:
				r.xref[n] = xrefEntry{typ: 2, stream: a, idx: b}
			default:
				r.xref[n] = xrefEntry{typ: 0}
			}
		}
	}
	return d, nil
}

var objHdr = regexp.MustCompile(`(\d+)\s+(\d+)\s+obj\b`)

// scan rebuilds the cross-reference table by searching for "n g obj".
func (r *Reader) scan() {
	for _, m := range objHdr.FindAllSubmatchIndex(r.b, -1) {
		n, _ := strconv.Atoi(string(r.b[m[2]:m[3]]))
		g, _ := strconv.Atoi(string(r.b[m[4]:m[5]]))
		r.xref[n] = xrefEntry{typ: 1, off: m[0], gen: g}
	}
	for i := 0; ; {
		j := bytes.Index(r.b[i:], []byte("trailer"))
		if j < 0 {
			break
		}
		p := parser{lx: lexer{b: r.b, pos: i + j + 7}, allowRefs: true}
		if o, _ := p.object(0); o != nil {
			if d, ok := o.(Dict); ok {
				for k, v := range d {
					r.trailer[k] = v
				}
			}
		}
		i += j + 7
	}
	if r.trailer["Root"] == nil {
		// find a catalog
		for n := range r.xref {
			if d, ok := r.resolve(Ref{n, 0}).(Dict); ok && d.Name("Type") == "Catalog" {
				r.trailer["Root"] = Ref{n, 0}
				break
			}
		}
	}
	// object streams found by scanning
	for n := range r.xref {
		if s, ok := r.resolve(Ref{n, 0}).(*Stream); ok && s.Dict.Name("Type") == "ObjStm" {
			if os := r.loadObjStm(n); os != nil {
				for on := range os.offs {
					if _, exists := r.xref[on]; !exists {
						r.xref[on] = xrefEntry{typ: 2, stream: n}
					}
				}
			}
		}
	}
}

func (r *Reader) streamBytes(lx *lexer, d Dict) []byte {
	p := parser{lx: *lx}
	t := p.tok()
	if t.kind != tKeyword || string(t.s) != "stream" {
		return nil
	}
	pos := p.lx.pos
	if pos < len(r.b) && r.b[pos] == '\r' {
		pos++
	}
	if pos < len(r.b) && r.b[pos] == '\n' {
		pos++
	}
	length := -1
	if l, ok := num(r.resolveNoCrypt(d["Length"])); ok {
		length = int(l)
	}
	if length >= 0 && pos+length <= len(r.b) {
		end := pos + length
		tail := r.b[end:min(len(r.b), end+20)]
		if bytes.Contains(tail, []byte("endstream")) {
			return r.b[pos:end]
		}
	}
	e := bytes.Index(r.b[pos:], []byte("endstream"))
	if e < 0 {
		return r.b[pos:]
	}
	end := pos + e
	for end > pos && (r.b[end-1] == '\n' || r.b[end-1] == '\r') {
		end--
	}
	return r.b[pos:end]
}

func (r *Reader) resolveNoCrypt(o Object) Object {
	saved := r.crypt
	r.crypt = nil
	v := r.resolve(o)
	r.crypt = saved
	return v
}

// resolve follows indirect references.
func (r *Reader) resolve(o Object) Object {
	for i := 0; i < 32; i++ {
		ref, ok := o.(Ref)
		if !ok {
			return o
		}
		o = r.load(ref.Num)
	}
	return nil
}

func (r *Reader) Resolve(o Object) Object { return r.resolve(o) }

func (r *Reader) load(n int) Object {
	if v, ok := r.cache[n]; ok {
		return v
	}
	if r.loading[n] {
		return nil
	}
	r.loading[n] = true
	defer delete(r.loading, n)
	e, ok := r.xref[n]
	if !ok {
		return nil
	}
	var v Object
	switch e.typ {
	case 1:
		v = r.loadAt(n, e)
	case 2:
		v = r.loadFromStm(n, e.stream)
	}
	r.cache[n] = v
	return v
}

func (r *Reader) loadAt(n int, e xrefEntry) Object {
	if e.off < 0 || e.off >= len(r.b) {
		return nil
	}
	p := parser{lx: lexer{b: r.b, pos: e.off}, allowRefs: true}
	t1 := p.tok()
	t2 := p.tok()
	t3 := p.tok()
	if t1.kind != tNum || t2.kind != tNum || t3.kind != tKeyword || string(t3.s) != "obj" {
		// offset is off: search nearby
		m := objHdr.FindIndex(r.b[e.off:min(len(r.b), e.off+200)])
		if m == nil {
			return nil
		}
		p = parser{lx: lexer{b: r.b, pos: e.off + m[1]}, allowRefs: true}
	}
	o, _ := p.object(0)
	ref := Ref{n, e.gen}
	if d, ok := o.(Dict); ok {
		save := p.lx
		t := p.tok()
		if t.kind == tKeyword && string(t.s) == "stream" {
			p.lx = save
			raw := r.streamBytes(&p.lx, d)
			if r.crypt != nil && n != r.encRef {
				d = r.crypt.decryptObj(d, ref).(Dict)
				if d.Name("Type") != "XRef" {
					raw = r.crypt.decrypt(raw, ref, r.crypt.stmMethod)
				}
			}
			return &Stream{Dict: d, Raw: raw, Ref: ref}
		}
	}
	if r.crypt != nil && n != r.encRef {
		o = r.crypt.decryptObj(o, ref)
	}
	return o
}

func (r *Reader) loadObjStm(sn int) *objStm {
	if os, ok := r.objStms[sn]; ok {
		return os
	}
	r.objStms[sn] = nil
	s, ok := r.load(sn).(*Stream)
	if !ok {
		return nil
	}
	data, err := r.StreamData(s)
	if err != nil {
		return nil
	}
	nobj := intOr(r.resolve(s.Dict["N"]), 0)
	first := intOr(r.resolve(s.Dict["First"]), 0)
	os := &objStm{data: data, offs: map[int]int{}, first: first}
	p := parser{lx: lexer{b: data}}
	for k := 0; k < nobj; k++ {
		a := p.tok()
		b := p.tok()
		if a.kind != tNum || b.kind != tNum {
			break
		}
		os.offs[int(a.num)] = int(b.num)
	}
	r.objStms[sn] = os
	return os
}

func (r *Reader) loadFromStm(n, sn int) Object {
	os := r.loadObjStm(sn)
	if os == nil {
		return nil
	}
	off, ok := os.offs[n]
	if !ok {
		return nil
	}
	p := parser{lx: lexer{b: os.data, pos: os.first + off}, allowRefs: true}
	o, _ := p.object(0)
	return o
}

// StreamData returns the decoded bytes of a stream.
func (r *Reader) StreamData(s *Stream) ([]byte, error) {
	if s == nil {
		return nil, errors.New("nil stream")
	}
	if !s.done {
		s.data, s.err = applyFilters(s.Raw, s.Dict, r.resolve)
		s.done = true
	}
	return s.data, s.err
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
