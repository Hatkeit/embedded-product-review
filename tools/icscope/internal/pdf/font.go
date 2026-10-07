package pdf

import (
	"regexp"
	"strconv"
	"strings"
	"unicode/utf16"
)

// Font holds what is needed to turn shown strings into positioned text.
type Font struct {
	Subtype   Name
	BaseFont  string
	twoByte   bool
	codespace []csRange
	toUni     map[int]string
	enc       [256]string // simple fonts: glyph name per code
	encRune   [256]rune   // simple fonts: fallback unicode per code
	widths    map[int]float64
	dw        float64
	firstChar int
	matrix    Matrix // Type3 only
	Ascent    float64
	Descent   float64
	type3     bool
	gNames    bool // Ghostscript PScript Type3 fonts name glyphs g<N> = Mac glyph order
	vertical  bool
}

type csRange struct {
	n      int
	lo, hi int
}

// Glyph name of a simple-font code (Type1/TrueType/Type3), "" otherwise.
func (f *Font) GlyphName(code int) string {
	if f.twoByte || code < 0 || code > 255 {
		return ""
	}
	return f.enc[code]
}

func (r *Reader) loadFont(o Object) *Font {
	d, _ := r.resolve(o).(Dict)
	f := &Font{widths: map[int]float64{}, dw: 1000, Ascent: 0.8, Descent: -0.2, matrix: Matrix{0.001, 0, 0, 0.001, 0, 0}}
	if d == nil {
		return f
	}
	f.Subtype = d.Name("Subtype")
	f.BaseFont = string(nameOf(r.resolve(d["BaseFont"])))
	if f.Subtype == "Type0" {
		f.twoByte = true
		f.codespace = []csRange{{2, 0, 0xFFFF}}
		switch e := r.resolve(d["Encoding"]).(type) {
		case Name:
			if strings.HasSuffix(string(e), "-V") {
				f.vertical = true
			}
		case *Stream:
			if data, err := r.StreamData(e); err == nil {
				if cs := parseCodespace(data); len(cs) > 0 {
					f.codespace = cs
				}
			}
		}
		if da, ok := r.resolve(d["DescendantFonts"]).(Array); ok && len(da) > 0 {
			dd, _ := r.resolve(da[0]).(Dict)
			if dd != nil {
				f.dw = numOr(r.resolve(dd["DW"]), 1000)
				if w, ok := r.resolve(dd["W"]).(Array); ok {
					for i := 0; i < len(w); {
						c0 := intOr(r.resolve(w[i]), 0)
						if i+1 >= len(w) {
							break
						}
						if arr, ok := r.resolve(w[i+1]).(Array); ok {
							for k, x := range arr {
								f.widths[c0+k] = numOr(r.resolve(x), f.dw)
							}
							i += 2
							continue
						}
						if i+2 >= len(w) {
							break
						}
						c1 := intOr(r.resolve(w[i+1]), c0)
						wv := numOr(r.resolve(w[i+2]), f.dw)
						for c := c0; c <= c1 && c-c0 < 70000; c++ {
							f.widths[c] = wv
						}
						i += 3
					}
				}
				r.fontDescriptor(f, dd)
			}
		}
	} else {
		f.type3 = f.Subtype == "Type3"
		base := standardEnc
		symbolic := false
		if fd, ok := r.resolve(d["FontDescriptor"]).(Dict); ok {
			flags := intOr(r.resolve(fd["Flags"]), 0)
			symbolic = flags&4 != 0
		}
		if f.Subtype == "TrueType" || symbolic {
			base = winAnsi
		}
		var diffs Array
		switch e := r.resolve(d["Encoding"]).(type) {
		case Name:
			base = pickEnc(e, base)
		case Dict:
			if b := e.Name("BaseEncoding"); b != "" {
				base = pickEnc(b, base)
			}
			diffs, _ = r.resolve(e["Differences"]).(Array)
		}
		for c := 0; c < 256; c++ {
			f.encRune[c] = base[c]
		}
		code := 0
		gn := 0
		total := 0
		for _, x := range diffs {
			switch v := r.resolve(x).(type) {
			case float64:
				code = int(v)
			case Name:
				if code >= 0 && code < 256 {
					f.enc[code] = string(v)
					f.encRune[code] = glyphRune(string(v))
					total++
					if gNameRe.MatchString(string(v)) {
						gn++
					}
				}
				code++
			}
		}
		if f.type3 && total > 0 && gn == total {
			f.gNames = true
		}
		f.firstChar = intOr(r.resolve(d["FirstChar"]), 0)
		if w, ok := r.resolve(d["Widths"]).(Array); ok {
			for i, x := range w {
				f.widths[f.firstChar+i] = numOr(r.resolve(x), 0)
			}
		}
		if f.type3 {
			if m, ok := r.resolve(d["FontMatrix"]).(Array); ok {
				f.matrix = matrixFrom(resolveArr(r, m))
			}
			if bb, ok := r.resolve(d["FontBBox"]).(Array); ok && len(bb) == 4 {
				_, y0 := f.matrix.Apply(0, numOr(r.resolve(bb[1]), 0))
				_, y1 := f.matrix.Apply(0, numOr(r.resolve(bb[3]), 0))
				if y1 > y0 && y1-y0 < 5 {
					f.Ascent, f.Descent = y1, y0
				}
			}
		} else if fd, ok := r.resolve(d["FontDescriptor"]).(Dict); ok {
			r.fontDescriptor(f, Dict{"FontDescriptor": fd})
		}
		f.dw = 0
		if !f.type3 && len(f.widths) == 0 {
			f.dw = 500 // standard 14 font without widths: rough average
		}
	}
	if tu, ok := r.resolve(d["ToUnicode"]).(*Stream); ok {
		if data, err := r.StreamData(tu); err == nil {
			f.toUni = parseToUnicode(data)
			if !f.twoByte {
				// a simple font's ToUnicode is single-byte
			} else if cs := parseCodespace(data); len(cs) > 0 && len(f.codespace) == 1 && f.codespace[0].n == 2 {
				// keep 2-byte unless the cmap says otherwise
				allOne := true
				for _, c := range cs {
					if c.n != 1 {
						allOne = false
					}
				}
				if allOne {
					f.codespace = cs
				}
			}
		}
	}
	return f
}

