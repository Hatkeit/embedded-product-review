from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.comments import Comment

F  = "Arial"
HDR_FILL = PatternFill("solid", fgColor="1F3864")
HDR_FONT = Font(name=F, size=10, bold=True, color="FFFFFF")
SUB_FILL = PatternFill("solid", fgColor="D9E2F3")
IN_FONT  = Font(name=F, size=10, color="0000FF")     # 직접 입력값
FX_FONT  = Font(name=F, size=10, color="000000")     # 수식
LK_FONT  = Font(name=F, size=10, color="008000")     # 타 시트 참조
WARN     = PatternFill("solid", fgColor="FFF2CC")
thin = Side(style="thin", color="B4C6E7")
BOX  = Border(left=thin, right=thin, top=thin, bottom=thin)

wb = Workbook()

# =====================================================================
# 1. Footprints  (마스터)
# =====================================================================
fp = wb.active
fp.title = "Footprints"
fp_cols = [
    ("풋프린트명", 30), ("유형", 8), ("패키지", 20), ("핀수", 7),
    ("피치 (mm)", 11), ("랜드 (mm)", 14), ("드릴 (mm)", 11),
    ("바디 (mm)", 14), ("PLACE_BOUND (mm)", 18), ("페이스트", 22),
    ("벤더 권장랜드", 14), ("사내규칙 이탈", 40), ("DRC", 8),
    ("검증상태", 12), ("빌드 스크립트", 22), ("데이터시트 근거", 34),
]
for i,(h,w) in enumerate(fp_cols, start=1):
    c = fp.cell(row=1, column=i, value=h)
    c.fill, c.font, c.border = HDR_FILL, HDR_FONT, BOX
    c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    fp.column_dimensions[get_column_letter(i)].width = w

fp_rows = [
    ["QFN50P500X500X90-33M", "SMD", "PG-VQFN-32-13", 33, 0.5,
     "0.25 x 0.95 (토 0.25 연장)", None, "5.0 x 5.0 x 0.9max", "±3.10",
     "리드=벤더랜드 0.70 오프셋 / 열패드=3x3 윈도우 69.4%", "있음",
     "규칙2로 토 0.25 연장(벤더 0.70→0.95). 그 외 이탈 없음", None,
     "미검증", "buildqfn32.il", "SLB9670VQ2.0 DS Rev1.5 Fig.4/Fig.6 (p.15)"],
    ["CAPRR750W80D185H420", "THT", "래디얼 φ18x40, F=7.5", 2, 7.5,
     "φ2.0 (핀1 사각)", 1.1, "φ18.5max x 42.0max", "±9.35",
     "없음 (스루홀)", "없음",
     "THT 규정 부재로 드릴·랜드는 IPC-7251 유도. 실크 REFDES y=9.60 (규칙12의 1.35는 바디에 가림)",
     None, "미검증", "buildcaprr750.il", "Rubycon ZLJ DS p.2 치수표(φD=18) / p.3 규격표"],
    ["DIOM2014X90M", "SMD", "SOD-323", 2, None,
     "1.13 x 0.50 (토 0.40 연장)", None, "1.95 x 1.35 x 0.90max", "x ±1.95 / y ±0.775",
     "벤더랜드 0.73 만큼만 오프셋", "있음",
     "규칙2로 토 0.40 연장(벤더 0.73→1.13). 규칙4(리드부품=랜드전체) 이탈 — 페이스트는 벤더량 유지",
     None, "미검증", "builddiom2014.il", "BAS100CS-AU-REV.00S p.4 Dimension / Pad Layout"],
    ["INDM8084X550-8M", "SMD", "Eaton EE5.0 SMT (8핀)", 8, 1.85,
     "소형 1.20 x 1.89 / 탭 3.15 x 3.00", None, "8.00 x 8.38 x 5.50max", "x ±4.60 / y ±4.79",
     "벤더랜드(소형 1.2x1.6, 탭 2.7x3.0)만큼만 오프셋", "있음",
     "규칙2로 토 0.50 연장(소형 1.6→1.89, 탭 2.7→3.15). 규칙4 이탈 — 페이스트는 벤더량 유지. TOP/BOTTOM VIEW 미확정",
     None, "미검증", "buildindm8084.il", "Eaton ELX1187 p.2 Mechanical / Recommended PCB Layout"],
]
for r, row in enumerate(fp_rows, start=2):
    for c, v in enumerate(row, start=1):
        cell = fp.cell(row=r, column=c, value=v)
        cell.font, cell.border = IN_FONT, BOX
        cell.alignment = Alignment(vertical="top", wrap_text=True)
    fp.row_dimensions[r].height = 46

