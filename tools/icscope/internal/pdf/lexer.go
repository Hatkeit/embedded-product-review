package pdf

import (
	"bytes"
	"strconv"
)

func isWhite(c byte) bool {
	return c == ' ' || c == '\n' || c == '\r' || c == '\t' || c == '\f' || c == 0
}

func isDelim(c byte) bool {
	switch c {
	case '(', ')', '<', '>', '[', ']', '{', '}', '/', '%':
		return true
	}
	return false
}

type tokKind int

const (
	tEOF tokKind = iota
	tNum
	tName
	tStr
	tDictOpen
	tDictClose
	tArrOpen
	tArrClose
	tKeyword
)

type token struct {
	kind  tokKind
	num   float64
	isInt bool
	s     []byte
}

type lexer struct {
	b   []byte
	pos int
}

func (l *lexer) skipWS() {
	for l.pos < len(l.b) {
		c := l.b[l.pos]
		if isWhite(c) {
			l.pos++
		} else if c == '%' {
			for l.pos < len(l.b) && l.b[l.pos] != '\n' && l.b[l.pos] != '\r' {
				l.pos++
			}
		} else {
			return
		}
	}
}

func (l *lexer) next() token {
	l.skipWS()
	if l.pos >= len(l.b) {
		return token{kind: tEOF}
	}
	c := l.b[l.pos]
	switch {
	case c == '/':
		l.pos++
		st := l.pos
		for l.pos < len(l.b) && !isWhite(l.b[l.pos]) && !isDelim(l.b[l.pos]) {
			l.pos++
		}
		return token{kind: tName, s: decodeName(l.b[st:l.pos])}
	case c == '(':
		return token{kind: tStr, s: l.literal()}
	case c == '<':
		if l.pos+1 < len(l.b) && l.b[l.pos+1] == '<' {
			l.pos += 2
			return token{kind: tDictOpen}
		}
		return token{kind: tStr, s: l.hex()}
	case c == '>':
		if l.pos+1 < len(l.b) && l.b[l.pos+1] == '>' {
			l.pos += 2
			return token{kind: tDictClose}
		}
		l.pos++
		return l.next()
	case c == '[':
		l.pos++
		return token{kind: tArrOpen}
	case c == ']':
		l.pos++
		return token{kind: tArrClose}
	case c == '{' || c == '}' || c == ')':
		l.pos++
		return token{kind: tKeyword, s: []byte{c}}
	case c == '+' || c == '-' || c == '.' || (c >= '0' && c <= '9'):
		st := l.pos
		l.pos++
		for l.pos < len(l.b) {
			d := l.b[l.pos]
			if (d >= '0' && d <= '9') || d == '.' || d == '-' || d == '+' {
				l.pos++
				continue
			}
			break
		}
		raw := l.b[st:l.pos]
		if f, ok := parseNum(raw); ok {
			isInt := !bytes.ContainsRune(raw, '.')
			return token{kind: tNum, num: f, isInt: isInt}
		}
		return token{kind: tKeyword, s: raw}
	default:
		st := l.pos
		for l.pos < len(l.b) && !isWhite(l.b[l.pos]) && !isDelim(l.b[l.pos]) {
			l.pos++
		}
		if l.pos == st {
			l.pos++
		}
		return token{kind: tKeyword, s: l.b[st:l.pos]}
	}
}

func parseNum(raw []byte) (float64, bool) {
	s := string(raw)
	// tolerate malformed numbers such as "--5" or "4.-2" that some producers write
	for len(s) > 1 && (s[0] == '-' || s[0] == '+') && (s[1] == '-' || s[1] == '+') {
		s = s[1:]
	}
	if s == "-" || s == "+" || s == "." || s == "" {
		return 0, true
	}
	if f, err := strconv.ParseFloat(s, 64); err == nil {
		return f, true
	}
	// cut at the first invalid character
	for i := len(s) - 1; i > 0; i-- {
		if f, err := strconv.ParseFloat(s[:i], 64); err == nil {
			return f, true
		}
	}
	return 0, false
}

func decodeName(b []byte) []byte {
	if bytes.IndexByte(b, '#') < 0 {
		return append([]byte(nil), b...)
	}
	out := make([]byte, 0, len(b))
	for i := 0; i < len(b); i++ {
		if b[i] == '#' && i+2 < len(b) {
			if v, err := strconv.ParseUint(string(b[i+1:i+3]), 16, 8); err == nil {
				out = append(out, byte(v))
				i += 2
				continue
			}
		}
		out = append(out, b[i])
	}
	return out
}

