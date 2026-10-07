package netlist

import (
	"math"
	"testing"
)

func TestParseValue(t *testing.T) {
	for s, want := range map[string]float64{"4.7k": 4700, "4K7": 4700, "100nF": 100e-9, "20m": 0.02, "1M": 1e6, "51.1KF": 51100, "0F": 0, "2.2uF": 2.2e-6, "10": 10} {
		v, ok := ParseValue(s)
		if !ok || math.Abs(v-want) > want*1e-9+1e-15 {
			t.Errorf("ParseValue(%q) = %g %v, want %g", s, v, ok, want)
		}
	}
}