fp["G2"] = "—"; fp["G2"].font = IN_FONT
fp["G4"] = "—"; fp["G4"].font = IN_FONT
fp["G5"] = "—"; fp["G5"].font = IN_FONT
fp["E4"] = "—"; fp["E4"].font = IN_FONT
for rr in (2,3,4,5):
    fp.cell(row=rr, column=13, value="미실행").font = IN_FONT
for rr in (2,3,4,5):
    fp.cell(row=rr, column=13).fill = WARN
    fp.cell(row=rr, column=14).fill = WARN

fp["A7"] = "※ DRC / 검증상태는 axlDRCUpdate(t) 와 extracta 대조를 실제로 돌린 뒤에만 갱신할 것."
fp["A7"].font = Font(name=F, size=9, italic=True, color="C00000")
fp["A8"] = "※ 네 풋프린트 모두 이 세션에서는 빌드하지 못했습니다 (Allegro/extracta 부재). 스크립트만 작성된 상태입니다."
fp["A8"].font = Font(name=F, size=9, italic=True, color="C00000")
fp.freeze_panes = "A2"

fp["L2"].comment = Comment(
    "벤더 권장랜드는 0.25 x 0.70 (내측 span 4.10). 사내규칙 2(리드/바디 끝 바깥 노출동판 >=0.5)를\n"
    "충족시키려 토 방향으로만 0.25 연장 -> 0.25 x 0.95. 힐(2.05)·피치(0.5)·패드간 갭(0.25)은 원문 유지.", "footprint")
fp["G3"].comment = Comment(
    "이 데이터시트에는 권장 랜드패턴이 없습니다.\n"
    "드릴 = 리드경 0.8 + 0.30 = 1.10 (IPC-7251 Level B)\n"
    "랜드 = 드릴 + 0.90 = 2.00 (환형링 0.45/측)\n"
    "사내 THT 규정이 확정되면 이 두 값을 먼저 재검토해야 합니다.", "footprint")

# =====================================================================
# 2. V2000  (보드별 관리 탭)
# =====================================================================
v = wb.create_sheet("V2000")
v["A1"] = "V2000  부품 / 풋프린트 관리"
v["A1"].font = Font(name=F, size=14, bold=True, color="1F3864")
v["A2"] = "보드 리비전"; v["A2"].font = Font(name=F, size=10, bold=True)
v["B2"] = "V2000";       v["B2"].font = IN_FONT
v["D2"] = "등록 부품 수"; v["D2"].font = Font(name=F, size=10, bold=True)
v["E2"] = "=COUNTA(A6:A1000)"; v["E2"].font = FX_FONT
v["G2"] = "검증 완료";    v["G2"].font = Font(name=F, size=10, bold=True)
v["H2"] = '=COUNTIF(L6:L1000,"검증완료")'; v["H2"].font = FX_FONT
v["J2"] = "미검증";       v["J2"].font = Font(name=F, size=10, bold=True)
v["K2"] = "=E2-H2";      v["K2"].font = FX_FONT
for a in ("E2","H2","K2"):
    v[a].fill = SUB_FILL; v[a].border = BOX
    v[a].alignment = Alignment(horizontal="center")