var gNameRe = regexp.MustCompile(`^g\d+$`)

func resolveArr(r *Reader, a Array) Array {
	out := make(Array, len(a))
	for i := range a {
		out[i] = r.resolve(a[i])
	}
	return out
}

func (r *Reader) fontDescriptor(f *Font, d Dict) {
	fd, _ := r.resolve(d["FontDescriptor"]).(Dict)
	if fd == nil {
		return
	}
	a := numOr(r.resolve(fd["Ascent"]), 0)
	de := numOr(r.resolve(fd["Descent"]), 0)
	if a > 0 && a < 2000 {
		f.Ascent = a / 1000
	}
	if de < 0 && de > -1000 {
		f.Descent = de / 1000
	}
}

func pickEnc(n Name, def [256]rune) [256]rune {
	switch n {
	case "WinAnsiEncoding":
		return winAnsi
	case "MacRomanEncoding":
		return macRoman
	case "StandardEncoding":
		return standardEnc
	}
	return def
}

func glyphRune(name string) rune {
	if r, ok := glyphNames[name]; ok {
		return r
	}
	if i := strings.IndexByte(name, '.'); i > 0 {
		return glyphRune(name[:i])
	}
	if strings.HasPrefix(name, "uni") && len(name) >= 7 {
		if v, err := strconv.ParseUint(name[3:7], 16, 32); err == nil {
			return rune(v)
		}
	}
	if strings.HasPrefix(name, "u") && len(name) >= 5 && len(name) <= 7 {
		if v, err := strconv.ParseUint(name[1:], 16, 32); err == nil {
			return rune(v)
		}
	}
	return 0
}

// codes splits a shown string into character codes.
func (f *Font) codes(s []byte) []int {
	if !f.twoByte {
		out := make([]int, len(s))
		for i, b := range s {
			out[i] = int(b)
		}
		return out
	}
	var out []int
	for i := 0; i < len(s); {
		n := 0
		for _, cs := range f.codespace {
			if i+cs.n > len(s) {
				continue
			}
			v := 0
			for k := 0; k < cs.n; k++ {
				v = v<<8 | int(s[i+k])
			}
			if v >= cs.lo && v <= cs.hi {
				n = cs.n
				out = append(out, v)
				break
			}
		}
		if n == 0 {
			if i+1 < len(s) {
				out = append(out, int(s[i])<<8|int(s[i+1]))
				n = 2
			} else {
				out = append(out, int(s[i]))
				n = 1
			}
		}
		i += n
	}
	return out
}

