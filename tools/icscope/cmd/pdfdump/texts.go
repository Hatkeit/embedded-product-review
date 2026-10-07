package main

import (
	"fmt"

	"icscope/internal/pdf"
	"icscope/internal/schematic"
)

func dumpSchTexts(r *pdf.Reader, pg int) {
	for _, s := range schematic.DebugTexts(r.Page(pg).Interpret()) {
		fmt.Println(s)
	}
}

func dumpSchComps(r *pdf.Reader, pg int) {
	for _, s := range schematic.DebugComps(r.Page(pg).Interpret()) {
		fmt.Println(s)
	}
}

func dumpSVG(name string, r *pdf.Reader, pg int) {
	d := schematic.NewDoc(name, r)
	fmt.Print(string(d.SVG(pg)))
}
