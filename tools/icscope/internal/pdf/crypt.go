package pdf

import (
	"bytes"
	"crypto/aes"
	"crypto/cipher"
	"crypto/md5"
	"crypto/rc4"
	"crypto/sha256"
	"crypto/sha512"
	"errors"
)

var padding = []byte{
	0x28, 0xBF, 0x4E, 0x5E, 0x4E, 0x75, 0x8A, 0x41, 0x64, 0x00, 0x4E, 0x56, 0xFF, 0xFA, 0x01, 0x08,
	0x2E, 0x2E, 0x00, 0xB6, 0xD0, 0x68, 0x3E, 0x80, 0x2F, 0x0C, 0xA9, 0xFE, 0x64, 0x53, 0x69, 0x7A,
}

type cryptMethod int

const (
	cmNone cryptMethod = iota
	cmRC4
	cmAES128
	cmAES256
)

type decrypter struct {
	key       []byte
	strMethod cryptMethod
	stmMethod cryptMethod
}

func (r *Reader) setupCrypt(enc Dict, ids Array) error {
	if enc.Name("Filter") != "Standard" {
		return errors.New("unsupported security handler " + string(enc.Name("Filter")))
	}
	v := intOr(r.resolve(enc["V"]), 0)
	rev := intOr(r.resolve(enc["R"]), 2)
	length := intOr(r.resolve(enc["Length"]), 40)
	o, _ := r.resolve(enc["O"]).(String)
	u, _ := r.resolve(enc["U"]).(String)
	p := intOr(r.resolve(enc["P"]), 0)
	var id0 []byte
	if len(ids) > 0 {
		if s, ok := r.resolve(ids[0]).(String); ok {
			id0 = s
		}
	}
	d := &decrypter{strMethod: cmRC4, stmMethod: cmRC4}
	if v >= 4 {
		cf, _ := r.resolve(enc["CF"]).(Dict)
		method := func(n Name) cryptMethod {
			if n == "Identity" || n == "" {
				return cmNone
			}
			sub, _ := r.resolve(cf[n]).(Dict)
			switch sub.Name("CFM") {
			case "AESV2":
				return cmAES128
			case "AESV3":
				return cmAES256
			case "V2":
				return cmRC4
			}
			return cmNone
		}
		d.strMethod = method(enc.Name("StrF"))
		d.stmMethod = method(enc.Name("StmF"))
		if l, ok := num(r.resolve(cf["StdCF"]).(Dict)["Length"]); ok && l > 0 && v == 4 {
			if l <= 32 {
				length = int(l) * 8
			} else {
				length = int(l)
			}
		}
	}
	if rev >= 5 {
		key, err := aes256Key(rev, enc, r)
		if err != nil {
			return err
		}
		d.key = key
		r.crypt = d
		return nil
	}
	n := length / 8
	if rev == 2 {
		n = 5
	}
	if n < 5 || n > 16 {
		n = 16
	}
	h := md5.New()
	h.Write(padding)
	h.Write(o)
	h.Write([]byte{byte(p), byte(p >> 8), byte(p >> 16), byte(p >> 24)})
	h.Write(id0)
	if rev >= 4 {
		if em, ok := r.resolve(enc["EncryptMetadata"]).(bool); ok && !em {
			h.Write([]byte{0xff, 0xff, 0xff, 0xff})
		}
	}
	key := h.Sum(nil)
	if rev >= 3 {
		for i := 0; i < 50; i++ {
			s := md5.Sum(key[:n])
			key = s[:]
		}
	}
	key = key[:n]
	// verify the empty user password; owner-password-only files decrypt the same way
	if !checkUser(key, rev, u, id0) {
		// still try: many files restrict only printing/copying
	}
	d.key = key
	r.crypt = d
	return nil
}

func checkUser(key []byte, rev int, u, id0 []byte) bool {
	if len(u) < 16 {
		return false
	}
	if rev == 2 {
		c, _ := rc4.NewCipher(key)
		out := make([]byte, 32)
		c.XORKeyStream(out, padding)
		return bytes.Equal(out, u[:32])
	}
	h := md5.New()
	h.Write(padding)
	h.Write(id0)
	x := h.Sum(nil)
	for i := 0; i < 20; i++ {
		k := make([]byte, len(key))
		for j := range key {
			k[j] = key[j] ^ byte(i)
		}
		c, _ := rc4.NewCipher(k)
		c.XORKeyStream(x, x)
	}
	return bytes.Equal(x[:16], u[:16])
}