// Text returns the Unicode text of a code.
func (f *Font) Text(code int) string {
	if f.gNames {
		if n := f.GlyphName(code); n != "" {
			if v, err := strconv.Atoi(n[1:]); err == nil && v+29 < 0x110000 && v+29 >= 32 {
				return string(rune(v + 29))
			}
		}
	}
	if f.toUni != nil {
		if s, ok := f.toUni[code]; ok {
			return s
		}
	}
	if !f.twoByte && code >= 0 && code < 256 {
		if r := f.encRune[code]; r != 0 {
			return string(r)
		}
	}
	return ""
}

// Width returns the advance of a code in text space units (1 = font size).
func (f *Font) Width(code int) float64 {
	w, ok := f.widths[code]
	if !ok {
		w = f.dw
	}
	if f.type3 {
		x, _ := f.matrix.Apply(w, 0)
		x0, _ := f.matrix.Apply(0, 0)
		return x - x0
	}
	return w / 1000
}

func parseCodespace(data []byte) []csRange {
	var out []csRange
	for _, blk := range sections(data, "begincodespacerange", "endcodespacerange") {
		p := parser{lx: lexer{b: blk}}
		for {
			a, ok1 := p.object(0)
			b, ok2 := p.object(0)
			if !ok1 || !ok2 {
				break
			}
			sa, _ := a.(String)
			sb, _ := b.(String)
			if len(sa) == 0 || len(sa) != len(sb) {
				continue
			}
			out = append(out, csRange{len(sa), bytesInt(sa), bytesInt(sb)})
		}
	}
	return out
}

func sections(data []byte, begin, end string) [][]byte {
	var out [][]byte
	s := string(data)
	for {
		i := strings.Index(s, begin)
		if i < 0 {
			return out
		}
		s = s[i+len(begin):]
		j := strings.Index(s, end)
		if j < 0 {
			return out
		}
		out = append(out, []byte(s[:j]))
		s = s[j+len(end):]
	}
}

func bytesInt(b []byte) int {
	v := 0
	for _, x := range b {
		v = v<<8 | int(x)
	}
	return v
}

func utf16be(b []byte) string {
	if len(b)%2 == 1 {
		b = append(b, 0)
	}
	u := make([]uint16, len(b)/2)
	for i := range u {
		u[i] = uint16(b[2*i])<<8 | uint16(b[2*i+1])
	}
	return string(utf16.Decode(u))
}

func parseToUnicode(data []byte) map[int]string {
	m := map[int]string{}
	for _, blk := range sections(data, "beginbfchar", "endbfchar") {
		p := parser{lx: lexer{b: blk}}
		for {
			a, ok1 := p.object(0)
			b, ok2 := p.object(0)
			if !ok1 || !ok2 {
				break
			}
			sa, _ := a.(String)
			switch v := b.(type) {
			case String:
				m[bytesInt(sa)] = utf16be(v)
			case Name:
				if r := glyphRune(string(v)); r != 0 {
					m[bytesInt(sa)] = string(r)
				}
			}
		}
	}
	for _, blk := range sections(data, "beginbfrange", "endbfrange") {
		p := parser{lx: lexer{b: blk}}
		for {
			a, ok1 := p.object(0)
			b, ok2 := p.object(0)
			c, ok3 := p.object(0)
			if !ok1 || !ok2 || !ok3 {
				break
			}
			sa, _ := a.(String)
			sb, _ := b.(String)
			lo, hi := bytesInt(sa), bytesInt(sb)
			if hi-lo > 65535 || hi < lo {
				continue
			}
			switch v := c.(type) {
			case String:
				base := []byte(v)
				for k := 0; lo+k <= hi; k++ {
					d := append([]byte(nil), base...)
					if len(d) > 0 {
						// increment the last byte(s)
						carry := k
						for i := len(d) - 1; i >= 0 && carry > 0; i-- {
							s := int(d[i]) + carry
							d[i] = byte(s & 0xff)
							carry = s >> 8
						}
					}
					m[lo+k] = utf16be(d)
				}
			case Array:
				for k, x := range v {
					if s, ok := x.(String); ok && lo+k <= hi {
						m[lo+k] = utf16be(s)
					}
				}
			}
		}
	}
	return m
}
