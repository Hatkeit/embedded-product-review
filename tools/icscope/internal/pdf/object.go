// Package pdf is a small, dependency-free PDF reader: objects, cross-reference
// tables and streams, the standard security handler, stream filters, fonts
// and a content-stream interpreter that reports glyphs and painted paths.
package pdf

import (
	"fmt"
	"strconv"
)

// Object is any PDF object: nil, bool, float64, Name, String, Array, Dict,
// *Stream, Ref or Keyword (content-stream operators only).
type Object interface{}

type Name string
type String []byte
type Array []Object
type Dict map[Name]Object
type Keyword string

type Ref struct{ Num, Gen int }

func (r Ref) String() string { return fmt.Sprintf("%d %d R", r.Num, r.Gen) }

type Stream struct {
	Dict Dict
	Raw  []byte
	Ref  Ref
	data []byte
	done bool
	err  error
}

func num(o Object) (float64, bool) {
	switch v := o.(type) {
	case float64:
		return v, true
	case int:
		return float64(v), true
	}
	return 0, false
}

func numOr(o Object, def float64) float64 {
	if v, ok := num(o); ok {
		return v
	}
	return def
}

func intOr(o Object, def int) int {
	if v, ok := num(o); ok {
		return int(v)
	}
	return def
}

func nameOf(o Object) Name {
	if n, ok := o.(Name); ok {
		return n
	}
	return ""
}

func (d Dict) Name(k Name) Name { return nameOf(d[k]) }

func fmtNum(f float64) string { return strconv.FormatFloat(f, 'g', -1, 64) }
