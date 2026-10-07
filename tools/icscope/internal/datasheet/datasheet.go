package datasheet

import (
	"math"
	"path/filepath"
	"regexp"
	"sort"
	"strings"

	"icscope/internal/pdf"
)

// Spec is one key specification picked from the tables.
type Spec struct {
	Key   string `json:"key"`
	Label string `json:"label"`
	Min   string `json:"min,omitempty"`
	Typ   string `json:"typ,omitempty"`
	Max   string `json:"max,omitempty"`
	Unit  string `json:"unit,omitempty"`
	Cond  string `json:"cond,omitempty"`
	Param string `json:"param"`
	Page  int    `json:"page"`
	Table string `json:"table,omitempty"`
	// Variants lists the same parameter for other device variants or conditions
	Variants []string `json:"variants,omitempty"`
}

type Pin struct {
	Name string            `json:"name"`
	Num  string            `json:"num"`
	Nums map[string]string `json:"nums,omitempty"`
	Type string            `json:"type,omitempty"`
	Desc string            `json:"desc,omitempty"`
	Page int               `json:"page"`
}

type Datasheet struct {
	File     string   `json:"file"`
	Title    string   `json:"title"`
	Parts    []string `json:"parts"`
	Class    string   `json:"class"`
	ClassKo  string   `json:"classKo"`
	Packages []string `json:"packages"`
	Specs    []Spec   `json:"specs"`
	Rows     []Row    `json:"rows"`
	Pins     []Pin    `json:"pins"`
	Pages    int      `json:"pages"`
	TextLess bool     `json:"textLess"`
	Notes    []string `json:"notes,omitempty"`
}

var classes = []struct {
	key, ko string
	re      *regexp.Regexp
}{
	{"csa", "전류 감지 증폭기", regexp.MustCompile(`(?i)current[- ]sens(e|ing) amplifier|current[- ]shunt monitor|shunt amplifier`)},
	{"isoamp", "절연 증폭기", regexp.MustCompile(`(?i)isolat(ed|ion) (amplifier|modulator)|isolated .*(amplifier|ADC)`)},
	{"comparator", "비교기", regexp.MustCompile(`(?i)\bcomparators?\b`)},
	{"opamp", "연산 증폭기", regexp.MustCompile(`(?i)operational amplifiers?|\bop[- ]?amps?\b`)},
	{"logic", "로직(인버터/슈미트)", regexp.MustCompile(`(?i)\binverters?\b|schmitt[- ]trigger|\bbuffers?/drivers?\b|\bgates?\b.*\blogic\b`)},
	{"gatedriver", "게이트 드라이버", regexp.MustCompile(`(?i)gate[- ]driver|eicedriver`)},
	{"reference", "전압 기준", regexp.MustCompile(`(?i)voltage reference|\breference\b.*SOT`)},
	{"opto", "포토커플러", regexp.MustCompile(`(?i)photocoupler|optocoupler|triac driver|opto[- ]?isolator`)},
	{"controller", "전원 컨트롤러", regexp.MustCompile(`(?i)\bcontroller\b|converter`)},
	{"mosfet", "MOSFET", regexp.MustCompile(`(?i)\bmosfet\b|power[- ]transistor`)},
	{"diode", "다이오드", regexp.MustCompile(`(?i)\bdiode\b`)},
	{"magnetics", "자기부품", regexp.MustCompile(`(?i)transformer|inductor`)},
}

