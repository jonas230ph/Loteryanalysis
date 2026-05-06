Attribute VB_Name = "FlightAwareScraper"
Option Explicit

Private Const BASE_URL As String = "https://www.flightaware.com/live/cancelled"
Private Const OUTPUT_SHEET As String = "FlightAware_US_Totals"
Private Const HEADLESS_BROWSER As Boolean = True
Private Const MIN_PAGE_PAUSE_SECONDS As Double = 4#
Private Const MAX_PAGE_PAUSE_SECONDS As Double = 9#
Private Const MAX_PAGE_RETRIES As Long = 2

Public Sub ScrapeFlightAwareUSTotals()
    Dim driver As Object
    Dim ws As Worksheet
    Dim endpoints As Variant
    Dim labels As Variant
    Dim i As Long
    Dim rowIndex As Long
    Dim url As String
    Dim pageText As String
    Dim periodName As String
    Dim usDelays As Variant
    Dim usCancellations As Variant

    endpoints = Array("", "yesterday", "minus2days", "minus3days")
    labels = Array("Today", "Yesterday", "Minus 2 days", "Minus 3 days")

    Set ws = PrepareOutputSheet()
    Set driver = StartChromeDriver(HEADLESS_BROWSER)

    On Error GoTo CleanFail
    Randomize

    rowIndex = 2
    For i = LBound(endpoints) To UBound(endpoints)
        If Len(endpoints(i)) = 0 Then
            url = BASE_URL
        Else
            url = BASE_URL & "/" & endpoints(i)
        End If

        If i > LBound(endpoints) Then
            PolitePause MIN_PAGE_PAUSE_SECONDS, MAX_PAGE_PAUSE_SECONDS
        End If

        pageText = LoadStatsPage(driver, url, 30)

        periodName = ExtractPeriodName(pageText)
        usDelays = ExtractStatNumber(pageText, "Total delays within, into, or out of the United States")
        usCancellations = ExtractStatNumber(pageText, "Total cancellations within, into, or out of the United States")

        ws.Cells(rowIndex, 1).Value = Now
        ws.Cells(rowIndex, 2).Value = labels(i)
        ws.Cells(rowIndex, 3).Value = periodName
        ws.Cells(rowIndex, 4).Value = url
        ws.Cells(rowIndex, 5).Value = usDelays
        ws.Cells(rowIndex, 6).Value = usCancellations
        rowIndex = rowIndex + 1
    Next i

    ws.Columns("A:F").AutoFit
    SaveOutputCsv ws

CleanExit:
    On Error Resume Next
    If Not driver Is Nothing Then driver.Quit
    On Error GoTo 0
    Exit Sub

CleanFail:
    MsgBox "FlightAware scrape failed: " & Err.Description, vbExclamation, "FlightAware Scraper"
    Resume CleanExit
End Sub

Private Function StartChromeDriver(ByVal headless As Boolean) As Object
    Dim driver As Object

    Set driver = CreateObject("Selenium.ChromeDriver")

    If headless Then
        driver.AddArgument "--headless=new"
        driver.AddArgument "--disable-gpu"
        driver.AddArgument "--window-size=1920,1080"
    End If

    driver.AddArgument "--disable-dev-shm-usage"
    driver.AddArgument "--no-sandbox"

    Set StartChromeDriver = driver
End Function

Private Function LoadStatsPage(ByVal driver As Object, ByVal url As String, ByVal timeoutSeconds As Long) As String
    Dim attempt As Long
    Dim lastError As String

    For attempt = 1 To MAX_PAGE_RETRIES + 1
        Err.Clear
        On Error Resume Next
        driver.Get url
        LoadStatsPage = WaitForStatsText(driver, timeoutSeconds)
        lastError = Err.Description
        On Error GoTo 0

        If Len(LoadStatsPage) > 0 Then
            Exit Function
        End If

        PolitePause MIN_PAGE_PAUSE_SECONDS * attempt, MAX_PAGE_PAUSE_SECONDS * attempt
    Next attempt

    Err.Raise vbObjectError + 1002, "LoadStatsPage", "Could not load FlightAware totals from " & url & ". Last error: " & lastError
End Function

Private Function PrepareOutputSheet() As Worksheet
    Dim ws As Worksheet

    On Error Resume Next
    Set ws = ThisWorkbook.Worksheets(OUTPUT_SHEET)
    On Error GoTo 0

    If ws Is Nothing Then
        Set ws = ThisWorkbook.Worksheets.Add
        ws.Name = OUTPUT_SHEET
    Else
        ws.Cells.Clear
    End If

    ws.Range("A1:F1").Value = Array( _
        "ScrapedAt", _
        "RequestedDay", _
        "FlightAwarePeriod", _
        "URL", _
        "US_TotalDelays", _
        "US_TotalCancellations" _
    )
    ws.Range("A1:F1").Font.Bold = True

    Set PrepareOutputSheet = ws