func aes256Key(rev int, enc Dict, r *Reader) ([]byte, error) {
	u, _ := r.resolve(enc["U"]).(String)
	ue, _ := r.resolve(enc["UE"]).(String)
	if len(u) < 48 || len(ue) < 32 {
		return nil, errors.New("bad AES-256 encryption dictionary")
	}
	pw := []byte{}
	hash := func(data []byte, udata []byte) []byte {
		if rev == 5 {
			s := sha256.Sum256(data)
			return s[:]
		}
		return hash2B(data, pw, udata)
	}
	// validation (not fatal): hash(pw + validation salt) == U[0:32]
	_ = bytes.Equal(hash(append(append([]byte{}, pw...), u[32:40]...), nil), u[:32])
	ik := hash(append(append([]byte{}, pw...), u[40:48]...), nil)
	block, err := aes.NewCipher(ik)
	if err != nil {
		return nil, err
	}
	out := make([]byte, 32)
	cipher.NewCBCDecrypter(block, make([]byte, 16)).CryptBlocks(out, ue[:32])
	return out, nil
}

// hash2B implements algorithm 2.B of ISO 32000-2.
func hash2B(input, pw, udata []byte) []byte {
	s := sha256.Sum256(input)
	k := s[:]
	for i := 0; ; i++ {
		var k1 []byte
		for j := 0; j < 64; j++ {
			k1 = append(k1, pw...)
			k1 = append(k1, k...)
			k1 = append(k1, udata...)
		}
		block, _ := aes.NewCipher(k[:16])
		e := make([]byte, len(k1))
		cipher.NewCBCEncrypter(block, k[16:32]).CryptBlocks(e, k1)
		sum := 0
		for _, b := range e[:16] {
			sum += int(b)
		}
		switch sum % 3 {
		case 0:
			h := sha256.Sum256(e)
			k = h[:]
		case 1:
			h := sha512.Sum384(e)
			k = h[:]
		default:
			h := sha512.Sum512(e)
			k = h[:]
		}
		if i >= 63 && int(e[len(e)-1]) <= i-32 {
			break
		}
	}
	return k[:32]
}

func (d *decrypter) objKey(ref Ref, aesMode bool) []byte {
	if len(d.key) == 32 {
		return d.key
	}
	h := md5.New()
	h.Write(d.key)
	h.Write([]byte{byte(ref.Num), byte(ref.Num >> 8), byte(ref.Num >> 16), byte(ref.Gen), byte(ref.Gen >> 8)})
	if aesMode {
		h.Write([]byte("sAlT"))
	}
	k := h.Sum(nil)
	n := len(d.key) + 5
	if n > 16 {
		n = 16
	}
	return k[:n]
}

func (d *decrypter) decrypt(b []byte, ref Ref, m cryptMethod) []byte {
	switch m {
	case cmRC4:
		c, err := rc4.NewCipher(d.objKey(ref, false))
		if err != nil {
			return b
		}
		out := make([]byte, len(b))
		c.XORKeyStream(out, b)
		return out
	case cmAES128, cmAES256:
		if len(b) < 32 || len(b)%16 != 0 {
			return b
		}
		block, err := aes.NewCipher(d.objKey(ref, true))
		if err != nil {
			return b
		}
		out := make([]byte, len(b)-16)
		cipher.NewCBCDecrypter(block, b[:16]).CryptBlocks(out, b[16:])
		if n := len(out); n > 0 {
			pad := int(out[n-1])
			if pad >= 1 && pad <= 16 && pad <= n {
				out = out[:n-pad]
			}
		}
		return out
	}
	return b
}

func (d *decrypter) decryptObj(o Object, ref Ref) Object {
	switch v := o.(type) {
	case String:
		return String(d.decrypt(v, ref, d.strMethod))
	case Array:
		for i := range v {
			v[i] = d.decryptObj(v[i], ref)
		}
		return v
	case Dict:
		for k, x := range v {
			v[k] = d.decryptObj(x, ref)
		}
		return v
	}
	return o
}
