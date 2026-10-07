// pdfdump prints interpreted page content as JSON, for cross-checking.
package main

import (
	"encoding/json"
	"fmt"
	"os"
	"strconv"

	"icscope/internal/pdf"
)

func main() {
	b, err := os.ReadFile(os.Args[1])
	if err != nil {
		panic(err)
	}
	if len(os.Args) > 2 && os.Args[2] == "ds" {
		dumpDatasheet(os.Args[1], b)
		return
	}
	r, err := pdf.Open(b)
	if err != nil {
		fmt.Println("ERR", err)
		os.Exit(1)
	}
	pg := 0
	if len(os.Args) > 2 {
		pg, _ = strconv.Atoi(os.Args[2])
	}
	mode := "summary"
	if len(os.Args) > 3 {
		mode = os.Args[3]
	}
	if mode == "svg" {
		dumpSVG(os.Args[1], r, pg)
		return
	}
	if mode == "scomps" {
		dumpSchComps(r, pg)
		return
	}
	if mode == "stexts" {
		dumpSchTexts(r, pg)
		return
	}
	if mode == "lines" {
		dumpLines(r, pg)
		return
	}
	if mode == "summary" {
		fmt.Println("pages", r.NumPages())
		c := r.Page(pg).Interpret()
		txt := ""
		for _, g := range c.Glyphs {
			txt += g.Text
		}
		if len(txt) > 600 {
			txt = txt[:600]
		}
		fmt.Printf("size %.1fx%.1f glyphs %d paths %d\n%s\n", c.Width, c.Height, len(c.Glyphs), len(c.Paths), txt)
		return
	}
	c := r.Page(pg).Interpret()
	type G struct {
		T                 string
		X0, Y0, X1, Y1, S float64
		C                 [3]float64
		N                 string
		Show              int
	}
	type P struct {
		S, F           bool
		SC, FC         [3]float64
		K              string
		X0, Y0, X1, Y1 float64
		Pts            [][]float64
	}
	var gs []G
	for _, g := range c.Glyphs {
		gs = append(gs, G{g.Text, g.X0, g.Y0, g.X1, g.Y1, g.Size, g.Color, g.GlyphName, g.Show})
	}
	var ps []P
	for _, p := range c.Paths {
		k := ""
		var pts [][]float64
		for _, it := range p.Items {
			k += string(it.Kind)
			var q []float64
			for _, x := range it.P {
				q = append(q, x.X, x.Y)
			}
			pts = append(pts, q)
		}
		ps = append(ps, P{p.Stroke, p.Fill, p.SColor, p.FColor, k, p.X0, p.Y0, p.X1, p.Y1, pts})
	}
	json.NewEncoder(os.Stdout).Encode(map[string]interface{}{"glyphs": gs, "paths": ps, "w": c.Width, "h": c.Height})
}
