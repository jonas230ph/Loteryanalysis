# FlightAware US Delay CSV Chrome Extension

Version: `1.0.1`

This Chrome extension scrapes FlightAware cancellation statistics and exports a CSV containing the United States delay and cancellation totals for the current day and the previous 3 days.

## Requirements

- Google Chrome or another Chromium browser that supports Manifest V3 extensions.
- Internet access to `https://www.flightaware.com`.
- The unpacked extension folder:

```text
/Users/jonasodones/Desktop/Plugin/Flightdelay
```

- Chrome downloads permission. The extension requests this through `manifest.json`.
- FlightAware must continue publishing the target text lines on its cancelled flights pages.

No API key, login, server, Python environment, or npm install is required.

## Source Pages

The extension scrapes these 4 pages:

- Today: `https://www.flightaware.com/live/cancelled`
- Yesterday: `https://www.flightaware.com/live/cancelled/yesterday`
- Minus 2 days: `https://www.flightaware.com/live/cancelled/minus2days`
- Minus 3 days: `https://www.flightaware.com/live/cancelled/minus3days`

## Captured Fields

From each page, the extension captures only these 2 FlightAware values:

- `Total delays within, into, or out of the United States ...`
- `Total cancellations within, into, or out of the United States ...`

Other page data is ignored.

## Install Step By Step

1. Open Google Chrome.
2. Go to `chrome://extensions`.
3. Turn on **Developer mode** in the top-right corner.
4. Click **Load unpacked**.
5. Select this folder:

```text
/Users/jonasodones/Desktop/Plugin/Flightdelay
```

6. Confirm the extension appears in the extensions list as **FlightAware US Delay CSV**.
7. Optional: pin the extension from Chrome's extensions menu so it is easier to open.

## Run Step By Step

1. Click the **FlightAware US Delay CSV** extension icon in Chrome.
2. Click **Scrape 4 days and export CSV**.
3. Wait until the popup shows `CSV created`.
4. Chrome saves the generated CSV to your default Downloads folder.
5. Open the CSV in Excel, Numbers, Google Sheets, or any text editor.

The generated filename uses this pattern:

```text
flightaware_us_delays_YYYY-MM-DD.csv
```

Example:

```text
flightaware_us_delays_2026-05-09.csv
```

## CSV Output

The CSV contains these columns:

```csv
date,day_offset,page_label,total_delays_within_into_or_out_of_united_states,total_cancellations_within_into_or_out_of_united_states,source_url,scraped_at
```

Column meanings:

- `date`: Local date assigned by the extension.
- `day_offset`: `0` for today, `1` for yesterday, `2` for minus 2 days, `3` for minus 3 days.
- `page_label`: FlightAware page label used by the extension.
- `total_delays_within_into_or_out_of_united_states`: Parsed United States delay total.
- `total_cancellations_within_into_or_out_of_united_states`: Parsed United States cancellation total.
- `source_url`: FlightAware page URL used for the row.
- `scraped_at`: ISO timestamp when the row was scraped.

Example output:

```csv
date,day_offset,page_label,total_delays_within_into_or_out_of_united_states,total_cancellations_within_into_or_out_of_united_states,source_url,scraped_at
2026-05-09,0,today,4785,76,https://www.flightaware.com/live/cancelled,2026-05-09T02:39:43.414Z
2026-05-08,1,yesterday,7193,87,https://www.flightaware.com/live/cancelled/yesterday,2026-05-09T02:39:44.014Z
2026-05-07,2,minus2days,5970,296,https://www.flightaware.com/live/cancelled/minus2days,2026-05-09T02:39:44.530Z
2026-05-06,3,minus3days,4179,306,https://www.flightaware.com/live/cancelled/minus3days,2026-05-09T02:39:45.080Z
```

## Troubleshooting

If the extension shows an error:

1. Confirm your internet connection is working.
2. Open `https://www.flightaware.com/live/cancelled` in Chrome and confirm the page loads.
3. Reload the extension from `chrome://extensions`.
4. Run the extension again.

If no CSV appears:

1. Check Chrome's default Downloads folder.
2. Check whether Chrome blocked downloads for the extension.
3. Reload the extension and run it again.

If FlightAware changes the text or structure of its cancelled flights pages, the parser may need to be updated.

## Notes

Chrome extensions cannot silently write directly to an arbitrary folder on your Mac. This extension uses Chrome's built-in downloads API, so the CSV is saved through Chrome's normal download behavior.

The extension has been tested with Chromium by loading the unpacked extension, clicking the popup button, scraping all 4 FlightAware pages, rendering 4 result rows, and producing a CSV file.
