const BASE_URL = "https://www.flightaware.com/live/cancelled";

const PAGE_CONFIG = [
  { offsetDays: 0, label: "today", path: "" },
  { offsetDays: 1, label: "yesterday", path: "/yesterday" },
  { offsetDays: 2, label: "minus2days", path: "/minus2days" },
  { offsetDays: 3, label: "minus3days", path: "/minus3days" }
];

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type !== "SCRAPE_FLIGHTAWARE") {
    return false;
  }

  scrapeFlightAware()
    .then(sendResponse)
    .catch((error) => {
      sendResponse({
        ok: false,
        error: error instanceof Error ? error.message : String(error)
      });
    });

  return true;
});

async function scrapeFlightAware() {
  const rows = [];

  for (const page of PAGE_CONFIG) {
    const url = `${BASE_URL}${page.path}`;
    const response = await fetch(url, {
      credentials: "include",
      cache: "no-store"
    });

    if (!response.ok) {
      throw new Error(`FlightAware returned ${response.status} for ${url}`);
    }

    const html = await response.text();
    rows.push(parseStatsPage(html, page, url));
  }

  const csv = toCsv(rows);
  const csvUrl = `data:text/csv;charset=utf-8,${encodeURIComponent(csv)}`;
  const filename = `flightaware_us_delays_${formatDateForFilename(new Date())}.csv`;

  await chrome.downloads.download({
    url: csvUrl,
    filename,
    saveAs: false,
    conflictAction: "uniquify"
  });

  return { ok: true, rows, filename };
}

function parseStatsPage(html, page, sourceUrl) {
  const text = normalizeText(stripHtml(html));
  const pageDate = dateForOffset(page.offsetDays);
  const delayRegex = /Total delays within, into, or out of the United States\s+[^:]*:\s*([0-9][0-9,]*)/i;
  const cancellationRegex = /Total cancellations within, into, or out of the United States\s+[^:]*:\s*([0-9][0-9,]*)/i;
  const delayMatch = text.match(delayRegex);
  const cancellationMatch = text.match(cancellationRegex);

  if (!delayMatch || !cancellationMatch) {
    throw new Error(`Could not find US delay/cancellation totals on ${sourceUrl}`);
  }

  return {
    date: pageDate,
    day_offset: page.offsetDays,
    page_label: page.label,
    total_delays_within_into_or_out_of_united_states: numberFromMatch(delayMatch[1]),
    total_cancellations_within_into_or_out_of_united_states: numberFromMatch(cancellationMatch[1]),
    source_url: sourceUrl,
    scraped_at: new Date().toISOString()
  };
}

function stripHtml(html) {
  return html
    .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, " ")
    .replace(/<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>/gi, " ")
    .replace(/<[^>]+>/g, " ");
}

function normalizeText(value) {
  return value
    .replace(/\u00a0/g, " ")
    .replace(/&nbsp;/gi, " ")
    .replace(/&amp;/gi, "&")
    .replace(/&#39;/g, "'")
    .replace(/&quot;/gi, "\"")
    .replace(/\s+/g, " ")
    .trim();
}

function numberFromMatch(value) {
  return Number.parseInt(value.replace(/,/g, ""), 10);
}

function toCsv(rows) {
  const headers = [
    "date",
    "day_offset",
    "page_label",
    "total_delays_within_into_or_out_of_united_states",
    "total_cancellations_within_into_or_out_of_united_states",
    "source_url",
    "scraped_at"
  ];

  return "\ufeff" + [
    headers.join(","),
    ...rows.map((row) => headers.map((header) => csvCell(row[header])).join(","))
  ].join("\r\n");
}

function csvCell(value) {
  const stringValue = String(value ?? "");
  if (!/[",\n\r]/.test(stringValue)) {
    return stringValue;
  }

  return `"${stringValue.replace(/"/g, '""')}"`;
}

function dateForOffset(offsetDays) {
  const date = new Date();
  date.setDate(date.getDate() - offsetDays);
  return formatDateForFilename(date);
}

function formatDateForFilename(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}
