package main

import (
	"encoding/json"
	"os"

	"icscope/internal/datasheet"
)

func dumpDatasheet(name string, b []byte) {
	ds, err := datasheet.Analyze(name, b)
	if err != nil {
		panic(err)
	}
	e := json.NewEncoder(os.Stdout)
	e.SetIndent("", " ")
	e.Encode(ds)
}
