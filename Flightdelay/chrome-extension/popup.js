const scrapeButton = document.querySelector("#scrapeButton");
const statusElement = document.querySelector("#status");
const resultsElement = document.querySelector("#results");
const resultsBody = document.querySelector("#resultsBody");

scrapeButton.addEventListener("click", async () => {
  setBusy(true);
  setStatus("Scraping FlightAware pages...");
  resultsElement.hidden = true;
  resultsBody.replaceChildren();

  try {
    const response = await chrome.runtime.sendMessage({ type: "SCRAPE_FLIGHTAWARE" });

    if (!response?.ok) {
      throw new Error(response?.error || "Unknown scrape error.");
    }

    renderRows(response.rows);
    setStatus(`CSV created: ${response.filename}`);
  } catch (error) {
    setStatus(error instanceof Error ? error.message : String(error), true);
  } finally {
    setBusy(false);
  }
});

function renderRows(rows) {
  const fragment = document.createDocumentFragment();

  for (const row of rows) {
    const tableRow = document.createElement("tr");
    tableRow.append(
      cell(row.date),
      cell(formatNumber(firstValue(row.total_delays_within_into_or_out_of_united_states, row.us_total_delays))),
      cell(formatNumber(firstValue(row.total_cancellations_within_into_or_out_of_united_states, row.us_total_cancellations)))
    );
    fragment.append(tableRow);
  }

  resultsBody.replaceChildren(fragment);
  resultsElement.hidden = false;
}

function cell(value) {
  const tableCell = document.createElement("td");
  tableCell.textContent = value;
  return tableCell;
}

function formatNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number.toLocaleString("en-US") : "";
}

function firstValue(...values) {
  return values.find((value) => value !== undefined && value !== null && value !== "");
}

function setBusy(isBusy) {
  scrapeButton.disabled = isBusy;
  scrapeButton.textContent = isBusy ? "Scraping..." : "Scrape 4 days and export CSV";
}

function setStatus(message, isError = false) {
  statusElement.textContent = message;
  statusElement.classList.toggle("error", isError);
}