v_cols = [
    ("No.", 6), ("부품번호 (MPN)", 24), ("제조사", 12), ("분류", 22),
    ("값 / 정격", 42), ("패키지", 20), ("풋프린트", 30), ("핀수", 7),
    ("벤더 권장랜드", 14), ("데이터시트", 30), ("빌드 스크립트", 20),
    ("검증상태", 12), ("비고", 40),
]
HR = 5
for i,(h,w) in enumerate(v_cols, start=1):
    c = v.cell(row=HR, column=i, value=h)
    c.fill, c.font, c.border = HDR_FILL, HDR_FONT, BOX
    c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    v.column_dimensions[get_column_letter(i)].width = w

v_rows = [
    ["SLB9670VQ2.0", "Infineon", "TPM 2.0 보안칩",
     "TPM2.0, SPI ≤43MHz, CC EAL4+, 노출패드=GND",
     "PG-VQFN-32-13", "QFN50P500X500X90-33M", None, "있음",
     "SLB9670VQ2.0 DS Rev1.5 (2024-08-07)", "buildqfn32.il", "미검증",
     "핀1=NCI/VDD, 핀2/9/23/32=GND, 노출패드는 GND 외부 연결 필수"],
    ["63ZLJ2700M18X40", "Rubycon", "알루미늄 전해 (래디얼)",
     "2700µF ±20% / 63Vdc / -40~+105°C / 리플 4300mArms / Z 0.015Ω / 10000h",
     "φ18 × 40, F=7.5", "CAPRR750W80D185H420", None, "없음",
     "Rubycon ZLJ series DS", "buildcaprr750.il", "미검증",
     "극성품. 핀1=(+) 사각패드, 핀2=(−). 최대 외형 φ18.5 × 42.0 확보 필요"],
    ["BAS100CS-AU", "Panjit", "쇼트키 다이오드 (SMD)",
     "100V / 0.5A / IFSM 5.5A / Cj 21pF / Tj -55~150°C / AEC-Q101",
     "SOD-323", "DIOM2014X90M", None, "있음",
     "BAS100CS-AU-REV.00S (2017-11-01)", "builddiom2014.il", "미검증",
     "극성품. 핀1=K(띠), 핀2=A — pstchip.dat 로 극성 배정 확인 필요. RθJA 650°C/W"],
    ["ECST1V0805-1100-R", "Eaton", "SMT 전류센스 트랜스포머",
     "100:1 / Lsec 2000µH min @100kHz / DCR sec 5.5Ω max / pri 0.7mΩ / Hi-pot 500Vac / 10A / 50kHz~1MHz / -40~+125°C",
     "EE5.0 SMT 8핀", "INDM8084X550-8M", None, "있음",
     "Eaton ELX1187 (2022-04)", "buildindm8084.il", "미검증",
     "Pri=8(dot)-7(대형탭), Sec=1(dot)-3, 2/4/5/6=NC. 평면도 TOP/BOTTOM 미확정 — 뒤집히면 1↔3, 7↔8 극성 반전. 부품 아래 배선·비아 금지(데이터시트)"],
]
for r, row in enumerate(v_rows, start=HR+1):
    v.cell(row=r, column=1, value=f"=ROW()-{HR}").font = FX_FONT
    for c, val in enumerate(row, start=2):
        cell = v.cell(row=r, column=c, value=val)
        cell.font, cell.border = IN_FONT, BOX
        cell.alignment = Alignment(vertical="top", wrap_text=True)
    # 핀수는 Footprints 탭에서 조회
    pin = v.cell(row=r, column=8,
        value=f'=IFERROR(INDEX(Footprints!$D$2:$D$1000,MATCH($G{r},Footprints!$A$2:$A$1000,0)),"")')
    pin.font, pin.border = LK_FONT, BOX
    pin.alignment = Alignment(horizontal="center", vertical="top")
    v.cell(row=r, column=1).border = BOX
    v.row_dimensions[r].height = 42

