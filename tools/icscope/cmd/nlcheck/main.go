// nlcheck runs the circuit analysis on OrCAD PST files or a schematic PDF.
package main

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"

	"icscope/internal/analysis"
	"icscope/internal/datasheet"
	"icscope/internal/netlist"
	"icscope/internal/orcad"
	"icscope/internal/pdf"
	"icscope/internal/schematic"
)

func main() {
	var f orcad.Files
	var ds []*datasheet.Datasheet
	var pdfs [][]byte
	var pdfNames []string
	for _, a := range os.Args[1:] {
		b, err := os.ReadFile(a)
		if err != nil {
			panic(err)
		}
		switch orcad.Kind(b) {
		case "net":
			f.Net = b
		case "prt":
			f.Prt = b
		case "chip":
			f.Chip = b
		default:
			if len(os.Getenv("SCH")) > 0 && filepath.Base(a) == os.Getenv("SCH") {
				pdfs = append(pdfs, b)
				pdfNames = append(pdfNames, filepath.Base(a))
				continue
			}
			if d, err := datasheet.Analyze(filepath.Base(a), b); err == nil {
				ds = append(ds, d)
			}
			continue
		}
		f.Names = append(f.Names, filepath.Base(a))
	}
	var nl *netlist.Netlist
	var err error
	if f.Net == nil && len(pdfs) > 0 {
		r, e := pdf.Open(pdfs[0])
		if e != nil {
			panic(e)
		}
		nl, err = schematic.FromPDF(schematic.NewDoc(pdfNames[0], r))
		if os.Getenv("DUMP") != "" {
			json.NewEncoder(os.Stdout).Encode(nl)
			return
		}
	} else {
		nl, err = orcad.Read(f)
	}
	if err != nil {
		fmt.Println(err)
		os.Exit(1)
	}
	rep := analysis.Analyze(nl, ds)
	e := json.NewEncoder(os.Stdout)
	e.SetIndent("", " ")
	e.SetEscapeHTML(false)
	e.Encode(rep)
}