var specDefs = []struct {
	key, label string
	re, not    *regexp.Regexp
}{
	{"vos", "입력 오프셋 전압", regexp.MustCompile(`(?i)offset voltage|^V_?OS\b|^VIO\b`), regexp.MustCompile(`(?i)drift|temperature|coefficient|vs\.|/°C|current`)},
	{"vos_drift", "오프셋 드리프트", regexp.MustCompile(`(?i)offset.*(drift|temperature coefficient)|dVOS/dT|ΔVOS|αVIO`), nil},
	{"ib", "입력 바이어스 전류", regexp.MustCompile(`(?i)input bias current|\bIIB\b|^IB\b`), nil},
	{"ios", "입력 오프셋 전류", regexp.MustCompile(`(?i)input offset current|\bIIO\b|\bIOS\b`), nil},
	{"gbw", "이득 대역폭(GBW)", regexp.MustCompile(`(?i)gain[- ]bandwidth|\bGBW\b|\bGBP\b|unity[- ]gain (bandwidth|frequency)`), nil},
	{"bw", "대역폭(-3 dB)", regexp.MustCompile(`(?i)bandwidth`), regexp.MustCompile(`(?i)gain[- ]bandwidth|unity`)},
	{"sr", "슬루율", regexp.MustCompile(`(?i)slew rate|\bSR\b`), nil},
	{"aol", "개루프 이득", regexp.MustCompile(`(?i)open[- ]loop (voltage )?gain|\bAOL\b`), nil},
	{"gain", "이득", regexp.MustCompile(`(?i)^gain$|^G\b`), nil},
	{"gain_err", "이득 오차", regexp.MustCompile(`(?i)gain error`), regexp.MustCompile(`(?i)drift|temperature`)},
	{"cmrr", "CMRR", regexp.MustCompile(`(?i)common[- ]mode rejection|\bCMRR\b`), nil},
	{"psrr", "PSRR", regexp.MustCompile(`(?i)power[- ]supply rejection|\bPSRR\b|\bkSVR\b`), nil},
	{"vcm", "입력 동상 범위", regexp.MustCompile(`(?i)common[- ]mode (input )?(voltage )?range|input voltage range|\bVICR\b|\bVCM\b`), regexp.MustCompile(`(?i)rejection`)},
	{"en", "전압 잡음 밀도", regexp.MustCompile(`(?i)voltage noise density|input voltage noise|^e[nN]\b`), regexp.MustCompile(`(?i)tracking`)},
	{"swing", "출력 스윙", regexp.MustCompile(`(?i)swing|output voltage (high|low)|\bVOH\b|\bVOL\b`), nil},
	{"isc", "출력 단락 전류", regexp.MustCompile(`(?i)short[- ]circuit current|\bISC\b`), nil},
	{"tpd", "전파 지연", regexp.MustCompile(`(?i)propagation delay|\btPD\b|\btPLH\b|\btPHL\b|\btd\(on\)`), nil},
	{"vhys", "히스테리시스", regexp.MustCompile(`(?i)hysteresis|\bVHYS\b|\bΔVT\b`), regexp.MustCompile(`(?i)thermal|UVLO|lockout|undervoltage`)},
	{"vt", "입력 문턱 전압", regexp.MustCompile(`(?i)positive[- ]going|negative[- ]going|input (high |low )?(voltage )?threshold|logic threshold|^VT[+-]|^VI[HL]\b`), regexp.MustCompile(`(?i)UVLO|lockout|undervoltage|DCDC|overvoltage`)},
	{"iq", "소비 전류", regexp.MustCompile(`(?i)quiescent current|supply current|\bIQ\b|\bIDD\b|\bICC\b`), nil},
	{"vs", "전원 전압 범위", regexp.MustCompile(`(?i)supply voltage|operating (supply )?voltage|power supply|^VDD\b|^VCC\b|^VS$|^V\+`), regexp.MustCompile(`(?i)rejection|current|UVLO|lockout|regulation|undervoltage|threshold|ripple`)},
	{"vout", "출력 전압", regexp.MustCompile(`(?i)output voltage$|initial accuracy|\bVOUT\b`), regexp.MustCompile(`(?i)swing|noise|high|low`)},
}