End Function

Private Function WaitForStatsText(ByVal driver As Object, ByVal timeoutSeconds As Long) As String
    Dim startedAt As Single
    Dim bodyText As String

    startedAt = Timer
    Do
        DoEvents
        On Error Resume Next
        bodyText = driver.FindElementByTag("body").Text
        On Error GoTo 0

        If InStr(1, bodyText, "Total delays within, into, or out of the United States", vbTextCompare) > 0 _
           And InStr(1, bodyText, "Total cancellations within, into, or out of the United States", vbTextCompare) > 0 Then
            WaitForStatsText = NormalizeWhitespace(bodyText)
            Exit Function
        End If

        driver.Wait 500
    Loop While SecondsElapsed(startedAt) < timeoutSeconds

    Err.Raise vbObjectError + 1000, "WaitForStatsText", "Timed out waiting for FlightAware totals."
End Function

Private Function ExtractPeriodName(ByVal pageText As String) As String
    Dim re As Object
    Dim matches As Object

    Set re = CreateObject("VBScript.RegExp")
    re.Pattern = "FlightAware\.com live flight delay and cancellation statistics for ([^\r\n]+)"
    re.IgnoreCase = True
    re.Global = False

    Set matches = re.Execute(pageText)
    If matches.Count > 0 Then
        ExtractPeriodName = Trim$(matches(0).SubMatches(0))
    Else
        ExtractPeriodName = ""
    End If
End Function

Private Function ExtractStatNumber(ByVal pageText As String, ByVal statLabel As String) As Long
    Dim re As Object
    Dim matches As Object
    Dim patternText As String

    patternText = EscapeRegex(statLabel) & "\s+[^:]+:\s*([0-9,]+)"

    Set re = CreateObject("VBScript.RegExp")
    re.Pattern = patternText
    re.IgnoreCase = True
    re.Global = False

    Set matches = re.Execute(pageText)
    If matches.Count = 0 Then
        Err.Raise vbObjectError + 1001, "ExtractStatNumber", "Could not find stat: " & statLabel
    End If

    ExtractStatNumber = CLng(Replace(matches(0).SubMatches(0), ",", ""))
End Function

Private Function EscapeRegex(ByVal value As String) As String
    Dim specialChars As Variant
    Dim i As Long

    specialChars = Array("\", ".", "+", "*", "?", "^", "$", "(", ")", "[", "]", "{", "}", "|")
    EscapeRegex = value

    For i = LBound(specialChars) To UBound(specialChars)
        EscapeRegex = Replace(EscapeRegex, specialChars(i), "\" & specialChars(i))
    Next i
End Function

Private Function NormalizeWhitespace(ByVal value As String) As String
    Dim re As Object

    Set re = CreateObject("VBScript.RegExp")
    re.Pattern = "[ \t" & ChrW$(160) & "]+"
    re.Global = True

    NormalizeWhitespace = re.Replace(value, " ")
End Function

Private Function SecondsElapsed(ByVal startedAt As Single) As Single
    If Timer >= startedAt Then
        SecondsElapsed = Timer - startedAt
    Else
        SecondsElapsed = (86400! - startedAt) + Timer
    End If
End Function

Private Sub PolitePause(ByVal minSeconds As Double, ByVal maxSeconds As Double)
    Dim startedAt As Single
    Dim waitSeconds As Double

    If maxSeconds < minSeconds Then
        maxSeconds = minSeconds
    End If

    waitSeconds = minSeconds + (Rnd() * (maxSeconds - minSeconds))
    startedAt = Timer

    Do While SecondsElapsed(startedAt) < waitSeconds
        DoEvents
        Application.Wait Now + TimeSerial(0, 0, 1)
    Loop
End Sub

Private Sub SaveOutputCsv(ByVal ws As Worksheet)
    Dim outputPath As String
    Dim fileNumber As Integer
    Dim lastRow As Long
    Dim r As Long

    outputPath = ThisWorkbook.Path & Application.PathSeparator & "flightaware_us_totals.csv"
    lastRow = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row
    fileNumber = FreeFile

    Open outputPath For Output As #fileNumber
    Print #fileNumber, "ScrapedAt,RequestedDay,FlightAwarePeriod,URL,US_TotalDelays,US_TotalCancellations"

    For r = 2 To lastRow
        Print #fileNumber, CsvValue(ws.Cells(r, 1).Text) & "," & _
                           CsvValue(ws.Cells(r, 2).Text) & "," & _
                           CsvValue(ws.Cells(r, 3).Text) & "," & _
                           CsvValue(ws.Cells(r, 4).Text) & "," & _
                           CsvValue(ws.Cells(r, 5).Text) & "," & _
                           CsvValue(ws.Cells(r, 6).Text)
    Next r

    Close #fileNumber
End Sub

Private Function CsvValue(ByVal value As String) As String
    CsvValue = """" & Replace(value, """", """""") & """"
End Function