ex = HR + len(v_rows) + 2
v.cell(row=ex, column=2, value="예시)  GRM188R71C104KA01D").font = Font(name=F, size=9, italic=True, color="808080")
v.cell(row=ex, column=3, value="Murata").font = Font(name=F, size=9, italic=True, color="808080")
v.cell(row=ex, column=4, value="MLCC").font = Font(name=F, size=9, italic=True, color="808080")
v.cell(row=ex, column=5, value="100nF ±10% / 16V / X7R").font = Font(name=F, size=9, italic=True, color="808080")
v.cell(row=ex, column=6, value="0603").font = Font(name=F, size=9, italic=True, color="808080")
v.cell(row=ex, column=7, value="CAPC1608X90N").font = Font(name=F, size=9, italic=True, color="808080")
v.cell(row=ex, column=13, value="입력 형식 예시 행 (집계에서 제외됨). 실제 등록은 6행부터, 이 행은 지워도 됩니다. 검증상태 칸에는 미검증/빌드완료/검증완료 중 하나를 적습니다.").font = Font(name=F, size=9, italic=True, color="808080")

v.freeze_panes = "A6"
v.auto_filter.ref = f"A{HR}:M{HR+len(v_rows)}"

# =====================================================================
# 3. Legend
# =====================================================================
lg = wb.create_sheet("Legend")
lg.column_dimensions["A"].width = 26
lg.column_dimensions["B"].width = 96
lg["A1"] = "표기 규칙 / 사용법"; lg["A1"].font = Font(name=F, size=14, bold=True, color="1F3864")
items = [
    ("파란 글씨", "직접 입력하는 값. 여기만 고치면 됩니다."),
    ("검은 글씨", "수식. 건드리지 마세요."),
    ("초록 글씨", "다른 시트 참조 (V2000!핀수 는 Footprints 탭에서 자동 조회)."),
    ("노란 배경", "실제 검증을 돌린 뒤 채워야 하는 칸 (DRC / 검증상태)."),
    ("", ""),
    ("탭 구성", "Footprints = 풋프린트 마스터(부품과 무관하게 1행 1풋프린트)"),
    ("", "V2000 = 보드 리비전별 부품 목록. 보드가 늘어나면 이 탭을 복제해서 쓰세요."),
    ("", ""),
    ("검증상태 값", "미검증 / 빌드완료 / 검증완료  — 아래 5개를 전부 통과해야 '검증완료'"),
    ("  1", "extracta COMPOSITE_PAD: 핀번호·좌표·패드크기가 expected.txt 와 일치"),
    ("  2", "extracta GEOMETRY: 레이어별 레코드 수 / 실크·어셈블리 좌표"),
    ("  3", "axlDRCUpdate(t) == 0  (심볼에 저장된 값이 아니라 강제 실행값)"),
    ("  4", "핀 수 == pstchip.dat 디바이스 핀 수"),
    ("  5", "토 노출 동판 >= 0.5"),
    ("", ""),
    ("주의", "이 파일은 기존 관리 대장이 없어 새로 만든 것입니다."),
    ("", "기존 엑셀이 있으면 그 쪽 열 구성에 맞춰 옮겨야 합니다 — 원본을 올려 주세요."),
]
for i,(a,b) in enumerate(items, start=3):
    lg.cell(row=i, column=1, value=a).font = Font(name=F, size=10, bold=bool(a and not a.startswith("  ")))
    lg.cell(row=i, column=2, value=b).font = Font(name=F, size=10)
lg["A18"].font = Font(name=F, size=10, bold=True, color="C00000")
lg["B18"].font = Font(name=F, size=10, color="C00000")
lg["B19"].font = Font(name=F, size=10, color="C00000")

for ws in wb.worksheets:
    for row in ws.iter_rows():
        for cell in row:
            if cell.font and cell.font.name != F:
                cell.font = Font(name=F, size=cell.font.size or 10, bold=cell.font.bold,
                                 italic=cell.font.italic, color=cell.font.color)

out = "/home/user/embedded-product-review/footprints/parts_registry.xlsx"
wb.save(out)
print("saved", out)
