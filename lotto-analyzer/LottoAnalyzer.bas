Attribute VB_Name = "LottoAnalyzer"
Option Explicit

'==============================================================================
' Lotto 6/45 pattern analyzer
'
' Fixed rules (same data + same settings => always the same result):
'  1) Past 1st-prize numbers are read from the data sheet.
'  2) For every past draw these features are counted:
'       sum, odd count, low (1-22) count, consecutive pairs, distinct last
'       digits, max numbers in one section (1-9/10-19/20-29/30-39/40-45),
'       overlap with the previous draw, AC value, and how often each number
'       appeared (all draws / recent draws).
'  3) Each of the 8,145,060 combinations gets
'       score = sum of weight * ln(historical probability of its feature value)
'     i.e. how closely it resembles past 1st-prize combinations.
'     Stage 1 scores every combination without AC and keeps the best 20,000.
'     Stage 2 adds the AC score to those and re-ranks them.
'  4) The top combinations are listed, limited so that the chosen sets do not
'     share too many numbers with each other.
'
' NOTE: Draws are independent random events. Every combination still has a
'       winning probability of exactly 1 / 8,145,060. The score shows only
'       similarity to past patterns, not a higher chance to win.
'
' Korean text is stored as \uXXXX escapes and decoded by U() so that the code
' survives any VBA code page.
'==============================================================================

Private Const HEAP_SIZE As Long = 20000
Private Const SUM_WIN As Long = 7
Private Const LOW_MAX As Long = 22
Private Const MIN_DRAWS As Long = 30
Private Const SUM_TOP As Long = 300

' cells on the settings sheet
Private Const C_FOLDER As String = "C4"
Private Const C_LASTFILE As String = "C5"
Private Const C_COUNT As String = "C7"
Private Const C_OVERLAP As String = "C8"
Private Const C_RECENT As String = "C9"
Private Const C_EXCLUDE As String = "C10"
Private Const W_ROW0 As Long = 13      ' weights are in C13:C22
Private Const W_COUNT As Long = 10

Public gMaxN As Long        ' 0 = 45 (a smaller value is only for testing)
Public gSilent As Boolean   ' True = no message boxes (testing)

' heap of the best stage-1 combinations (min-heap on score)
Private hS() As Double
Private hC() As Double
Private hN As Long

'------------------------------------------------------------------------------
' sheet names
'------------------------------------------------------------------------------
Private Function SH_SET() As String
    SH_SET = U("\uC124\uC815")
End Function

Private Function SH_DATA() As String
    SH_DATA = U("\uB2F9\uCCA8\uBC88\uD638")
End Function

Private Function SH_STAT() As String
    SH_STAT = U("\uD1B5\uACC4")
End Function

Private Function SH_RES() As String
    SH_RES = U("\uCD94\uCC9C\uBC88\uD638")
End Function

Private Function SetWs() As Worksheet
    Set SetWs = ThisWorkbook.Worksheets(SH_SET())
End Function

'==============================================================================
' Buttons (called from Workbook_Open)
'==============================================================================
Public Sub EnsureButtons()
    Dim ws As Worksheet
    On Error Resume Next
    Set ws = SetWs()
    If ws Is Nothing Then Exit Sub
    AddButton ws, "btnImport", "F4", U("\u2460 \uB2F9\uCCA8\uBC88\uD638 \uC5D1\uC140 \uBD88\uB7EC\uC624\uAE30"), "ImportLottoFile"
    AddButton ws, "btnRun", "F7", U("\u2461 \uCD94\uCC9C\uBC88\uD638 \uACC4\uC0B0"), "RunAnalysis"
End Sub

Private Sub AddButton(ws As Worksheet, nm As String, addr As String, cap As String, act As String)
    Dim b As Object
    On Error Resume Next
    Set b = ws.Buttons(nm)
    On Error GoTo 0
    If Not b Is Nothing Then Exit Sub
    Set b = ws.Buttons.Add(ws.Range(addr).Left, ws.Range(addr).Top, 210, 32)
    b.Name = nm
    b.Caption = cap
    b.OnAction = act
End Sub

'==============================================================================
' 1) Import past winning numbers from another Excel / CSV file
'==============================================================================
Public Sub ImportLottoFile()
    Dim f As Variant, folder As String, msg As String, n As Long

    folder = Trim$(CStr(SetWs().Range(C_FOLDER).Value))
    If Len(folder) > 0 Then
        On Error Resume Next
        If Len(Dir(folder, vbDirectory)) > 0 Then
            ChDrive Left$(folder, 1)
            ChDir folder
        End If
        On Error GoTo 0
    End If

    f = Application.GetOpenFilename( _
        "Excel/CSV (*.xls;*.xlsx;*.xlsm;*.xlsb;*.csv),*.xls;*.xlsx;*.xlsm;*.xlsb;*.csv", , _
        U("\uB85C\uB610 \uB2F9\uCCA8\uBC88\uD638 \uC5D1\uC140 \uD30C\uC77C \uC120\uD0DD"))
    If VarType(f) = vbBoolean Then Exit Sub

    msg = ImportFromPath(CStr(f), n)
    Say msg
End Sub

