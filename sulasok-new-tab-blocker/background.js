const protectedTabs = new Map();
const PROTECTED_NAME = "sulasok";
const HISTORY_SEARCH_TERMS = ["sulasok", "sulasok.", "www.sulasok", "https://sulasok"];

function isProtectedUrl(url) {
  try {
    const { hostname } = new URL(url);
    return hostname.toLowerCase().includes(PROTECTED_NAME);
  } catch {
    return false;
  }
}

function protectedOrigin(url) {
  try {
    const parsedUrl = new URL(url);
    if (parsedUrl.hostname.toLowerCase().includes(PROTECTED_NAME)) {
      return parsedUrl.origin;
    }
  } catch {
    // Ignore invalid or empty tab URLs.
  }

  return null;
}

function rememberProtectedTab(tabId, url) {
  if (typeof tabId !== "number") {
    return;
  }

  const origin = protectedOrigin(url);
  if (!origin) {
    return;
  }

  const state = protectedTabs.get(tabId) || {
    origins: new Set(),
    urls: new Set()
  };

  state.origins.add(origin);
  state.urls.add(url);
  protectedTabs.set(tabId, state);
}

async function removeSiteDataForOrigins(origins) {
  const uniqueOrigins = Array.from(new Set(origins)).filter(Boolean);

  if (!uniqueOrigins.length) {
    return;
  }

  try {
    await chrome.browsingData.remove(
      {
        origins: uniqueOrigins,
        originTypes: {
          unprotectedWeb: true
        }
      },
      {
        appcache: true,
        cache: true,
        cacheStorage: true,
        cookies: true,
        fileSystems: true,
        indexedDB: true,
        localStorage: true,
        serviceWorkers: true,
        webSQL: true
      }
    );
  } catch {
    try {
      await chrome.browsingData.remove(
        {
          origins: uniqueOrigins,
          originTypes: {
            unprotectedWeb: true
          }
        },
        {
          cache: true,
          cacheStorage: true,
          cookies: true
        }
      );
    } catch {
      // Brave/Chrome may already have cleared some data or reject unsupported data types.
    }
  }
}

async function findProtectedHistory() {
  const urls = new Set();
  const origins = new Set();

  try {
    const searchResults = await Promise.all(
      HISTORY_SEARCH_TERMS.map((text) =>
        chrome.history.search({
          text,
          startTime: 0,
          maxResults: 100000
        })
      )
    );

    for (const historyItems of searchResults) {
      for (const item of historyItems) {
        if (isProtectedUrl(item.url || "")) {
          urls.add(item.url);
          origins.add(new URL(item.url).origin);
        }
      }
    }
  } catch {
    // History may be unavailable in some privacy modes.
  }

  return { origins, urls };
}

async function clearProtectedSiteData(state = { origins: new Set(), urls: new Set() }) {
  const originsToClear = new Set(state.origins);
  const urlsToDelete = new Set(state.urls);
  const historyData = await findProtectedHistory();

  for (const origin of historyData.origins) {
    originsToClear.add(origin);
  }

  for (const url of historyData.urls) {
    urlsToDelete.add(url);
  }

  for (const url of urlsToDelete) {
    const origin = protectedOrigin(url);
    if (origin) {
      originsToClear.add(origin);
    }
  }

  await removeSiteDataForOrigins(Array.from(originsToClear));
  await Promise.allSettled(
    Array.from(urlsToDelete).map((url) => chrome.history.deleteUrl({ url }))
  );
}

async function tabIsFromProtectedSite(tabId) {
  if (typeof tabId !== "number" || tabId < 0) {
    return false;
  }

  try {
    const opener = await chrome.tabs.get(tabId);
    rememberProtectedTab(opener.id, opener.pendingUrl || opener.url || "");
    return isProtectedUrl(opener.pendingUrl || opener.url || "");
  } catch {
    return false;
  }
}

chrome.tabs.onCreated.addListener((tab) => {
  rememberProtectedTab(tab.id, tab.pendingUrl || tab.url || "");
});

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  rememberProtectedTab(tabId, changeInfo.url || tab.pendingUrl || tab.url || "");
});

chrome.tabs.onRemoved.addListener((tabId) => {
  const state = protectedTabs.get(tabId);
  if (!state) {
    return;
  }

  protectedTabs.delete(tabId);
  clearProtectedSiteData(state);
});

chrome.history.onVisited.addListener((historyItem) => {
  if (!isProtectedUrl(historyItem.url || "")) {
    return;
  }

  clearProtectedSiteData({
    origins: new Set([protectedOrigin(historyItem.url)]),
    urls: new Set([historyItem.url])
  });
});

chrome.runtime.onInstalled.addListener(() => {
  clearProtectedSiteData();
});

chrome.runtime.onStartup.addListener(() => {
  clearProtectedSiteData();
});

chrome.tabs.onCreated.addListener(async (tab) => {
  if (!(await tabIsFromProtectedSite(tab.openerTabId))) {
    return;
  }

  try {
    await chrome.tabs.remove(tab.id);
  } catch {
    // The tab may already be gone if Brave blocked it first.
  }
});

chrome.webNavigation?.onCreatedNavigationTarget?.addListener(async (details) => {
  if (!(await tabIsFromProtectedSite(details.sourceTabId))) {
    return;
  }

  try {
    await chrome.tabs.remove(details.tabId);
  } catch {
    // The tab may already be closed by the tabs.onCreated safety net.
  }
});
