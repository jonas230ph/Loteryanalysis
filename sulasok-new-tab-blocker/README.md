# Sulasok New Tab Blocker

A small Brave/Chromium extension that stops any site with `sulasok` in its domain name from opening extra tabs or pop-up windows. When a matching tab is closed, it also clears that site's cookies, cache, history entries, and address-bar typed URL suggestions.

## Install in Brave

1. Open `brave://extensions/`.
2. Turn on **Developer mode**.
3. Click **Load unpacked**.
4. Select this folder:

   `/Users/jonasodones/Desktop/Plugin`

5. Visit a site whose domain contains `sulasok`, such as `https://sulasok.am/`.

## What it does

- Rewrites links and forms on matching `sulasok` domains so `_blank` opens in the current tab.
- Blocks programmatic `window.open(...)` calls.
- Closes any tab that Brave still creates from a matching `sulasok` opener.
- Clears cookies, cache, history URLs, and address-bar autocomplete suggestions for any visited/history domain whose hostname contains `sulasok`.
- Runs cleanup when the extension is installed/reloaded, when Brave starts, when a matching tab closes, and whenever Brave records a new matching history visit.

## Note about Brave history files

This extension deletes matching `sulasok` history entries through Brave's extension API. It does not delete Brave's physical browser database file named `History`, because Brave owns that file while the browser is running and it also contains unrelated history.

## How it was created

1. Created a plugin folder:

   `/Users/jonasodones/Desktop/Plugin`

2. Added `manifest.json` using Chrome Extension Manifest V3.

3. Gave the extension permission to observe browser tabs and site data. The content script runs on all URLs, but its code exits unless the hostname contains `sulasok`.

4. Added `content.js`, which runs at `document_start` and activates only when the current hostname contains `sulasok`.

5. In `content.js`, replaced `window.open(...)` so scripts on the page cannot create popup tabs.

6. In `content.js`, changed links and forms with `target="_blank"` so they use the current tab instead.

7. Added a `MutationObserver` in `content.js` so new links/forms added later by the website are also fixed.

8. Added `background.js`, a service worker that watches for new tabs opened by matching `sulasok` domains.

9. In `background.js`, if Brave still creates a new tab from a matching `sulasok` domain, the extension closes that tab immediately.

10. Added the `browsingData` permission so the extension can clear cookies and cache for matching `sulasok` domains.

11. Added the `history` permission so the extension can delete tracked `sulasok` history URLs.

12. Updated `background.js` to remember matching `sulasok` tabs and URLs while they are open.

13. Added the `webNavigation` permission so the extension can catch new-tab navigation targets more reliably.

14. Updated `background.js` so closing a remembered matching tab clears cookies, cache, cache storage, and history entries for that site.

15. Updated `background.js` to search Brave/Chrome history for `sulasok` entries, then delete matching URLs so the sites stop appearing in address-bar autocomplete suggestions.

16. Added cleanup triggers for extension install/reload, Brave startup, and new matching history visits.

17. Verified `manifest.json` is valid JSON.

## Files

- `manifest.json` controls extension metadata, permissions, and script loading.
- `content.js` blocks popup behavior inside the `sulasok.am` page.
- `background.js` closes extra tabs that still get created from the protected site and clears cookies, cache, history, and address-bar suggestions when a protected tab closes.
- `README.md` explains setup and creation steps.