Public Function ImportFromPath(ByVal path As String, ByRef nOut As Long) As String
    Dim wb As Workbook, ws As Worksheet, v As Variant
    Dim cnt As Long, rds() As Long, n6() As Long, bon() As Long
    Dim allRound As Boolean, oldAlerts As Boolean

    nOut = 0
    If StrComp(path, ThisWorkbook.FullName, vbTextCompare) = 0 Then
        ImportFromPath = U("\uC774 \uBD84\uC11D \uD30C\uC77C \uC790\uCCB4\uB294 \uBD88\uB7EC\uC62C \uC218 \uC5C6\uC2B5\uB2C8\uB2E4. \uB2F9\uCCA8\uBC88\uD638\uAC00 \uB4E4\uC5B4\uC788\uB294 \uB2E4\uB978 \uD30C\uC77C\uC744 \uC120\uD0DD\uD558\uC138\uC694.")
        Exit Function
    End If

    ReDim rds(1 To 64)
    ReDim n6(1 To 64 * 6)
    ReDim bon(1 To 64)
    allRound = True

    oldAlerts = Application.DisplayAlerts
    Application.ScreenUpdating = False
    Application.DisplayAlerts = False
    On Error GoTo Fail
    Set wb = Workbooks.Open(Filename:=path, UpdateLinks:=0, ReadOnly:=True)
    For Each ws In wb.Worksheets
        v = ws.UsedRange.Value
        If IsArray(v) Then ParseBlock v, rds, n6, bon, cnt, allRound
    Next ws
    wb.Close SaveChanges:=False
    Set wb = Nothing
    On Error GoTo 0
    Application.DisplayAlerts = oldAlerts
    Application.ScreenUpdating = True

    If cnt = 0 Then
        ImportFromPath = U("\uB2F9\uCCA8\uBC88\uD638\uB97C \uCC3E\uC9C0 \uBABB\uD588\uC2B5\uB2C8\uB2E4.") & vbLf & _
            U("\uD55C \uD589\uC5D0 1~45 \uC0AC\uC774\uC758 \uBC88\uD638 6\uAC1C\uAC00 \uC5F0\uC18D\uB41C \uCE78\uC5D0 \uC788\uC5B4\uC57C \uD569\uB2C8\uB2E4. (\uC608: \uD68C\uCC28 | \uBC88\uD6381~6 | \uBCF4\uB108\uC2A4)")
        Exit Function
    End If

    ImportFromPath = StoreDraws(cnt, rds, n6, bon, allRound, nOut)
    SetWs().Range(C_LASTFILE).Value = path & "  (" & Format$(Now, "yyyy-mm-dd hh:nn") & ")"
    Exit Function

Fail:
    Dim emsg As String
    emsg = Err.Description
    On Error Resume Next
    If Not wb Is Nothing Then wb.Close SaveChanges:=False
    Application.DisplayAlerts = oldAlerts
    Application.ScreenUpdating = True
    ImportFromPath = U("\uD30C\uC77C\uC744 \uC5EC\uB294 \uC911 \uC624\uB958\uAC00 \uBC1C\uC0DD\uD588\uC2B5\uB2C8\uB2E4: ") & emsg
End Function

' Parse one sheet (2-D array) and append every row that holds a draw.
Private Sub ParseBlock(v As Variant, rds() As Long, n6() As Long, bon() As Long, _
                       cnt As Long, allRound As Boolean)
    Dim r As Long, c As Long, r0 As Long, c0 As Long, nr As Long, nc As Long
    Dim hasRound As Boolean, s As String, k As Long
    Dim rd As Long, six(1 To 6) As Long, bonus As Long

    r0 = LBound(v, 1): c0 = LBound(v, 2)
    nr = UBound(v, 1) - r0 + 1
    nc = UBound(v, 2) - c0 + 1
    If nc < 6 Then Exit Sub

    ' a header such as "\uD68C\uCC28" means every data row starts with a round number
    For r = 1 To IIf(nr < 10, nr, 10)
        For c = 1 To nc
            If VarType(v(r0 + r - 1, c0 + c - 1)) = vbString Then
                s = LCase$(CStr(v(r0 + r - 1, c0 + c - 1)))
                If InStr(s, U("\uD68C\uCC28")) > 0 Or InStr(s, "round") > 0 Or InStr(s, "drw") > 0 Then hasRound = True
            End If
        Next c
    Next r

    For r = 1 To nr
        If ParseRow(v, r0 + r - 1, c0, nc, hasRound, rd, six, bonus) Then
            cnt = cnt + 1
            If cnt > UBound(rds) Then
                ReDim Preserve rds(1 To cnt * 2)
                ReDim Preserve n6(1 To cnt * 2 * 6)
                ReDim Preserve bon(1 To cnt * 2)
            End If
            rds(cnt) = rd
            For k = 1 To 6
                n6((cnt - 1) * 6 + k) = six(k)
            Next k
            bon(cnt) = bonus
            If rd = 0 Then allRound = False
        End If
    Next r
End Sub

' One row -> round (0 if none), six sorted numbers and bonus (0 if none).
Private Function ParseRow(v As Variant, ByVal r As Long, ByVal c0 As Long, ByVal nc As Long, _
                          ByVal hasRound As Boolean, ByRef rd As Long, six() As Long, _
                          ByRef bonus As Long) As Boolean
    Dim c As Long, k As Long, x As Long, startC As Long, ok As Boolean, isYear As Boolean

    ParseRow = False
    rd = 0: bonus = 0: startC = 1

    If hasRound Then
        For c = 1 To nc
            If IsWhole(v(r, c0 + c - 1), 1, 5000, x) Then
                ' "year | round | ..." layout (official download): skip the year
                isYear = False
                If x >= 2002 And x <= 2100 And c < nc Then
                    isYear = IsWhole(v(r, c0 + c), 1, 5000, k)
                End If
                If Not isYear Then
                    rd = x
                    startC = c + 1
                    Exit For
                End If
            End If
        Next c
        If rd = 0 Then Exit Function
    End If

    For c = startC To nc - 5
        ok = True
        For k = 1 To 6
            If IsWhole(v(r, c0 + c + k - 2), 1, 45, x) Then
                six(k) = x
            Else
                ok = False
                Exit For
            End If
        Next k
        If ok Then
            SortSix six
            For k = 2 To 6
                If six(k) = six(k - 1) Then ok = False
            Next k
        End If
        If ok Then
            If c + 6 <= nc Then
                If IsWhole(v(r, c0 + c + 5), 1, 45, x) Then
                    bonus = x
                    For k = 1 To 6
                        If six(k) = x Then bonus = 0
                    Next k
                End If
            End If
            ParseRow = True
            Exit Function
        End If
    Next c
