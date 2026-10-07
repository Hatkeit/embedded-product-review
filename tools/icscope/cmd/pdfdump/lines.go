package main

import (
	"fmt"

	"icscope/internal/pdf"
)

func dumpLines(r *pdf.Reader, pg int) {
	c := r.Page(pg).Interpret()
	for _, l := range pdf.Lines(pdf.Words(c.Glyphs)) {
		fmt.Printf("y%6.1f |", l.Y0)
		for _, w := range l.Words {
			fmt.Printf(" [%.0f]%s", w.X0, w.Text)
		}
		fmt.Println()
	}
}
