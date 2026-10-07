package pdf

import (
	"bytes"
	"compress/flate"
	"compress/zlib"
	"errors"
	"io"
)

func inflate(b []byte) ([]byte, error) {
	r, err := zlib.NewReader(bytes.NewReader(b))
	if err == nil {
		out, err2 := io.ReadAll(r)
		if err2 == nil || len(out) > 0 {
			return out, nil
		}
	}
	// raw deflate fallback (bad header / checksum)
	if len(b) > 2 {
		fr := flate.NewReader(bytes.NewReader(b[2:]))
		out, _ := io.ReadAll(fr)
		if len(out) > 0 {
			return out, nil
		}
	}
	fr := flate.NewReader(bytes.NewReader(b))
	out, err := io.ReadAll(fr)
	if len(out) > 0 {
		return out, nil
	}
	if err == nil {
		err = errors.New("empty inflate")
	}
	return nil, err
}

func predict(b []byte, parms Dict) []byte {
	if parms == nil {
		return b
	}
	pred := intOr(parms["Predictor"], 1)
	if pred <= 1 {
		return b
	}
	colors := intOr(parms["Colors"], 1)
	bpc := intOr(parms["BitsPerComponent"], 8)
	cols := intOr(parms["Columns"], 1)
	bpp := (colors*bpc + 7) / 8
	rowLen := (colors*bpc*cols + 7) / 8
	if pred == 2 {
		if bpc != 8 {
			return b
		}
		out := append([]byte(nil), b...)
		for r := 0; r+rowLen <= len(out); r += rowLen {
			for i := bpp; i < rowLen; i++ {
				out[r+i] += out[r+i-bpp]
			}
		}
		return out
	}
	// PNG predictors: every row starts with a filter type byte
	var out []byte
	prev := make([]byte, rowLen)
	for p := 0; p < len(b); p += rowLen + 1 {
		ft := b[p]
		end := p + 1 + rowLen
		if end > len(b) {
			end = len(b)
		}
		row := make([]byte, rowLen)
		copy(row, b[p+1:end])
		for i := 0; i < rowLen; i++ {
			var a, c byte
			if i >= bpp {
				a = row[i-bpp]
				c = prev[i-bpp]
			}
			up := prev[i]
			switch ft {
			case 1:
				row[i] += a
			case 2:
				row[i] += up
			case 3:
				row[i] += byte((int(a) + int(up)) / 2)
			case 4:
				pa := abs(int(up) - int(c))
				pb := abs(int(a) - int(c))
				pc := abs(int(a) + int(up) - 2*int(c))
				switch {
				case pa <= pb && pa <= pc:
					row[i] += a
				case pb <= pc:
					row[i] += up
				default:
					row[i] += c
				}
			}
		}
		out = append(out, row...)
		prev = row
	}
	return out
}

func abs(x int) int {
	if x < 0 {
		return -x
	}
	return x
}

func ascii85(b []byte) []byte {
	var out []byte
	var group [5]byte
	n := 0
	for i := 0; i < len(b); i++ {
		c := b[i]
		if isWhite(c) {
			continue
		}
		if c == '~' {
			break
		}
		if c == 'z' && n == 0 {
			out = append(out, 0, 0, 0, 0)
			continue
		}
		if c < '!' || c > 'u' {
			continue
		}
		group[n] = c - '!'
		n++
		if n == 5 {
			v := uint32(0)
			for _, g := range group {
				v = v*85 + uint32(g)
			}
			out = append(out, byte(v>>24), byte(v>>16), byte(v>>8), byte(v))
			n = 0
		}
	}
	if n > 1 {
		for k := n; k < 5; k++ {
			group[k] = 84
		}
		v := uint32(0)
		for _, g := range group {
			v = v*85 + uint32(g)
		}
		tmp := []byte{byte(v >> 24), byte(v >> 16), byte(v >> 8), byte(v)}
		out = append(out, tmp[:n-1]...)
	}
	return out
}

func asciiHex(b []byte) []byte {
	l := lexer{b: append([]byte{'<'}, b...)}
	return l.hex()
}

func runLength(b []byte) []byte {
	var out []byte
	for i := 0; i < len(b); {
		n := int(b[i])
		i++
		switch {
		case n < 128:
			end := i + n + 1
			if end > len(b) {
				end = len(b)
			}
			out = append(out, b[i:end]...)
			i = end
		case n > 128:
			if i < len(b) {
				for k := 0; k < 257-n; k++ {
					out = append(out, b[i])
				}
			}
			i++
		default:
			return out
		}
	}
	return out
}

func lzw(b []byte, early int) []byte {
	var out []byte
	dict := make([][]byte, 0, 4096)
	reset := func() {
		dict = dict[:0]
		for i := 0; i < 256; i++ {
			dict = append(dict, []byte{byte(i)})
		}
		dict = append(dict, nil, nil) // 256 clear, 257 EOD
	}
	reset()
	width := 9
	var bitbuf uint32
	nbits := 0
	var prev []byte
	for i := 0; i < len(b); i++ {
		bitbuf = bitbuf<<8 | uint32(b[i])
		nbits += 8
		for nbits >= width {
			code := int(bitbuf>>(uint(nbits-width))) & (1<<uint(width) - 1)
			nbits -= width
			switch {
			case code == 256:
				reset()
				width = 9
				prev = nil
				continue
			case code == 257:
				return out
			}
			var entry []byte
			if code < len(dict) && dict[code] != nil {
				entry = dict[code]
			} else if prev != nil {
				entry = append(append([]byte(nil), prev...), prev[0])
			} else {
				return out
			}
			out = append(out, entry...)
			if prev != nil && len(dict) < 4096 {
				ne := append(append([]byte(nil), prev...), entry[0])
				dict = append(dict, ne)
			}
			prev = entry
			if len(dict)+early >= 1<<uint(width) && width < 12 {
				width++
			}
		}
	}
	return out
}

// decodeStream applies the stream's filter chain. Image codecs are left
// encoded; callers never need decoded image pixels.
func applyFilters(raw []byte, d Dict, resolve func(Object) Object) ([]byte, error) {
	f := resolve(d["Filter"])
	p := resolve(d["DecodeParms"])
	if f == nil {
		f = resolve(d["F"]) // inline images
		if p == nil {
			p = resolve(d["DP"])
		}
	}
	var filters []Name
	var parms []Dict
	switch v := f.(type) {
	case Name:
		filters = []Name{v}
		pd, _ := p.(Dict)
		parms = []Dict{pd}
	case Array:
		for i, x := range v {
			filters = append(filters, nameOf(resolve(x)))
			var pd Dict
			if pa, ok := p.(Array); ok && i < len(pa) {
				pd, _ = resolve(pa[i]).(Dict)
			}
			parms = append(parms, pd)
		}
	}
	data := raw
	for i, name := range filters {
		var err error
		switch name {
		case "FlateDecode", "Fl":
			data, err = inflate(data)
			if err != nil {
				return nil, err
			}
			data = predict(data, parms[i])
		case "LZWDecode", "LZW":
			early := 1
			if parms[i] != nil {
				early = intOr(parms[i]["EarlyChange"], 1)
			}
			data = predict(lzw(data, early), parms[i])
		case "ASCII85Decode", "A85":
			data = ascii85(data)
		case "ASCIIHexDecode", "AHx":
			data = asciiHex(data)
		case "RunLengthDecode", "RL":
			data = runLength(data)
		case "Crypt":
			// identity crypt filter
		default:
			return data, errImage
		}
	}
	return data, nil
}

var errImage = errors.New("image codec not decoded")
