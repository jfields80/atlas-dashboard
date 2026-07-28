/*
 * PTF-WORKERS-003/006 -- operator capture service worker.
 *
 * Produces exactly one `ptf-official-capture/1.0` JSON file (plus a screenshot)
 * for the official hotel page the operator is currently looking at.
 *
 * WHAT THIS IS FOR
 * IHG, Hilton, Marriott, Red Roof, Best Western and Choice all refuse this
 * project's automated fetchers. A founder opening one of those public pages in
 * their everyday browser is an ordinary visitor, and no access control is
 * touched. This extension carries what that browser already rendered into the
 * committed attestation pipeline.
 *
 * HARD RULES, enforced by construction rather than by comment:
 *   * Runs ONLY on an explicit toolbar click (chrome.action.onClicked). There
 *     is no content script, no automatic injection, and no background polling.
 *   * Makes NO network request of its own. There is no fetch(), no XHR, no
 *     WebSocket, no beacon anywhere in this file. Everything it emits goes to
 *     the operator's own Downloads folder.
 *   * No analytics, no telemetry, no remote logging.
 *   * Collects NO cookies, storage, history, credentials or form data. The
 *     manifest requests none of those permissions, so it could not reach them
 *     even if this code tried.
 *   * No stealth, evasion, proxying, user-agent spoofing or automated
 *     browsing. It reads the page the human already opened, once.
 *   * It NEVER approves, submits or publishes anything. The file it writes is
 *     inert until a human runs `attest-official-page`, and the attestation that
 *     produces begins PENDING and unpublishable.
 */

const SCHEMA = "ptf-official-capture/1.0";
const EXTENSION_VERSION = "1.0.0";

// Keys the ingestion contract refuses outright. Listed here so this file can be
// read as a promise about what it collects, and asserted by test.
const FORBIDDEN_KEYS = [
  "cookies", "cookie", "localstorage", "local_storage", "sessionstorage",
  "session_storage", "headers", "authorization", "token", "tokens",
  "password", "passwords", "formdata", "form_data", "formvalues",
  "history", "credentials", "payment", "autofill",
];

/**
 * Runs INSIDE the page. Returns only what the capture contract needs.
 * Deliberately reads no storage, no cookies and no form values -- it touches
 * document markup and visible text only.
 */
function extractPage() {
  const canonicalEl = document.querySelector('link[rel="canonical"]');

  // JSON-LD is genuinely useful for confirming property identity (name,
  // address, telephone). Parsed defensively: anything unparseable is skipped
  // rather than guessed at, and the ingestion contract's forbidden-key scan is
  // the backstop if a site ever embeds something unexpected.
  const jsonld = [];
  for (const node of document.querySelectorAll('script[type="application/ld+json"]')) {
    try {
      const parsed = JSON.parse(node.textContent);
      if (parsed && typeof parsed === "object") jsonld.push(parsed);
    } catch (_) {
      /* malformed JSON-LD is skipped, never repaired */
    }
  }

  return {
    final_url: document.location.href,
    title: document.title || "",
    canonical_url: canonicalEl ? canonicalEl.href : "",
    html: document.documentElement ? document.documentElement.outerHTML : "",
    text: document.body ? document.body.innerText : "",
    jsonld: jsonld,
  };
}

async function sha256Hex(text) {
  const bytes = new TextEncoder().encode(text);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

/** Depth-first refusal: never emit a payload carrying a forbidden key. */
function findForbiddenKeys(node, path = "") {
  const found = [];
  if (node && typeof node === "object" && !Array.isArray(node)) {
    for (const key of Object.keys(node)) {
      const flat = key.toLowerCase().replace(/[-_]/g, "");
      if (FORBIDDEN_KEYS.some((bad) => flat === bad.replace(/_/g, ""))) {
        found.push(path + key);
      }
      found.push(...findForbiddenKeys(node[key], path + key + "."));
    }
  } else if (Array.isArray(node)) {
    node.forEach((v, i) => found.push(...findForbiddenKeys(v, path + "[" + i + "].")));
  }
  return found;
}

function slugForFilename(url) {
  try {
    const u = new URL(url);
    return (u.hostname + u.pathname).replace(/[^a-zA-Z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "").slice(0, 80).toLowerCase();
  } catch (_) {
    return "capture";
  }
}

function toDataUrl(mime, text) {
  // btoa needs latin-1; encode UTF-8 first so non-ASCII page content survives.
  const utf8 = unescape(encodeURIComponent(text));
  return "data:" + mime + ";base64," + btoa(utf8);
}

async function notify(tabId, message) {
  // Feedback via the badge only -- no page mutation, no injected UI.
  try {
    await chrome.action.setBadgeText({ tabId, text: message.ok ? "OK" : "ERR" });
    await chrome.action.setBadgeBackgroundColor({
      tabId, color: message.ok ? "#1a7f37" : "#b42318",
    });
    await chrome.action.setTitle({ tabId, title: message.title });
  } catch (_) {
    /* badge is cosmetic; never fail a capture over it */
  }
}

chrome.action.onClicked.addListener(async (tab) => {
  if (!tab || !tab.id) return;

  // Only ordinary web pages. Refuses chrome://, file://, extension pages and
  // anything else where "an official hotel page" is not a meaningful claim.
  if (!tab.url || !/^https?:\/\//i.test(tab.url)) {
    await notify(tab.id, { ok: false, title: "Capture refused: not an http(s) page" });
    return;
  }

  try {
    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: extractPage,
    });
    const page = results && results[0] && results[0].result;
    if (!page || !page.html || !page.html.trim()) {
      await notify(tab.id, { ok: false, title: "Capture refused: page had no HTML" });
      return;
    }

    const capture = {
      schema: SCHEMA,
      extension_version: EXTENSION_VERSION,
      captured_at: new Date().toISOString(),
      requested_url: tab.url,
      final_url: page.final_url,
      title: page.title,
      canonical_url: page.canonical_url,
      html: page.html,
      text: page.text,
      jsonld: page.jsonld,
      html_sha256: await sha256Hex(page.html),
      text_sha256: await sha256Hex(page.text),
      capture_note:
        "Captured by a human operator from a public official page. Not evidence " +
        "of approval. Ingestion re-derives all hashes and re-applies every gate.",
    };

    // Fail closed rather than emit something ingestion would reject.
    const forbidden = findForbiddenKeys(capture);
    if (forbidden.length) {
      await notify(tab.id, {
        ok: false, title: "Capture refused: forbidden key " + forbidden[0],
      });
      return;
    }

    const slug = slugForFilename(page.final_url);
    const stamp = capture.captured_at.replace(/[:.]/g, "-");

    // Screenshot of exactly what the operator sees. captureVisibleTab is
    // permitted here by activeTab, granted by the click that started this.
    let shot = null;
    try {
      shot = await chrome.tabs.captureVisibleTab(tab.windowId, { format: "png" });
    } catch (_) {
      shot = null; // a failed screenshot must not lose the capture
    }

    await chrome.downloads.download({
      url: toDataUrl("application/json", JSON.stringify(capture, null, 2)),
      filename: "ptf-capture/" + slug + "-" + stamp + ".json",
      saveAs: false,
    });
    if (shot) {
      await chrome.downloads.download({
        url: shot,
        filename: "ptf-capture/" + slug + "-" + stamp + ".png",
        saveAs: false,
      });
    }

    await notify(tab.id, {
      ok: true,
      title: "Captured" + (shot ? " with screenshot" : " (screenshot unavailable)"),
    });
  } catch (err) {
    await notify(tab.id, { ok: false, title: "Capture failed: " + (err && err.message) });
  }
});
