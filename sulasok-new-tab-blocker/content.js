if (location.hostname.toLowerCase().includes("sulasok")) {
const blockedMethods = new Set(["_blank", "blank", "new", "popup"]);

function sameWindowTarget(target) {
  if (!target) {
    return true;
  }

  return !blockedMethods.has(String(target).trim().toLowerCase().replace(/^_/, ""));
}

function normalizeAnchor(anchor) {
  if (anchor.target && !sameWindowTarget(anchor.target)) {
    anchor.target = "_self";
  }

  if (anchor.rel && anchor.rel.includes("noopener")) {
    anchor.rel = anchor.rel
      .split(/\s+/)
      .filter((part) => part && part !== "noopener" && part !== "noreferrer")
      .join(" ");
  }
}

function normalizeForm(form) {
  if (form.target && !sameWindowTarget(form.target)) {
    form.target = "_self";
  }
}

function normalizeExistingElements(root = document) {
  root.querySelectorAll?.("a[target], area[target]").forEach(normalizeAnchor);
  root.querySelectorAll?.("form[target]").forEach(normalizeForm);
}

window.open = function blockNewWindow() {
  return null;
};

document.addEventListener(
  "click",
  (event) => {
    const link = event.target?.closest?.("a[href], area[href]");
    if (!link || sameWindowTarget(link.target)) {
      return;
    }

    event.preventDefault();
    event.stopImmediatePropagation();
    window.location.assign(link.href);
  },
  true
);

document.addEventListener(
  "submit",
  (event) => {
    const form = event.target;
    if (!form || sameWindowTarget(form.target)) {
      return;
    }

    form.target = "_self";
  },
  true
);

new MutationObserver((mutations) => {
  for (const mutation of mutations) {
    if (mutation.type === "attributes") {
      if (mutation.target.matches?.("a[target], area[target]")) {
        normalizeAnchor(mutation.target);
      } else if (mutation.target.matches?.("form[target]")) {
        normalizeForm(mutation.target);
      }
      continue;
    }

    for (const node of mutation.addedNodes) {
      if (node.nodeType === Node.ELEMENT_NODE) {
        normalizeExistingElements(node);
      }
    }
  }
}).observe(document.documentElement, {
  childList: true,
  subtree: true,
  attributes: true,
  attributeFilter: ["target", "rel"]
});

normalizeExistingElements();
}
