package pdf

import "math"

// Matrix is a PDF transformation [a b c d e f]: x' = a x + c y + e, y' = b x + d y + f.
type Matrix [6]float64

var Identity = Matrix{1, 0, 0, 1, 0, 0}

// Mul returns m then n (apply m first).
func (m Matrix) Mul(n Matrix) Matrix {
	return Matrix{
		m[0]*n[0] + m[1]*n[2],
		m[0]*n[1] + m[1]*n[3],
		m[2]*n[0] + m[3]*n[2],
		m[2]*n[1] + m[3]*n[3],
		m[4]*n[0] + m[5]*n[2] + n[4],
		m[4]*n[1] + m[5]*n[3] + n[5],
	}
}

func (m Matrix) Apply(x, y float64) (float64, float64) {
	return m[0]*x + m[2]*y + m[4], m[1]*x + m[3]*y + m[5]
}

// Scale is the mean linear scale factor of the matrix.
func (m Matrix) Scale() float64 {
	return math.Sqrt(math.Abs(m[0]*m[3] - m[1]*m[2]))
}

func matrixFrom(a Array) Matrix {
	if len(a) != 6 {
		return Identity
	}
	var m Matrix
	for i := range a {
		m[i] = numOr(a[i], 0)
	}
	return m
}