func (l *lexer) literal() []byte {
	l.pos++ // (
	depth := 1
	var out []byte
	for l.pos < len(l.b) {
		c := l.b[l.pos]
		l.pos++
		switch c {
		case '(':
			depth++
			out = append(out, c)
		case ')':
			depth--
			if depth == 0 {
				return out
			}
			out = append(out, c)
		case '\\':
			if l.pos >= len(l.b) {
				return out
			}
			e := l.b[l.pos]
			l.pos++
			switch e {
			case 'n':
				out = append(out, '\n')
			case 'r':
				out = append(out, '\r')
			case 't':
				out = append(out, '\t')
			case 'b':
				out = append(out, '\b')
			case 'f':
				out = append(out, '\f')
			case '\r':
				if l.pos < len(l.b) && l.b[l.pos] == '\n' {
					l.pos++
				}
			case '\n':
			default:
				if e >= '0' && e <= '7' {
					v := int(e - '0')
					for k := 0; k < 2 && l.pos < len(l.b) && l.b[l.pos] >= '0' && l.b[l.pos] <= '7'; k++ {
						v = v*8 + int(l.b[l.pos]-'0')
						l.pos++
					}
					out = append(out, byte(v))
				} else {
					out = append(out, e)
				}
			}
		default:
			out = append(out, c)
		}
	}
	return out
}

func hexVal(c byte) int {
	switch {
	case c >= '0' && c <= '9':
		return int(c - '0')
	case c >= 'a' && c <= 'f':
		return int(c-'a') + 10
	case c >= 'A' && c <= 'F':
		return int(c-'A') + 10
	}
	return -1
}

func (l *lexer) hex() []byte {
	l.pos++ // <
	var out []byte
	hi := -1
	for l.pos < len(l.b) {
		c := l.b[l.pos]
		l.pos++
		if c == '>' {
			break
		}
		v := hexVal(c)
		if v < 0 {
			continue
		}
		if hi < 0 {
			hi = v
		} else {
			out = append(out, byte(hi<<4|v))
			hi = -1
		}
	}
	if hi >= 0 {
		out = append(out, byte(hi<<4))
	}
	return out
}

// parser builds objects from tokens. allowRefs enables "n g R" detection,
// which is never valid inside content streams.
type parser struct {
	lx        lexer
	allowRefs bool
	peeked    []token
}

func (p *parser) tok() token {
	if n := len(p.peeked); n > 0 {
		t := p.peeked[n-1]
		p.peeked = p.peeked[:n-1]
		return t
	}
	return p.lx.next()
}

func (p *parser) unread(t token) { p.peeked = append(p.peeked, t) }

// object reads one object. It returns (obj, keyword, ok). When the next token
// is a bare keyword it is returned as Keyword.
func (p *parser) object(depth int) (Object, bool) {
	if depth > 200 {
		return nil, false
	}
	t := p.tok()
	switch t.kind {
	case tEOF:
		return nil, false
	case tNum:
		if p.allowRefs && t.isInt {
			t2 := p.tok()
			if t2.kind == tNum && t2.isInt {
				t3 := p.tok()
				if t3.kind == tKeyword && string(t3.s) == "R" {
					return Ref{int(t.num), int(t2.num)}, true
				}
				p.unread(t3)
				p.unread(t2)
				return t.num, true
			}
			p.unread(t2)
		}
		return t.num, true
	case tName:
		return Name(t.s), true
	case tStr:
		return String(t.s), true
	case tArrOpen:
		arr := Array{}
		for {
			t2 := p.tok()
			if t2.kind == tArrClose || t2.kind == tEOF {
				return arr, true
			}
			p.unread(t2)
			o, ok := p.object(depth + 1)
			if !ok {
				return arr, true
			}
			arr = append(arr, o)
		}
	case tDictOpen:
		d := Dict{}
		for {
			t2 := p.tok()
			if t2.kind == tDictClose || t2.kind == tEOF {
				return d, true
			}
			if t2.kind != tName {
				// garbage inside dictionary: skip it
				if t2.kind == tKeyword && (string(t2.s) == "endobj" || string(t2.s) == "stream") {
					p.unread(t2)
					return d, true
				}
				continue
			}
			v, ok := p.object(depth + 1)
			if !ok {
				return d, true
			}
			if kw, isKw := v.(Keyword); isKw && (kw == "endobj" || kw == "stream") {
				p.unread(token{kind: tKeyword, s: []byte(kw)})
				return d, true
			}
			d[Name(t2.s)] = v
		}
	case tKeyword:
		s := string(t.s)
		switch s {
		case "true":
			return true, true
		case "false":
			return false, true
		case "null":
			return nil, true
		}
		return Keyword(s), true
	}
	return nil, false
}