End Function

' Sort by round, drop duplicates, write the data sheet.
Private Function StoreDraws(ByVal cnt As Long, rds() As Long, n6() As Long, bon() As Long, _
                            ByVal allRound As Boolean, ByRef nOut As Long) As String
    Dim i As Long, k As Long, m As Long, maxR As Long, minR As Long
    Dim idx() As Long, outv() As Variant, ws As Worksheet

    If allRound Then
        maxR = 0: minR = 2147483647
        For i = 1 To cnt
            If rds(i) > maxR Then maxR = rds(i)
            If rds(i) < minR Then minR = rds(i)
        Next i
        ReDim idx(1 To maxR)
        For i = 1 To cnt
            idx(rds(i)) = i              ' a later row with the same round wins
        Next i
        m = 0
        For i = 1 To maxR
            If idx(i) > 0 Then m = m + 1
        Next i
        ReDim outv(1 To m, 1 To 8)
        m = 0
        For i = 1 To maxR
            If idx(i) > 0 Then
                m = m + 1
                outv(m, 1) = i
                For k = 1 To 6
                    outv(m, k + 1) = n6((idx(i) - 1) * 6 + k)
                Next k
                If bon(idx(i)) > 0 Then outv(m, 8) = bon(idx(i))
            End If
        Next i
    Else
        ' no round numbers: keep the file order (oldest first is assumed)
        m = cnt
        ReDim outv(1 To m, 1 To 8)
        For i = 1 To m
            outv(i, 1) = i
            For k = 1 To 6
                outv(i, k + 1) = n6((i - 1) * 6 + k)
            Next k
            If bon(i) > 0 Then outv(i, 8) = bon(i)
        Next i
    End If

    Set ws = ThisWorkbook.Worksheets(SH_DATA())
    ws.Range("A2:H" & ws.Rows.Count).ClearContents
    ws.Range("A2").Resize(m, 8).Value = outv
    nOut = m

    If allRound Then
        StoreDraws = U("\uBD88\uB7EC\uC624\uAE30 \uC644\uB8CC: ") & m & U("\uD68C (") & minR & U("\uD68C ~ ") & maxR & U("\uD68C)")
        If maxR - minR + 1 > m Then
            StoreDraws = StoreDraws & vbLf & U("\u203B \uBE60\uC9C4 \uD68C\uCC28\uAC00 ") & (maxR - minR + 1 - m) & U("\uAC1C \uC788\uC2B5\uB2C8\uB2E4.")
        End If
    Else
        StoreDraws = U("\uBD88\uB7EC\uC624\uAE30 \uC644\uB8CC: ") & m & U("\uD68C") & vbLf & _
            U("\u203B \uD68C\uCC28 \uC5F4\uC744 \uCC3E\uC9C0 \uBABB\uD574 \uD30C\uC77C \uC21C\uC11C(\uC704=\uC624\uB798\uB41C \uD68C\uCC28)\uB300\uB85C \uC800\uC7A5\uD588\uC2B5\uB2C8\uB2E4.")
    End If
    StoreDraws = StoreDraws & vbLf & vbLf & U("\uC774\uC81C [\u2461 \uCD94\uCC9C\uBC88\uD638 \uACC4\uC0B0] \uBC84\uD2BC\uC744 \uB204\uB974\uC138\uC694.")
End Function

'==============================================================================
' 2) Analysis
'==============================================================================
Public Sub RunAnalysis()
    Dim msg As String, t0 As Double
    t0 = Timer
    msg = AnalyzeCore()
    ShowStatus False
    Say msg & vbLf & "(" & Format$(Timer - t0, "0.0") & "s)"
End Sub

