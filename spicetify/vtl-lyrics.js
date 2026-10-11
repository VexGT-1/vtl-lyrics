// VTL Lyrics - Spicetify extension
// Replaces the content of Spotify's own native Lyrics tab with VTL-hosted,
// word-timed lyrics (api.vexqyq.com/lyrics/<trackId>) whenever VTL has them
// for the playing track. Falls back to doing nothing (Spotify's own lyrics
// stay untouched) when VTL has no lyrics for that track.
//
// There's no official plugin point for a lyrics source on desktop - this
// finds the real Lyrics panel in the DOM and swaps its contents in place.
// Spotify's internal class/data-testid names change between client
// versions and are not documented, so SELECTORS below is a list of every
// known one; if the panel stops being found after a Spotify update, that's
// the first thing to check (open devtools in the client - Spicetify has a
// built-in "Show Devtools" option in its right-click menu - and inspect
// the Lyrics tab to find the current container's selector).
(function VTLLyrics() {
  if (typeof Spicetify === "undefined" || !Spicetify.Player || !Spicetify.Player.data || !Spicetify.showNotification) {
    setTimeout(VTLLyrics, 300);
    return;
  }

  const API = "https://api.vexqyq.com";
  const SELECTORS = [
    '[data-testid="lyrics-lyrics-contentContainer"]',
    '[data-testid="fullscreen-lyrics-container"]',
    '[data-testid="lyrics-container"]',
    ".main-nowPlayingView-lyrics",
  ];

  let currentTrackId = null;
  let lines = [];          // [{start, end, words: [{text, start, end}]}]
  let hasVtlLyrics = false;
  let pollId = null;
  let injectedRoot = null; // the VTL container currently standing in for Spotify's own
  let overlay = null;      // our own floating panel, used when Spotify's Lyrics tab can't be found
  let overlayOpen = false;

  const style = document.createElement("style");
  style.textContent = `
    #vtl-lyrics-root { padding: 24px; overflow-y: auto; height: 100%; }
    .vtl-line { color: rgba(255,255,255,.4); font-size: 16px; font-weight: 700; line-height: 1.5;
      margin-bottom: 14px; transition: color .25s, transform .25s; transform-origin: left center; }
    .vtl-line.vtl-active { color: #fff; transform: scale(1.03); }
    .vtl-word { transition: color .15s; }
    .vtl-line.vtl-active .vtl-word.vtl-sung { color: #c8ff2f; }
    #vtl-lyrics-badge { font-family: monospace; font-size: 10px; letter-spacing: .12em;
      text-transform: uppercase; color: #c8ff2f; opacity: .6; margin-bottom: 16px; }
  `;
  document.head.appendChild(style);

  function parseTTML(xmlText) {
    const doc = new DOMParser().parseFromString(xmlText, "text/xml");
    const ps = Array.from(doc.getElementsByTagName("p"));
    return ps.map((p) => {
      const spans = Array.from(p.getElementsByTagName("span"));
      const words = spans.map((s) => ({
        text: s.textContent,
        start: parseTime(s.getAttribute("begin")),
        end: parseTime(s.getAttribute("end")),
      }));
      return {
        start: parseTime(p.getAttribute("begin")),
        end: parseTime(p.getAttribute("end")),
        words,
      };
    });
  }

  function parseTime(t) {
    if (!t) return 0;
    const parts = t.split(":");
    if (parts.length === 2) return parseInt(parts[0], 10) * 60 + parseFloat(parts[1]);
    return parseFloat(parts[0]);
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  // Floating panel on the right. Works no matter what Spotify names its own Lyrics tab,
  // opened/closed with the "VTL" button in the top bar (or Ctrl+Shift+L).
  function toggleOverlay() {
    overlayOpen = !overlayOpen;
    if (!overlay) {
      overlay = document.createElement("div");
      overlay.id = "vtl-lyrics-overlay";
      overlay.style.cssText = "position:fixed;top:64px;right:12px;bottom:100px;width:380px;z-index:99999;" +
        "background:rgba(10,10,12,.96);border:1px solid rgba(200,255,47,.35);border-radius:12px;overflow:hidden;display:none;";
      document.body.appendChild(overlay);
    }
    overlay.style.display = overlayOpen ? "block" : "none";
    if (overlayOpen) injectInto(overlay); else injectedRoot = null;
  }

  function findLyricsContainer() {
    for (const sel of SELECTORS) {
      const el = document.querySelector(sel);
      if (el) return el;
    }
    return null;
  }

  // Swap the native panel's content for ours. The original children are
  // stashed on the element so they can be put back if VTL has nothing for
  // the next track (rather than permanently destroying Spotify's own view).
  function injectInto(container) {
    if (!container._vtlOriginal) {
      container._vtlOriginal = Array.from(container.childNodes);
    }
    container.innerHTML = "";
    const root = document.createElement("div");
    root.id = "vtl-lyrics-root";
    container.appendChild(root);
    injectedRoot = root;
    render();
  }

  function restoreNative(container) {
    if (!container || !container._vtlOriginal) return;
    container.innerHTML = "";
    container._vtlOriginal.forEach((n) => container.appendChild(n));
    container._vtlOriginal = null;
    injectedRoot = null;
  }

  function render() {
    if (!injectedRoot) return;
    if (!lines.length) {
      injectedRoot.innerHTML = '<div id="vtl-lyrics-badge">VTL LYRICS</div><div style="color:rgba(255,255,255,.4)">No VTL lyrics for this track.</div>';
      return;
    }
    injectedRoot.innerHTML = '<div id="vtl-lyrics-badge">VTL LYRICS</div>' + lines.map((l, i) =>
      `<div class="vtl-line" data-i="${i}">` +
      l.words.map((w, j) => `<span class="vtl-word" data-i="${i}" data-j="${j}">${escapeHtml(w.text)}</span>`).join(" ") +
      `</div>`
    ).join("");
  }

  function updateHighlight() {
    if (!injectedRoot || !lines.length) return;
    const t = Spicetify.Player.getProgress() / 1000;
    let activeLineIdx = -1;
    for (let i = 0; i < lines.length; i++) {
      if (t >= lines[i].start && t <= lines[i].end) { activeLineIdx = i; break; }
    }
    injectedRoot.querySelectorAll(".vtl-line").forEach((el, i) => {
      const active = i === activeLineIdx;
      el.classList.toggle("vtl-active", active);
      if (active) {
        el.scrollIntoView({ block: "center", behavior: "smooth" });
        const words = lines[i].words;
        el.querySelectorAll(".vtl-word").forEach((w, j) => {
          w.classList.toggle("vtl-sung", t >= words[j].start);
        });
      }
    });
  }

  async function loadLyricsFor(trackId) {
    lines = [];
    hasVtlLyrics = false;
    try {
      const res = await fetch(`${API}/lyrics/${trackId}`);
      if (!res.ok) return;
      const xml = await res.text();
      lines = parseTTML(xml);
      hasVtlLyrics = lines.length > 0;
    } catch (e) {
      // no VTL lyrics for this track, or a network hiccup
    }
    applyToPanel();
  }

  function applyToPanel() {
    const container = findLyricsContainer() || (overlayOpen ? overlay : null);
    if (!container) return; // Lyrics tab isn't open right now
    if (hasVtlLyrics) { if (!injectedRoot || !injectedRoot.isConnected) injectInto(container); else render(); }
    else restoreNative(container);
  }

  function onSongChange() {
    const uri = Spicetify.Player.data && Spicetify.Player.data.item && Spicetify.Player.data.item.uri;
    const m = uri && uri.match(/^spotify:track:([A-Za-z0-9]+)$/);
    const trackId = m ? m[1] : null;
    if (trackId === currentTrackId) return;
    currentTrackId = trackId;
    if (trackId) loadLyricsFor(trackId);
    else { lines = []; hasVtlLyrics = false; applyToPanel(); }
  }

  // The Lyrics tab mounts/unmounts its container as the user switches tabs,
  // so re-apply whenever the DOM changes rather than only on song change.
  const observer = new MutationObserver(() => {
    if (hasVtlLyrics && (!injectedRoot || !injectedRoot.isConnected)) { injectedRoot = null; applyToPanel(); }
  });
  observer.observe(document.body, { childList: true, subtree: true });

  Spicetify.Player.addEventListener("songchange", onSongChange);
  try {
    if (Spicetify.Topbar && Spicetify.Topbar.Button) new Spicetify.Topbar.Button("VTL Lyrics", "lyrics", toggleOverlay);
  } catch (e) {}
  document.addEventListener("keydown", (e) => { if (e.ctrlKey && e.shiftKey && e.code === "KeyL") toggleOverlay(); });
  Spicetify.showNotification("VTL Lyrics loaded. Click VTL in the top bar or press Ctrl+Shift+L.");
  onSongChange();

  if (pollId) clearInterval(pollId);
  pollId = setInterval(updateHighlight, 150);
})();
