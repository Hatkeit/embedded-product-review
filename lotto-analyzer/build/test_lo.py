"""Runs the VBA in the built .xlsm under LibreOffice and compares with ref.py.

    python3 test_lo.py [nMax]

Uses synthetic (random) draws - NOT real lottery results - only to check that
import + analysis behave exactly like the Python reference.
"""
import csv
import os
import random
import sys

from openpyxl import Workbook

import build
import ref

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.environ.get("LOTTO_TEST_DIR", os.path.join(HERE, "_test"))
N_MAX = int(sys.argv[1]) if len(sys.argv) > 1 else 20

HOOK = """
Public Function TImport(ByVal p As String) As String
    Dim n As Long
    gSilent = True
    TImport = ImportFromPath(p, n) & "|" & n
End Function

Public Function TAnalyze(ByVal m As Long) As String
    On Error GoTo EH
    gSilent = True
    gMaxN = m
    TAnalyze = AnalyzeCore()
    Exit Function
EH:
    TAnalyze = "ERR " & Err.Number & " " & Err.Description
End Function
"""


def make_draws(n, seed=12345):
    rng = random.Random(seed)
    return [sorted(rng.sample(range(1, 46), 6)) + [0] for _ in range(n)]


def add_bonus(draws, seed=7):
    rng = random.Random(seed)
    for d in draws:
        d[6] = rng.choice([x for x in range(1, 46) if x not in d[:6]])
    return draws


def write_official_like(path, draws):
    """Layout like the official download: 2 header rows, year only on the
    first row of each year (cells shift left), newest round first, numbers as text."""
    wb = Workbook()
    ws = wb.active
    ws.append(["년도", "회차", "추첨일", "1등", None, "2등", None, "3등", None, "4등", None,
               "5등", None, "당첨번호"])
    ws.append([None, None, None, "당첨자수", "당첨금액", "당첨자수", "당첨금액", "당첨자수", "당첨금액",
               "당첨자수", "당첨금액", "당첨자수", "당첨금액", "1", "2", "3", "4", "5", "6", "보너스"])
    rng = random.Random(99)
    prev_year = None
    for rd in range(len(draws), 0, -1):
        d = draws[rd - 1]
        year = 2003 + (rd - 1) // 52
        prize = [rng.randint(1, 20), "2,000,000,000원", rng.randint(30, 90), "50,000,000원",
                 rng.randint(1500, 3000), "1,500,000원", rng.randint(80000, 150000), "50,000원",
                 rng.randint(1000000, 2000000), "5,000원"]
        nums = [str(x) for x in d[:6]] + [str(d[6])]
        row = [str(rd), "%d.01.01" % year] + prize + nums
        if year != prev_year:
            row = [year] + row
            prev_year = year
        ws.append(row)
    wb.save(path)


def write_simple_csv(path, draws):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["round", "n1", "n2", "n3", "n4", "n5", "n6", "bonus"])
        for rd, d in enumerate(draws, 1):
            w.writerow([rd] + d)


def main():
    os.makedirs(WORK, exist_ok=True)
    draws = add_bonus(make_draws(300))
    xin = os.path.join(WORK, "official_like.xlsx")
    write_official_like(xin, draws)

    import uno  # noqa: F401
    proc, desk = build.lo_connect(port=2003)
    ok = True
    try:
        doc = desk.loadComponentFromURL(
            build.file_url(build.XLSM), "_blank", 0,
            (build.prop("Hidden", True), build.prop("MacroExecutionMode", 4)))
        lib = doc.BasicLibraries.getByName("VBAProject")
        from com.sun.star.script import ModuleInfo
        from com.sun.star.script.ModuleType import NORMAL
        mi = ModuleInfo()
        mi.ModuleType = NORMAL
        lib.insertModuleInfo("TestHook", mi)
        lib.insertByName("TestHook", "Option VBASupport 1\n" + HOOK)
        sp = doc.getScriptProvider()

        def call(name, *args):
            s = sp.getScript("vnd.sun.star.script:VBAProject.TestHook.%s?language=Basic&location=document" % name)
            return s.invoke(tuple(args), (), ())[0]

        # ---- import ----
        msg = call("TImport", xin)
        print("import:", msg.replace("\n", " / "))
        data = doc.Sheets.getByName("당첨번호")
        got = [list(r) for r in data.getCellRangeByName("A2:H301").DataArray]
        exp = [[float(i)] + [float(x) for x in d] for i, d in enumerate(draws, 1)]
        if got != exp:
            ok = False
            print("IMPORT MISMATCH", got[:3], exp[:3])
        else:
            print("import OK: 300 rows, rounds 1..300 in order, bonus kept")

        # ---- analysis ----
        msg = call("TAnalyze", N_MAX)
        print("analyze:", msg.replace("\n", " / "))
        res = doc.Sheets.getByName("추천번호")
        rows = res.getCellRangeByName("A5:P14").DataArray
        exp = ref.analyze([d[:6] for d in draws], n_max=N_MAX)
        for (t, total), row in zip(exp, rows):
            vb_nums = [int(x) for x in row[1:7]]
            same = vb_nums == list(t) and abs(row[7] - round(total, 4)) < 1e-9
            ok &= same
            print("  %2d  VBA %s %.4f | PY %s %.4f  %s" % (
                int(row[0]), vb_nums, row[7], list(t), total, "OK" if same else "DIFF"))
        if len(exp) != sum(1 for r in rows if r[0] != ""):
            ok = False
            print("COUNT MISMATCH")
        st = doc.Sheets.getByName("통계")
        cnts = [int(r[1]) for r in st.getCellRangeByName("A5:B49").DataArray]
        exp_c = [sum(d[:6].count(i) for d in draws) for i in range(1, 46)]
        print("stats number counts", "OK" if cnts == exp_c else "DIFF")
        ok &= cnts == exp_c
        # ---- other input layouts: simple table (xlsx) and CSV, oldest first ----
        simple = os.path.join(WORK, "simple.xlsx")
        wb = Workbook()
        ws = wb.active
        ws.append(["회차", "번호1", "번호2", "번호3", "번호4", "번호5", "번호6", "보너스"])
        for rd, d in enumerate(draws, 1):
            ws.append([rd] + d)
        wb.save(simple)
        csvp = os.path.join(WORK, "simple.csv")
        write_simple_csv(csvp, draws)
        exp_rows = [[float(i)] + [float(x) for x in d] for i, d in enumerate(draws, 1)]
        for path in (simple, csvp):
            msg = call("TImport", path)
            got = [list(r) for r in data.getCellRangeByName("A2:H301").DataArray]
            good = got == exp_rows and msg.endswith("|300")
            ok &= good
            print("import %s: %s" % (os.path.basename(path), "OK" if good else "FAIL " + msg))
        doc.close(True)
    finally:
        try:
            desk.terminate()
        except Exception:
            pass
        proc.wait(timeout=30)
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
