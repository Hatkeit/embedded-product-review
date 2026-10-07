// ICScope: a local browser tool that imports op-amp / comparator / inverter
// datasheets and schematics (PDF or OrCAD netlist) and analyses the circuits.
package main

import (
	"embed"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"io/fs"
	"log"
	"net"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"runtime/debug"
	"strconv"
	"strings"
	"sync"
	"time"

	"icscope/internal/analysis"
	"icscope/internal/datasheet"
	"icscope/internal/netlist"
	"icscope/internal/orcad"
	"icscope/internal/pdf"
	"icscope/internal/schematic"
)

//go:embed web
var webFS embed.FS

const version = "0.9"

type dsEntry struct {
	ID int `json:"id"`
	*datasheet.Datasheet
}

type server struct {
	mu   sync.Mutex
	ds   []*dsEntry
	next int
	pst  orcad.Files
	sch  *schematic.Doc
	nl   *netlist.Netlist
	rep  *analysis.Report
	locs map[string][]schematic.Loc
	log  []string
	svg  map[int][]byte
	port int
	quit chan struct{}
}

func (s *server) logf(format string, a ...interface{}) {
	msg := time.Now().Format("15:04:05 ") + fmt.Sprintf(format, a...)
	s.log = append(s.log, msg)
	if len(s.log) > 200 {
		s.log = s.log[len(s.log)-200:]
	}
	log.Println(msg)
}

// guard turns a panic in the PDF code into an error for one file.
func guard(f func() error) (err error) {
	defer func() {
		if r := recover(); r != nil {
			err = fmt.Errorf("내부 오류: %v", r)
			log.Printf("panic: %v\n%s", r, debug.Stack())
		}
	}()
	return f()
}

func (s *server) importFile(name string, b []byte) error {
	if k := orcad.Kind(b); k != "" {
		switch k {
		case "net":
			s.pst.Net = b
		case "prt":
			s.pst.Prt = b
		case "chip":
			s.pst.Chip = b
		}
		s.pst.Names = append(s.pst.Names, name)
		s.logf("OrCAD 넷리스트 파일: %s (%s)", name, k)
		return nil
	}
	if len(b) < 5 || string(b[:5]) != "%PDF-" {
		return errors.New("PDF 또는 OrCAD PST(.dat) 파일이 아닙니다")
	}
	r, err := pdf.Open(b)
	if err != nil {
		return fmt.Errorf("PDF 를 열 수 없습니다: %v", err)
	}
	doc := schematic.NewDoc(name, r)
	isSch := doc.OrCAD
	if !isSch && r.NumPages() <= 40 {
		// many reference designators and few table headers → schematic
		if doc.RefCount() >= 40 && !looksLikeDatasheet(doc) {
			isSch = true
		}
	}
	if isSch {
		s.sch = doc
		s.svg = map[int][]byte{}
		kind := "텍스트 회로도"
		if doc.OrCAD {
			kind = "OrCAD 회로도"
		}
		s.logf("회로도 PDF: %s (%d쪽, %s)", name, r.NumPages(), kind)
		return nil
	}
	ds, err := datasheet.Analyze(name, b)
	if err != nil {
		return err
	}
	for i, e := range s.ds { // same file name replaces the old one
		if e.File == name {
			s.ds = append(s.ds[:i], s.ds[i+1:]...)
			break
		}
	}
	s.next++
	s.ds = append(s.ds, &dsEntry{s.next, ds})
	s.logf("데이터시트: %s → %s (%s), 사양 %d개, 핀 %d개, 표 행 %d개", name, firstNonEmpty(ds.Title, strings.Join(ds.Parts, ",")), ds.ClassKo, len(ds.Specs), len(ds.Pins), len(ds.Rows))
	return nil
}

func looksLikeDatasheet(d *schematic.Doc) bool {
	n := 0
	for i := 0; i < d.R.NumPages() && i < 8; i++ {
		var sb strings.Builder
		for _, gl := range d.Page(i).Glyphs {
			sb.WriteString(gl.Text)
		}
		t := strings.ToUpper(sb.String())
		for _, k := range []string{"ELECTRICALCHARACTERISTICS", "ELECTRICAL CHARACTERISTICS", "ABSOLUTEMAXIMUM", "ABSOLUTE MAXIMUM", "DATASHEET", "DATA SHEET", "ORDERING INFORMATION"} {
			if strings.Contains(t, k) {
				n++
			}
		}
	}
	return n >= 2
}

func firstNonEmpty(a ...string) string {
	for _, s := range a {
		if strings.TrimSpace(s) != "" {
			return s
		}
	}
	return ""
}