var rePartTok = regexp.MustCompile(`^[A-Z0-9][A-Z0-9\-./]{3,}[A-Z0-9x]$`)
var rePackage = regexp.MustCompile(`(?i)\b(SOIC|TSSOP|VSSOP|MSOP|SSOP|SOT-?23(-\d)?|SOT-?\d{3}|SC-?70|WSON|VSON|SON|QFN|DFN|X2SON|PDIP|DIP|SO-?\d+|TO-?\d{3}(-\d)?|DSO-?\d+|LQFP|HTSSOP|UQFN|SOD-?\d+|DO-?\d{3}\w*|PG-[A-Z]+-\d+)\b(\s*\(\d+\))?`)

// Analyze reads a datasheet PDF.
func Analyze(name string, b []byte) (*Datasheet, error) {
	r, err := pdf.Open(b)
	if err != nil {
		return nil, err
	}
	ds := &Datasheet{File: name, Pages: r.NumPages()}
	var carry *header
	totalGlyphs := 0
	var firstLines []pdf.Line
	firstText := ""
	pins := []Pin{}
	for i := 0; i < r.NumPages(); i++ {
		c := r.Page(i).Interpret()
		totalGlyphs += len(c.Glyphs)
		words := pdf.Words(c.Glyphs)
		lines := pdf.Lines(words)
		if i == 0 {
			firstLines = lines
		}
		if i < 2 {
			for _, l := range lines {
				firstText += l.Text() + "\n"
			}
		}
		rows, nc := extractTables(i+1, c, lines, words, carry)
		carry = nc
		if len(rows) == 0 {
			carry = nil
		}
		ds.Rows = append(ds.Rows, rows...)
		pins = append(pins, extractPins(i+1, c, lines, words)...)
		for _, l := range lines {
			for _, m := range rePackage.FindAllString(l.Text(), -1) {
				ds.Packages = appendUniq(ds.Packages, strings.ToUpper(strings.TrimSpace(m)))
			}
		}
	}
	ds.Pins = pins
	if totalGlyphs < 50*r.NumPages()/10+20 {
		ds.TextLess = true
		ds.Notes = append(ds.Notes, "텍스트가 거의 없는 PDF입니다(스캔 이미지로 보임). 사양 추출이 불가능합니다.")
	}
	ds.Title, ds.Parts = titleAndParts(firstLines, name)
	ds.Class, ds.ClassKo = classify(ds.Title + "\n" + firstText)
	ds.Specs = pickSpecs(ds.Rows)
	if len(ds.Packages) > 12 {
		ds.Packages = ds.Packages[:12]
	}
	return ds, nil
}

func appendUniq(s []string, v string) []string {
	for _, x := range s {
		if x == v {
			return s
		}
	}
	return append(s, v)
}

func classify(text string) (string, string) {
	best, bestPos := "other", math.MaxInt32
	ko := "기타"
	for _, c := range classes {
		if loc := c.re.FindStringIndex(text); loc != nil && loc[0] < bestPos {
			best, bestPos, ko = c.key, loc[0], c.ko
		}
	}
	return best, ko
}

func titleAndParts(lines []pdf.Line, file string) (string, []string) {
	var parts []string
	// largest text in the upper part of page 1
	type cand struct {
		t    string
		size float64
		y    float64
	}
	var cs []cand
	for _, l := range lines {
		if l.Y0 > 420 {
			continue
		}
		size := 0.0
		for _, w := range l.Words {
			size = math.Max(size, w.Y1-w.Y0)
		}
		cs = append(cs, cand{l.Text(), size, l.Y0})
	}
	sort.SliceStable(cs, func(i, j int) bool { return cs[i].size > cs[j].size })
	title := ""
	for _, c := range cs {
		if len(c.t) > 6 && !strings.Contains(strings.ToLower(c.t), "www.") {
			title = c.t
			break
		}
	}
	for _, c := range cs[:min(len(cs), 6)] {
		for _, w := range strings.Fields(strings.NewReplacer(",", " ", "(", " ", ")", " ").Replace(c.t)) {
			if rePartTok.MatchString(w) && strings.ContainsAny(w, "0123456789") && !strings.Contains(w, "WWW") {
				parts = appendUniq(parts, w)
			}
		}
	}
	base := strings.TrimSuffix(filepath.Base(file), filepath.Ext(file))
	if i := strings.IndexByte(base, '_'); i > 0 {
		base = base[:i]
	}
	if j := strings.IndexByte(base, '-'); j == 8 { // upload prefix "xxxxxxxx-"
		base = base[j+1:]
	}
	if rePartTok.MatchString(strings.ToUpper(base)) {
		parts = appendUniq(parts, strings.ToUpper(base))
	}
	if len(parts) > 6 {
		parts = parts[:6]
	}
	return title, parts
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}

