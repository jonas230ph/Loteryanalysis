from curl_cffi import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
from pathlib import Path
import sys
import time

def scrape_pcso_stealth():
    url = "https://www.pcso.gov.ph/searchlottoresult.aspx"
    now = datetime.now()
    current_year = str(now.year)
    
    # We use impersonate="chrome124" to mimic a real browser's TLS fingerprint
    session = requests.Session(impersonate="chrome124")

    try:
        print(f"Connecting to PCSO as a browser (Stealth Mode)...")
        
        # Step 1: Initial GET to capture ASP.NET tokens
        # We use a real Referer and standard browser headers automatically provided by impersonate
        response = session.get(url, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Preserve all ASP.NET hidden fields so postback validation succeeds.
        hidden_fields = {
            field["name"]: field.get("value", "")
            for field in soup.find_all("input", type="hidden")
            if field.get("name")
        }
        vs = hidden_fields.get("__VIEWSTATE")
        vsg = hidden_fields.get("__VIEWSTATEGENERATOR")
        ev = hidden_fields.get("__EVENTVALIDATION")
        
        if not all([vs, vsg, ev]):
            raise RuntimeError("Could not find ASP.NET tokens. WAF might still be blocking.")

        # Prepare the payload
        payload = {
            **hidden_fields,
            "ctl00$ctl00$cphContainer$cpContent$ddlStartMonth": "January",
            "ctl00$ctl00$cphContainer$cpContent$ddlStartDate": "1",
            "ctl00$ctl00$cphContainer$cpContent$ddlStartYear": current_year,
            "ctl00$ctl00$cphContainer$cpContent$ddlEndMonth": now.strftime("%B"),
            "ctl00$ctl00$cphContainer$cpContent$ddlEndDay": str(now.day),
            "ctl00$ctl00$cphContainer$cpContent$ddlEndYear": current_year,
            "ctl00$ctl00$cphContainer$cpContent$ddlSelectGame": "0",
            "ctl00$ctl00$cphContainer$cpContent$btnSearch": "Search Lotto"
        }

        # Human-like delay
        print("Wait for 2 seconds to mimic human reading time...")
        time.sleep(2)

        # Step 2: POST request for data
        print("Submitting search request...")
        post_response = session.post(url, data=payload, timeout=30)
        post_response.raise_for_status()
        
        # Step 3: Parse results
        result_soup = BeautifulSoup(post_response.text, 'html.parser')
        table = result_soup.find("table", {"id": "cphContainer_cpContent_GridView1"})
        if not table:
            raise RuntimeError("Could not find the PCSO results table.")

        scraped_data = []
        rows = table.find_all("tr")
        for row in rows[1:]:  # Skip header
            cols = row.find_all("td")
            if len(cols) >= 5:
                scraped_data.append({
                    "lotto_game": cols[0].get_text(strip=True),
                    "combinations": cols[1].get_text(strip=True),
                    "draw_date": cols[2].get_text(strip=True),
                    "jackpot": cols[3].get_text(strip=True),
                    "winners": cols[4].get_text(strip=True)
                })

        if not scraped_data:
            raise RuntimeError("No lottery rows were parsed from the PCSO results table.")

        # Step 4: Save to JSON
        filename = Path(__file__).with_name("pcso_results.json")
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(scraped_data, f, indent=4, ensure_ascii=False)
        
        print(f"Success! {len(scraped_data)} results saved to {filename}")
        return True

    except Exception as e:
        print(f"Scrape failed: {e}")
        print("Hint: If this still fails, the site may be using JavaScript-based challenges (Cloudflare/Imperva).")
        return False

if __name__ == '__main__':
    sys.exit(0 if scrape_pcso_stealth() else 1)