// rebuild recomputes the netlist and the circuit analysis.
func (s *server) rebuild() {
	s.nl, s.rep, s.locs = nil, nil, nil
	var dss []*datasheet.Datasheet
	for _, e := range s.ds {
		dss = append(dss, e.Datasheet)
	}
	var err error
	switch {
	case s.pst.Net != nil:
		s.nl, err = orcad.Read(s.pst)
	case s.pst.Prt != nil || s.pst.Chip != nil:
		s.logf("pstxnet.dat 가 아직 없습니다 (pstxprt.dat·pstchip.dat 만으로는 연결을 알 수 없음).")
	}
	if err != nil {
		s.logf("넷리스트 오류: %v", err)
	}
	if s.nl == nil && s.sch != nil {
		err = guard(func() error {
			var e error
			if s.sch.OrCAD {
				s.nl, e = schematic.FromPDF(s.sch)
			}
			if s.nl == nil {
				s.nl = s.sch.TextParts(analysis.ClassOf)
			}
			return e
		})
		if err != nil {
			s.logf("회로도 해석 오류: %v", err)
		}
	}
	if s.nl == nil {
		return
	}
	s.rep = analysis.Analyze(s.nl, dss)
	if s.pst.Net != nil && s.sch != nil {
		s.rep.Notes = append(s.rep.Notes, fmt.Sprintf("분석은 OrCAD 넷리스트 기준이고, '회로도 보기'는 회로도 PDF(%s)에서 같은 참조번호를 찾아 보여줍니다. 두 파일의 리비전이 같은지 확인하세요.", s.sch.Name))
	}
	if s.sch != nil {
		s.locs = map[string][]schematic.Loc{}
		_ = guard(func() error {
			for _, f := range s.rep.Findings {
				if _, ok := s.locs[f.Ref]; !ok {
					s.locs[f.Ref] = s.sch.Locate(f.Ref)
				}
			}
			return nil
		})
	}
	s.logf("회로 분석: 부품 %d개, 넷 %d개, 대상 섹션 %d개", s.rep.Parts, s.rep.Nets, len(s.rep.Findings))
}

func (s *server) state() map[string]interface{} {
	var ds []map[string]interface{}
	for _, e := range s.ds {
		b, _ := json.Marshal(e)
		var m map[string]interface{}
		json.Unmarshal(b, &m)
		delete(m, "rows")
		m["nrows"] = len(e.Rows)
		ds = append(ds, m)
	}
	st := map[string]interface{}{"version": version, "datasheets": ds, "log": s.log}
	if s.sch != nil {
		st["schematic"] = map[string]interface{}{"name": s.sch.Name, "pages": s.sch.R.NumPages(), "orcad": s.sch.OrCAD}
	}
	if len(s.pst.Names) > 0 {
		st["pst"] = map[string]interface{}{"names": s.pst.Names, "net": s.pst.Net != nil, "prt": s.pst.Prt != nil, "chip": s.pst.Chip != nil}
	}
	if s.rep != nil {
		st["report"] = s.rep
		st["locs"] = s.locs
	}
	return st
}

func writeJSON(w http.ResponseWriter, v interface{}) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.Header().Set("Cache-Control", "no-store")
	e := json.NewEncoder(w)
	e.SetEscapeHTML(false)
	e.Encode(v)
}