// pickSpecs keeps the first matching row for each key (electrical
// characteristics preferred over ratings).
var (
	reHasDigit = regexp.MustCompile(`\d`)
	reWord2    = regexp.MustCompile(`[A-Za-z]{2,}`)
	reNegNum   = regexp.MustCompile(`^[-–−]\s*\d`)
)

// cleanRow moves condition text that landed in a value column back to Cond.
func cleanRow(r *Row) {
	for _, v := range []*string{&r.Min, &r.Typ, &r.Max} {
		t := strings.TrimSpace(*v)
		if t == "" || t == "–" || t == "-" || t == "—" {
			continue
		}
		if !reHasDigit.MatchString(t) || len(reWord2.FindAllString(t, -1)) >= 3 {
			if r.Cond == "" {
				r.Cond = t
			} else if !strings.Contains(r.Cond, t) {
				r.Cond += "; " + t
			}
			*v = ""
		}
	}
}

func rowHasValue(r *Row) bool {
	for _, v := range []string{r.Min, r.Typ, r.Max} {
		if reHasDigit.MatchString(v) {
			return true
		}
	}
	return false
}

func pickSpecs(rows []Row) []Spec {
	var out []Spec
	for i := range rows {
		cleanRow(&rows[i])
	}
	for _, d := range specDefs {
		var best *Row
		bestScore := -1
		for i := range rows {
			r := &rows[i]
			text := r.Param + " " + r.Symbol
			if !d.re.MatchString(text) && !d.re.MatchString(r.Symbol) {
				continue
			}
			if d.not != nil && d.not.MatchString(r.Param) {
				continue
			}
			if !rowHasValue(r) {
				continue
			}
			score := 1
			t := strings.ToLower(r.Table)
			switch {
			case strings.Contains(t, "electrical") || strings.Contains(t, "characteristics"):
				score = 3
			case strings.Contains(t, "recommended") || strings.Contains(t, "operating"):
				score = 2
			case strings.Contains(t, "absolute") || strings.Contains(t, "maximum ratings"):
				score = 0
			}
			if d.key == "vs" {
				switch {
				case strings.Contains(t, "recommended"):
					score = 4
				case reNegNum.MatchString(strings.TrimSpace(r.Min)) || r.Min == "" && r.Typ == "":
					score = 0 // −0.3 … 7 V style limits are absolute maximum ratings
				}
			}
			if score > bestScore {
				best, bestScore = r, score
			}
		}
		if best != nil {
			var variants []string
			for i := range rows {
				r := &rows[i]
				if r != best && r.Param == best.Param && r.Page == best.Page && r.Cond != "" {
					v := strings.TrimSpace(strings.Join([]string{r.Min, r.Typ, r.Max}, " / "))
					variants = append(variants, r.Cond+": "+v+" "+r.Unit)
				}
			}
			if len(variants) > 6 {
				variants = variants[:6]
			}
			label := d.label
			if t := strings.ToLower(best.Table); strings.Contains(t, "absolute") || strings.Contains(t, "maximum ratings") {
				label += " (절대최대정격)"
			}
			out = append(out, Spec{Variants: variants, Key: d.key, Label: label, Min: best.Min, Typ: best.Typ, Max: best.Max, Unit: best.Unit, Cond: best.Cond, Param: strings.TrimSpace(best.Symbol + " " + best.Param), Page: best.Page, Table: best.Table})
		}
	}
	return out
}
