# FlightAware SeleniumBasic VBA Scraper

This folder contains a VBA-only SeleniumBasic scraper for:

- `https://www.flightaware.com/live/cancelled`
- `https://www.flightaware.com/live/cancelled/yesterday`
- `https://www.flightaware.com/live/cancelled/minus2days`
- `https://www.flightaware.com/live/cancelled/minus3days`

It extracts these two visible FlightAware totals from each page:

- `Total delays within, into, or out of the United States ...`
- `Total cancellations within, into, or out of the United States ...`

## Requirements

SeleniumBasic by Florent Br:

https://github.com/florentbr/SeleniumBasic

SeleniumBasic is a Windows COM/VBA automation library, so run the macro from Windows Excel with SeleniumBasic installed.

## Install

1. Open Excel.
2. Create or open a macro-enabled workbook in this folder.
3. Press `Alt + F11`.
4. Choose `File > Import File...`.
5. Import `FlightAwareScraper.bas`.
6. In VBA, choose `Tools > References...`.
7. Enable `Selenium Type Library` if available. The module uses late binding, so this reference is helpful but not required.

## Run

Run:

```vb
ScrapeFlightAwareUSTotals
```

The scraper is configured for headless Chrome by default:

```vb
Private Const HEADLESS_BROWSER As Boolean = True
```

Change it to `False` if you need to watch the browser during debugging.

The scraper also uses polite pacing between page requests:

```vb
Private Const MIN_PAGE_PAUSE_SECONDS As Double = 4#
Private Const MAX_PAGE_PAUSE_SECONDS As Double = 9#
Private Const MAX_PAGE_RETRIES As Long = 2
```

Increase these values if you run the macro repeatedly. Avoid high-frequency scraping and make sure your use follows FlightAware's terms and any applicable data-use limits.

The macro writes results to a worksheet named `FlightAware_US_Totals` and also saves:

```text
flightaware_us_totals.csv
```

next to the workbook.

## Output Columns

- `ScrapedAt`
- `RequestedDay`
- `FlightAwarePeriod`
- `URL`
- `US_TotalDelays`
- `US_TotalCancellations`

## Notes

The scraper reads the visible page body text and uses regular expressions to find the U.S. delay and cancellation totals. This avoids fragile CSS selectors because FlightAware exposes these totals clearly in the rendered text.

For SeleniumBasic headless Chrome runs, keep Chrome and ChromeDriver compatible. If `--headless=new` fails on an older Chrome version, replace it with:

```vb
driver.AddArgument "--headless"
```