func (s *server) routes() http.Handler {
	mux := http.NewServeMux()
	sub, _ := fs.Sub(webFS, "web")
	mux.Handle("/", http.FileServer(http.FS(sub)))
	mux.HandleFunc("/api/ping", func(w http.ResponseWriter, r *http.Request) { io.WriteString(w, "icscope") })
	mux.HandleFunc("/api/state", func(w http.ResponseWriter, r *http.Request) {
		s.mu.Lock()
		defer s.mu.Unlock()
		writeJSON(w, s.state())
	})
	mux.HandleFunc("/api/import", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "POST", 405)
			return
		}
		if err := r.ParseMultipartForm(64 << 20); err != nil {
			http.Error(w, err.Error(), 400)
			return
		}
		s.mu.Lock()
		defer s.mu.Unlock()
		var msgs []string
		for _, fh := range r.MultipartForm.File["file"] {
			f, err := fh.Open()
			if err != nil {
				continue
			}
			b, _ := io.ReadAll(io.LimitReader(f, 300<<20))
			f.Close()
			name := filepath.Base(fh.Filename)
			t0 := time.Now()
			err = guard(func() error { return s.importFile(name, b) })
			if err != nil {
				s.logf("%s: %v", name, err)
				msgs = append(msgs, name+": "+err.Error())
			} else {
				msgs = append(msgs, fmt.Sprintf("%s: 완료 (%.1f초)", name, time.Since(t0).Seconds()))
			}
		}
		s.rebuild()
		writeJSON(w, map[string]interface{}{"messages": msgs})
	})
	mux.HandleFunc("/api/rows", func(w http.ResponseWriter, r *http.Request) {
		s.mu.Lock()
		defer s.mu.Unlock()
		id, _ := strconv.Atoi(r.URL.Query().Get("id"))
		for _, e := range s.ds {
			if e.ID == id {
				writeJSON(w, e.Rows)
				return
			}
		}
		writeJSON(w, []int{})
	})
	mux.HandleFunc("/api/netlist", func(w http.ResponseWriter, r *http.Request) {
		s.mu.Lock()
		defer s.mu.Unlock()
		ref := r.URL.Query().Get("ref")
		if s.nl == nil {
			writeJSON(w, nil)
			return
		}
		if ref != "" {
			writeJSON(w, s.nl.Parts[ref])
			return
		}
		writeJSON(w, s.nl)
	})
	mux.HandleFunc("/api/svg", func(w http.ResponseWriter, r *http.Request) {
		s.mu.Lock()
		defer s.mu.Unlock()
		pg, _ := strconv.Atoi(r.URL.Query().Get("page"))
		if s.sch == nil || pg < 0 || pg >= s.sch.R.NumPages() {
			http.NotFound(w, r)
			return
		}
		b, ok := s.svg[pg]
		if !ok {
			guard(func() error { b = s.sch.SVG(pg); return nil })
			s.svg[pg] = b
		}
		w.Header().Set("Content-Type", "image/svg+xml")
		w.Write(b)
	})
	mux.HandleFunc("/api/remove", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "POST", 405)
			return
		}
		s.mu.Lock()
		defer s.mu.Unlock()
		q := r.URL.Query()
		switch q.Get("kind") {
		case "ds":
			id, _ := strconv.Atoi(q.Get("id"))
			for i, e := range s.ds {
				if e.ID == id {
					s.ds = append(s.ds[:i], s.ds[i+1:]...)
					break
				}
			}
		case "sch":
			s.sch = nil
		case "pst":
			s.pst = orcad.Files{}
		case "all":
			s.ds, s.sch, s.pst = nil, nil, orcad.Files{}
		}
		s.rebuild()
		writeJSON(w, map[string]bool{"ok": true})
	})
	mux.HandleFunc("/api/quit", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "POST", 405)
			return
		}
		writeJSON(w, map[string]bool{"ok": true})
		go func() { time.Sleep(300 * time.Millisecond); close(s.quit) }()
	})
	// only answer requests addressed to the loopback host (DNS rebinding guard)
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		h := r.Host
		if i := strings.LastIndexByte(h, ':'); i >= 0 {
			h = h[:i]
		}
		if h != "127.0.0.1" && h != "localhost" {
			http.Error(w, "forbidden", 403)
			return
		}
		mux.ServeHTTP(w, r)
	})
}

func openBrowser(url string) {
	var cmd *exec.Cmd
	switch runtime.GOOS {
	case "windows":
		cmd = exec.Command("rundll32", "url.dll,FileProtocolHandler", url)
	case "darwin":
		cmd = exec.Command("open", url)
	default:
		cmd = exec.Command("xdg-open", url)
	}
	if err := cmd.Start(); err != nil {
		log.Printf("브라우저를 열지 못했습니다. 직접 여세요: %s", url)
	}
}

func main() {
	port := flag.Int("port", 17321, "listen port on 127.0.0.1 (0 = any free port)")
	noBrowser := flag.Bool("no-browser", false, "do not open a browser window")
	flag.Parse()
	log.SetFlags(0)
	fmt.Printf("ICScope %s — Op-amp·비교기·인버터 데이터시트/회로 분석기\n", version)

	addr := fmt.Sprintf("127.0.0.1:%d", *port)
	ln, err := net.Listen("tcp", addr)
	if err != nil && *port != 0 {
		// already running? then just open the page
		c := http.Client{Timeout: time.Second}
		if resp, e := c.Get("http://" + addr + "/api/ping"); e == nil {
			b, _ := io.ReadAll(resp.Body)
			resp.Body.Close()
			if string(b) == "icscope" {
				fmt.Println("이미 실행 중입니다. 브라우저 창을 엽니다.")
				openBrowser("http://" + addr + "/")
				return
			}
		}
		ln, err = net.Listen("tcp", "127.0.0.1:0")
	}
	if err != nil {
		log.Fatal(err)
	}
	s := &server{quit: make(chan struct{}), svg: map[int][]byte{}}
	s.port = ln.Addr().(*net.TCPAddr).Port
	url := fmt.Sprintf("http://127.0.0.1:%d/", s.port)
	for _, a := range flag.Args() { // files given on the command line (drag onto the exe)
		b, err := os.ReadFile(a)
		if err == nil {
			if err := guard(func() error { return s.importFile(filepath.Base(a), b) }); err != nil {
				s.logf("%s: %v", filepath.Base(a), err)
			}
		}
	}
	if len(flag.Args()) > 0 {
		s.rebuild()
	}
	srv := &http.Server{Handler: s.routes(), ReadHeaderTimeout: 10 * time.Second}
	go srv.Serve(ln)
	fmt.Println("주소:", url)
	fmt.Println("이 창을 닫거나 웹 화면의 [종료] 버튼을 누르면 프로그램이 끝납니다.")
	fmt.Println("파일은 이 PC 안에서만 처리되며 인터넷으로 전송되지 않습니다.")
	if !*noBrowser {
		openBrowser(url)
	}
	<-s.quit
	srv.Close()
	fmt.Println("종료합니다.")
}