Public Function AnalyzeCore() As String
    Dim nDraw As Long, rno() As Long, dr() As Long
    Dim nPick As Long, maxOv As Long, nRecent As Long, excl As Boolean
    Dim w(1 To W_COUNT) As Double
    Dim i As Long, k As Long, s As Long, j As Long, cw As Long
    Dim t(1 To 6) As Long, fv(1 To 7) As Long

    nDraw = LoadDraws(rno, dr)
    If nDraw < MIN_DRAWS Then
        AnalyzeCore = U("\uB2F9\uCCA8\uBC88\uD638\uAC00 ") & nDraw & U("\uD68C\uBFD0\uC785\uB2C8\uB2E4. \uCD5C\uC18C ") & MIN_DRAWS & U("\uD68C \uC774\uC0C1 \uD544\uC694\uD569\uB2C8\uB2E4.") & vbLf & _
            U("[\u2460 \uB2F9\uCCA8\uBC88\uD638 \uC5D1\uC140 \uBD88\uB7EC\uC624\uAE30]\uB85C \uBA3C\uC800 \uB370\uC774\uD130\uB97C \uB123\uC5B4\uC8FC\uC138\uC694.")
        Exit Function
    End If

    ' ---- settings ----
    With SetWs()
        nPick = GetLong(.Range(C_COUNT).Value, 1, 100, 10)
        maxOv = GetLong(.Range(C_OVERLAP).Value, 0, 5, 3)
        nRecent = GetLong(.Range(C_RECENT).Value, 1, 100000, 50)
        excl = (UCase$(Trim$(CStr(.Range(C_EXCLUDE).Value))) <> "N")
        For i = 1 To W_COUNT
            w(i) = GetDbl(.Cells(W_ROW0 + i - 1, 3).Value, 1#)
        Next i
    End With
    If nRecent > nDraw Then nRecent = nDraw

    Dim nMax As Long
    nMax = 45
    If gMaxN >= 6 And gMaxN < 45 Then nMax = gMaxN

    ' ---- count history ----
    Dim cNum(1 To 45) As Long, cRec(1 To 45) As Long
    Dim cSum(0 To SUM_TOP) As Long, cOdd(0 To 6) As Long, cLow(0 To 6) As Long
    Dim cCon(0 To 5) As Long, cDig(0 To 6) As Long, cSec(0 To 6) As Long
    Dim cPrv(0 To 6) As Long, cAC(0 To 10) As Long

    For i = 1 To nDraw
        For k = 1 To 6
            t(k) = dr(i, k)
            cNum(t(k)) = cNum(t(k)) + 1
            If i > nDraw - nRecent Then cRec(t(k)) = cRec(t(k)) + 1
        Next k
        FeatureSet t, fv
        cSum(fv(1)) = cSum(fv(1)) + 1
        cOdd(fv(2)) = cOdd(fv(2)) + 1
        cLow(fv(3)) = cLow(fv(3)) + 1
        cCon(fv(4)) = cCon(fv(4)) + 1
        cDig(fv(5)) = cDig(fv(5)) + 1
        cSec(fv(6)) = cSec(fv(6)) + 1
        cAC(fv(7)) = cAC(fv(7)) + 1
        If i > 1 Then
            j = OverlapDraws(dr, i, i - 1)
            cPrv(j) = cPrv(j) + 1
        End If
    Next i

    ' ---- score tables: weight * ln(probability) ----
    Dim tNum(1 To 45) As Double, tSum(0 To SUM_TOP) As Double
    Dim tOdd(0 To 6) As Double, tLow(0 To 6) As Double, tCon(0 To 5) As Double
    Dim tDig(0 To 6) As Double, tSec(0 To 6) As Double, tPrv(0 To 6) As Double
    Dim tAC(0 To 10) As Double

    For i = 1 To 45
        tNum(i) = w(1) * Log((cNum(i) + 1) / (6# * nDraw + 45#) * 45#) + _
                  w(2) * Log((cRec(i) + 1) / (6# * nRecent + 45#) * 45#)
    Next i
    For s = 0 To SUM_TOP
        cw = 0
        For j = s - SUM_WIN To s + SUM_WIN
            If j >= 0 And j <= SUM_TOP Then cw = cw + cSum(j)
        Next j
        tSum(s) = w(3) * Log((cw + 1) / ((2 * SUM_WIN + 1) * CDbl(nDraw) + 235#))
    Next s
    For i = 0 To 6
        tOdd(i) = w(4) * Log((cOdd(i) + 1) / (nDraw + 7#))
        tLow(i) = w(5) * Log((cLow(i) + 1) / (nDraw + 7#))
        tPrv(i) = w(9) * Log((cPrv(i) + 1) / (nDraw - 1 + 7#))
    Next i
    For i = 0 To 5
        tCon(i) = w(6) * Log((cCon(i) + 1) / (nDraw + 6#))
    Next i
    For i = 1 To 6
        tDig(i) = w(7) * Log((cDig(i) + 1) / (nDraw + 6#))
        tSec(i) = w(8) * Log((cSec(i) + 1) / (nDraw + 6#))
    Next i
    For i = 0 To 10
        tAC(i) = w(10) * Log((cAC(i) + 1) / (nDraw + 11#))
    Next i

    ' ---- per-number lookups ----
    Dim nOdd(1 To 45) As Long, nLow(1 To 45) As Long, nBit(1 To 45) As Long
    Dim nSecI(1 To 45) As Long, nPrv(1 To 45) As Long, pc(0 To 1023) As Long
    For i = 1 To 45
        nOdd(i) = i Mod 2
        If i <= LOW_MAX Then nLow(i) = 1
        nBit(i) = 2 ^ (i Mod 10)
        nSecI(i) = i \ 10
    Next i
    For k = 1 To 6
        nPrv(dr(nDraw, k)) = 1
    Next k
    For i = 0 To 1023
        cw = 0: j = i
        Do While j > 0
            cw = cw + (j And 1)
            j = j \ 2
        Loop
        pc(i) = cw
    Next i

    ' ---- stage 1: score every combination ----
    Dim a As Long, b As Long, c As Long, d As Long, e As Long, f As Long
    Dim s1 As Long, s2 As Long, s3 As Long, s4 As Long, s5 As Long
    Dim o1 As Long, o2 As Long, o3 As Long, o4 As Long, o5 As Long
    Dim l1 As Long, l2 As Long, l3 As Long, l4 As Long, l5 As Long
    Dim q2 As Long, q3 As Long, q4 As Long, q5 As Long, qq As Long
    Dim m1 As Long, m2 As Long, m3 As Long, m4 As Long, m5 As Long
    Dim p1 As Long, p2 As Long, p3 As Long, p4 As Long, p5 As Long
    Dim x1 As Long, x2 As Long, x3 As Long, x4 As Long, x5 As Long, xx As Long
    Dim z1 As Double, z2 As Double, z3 As Double, z4 As Double, z5 As Double
    Dim sc As Double, cd As Double
    Dim secCnt(0 To 4) As Long

    ReDim hS(1 To HEAP_SIZE)
    ReDim hC(1 To HEAP_SIZE)
    hN = 0

    For a = 1 To nMax - 5
        ShowStatus "1/2 " & Format$(a / (nMax - 5), "0%")
        s1 = a: o1 = nOdd(a): l1 = nLow(a): m1 = nBit(a): p1 = nPrv(a): z1 = tNum(a)
        secCnt(nSecI(a)) = secCnt(nSecI(a)) + 1: x1 = 1
        For b = a + 1 To nMax - 4
            s2 = s1 + b: o2 = o1 + nOdd(b): l2 = l1 + nLow(b): m2 = m1 Or nBit(b)
            p2 = p1 + nPrv(b): z2 = z1 + tNum(b)
            q2 = 0: If b = a + 1 Then q2 = 1
            secCnt(nSecI(b)) = secCnt(nSecI(b)) + 1
            x2 = x1: If secCnt(nSecI(b)) > x2 Then x2 = secCnt(nSecI(b))
            For c = b + 1 To nMax - 3
                s3 = s2 + c: o3 = o2 + nOdd(c): l3 = l2 + nLow(c): m3 = m2 Or nBit(c)
                p3 = p2 + nPrv(c): z3 = z2 + tNum(c)
                q3 = q2: If c = b + 1 Then q3 = q3 + 1
                secCnt(nSecI(c)) = secCnt(nSecI(c)) + 1
                x3 = x2: If secCnt(nSecI(c)) > x3 Then x3 = secCnt(nSecI(c))
                For d = c + 1 To nMax - 2
                    s4 = s3 + d: o4 = o3 + nOdd(d): l4 = l3 + nLow(d): m4 = m3 Or nBit(d)
                    p4 = p3 + nPrv(d): z4 = z3 + tNum(d)
                    q4 = q3: If d = c + 1 Then q4 = q4 + 1
                    secCnt(nSecI(d)) = secCnt(nSecI(d)) + 1
                    x4 = x3: If secCnt(nSecI(d)) > x4 Then x4 = secCnt(nSecI(d))
                    For e = d + 1 To nMax - 1
                        s5 = s4 + e: o5 = o4 + nOdd(e): l5 = l4 + nLow(e): m5 = m4 Or nBit(e)
                        p5 = p4 + nPrv(e): z5 = z4 + tNum(e)
                        q5 = q4: If e = d + 1 Then q5 = q5 + 1
                        secCnt(nSecI(e)) = secCnt(nSecI(e)) + 1
                        x5 = x4: If secCnt(nSecI(e)) > x5 Then x5 = secCnt(nSecI(e))
                        For f = e + 1 To nMax
                            qq = q5: If f = e + 1 Then qq = qq + 1
                            xx = secCnt(nSecI(f)) + 1: If xx < x5 Then xx = x5
                            sc = z5 + tNum(f) + tSum(s5 + f) + tOdd(o5 + nOdd(f)) + tLow(l5 + nLow(f)) _
                                 + tCon(qq) + tDig(pc(m5 Or nBit(f))) + tSec(xx) + tPrv(p5 + nPrv(f))
                            If hN < HEAP_SIZE Then
                                cd = ((((CDbl(a) * 64 + b) * 64 + c) * 64 + d) * 64 + e) * 64 + f
                                HeapPush sc, cd
                            ElseIf sc > hS(1) Then
                                cd = ((((CDbl(a) * 64 + b) * 64 + c) * 64 + d) * 64 + e) * 64 + f
                                HeapReplaceTop sc, cd
                            End If
                        Next f
                        secCnt(nSecI(e)) = secCnt(nSecI(e)) - 1
                    Next e
                    secCnt(nSecI(d)) = secCnt(nSecI(d)) - 1
                Next d
                secCnt(nSecI(c)) = secCnt(nSecI(c)) - 1
            Next c
            secCnt(nSecI(b)) = secCnt(nSecI(b)) - 1
        Next b
        secCnt(nSecI(a)) = secCnt(nSecI(a)) - 1
    Next a

    ' ---- stage 2: add AC score and rank ----
    ShowStatus "2/2"
    Dim tot() As Double, ord() As Long
    ReDim tot(1 To hN)
    ReDim ord(1 To hN)
    For i = 1 To hN
        DecodeSix hC(i), t
        FeatureSet t, fv
        tot(i) = hS(i) + tAC(fv(7))
        ord(i) = i
    Next i
    SortRank tot, hC, ord, 1, hN

    ' past winning combinations (sorted codes for binary search)
    Dim past() As Double
    ReDim past(1 To nDraw)
    For i = 1 To nDraw
        past(i) = CodeOfDraw(dr, i)
    Next i
    SortDbl past, 1, nDraw

    ' ---- pick diverse top sets ----
    Dim pick() As Long, picked As Long, mem() As Boolean, ok As Boolean, common As Long
    ReDim pick(1 To nPick)
    ReDim mem(1 To nPick, 1 To 45)
    picked = 0
    For i = 1 To hN
        If picked >= nPick Then Exit For
        ok = True
        If excl Then
            If FindDbl(past, nDraw, hC(ord(i))) Then ok = False
        End If
        If ok Then
            DecodeSix hC(ord(i)), t
            For j = 1 To picked
                common = 0
                For k = 1 To 6
                    If mem(j, t(k)) Then common = common + 1
                Next k
                If common > maxOv Then ok = False: Exit For
            Next j
        End If
        If ok Then
            picked = picked + 1
            pick(picked) = ord(i)
            For k = 1 To 6
                mem(picked, t(k)) = True
            Next k
        End If
    Next i

    ' ---- write sheets ----
    WriteStats nDraw, rno, nRecent, cNum, cRec, tNum, cOdd, tOdd, cLow, tLow, cCon, tCon, _
               cDig, tDig, cSec, tSec, cPrv, tPrv, cAC, tAC, cSum
    WriteResult nDraw, rno, dr, picked, pick, tot, nRecent, nMax

    AnalyzeCore = U("\uACC4\uC0B0 \uC644\uB8CC: ") & rno(1) & U("\uD68C ~ ") & rno(nDraw) & U("\uD68C (") & nDraw & U("\uD68C) \uAE30\uC900, ") & _
        picked & U("\uAC1C \uC870\uD569\uC744 [") & SH_RES() & U("] \uC2DC\uD2B8\uC5D0 \uCD9C\uB825\uD588\uC2B5\uB2C8\uB2E4.") & vbLf & _
        U("\u203B \uBAA8\uB4E0 \uC870\uD569\uC758 1\uB4F1 \uB2F9\uCCA8\uD655\uB960\uC740 \uB611\uAC19\uC774 1/8,145,060\uC785\uB2C8\uB2E4.")
    If picked < nPick Then
        AnalyzeCore = AnalyzeCore & vbLf & U("\u203B \uACF5\uD1B5\uBC88\uD638 \uC81C\uD55C \uB54C\uBB38\uC5D0 ") & nPick & U("\uAC1C\uB97C \uB2E4 \uCC44\uC6B0\uC9C0 \uBABB\uD588\uC2B5\uB2C8\uB2E4. \uC124\uC815 C8 \uAC12\uC744 \uB298\uB824\uBCF4\uC138\uC694.")
    End If
End Function

'------------------------------------------------------------------------------
' features: fv(1)=sum 2=odd 3=low 4=consecutive pairs 5=distinct last digits
'           6=max count in one section 7=AC value      (t() must be sorted)
'------------------------------------------------------------------------------
Private Sub FeatureSet(t() As Long, fv() As Long)
    Dim k As Long, j As Long, mask As Long, sec(0 To 4) As Long
    Dim df(0 To 44) As Boolean, nd As Long, x As Long

    For j = 1 To 7
        fv(j) = 0
    Next j
    For k = 1 To 6
        fv(1) = fv(1) + t(k)
        fv(2) = fv(2) + (t(k) Mod 2)
        If t(k) <= LOW_MAX Then fv(3) = fv(3) + 1
        If k > 1 Then
            If t(k) = t(k - 1) + 1 Then fv(4) = fv(4) + 1
        End If
        mask = mask Or (2 ^ (t(k) Mod 10))
        sec(t(k) \ 10) = sec(t(k) \ 10) + 1
        If sec(t(k) \ 10) > fv(6) Then fv(6) = sec(t(k) \ 10)
    Next k
    For j = 0 To 9
        If (mask And (2 ^ j)) <> 0 Then fv(5) = fv(5) + 1
    Next j
    nd = 0
    For k = 1 To 5
        For j = k + 1 To 6
            x = t(j) - t(k)
            If Not df(x) Then df(x) = True: nd = nd + 1
        Next j
    Next k
    fv(7) = nd - 5
End Sub

Private Function OverlapDraws(dr() As Long, ByVal i1 As Long, ByVal i2 As Long) As Long
    Dim k As Long, j As Long, n As Long
    For k = 1 To 6
        For j = 1 To 6
            If dr(i1, k) = dr(i2, j) Then n = n + 1
        Next j
    Next k
    OverlapDraws = n
End Function

'------------------------------------------------------------------------------
' data sheet -> arrays (rows with 6 valid numbers, ordered by round)
'------------------------------------------------------------------------------
Private Function LoadDraws(rno() As Long, dr() As Long) As Long
    Dim ws As Worksheet, lastRow As Long, v As Variant
    Dim i As Long, k As Long, n As Long, x As Long, ok As Boolean
    Dim t(1 To 6) As Long, sorted As Boolean, j As Long, tmp As Long

    LoadDraws = 0
    Set ws = ThisWorkbook.Worksheets(SH_DATA())
    lastRow = ws.UsedRange.Row + ws.UsedRange.Rows.Count - 1
    If lastRow < 3 Then Exit Function
    v = ws.Range("A2:G" & lastRow).Value

    ReDim rno(1 To UBound(v, 1))
    ReDim dr(1 To UBound(v, 1), 1 To 6)
    n = 0
    For i = 1 To UBound(v, 1)
        ok = True
        For k = 1 To 6
            If IsWhole(v(i, k + 1), 1, 45, x) Then
                t(k) = x
            Else
                ok = False
                Exit For
            End If
        Next k
        If ok Then
            SortSix t
            For k = 2 To 6
                If t(k) = t(k - 1) Then ok = False
            Next k
        End If
        If ok Then
            n = n + 1
            If IsWhole(v(i, 1), 1, 100000, x) Then rno(n) = x Else rno(n) = n
            For k = 1 To 6
                dr(n, k) = t(k)
            Next k
        End If
    Next i

    ' keep the draws in round order (insertion sort, stable)
    sorted = True
    For i = 2 To n
        If rno(i) < rno(i - 1) Then sorted = False: Exit For
    Next i
    If Not sorted Then
        For i = 2 To n
            j = i
            Do While j > 1
                If rno(j - 1) <= rno(j) Then Exit Do
                tmp = rno(j): rno(j) = rno(j - 1): rno(j - 1) = tmp
                For k = 1 To 6
                    tmp = dr(j, k): dr(j, k) = dr(j - 1, k): dr(j - 1, k) = tmp
                Next k
                j = j - 1
            Loop
        Next i
    End If
    LoadDraws = n
End Function

'------------------------------------------------------------------------------
' output sheets
'------------------------------------------------------------------------------
Private Sub WriteResult(ByVal nDraw As Long, rno() As Long, dr() As Long, ByVal picked As Long, _
                        pick() As Long, tot() As Double, ByVal nRecent As Long, ByVal nMax As Long)
    Dim ws As Worksheet, outv() As Variant, i As Long, k As Long
    Dim t(1 To 6) As Long, fv(1 To 7) As Long, ov As Long, j As Long

    Set ws = ThisWorkbook.Worksheets(SH_RES())
    ws.Range("A5:Q" & ws.Rows.Count).ClearContents
    ws.Range("B2").Value = rno(1) & U("\uD68C ~ ") & rno(nDraw) & U("\uD68C (") & nDraw & U("\uD68C), \uCD5C\uADFC ") & nRecent & _
        U("\uD68C \uBC18\uC601, \uACC4\uC0B0: ") & Format$(Now, "yyyy-mm-dd hh:nn")
    If nMax < 45 Then ws.Range("B2").Value = ws.Range("B2").Value & "  [TEST 1~" & nMax & "]"
    If picked = 0 Then Exit Sub

    ReDim outv(1 To picked, 1 To 16)
    For i = 1 To picked
        DecodeSix hC(pick(i)), t
        FeatureSet t, fv
        ov = 0
        For k = 1 To 6
            For j = 1 To 6
                If t(k) = dr(nDraw, j) Then ov = ov + 1
            Next j
        Next k
        outv(i, 1) = i
        For k = 1 To 6
            outv(i, k + 1) = t(k)
        Next k
        outv(i, 8) = Round(tot(pick(i)), 4)
        outv(i, 9) = fv(1)
        outv(i, 10) = fv(2) & ":" & (6 - fv(2))
        outv(i, 11) = fv(3) & ":" & (6 - fv(3))
        outv(i, 12) = fv(4)
        outv(i, 13) = fv(5)
        outv(i, 14) = fv(6)
        outv(i, 15) = ov
        outv(i, 16) = fv(7)
    Next i
    ws.Range("A5").Resize(picked, 16).Value = outv
End Sub

Private Sub WriteStats(ByVal nDraw As Long, rno() As Long, ByVal nRecent As Long, _
        cNum() As Long, cRec() As Long, tNum() As Double, _
        cOdd() As Long, tOdd() As Double, cLow() As Long, tLow() As Double, _
        cCon() As Long, tCon() As Double, cDig() As Long, tDig() As Double, _
        cSec() As Long, tSec() As Double, cPrv() As Long, tPrv() As Double, _
        cAC() As Long, tAC() As Double, cSum() As Long)
    Dim ws As Worksheet, outv() As Variant, i As Long, r As Long

    Set ws = ThisWorkbook.Worksheets(SH_STAT())
    ws.Range("A5:E" & ws.Rows.Count).ClearContents
    ws.Range("G5:K" & ws.Rows.Count).ClearContents
    ws.Range("B2").Value = rno(1) & U("\uD68C ~ ") & rno(nDraw) & U("\uD68C (") & nDraw & U("\uD68C), \uCD5C\uADFC ") & nRecent & U("\uD68C")

    ' number table A5:E49
    ReDim outv(1 To 45, 1 To 5)
    For i = 1 To 45
        outv(i, 1) = i
        outv(i, 2) = cNum(i)
        outv(i, 3) = Round(cNum(i) / nDraw, 4)
        outv(i, 4) = cRec(i)
        outv(i, 5) = Round(tNum(i), 4)
    Next i
    ws.Range("A5").Resize(45, 5).Value = outv

    ' feature tables G:K  (feature | value | count | ratio | score)
    r = 5
    For i = 0 To 6: PutFeat ws, r, U("\uD640\uC218 \uAC1C\uC218"), CStr(i), cOdd(i), nDraw, tOdd(i): Next i
    For i = 0 To 6: PutFeat ws, r, U("\uC800\uBC88\uD638(1~22) \uAC1C\uC218"), CStr(i), cLow(i), nDraw, tLow(i): Next i
    For i = 0 To 5: PutFeat ws, r, U("\uC5F0\uC18D\uBC88\uD638 \uC30D"), CStr(i), cCon(i), nDraw, tCon(i): Next i
    For i = 1 To 6: PutFeat ws, r, U("\uB05D\uC218 \uC885\uB958"), CStr(i), cDig(i), nDraw, tDig(i): Next i
    For i = 1 To 6: PutFeat ws, r, U("\uD55C \uAD6C\uAC04 \uCD5C\uB300 \uAC1C\uC218"), CStr(i), cSec(i), nDraw, tSec(i): Next i
    For i = 0 To 6: PutFeat ws, r, U("\uC9C1\uC804\uD68C\uCC28 \uC911\uBCF5"), CStr(i), cPrv(i), nDraw - 1, tPrv(i): Next i
    For i = 0 To 10: PutFeat ws, r, U("AC\uAC12"), CStr(i), cAC(i), nDraw, tAC(i): Next i
    For i = 0 To 27
        PutFeat ws, r, U("\uD569\uACC4"), (21 + i * 10) & "~" & (30 + i * 10), _
            RangeSum(cSum, 21 + i * 10, 30 + i * 10), nDraw, Empty
    Next i
End Sub

Private Sub PutFeat(ws As Worksheet, r As Long, ByVal nm As String, ByVal valTxt As String, _
                    ByVal cnt As Long, ByVal total As Long, ByVal score As Variant)
    ws.Cells(r, 7).Value = nm
    ws.Cells(r, 8).Value = "'" & valTxt
    ws.Cells(r, 9).Value = cnt
    If total > 0 Then ws.Cells(r, 10).Value = Round(cnt / total, 4)
    If Not IsEmpty(score) Then ws.Cells(r, 11).Value = Round(score, 4)
    r = r + 1
End Sub

Private Function RangeSum(cSum() As Long, ByVal lo As Long, ByVal hi As Long) As Long
    Dim i As Long
    For i = lo To hi
        If i >= 0 And i <= SUM_TOP Then RangeSum = RangeSum + cSum(i)
    Next i
End Function

'------------------------------------------------------------------------------
' heap
'------------------------------------------------------------------------------
Private Sub HeapPush(ByVal sc As Double, ByVal cd As Double)
    Dim i As Long, p As Long
    hN = hN + 1
    i = hN
    Do While i > 1
        p = i \ 2
        If hS(p) <= sc Then Exit Do
        hS(i) = hS(p): hC(i) = hC(p)
        i = p
    Loop
    hS(i) = sc: hC(i) = cd
End Sub

Private Sub HeapReplaceTop(ByVal sc As Double, ByVal cd As Double)
    Dim i As Long, l As Long
    i = 1
    Do
        l = 2 * i
        If l > hN Then Exit Do
        If l < hN Then
            If hS(l + 1) < hS(l) Then l = l + 1
        End If
        If hS(l) >= sc Then Exit Do
        hS(i) = hS(l): hC(i) = hC(l)
        i = l
    Loop
    hS(i) = sc: hC(i) = cd
End Sub

'------------------------------------------------------------------------------
' small helpers
'------------------------------------------------------------------------------
Private Sub DecodeSix(ByVal cd As Double, t() As Long)
    Dim k As Long, q As Double
    For k = 6 To 1 Step -1
        q = Int(cd / 64)
        t(k) = CLng(cd - q * 64)
        cd = q
    Next k
End Sub

Private Function CodeOfDraw(dr() As Long, ByVal i As Long) As Double
    Dim k As Long, cd As Double
    For k = 1 To 6
        cd = cd * 64 + dr(i, k)
    Next k
    CodeOfDraw = cd
End Function

Private Sub SortSix(t() As Long)
    Dim i As Long, j As Long, x As Long
    For i = 2 To 6
        x = t(i): j = i - 1
        Do While j >= 1
            If t(j) <= x Then Exit Do
            t(j + 1) = t(j)
            j = j - 1
        Loop
        t(j + 1) = x
    Next i
End Sub

' rank: higher total first, then lower code (= lexicographic order)
Private Function RankBefore(tot() As Double, cds() As Double, ByVal i As Long, ByVal j As Long) As Boolean
    If tot(i) > tot(j) Then
        RankBefore = True
    ElseIf tot(i) < tot(j) Then
        RankBefore = False
    Else
        RankBefore = (cds(i) < cds(j))
    End If
End Function

Private Sub SortRank(tot() As Double, cds() As Double, ord() As Long, ByVal lo As Long, ByVal hi As Long)
    Dim i As Long, j As Long, pv As Long, tmp As Long
    Do While lo < hi
        pv = ord((lo + hi) \ 2)
        i = lo: j = hi
        Do While i <= j
            Do While RankBefore(tot, cds, ord(i), pv)
                i = i + 1
            Loop
            Do While RankBefore(tot, cds, pv, ord(j))
                j = j - 1
            Loop
            If i <= j Then
                tmp = ord(i): ord(i) = ord(j): ord(j) = tmp
                i = i + 1: j = j - 1
            End If
        Loop
        If j - lo < hi - i Then
            If lo < j Then SortRank tot, cds, ord, lo, j
            lo = i
        Else
            If i < hi Then SortRank tot, cds, ord, i, hi
            hi = j
        End If
    Loop
End Sub

Private Sub SortDbl(x() As Double, ByVal lo As Long, ByVal hi As Long)
    Dim i As Long, j As Long, pv As Double, tmp As Double
    Do While lo < hi
        pv = x((lo + hi) \ 2)
        i = lo: j = hi
        Do While i <= j
            Do While x(i) < pv
                i = i + 1
            Loop
            Do While pv < x(j)
                j = j - 1
            Loop
            If i <= j Then
                tmp = x(i): x(i) = x(j): x(j) = tmp
                i = i + 1: j = j - 1
            End If
        Loop
        If j - lo < hi - i Then
            If lo < j Then SortDbl x, lo, j
            lo = i
        Else
            If i < hi Then SortDbl x, i, hi
            hi = j
        End If
    Loop
End Sub

Private Function FindDbl(x() As Double, ByVal n As Long, ByVal key As Double) As Boolean
    Dim lo As Long, hi As Long, md As Long
    lo = 1: hi = n
    Do While lo <= hi
        md = (lo + hi) \ 2
        If x(md) = key Then FindDbl = True: Exit Function
        If x(md) < key Then lo = md + 1 Else hi = md - 1
    Loop
    FindDbl = False
End Function

' value -> whole number in [lo, hi]  (accepts numbers and numeric text)
Private Function IsWhole(ByVal v As Variant, ByVal lo As Long, ByVal hi As Long, ByRef x As Long) As Boolean
    Dim d As Double, s As String, i As Long, ch As String
    IsWhole = False
    Select Case VarType(v)
        Case 2, 3, 4, 5, 6, 14, 17          ' integer, long, single, double, currency, decimal, byte
            d = CDbl(v)
        Case 8                              ' string
            s = Trim$(CStr(v))
            s = Replace(s, ",", "")
            s = Replace(s, U("\uD68C"), "")
            s = Replace(s, U("\uBC88"), "")
            s = Trim$(s)
            If Len(s) = 0 Or Len(s) > 9 Then Exit Function
            For i = 1 To Len(s)
                ch = Mid$(s, i, 1)
                If ch < "0" Or ch > "9" Then Exit Function
            Next i
            d = CDbl(s)
        Case Else
            Exit Function
    End Select
    If d <> Int(d) Then Exit Function
    If d < lo Or d > hi Then Exit Function
    x = CLng(d)
    IsWhole = True
End Function

Private Function GetLong(ByVal v As Variant, ByVal lo As Long, ByVal hi As Long, ByVal dflt As Long) As Long
    Dim x As Long
    If IsWhole(v, lo, hi, x) Then GetLong = x Else GetLong = dflt
End Function

Private Function GetDbl(ByVal v As Variant, ByVal dflt As Double) As Double
    Select Case VarType(v)
        Case 2, 3, 4, 5, 6, 14, 17
            GetDbl = CDbl(v)
        Case Else
            GetDbl = dflt
    End Select
End Function

Private Sub ShowStatus(ByVal v As Variant)
    If gSilent Then Exit Sub
    On Error Resume Next
    Application.StatusBar = v
    DoEvents
End Sub

Private Sub Say(ByVal msg As String)
    If gSilent Then
        Debug.Print msg
    Else
        MsgBox msg, vbInformation, U("\uB85C\uB610\uBC88\uD638 \uBD84\uC11D")
    End If
End Sub

' decodes \uXXXX escapes (keeps the module ASCII-only)
Private Function U(ByVal s As String) As String
    Dim r As String, i As Long, k As Long, cp As Long, h As String
    i = 1
    Do While i <= Len(s)
        If Mid$(s, i, 2) = "\u" And i + 5 <= Len(s) Then
            h = UCase$(Mid$(s, i + 2, 4))
            cp = 0
            For k = 1 To 4
                cp = cp * 16 + InStr("0123456789ABCDEF", Mid$(h, k, 1)) - 1
            Next k
            r = r & ChrW(cp)
            i = i + 6
        Else
            r = r & Mid$(s, i, 1)
            i = i + 1
        End If
    Loop
    U = r
End Function
