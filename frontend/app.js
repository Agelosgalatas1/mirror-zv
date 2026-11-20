/* Επεξήγηση: Χειρίζεται οθόνες, συνομιλίες και ήχο· γνώση, δικαιώματα και κληρονομικότητα αποφασίζονται στον server. */
/* MIRROR — chat with the AI counterpart of a colleague. Everything behind the
   conversation (knowledge, inheritance, approvals, learning) stays on the server. */
"use strict";

/* ---------- tiny DOM toolkit (all server data is inserted as text) ---------- */
const SVGNS = "http://www.w3.org/2000/svg";
function h(tag, props, ...kids) { const el = document.createElement(tag); setProps(el, props); return add(el, kids); }
function s(tag, props, ...kids) { const el = document.createElementNS(SVGNS, tag); for (const [k, v] of Object.entries(props || {})) if (v != null) el.setAttribute(k, v); return add(el, kids); }
function setProps(el, props) {
  for (const [k, v] of Object.entries(props || {})) {
    if (v == null || v === false) continue;
    if (k === "class") el.className = v;
    else if (k === "style") for (const [p, val] of Object.entries(v)) el.style.setProperty(p, val);
    else if (k.startsWith("on")) el.addEventListener(k.slice(2).toLowerCase(), v);
    else if (k === "value") el.value = v;
    else el.setAttribute(k, v === true ? "" : v);
  }
}
function add(el, kids) { for (const kid of [kids].flat(Infinity)) { if (kid == null || kid === false || kid === true) continue; el.appendChild(kid instanceof Node ? kid : document.createTextNode(String(kid))); } return el; }
function fill(el, ...kids) { el.replaceChildren(); return add(el, kids); }
const $ = (sel, root = document) => root.querySelector(sel);
const icon = (paths, size = 18) => s("svg", { viewBox: "0 0 24 24", width: size, height: size, fill: "none", stroke: "currentColor", "stroke-width": "1.9", "stroke-linecap": "round", "stroke-linejoin": "round", "aria-hidden": "true" }, ...paths.map(d => s("path", { d })));
const I = {
  send: ["M5 12h14", "M13 6l6 6-6 6"], menu: ["M4 7h16M4 12h16M4 17h16"], close: ["M6 6l12 12M18 6 6 18"],
  trash: ["M5 7h14", "M10 11v6M14 11v6", "M6 7l1 13h10l1-13", "M9 7V4h6v3"], edit: ["M4 20h4L19 9l-4-4L4 16z", "M13 7l4 4"], search: ["M11 4a7 7 0 1 1 0 14 7 7 0 0 1 0-14z", "M20 20l-4-4"], copy: ["M9 9h11v11H9z", "M5 15V4h11"],
  up: ["M7 11v9H4v-9z", "M7 11l4-7a2 2 0 0 1 3 2l-1 4h5a2 2 0 0 1 2 2.3l-1.2 6A2 2 0 0 1 16.8 20H7"],
  down: ["M17 13V4h3v9z", "M17 13l-4 7a2 2 0 0 1-3-2l1-4H6a2 2 0 0 1-2-2.3l1.2-6A2 2 0 0 1 7.2 4H17"],
  back: ["M15 6l-6 6 6 6"], lock: ["M6 11h12v9H6z", "M8 11V8a4 4 0 0 1 8 0v3"], chat: ["M4 5h16v11H9l-5 4z"],
  mic: ["M12 3a3 3 0 0 1 3 3v6a3 3 0 0 1-6 0V6a3 3 0 0 1 3-3z", "M5 11a7 7 0 0 0 14 0", "M12 18v3"], stop: ["M7 7h10v10H7z"],
  speaker: ["M4 9h4l5-4v14l-5-4H4z", "M16 9a4 4 0 0 1 0 6", "M18.5 6.5a8 8 0 0 1 0 11"], face: ["M12 3a9 9 0 1 1 0 18 9 9 0 0 1 0-18z", "M9 10h.01M15 10h.01", "M8.5 14.5a5 5 0 0 0 7 0"],
  moon: ["M20 14A8 8 0 1 1 10 4a6.5 6.5 0 0 0 10 10z"], out: ["M15 4h4v16h-4", "M10 8l-4 4 4 4", "M6 12h11"], dots: ["M5 12h.01M12 12h.01M19 12h.01"],
};
let logoSeq = 0;
function logo(size = 40, label) {
  const id = "lg" + (++logoSeq);
  return s("svg", { class: "logo", viewBox: "0 0 64 64", width: size, height: size, role: label ? "img" : null, "aria-label": label || null, "aria-hidden": label ? null : "true" },
    s("defs", {},
      s("linearGradient", { id: id + "m", x1: 0, y1: 0, x2: 1, y2: 1 }, s("stop", { offset: 0, "stop-color": "#c7b3ff" }), s("stop", { offset: 1, "stop-color": "#5ee6c5" })),
      s("linearGradient", { id: id + "r", x1: 0, y1: 0, x2: 0, y2: 1 }, s("stop", { offset: 0, "stop-color": "#5ee6c5", "stop-opacity": ".55" }), s("stop", { offset: 1, "stop-color": "#5ee6c5", "stop-opacity": "0" })),
      s("linearGradient", { id: id + "e", x1: 0, y1: 0, x2: 1, y2: 1 }, s("stop", { offset: 0, "stop-color": "#c7b3ff", "stop-opacity": ".55" }), s("stop", { offset: 1, "stop-color": "#5ee6c5", "stop-opacity": ".25" }))),
    s("rect", { x: 1, y: 1, width: 62, height: 62, rx: 17, fill: "#0b0d16", stroke: `url(#${id}e)`, "stroke-width": "1.5" }),
    s("path", { d: "M14 40 L23 18 L32 31 L41 18 L50 40", fill: "none", stroke: `url(#${id}m)`, "stroke-width": 5, "stroke-linecap": "round", "stroke-linejoin": "round" }),
    s("path", { d: "M11 45.5 H53", stroke: "#fff", "stroke-opacity": ".28", "stroke-width": "1.4", "stroke-linecap": "round" }),
    s("path", { class: "logo-r", d: "M14 48.5 L23 56 L32 51.5 L41 56 L50 48.5", fill: "none", stroke: `url(#${id}r)`, "stroke-width": 3, "stroke-linecap": "round", "stroke-linejoin": "round" }));
}
const wordmark = () => h("div", { class: "brand", "aria-label": "MIRROR" }, logo(34), h("span", { class: "word" }, "MIR", h("span", {}, "ROR")));
const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;

/* ---------- state & API ---------- */
const CHANNELS = [["chat_team", "Chat ομάδας"], ["chat_personal", "Προσωπικό chat"], ["email_internal", "Email (εσωτερικό)"], ["email_external", "Email (πελάτης/συνεργάτης)"]];
const state = { channel: (() => { try { return localStorage.getItem("mirror-channel") || "chat_team"; } catch { return "chat_team"; } })(), session: null, view: "home", people: [], hierarchyError: false, mirror: null, thread: null, threads: [], messages: [], busy: false, offline: false, voiceTurn: null, looks: {}, rec: null, mode: "text", threadQuery: "", audio: null, micPending: false, transcribing: false, submitAfterTranscript: false, voiceOpen: false, voiceContinuous: false };
const store = (k, v) => { try { v == null ? localStorage.removeItem(k) : localStorage.setItem(k, v); } catch { /* storage unavailable */ } };
const load = k => { try { return localStorage.getItem(k); } catch { return null; } };
// One abort scope per visible conversation. Backend work may finish after abort;
// only results belonging to the current session and view may update the browser.
let conversationController = new AbortController();
let avatarRequest = 0, recordingRequest = 0, playbackRequest = 0;
let overlayCloser = null;
const conversationContext = () => ({ signal: conversationController.signal, session: state.session, mirror: state.mirror?.id });
const currentContext = ctx => !ctx.signal.aborted && ctx.session === state.session && ctx.mirror === state.mirror?.id;
// Επεξήγηση: Ακυρώνει παλιά αιτήματα και σταματά μικρόφωνο και ήχο κατά την αλλαγή συζήτησης.
function invalidateConversation() {
  dismissOverlay();
  conversationController.abort(); conversationController = new AbortController();
  avatarRequest++; state.busy = false; state.voiceTurn = null; clearAvatarFallback();
  stopRecord(true); stopVoice();
  const composer = $("#composer"); if (composer) { composer.value = ""; autosize(composer); }
  voiceHint();
  state.voiceOpen = false; $("#voice-dialog")?.close();
  const frame = $("#avatar-frame"); if (frame) frame.src = "about:blank";
}
function clearSession() {
  invalidateConversation();
  Object.assign(state, { session: null, view: "home", people: [], hierarchyError: false, mirror: null, thread: null, threads: [], messages: [], looks: {}, offline: false, mode: "text" });
  const overlay = $("#overlay"); if (overlay) { overlay.classList.remove("on"); fill(overlay); }
  location.hash = ""; render();
}
function withdrawMirror(mid) {
  if (!state.session) return;
  state.session.mirrors = state.session.mirrors.filter(m => m.id !== mid);
  state.people = state.people.map(p => p.mirror_id === mid ? { ...p, can_chat: false } : p);
  delete state.looks[mid];
  if (state.mirror?.id !== mid) { paintSidebar(); return; }
  invalidateConversation();
  Object.assign(state, { view: "home", mirror: state.session.mirrors[0] || null, thread: null, threads: [], messages: [] });
  const overlay = $("#overlay"); if (overlay) { overlay.classList.remove("on"); fill(overlay); }
  location.hash = "#/"; render();
  toast("Η πρόσβαση σε αυτό το Mirror δεν είναι πλέον διαθέσιμη.", true);
}
// Επεξήγηση: Κοινή επικοινωνία με το API, με συνεδρία χρήστη και χειρισμό σφαλμάτων.
async function api(path, body, ctx) {
  const initiatingSession = state.session;
  const opts = { credentials: "same-origin", headers: {}, signal: ctx?.signal };
  if (body !== undefined) { opts.method = "POST"; opts.headers = { "Content-Type": "application/json", "X-Mirror-Request": "1" }; opts.body = JSON.stringify(body); }
  let res;
  try { res = await fetch(path, opts); } catch (error) { if (error.name === "AbortError") throw error; throw Object.assign(new Error("Δεν υπάρχει σύνδεση. Δοκίμασε ξανά σε λίγο."), { status: 0 }); }
  let data = null; try { data = await res.json(); } catch { /* empty */ }
  if (ctx && !currentContext(ctx)) throw new DOMException("Conversation changed", "AbortError");
  if (res.status === 401 && initiatingSession && state.session === initiatingSession && path !== "/api/logout") { clearSession(); toast("Η σύνδεση έληξε. Μπες ξανά.", true); }
  if (res.status === 403 && data?.code === "mirror_access" && state.session === initiatingSession) withdrawMirror(data.mirror_id);
  if (!res.ok) throw Object.assign(new Error(friendly(res.status, data)), { status: res.status, code: data?.code });
  return data;
}
function friendly(status, data) {
  if (data?.code === "provider") return "Το AI δεν είναι διαθέσιμο αυτή τη στιγμή. Δοκίμασε ξανά σε λίγο.";
  if (status === 403) return "Δεν έχεις πρόσβαση σε αυτό.";
  if (status >= 500) return "Κάτι πήγε στραβά. Δοκίμασε ξανά.";
  return data?.error || "Κάτι πήγε στραβά.";
}
function toast(text, bad = false) { const t = h("div", { class: "toast" + (bad ? " bad" : ""), role: "status" }, text); $("#toasts").appendChild(t); setTimeout(() => t.remove(), 3200); }

/* ---------- helpers ---------- */
const COLORS = { executive: "var(--violet)", sales: "var(--teal)", finance: "var(--amber)" };
const initials = n => (n || "?").split(/\s+/).slice(0, 2).map(w => w[0]).join("").toUpperCase();
const first = n => (n || "").split(/\s+/)[0];
const avatar = (p, cls = "", online = false) => h("div", { class: "av " + cls, style: { "--c": COLORS[(p?.department || "").toLowerCase()] || "var(--accent)" } }, initials(p?.name), online ? h("i", { class: "on" }) : null);
const personFor = mirror => state.people.find(p => p.mirror_id === mirror.id) || { id: mirror.id, name: mirror.title, job_title: "", department: mirror.id };
const threadKey = () => `mirror-thread:${state.session.user.username}:${state.mirror.id}`;
const when = v => { const d = new Date(v), now = new Date(); return d.toDateString() === now.toDateString() ? d.toLocaleTimeString("el-GR", { hour: "2-digit", minute: "2-digit" }) : d.toLocaleDateString("el-GR", { day: "numeric", month: "short" }); };

/* ---------- login ---------- */
function loginView() {
  const err = h("div", { class: "err", role: "alert" });
  const user = h("input", { class: "input", id: "u", autocomplete: "username", maxlength: "80", required: true });
  const pass = h("input", { class: "input", id: "p", type: "password", autocomplete: "current-password", maxlength: "256", required: true });
  const btn = h("button", { class: "btn primary", type: "submit" }, "Σύνδεση");
  setTimeout(() => {
    if (user.isConnected && [document.body, $("#root")].includes(document.activeElement)) user.focus();
  }, 30);
  return h("main", { class: "login" }, h("div", { class: "login-card" },
    logo(78, "MIRROR"), h("h1", {}, "MIR", h("span", {}, "ROR")),
    h("form", { class: "login-form", onsubmit: async e => {
      e.preventDefault(); err.textContent = ""; btn.disabled = true; btn.textContent = "Σύνδεση…";
      try { state.session = await api("/api/login", { username: user.value, password: pass.value }); await start(true); }
      catch (error) { err.textContent = error.status === 401 ? "Λάθος στοιχεία ή προσωρινό κλείδωμα." : error.message; btn.disabled = false; btn.textContent = "Σύνδεση"; pass.select(); }
    } },
      h("div", { class: "field" }, h("label", { for: "u" }, "Όνομα χρήστη"), user),
      h("div", { class: "field" }, h("label", { for: "p" }, "Κωδικός"), pass), err, btn),
    h("p", { class: "hint" }, "Demo (NexaTech): ceo / ceo2026 · sales_manager / sales2026 · finance_manager / finance2026 · sales_employee, finance_employee / employee2026")));
}

/* ---------- conversation flow ---------- */
async function start(enterChat = false) {
  const session = state.session;
  if (!session || !await loadHierarchy(session)) return;
  state.mirror = session.mirrors[0] || null;
  const [, view, mid] = location.hash.split("/");
  const target = view === "chat" ? session.mirrors.find(m => m.id === mid) : enterChat ? session.mirrors[0] : null;
  state.view = target ? "chat" : "home";
  render();
  if (target) await openMirror(target, true);
  else if (view === "chat") unavailableChat();
}
async function loadHierarchy(session) {
  let people = [], failed = false;
  try { people = await api("/api/hierarchy"); } catch { failed = true; }
  // A 401 or logout can replace the entire session while the request is in flight.
  if (state.session !== session) return false;
  state.people = people; state.hierarchyError = failed;
  return true;
}
async function retryHierarchy(button) {
  const session = state.session;
  if (!session) return;
  button.disabled = true; button.textContent = "Φόρτωση…";
  if (!await loadHierarchy(session)) return;
  paintSidebar();
  if (state.view === "home") paintMain(); else paintHead();
}
/* The address names a Mirror this user cannot chat with: never keep
   showing a different conversation under that address; return to the team and say why. */
function unavailableChat() {
  goHome();
  toast("Δεν έχεις πρόσβαση σε αυτό το AI.", true);
}
function goHome() { invalidateConversation(); state.view = "home"; location.hash = "#/"; closeNav(); paintMain(); paintSidebar(); }
window.addEventListener("hashchange", () => {
  if (!state.session) return;
  const [, view, mid] = location.hash.split("/");
  if (view === "chat") {
    const m = state.session.mirrors.find(x => x.id === mid);
    if (!m) { unavailableChat(); return; }
    if (state.view !== "chat" || state.mirror?.id !== m.id) openMirror(m);
  }
  else if (state.view !== "home") goHome();
});
// Επεξήγηση: Ανοίγει μόνο Mirror που επέστρεψε ως διαθέσιμο ο server.
async function openMirror(mirror, initial = false) {
  const switching = state.mirror?.id !== mirror.id || state.view !== "chat";
  if (!switching && !initial) { closeNav(); return; }
  invalidateConversation();
  state.mirror = mirror; state.view = "chat";
  if (location.hash !== "#/chat/" + mirror.id) location.hash = "#/chat/" + mirror.id;
  state.thread = null; state.messages = [{ role: "loading" }]; state.threads = []; state.busy = true;
  state.suggestions = [];
  const ctx = conversationContext();
  closeNav(); paintMain(); paintSidebar();
  loadSuggestions(ctx);
  try {
    state.threads = await api(`/api/mirrors/${mirror.id}/conversations`, undefined, ctx);
    const saved = load(threadKey());
    const target = state.threads.find(t => String(t.conversation_id) === saved);
    if (target && initial) await openThread(target.conversation_id);
    else paintSidebar();
  } catch (error) { if (currentContext(ctx)) toast(error.message, true); }
  finally {
    if (currentContext(ctx)) { state.busy = false; state.messages = []; paintChat(); }
  }
}
async function loadSuggestions(ctx) {
  if (!ctx.mirror) return;
  try {
    const { questions } = await api("/api/mirrors/" + ctx.mirror + "/suggestions", undefined, ctx);
    if (!currentContext(ctx)) return;
    state.suggestions = questions;
    if (state.messages.length === 0) paintChat();
  } catch {
    // The composer remains usable when suggestions are unavailable.
  }
}
async function openThread(id) {
  invalidateConversation();
  if (state.view !== "chat") { state.view = "chat"; location.hash = "#/chat/" + state.mirror.id; paintMain(); }
  state.thread = String(id); store(threadKey(), state.thread); closeNav();
  const ctx = conversationContext();
  state.busy = true; state.messages = [{ role: "loading" }]; paintChat(); paintSidebar(); loadAvatar();
  try {
    const turns = await api(`/api/mirrors/${ctx.mirror}/conversations/${state.thread}`, undefined, ctx);
    state.messages = turns.flatMap(t => [{ role: "user", text: t.question }, { role: "ai", text: t.answer, explain: t.explain, voiceTurn: t.voice_turn_id || null }]);
  } catch (error) {
    if (!currentContext(ctx)) return;
    state.messages = []; state.thread = null; store(threadKey(), null); toast(error.message, true);
  } finally {
    if (currentContext(ctx)) { state.busy = false; paintChat(); }
  }
}
function newChat() {
  invalidateConversation();
  if (state.view !== "chat" && state.mirror) { state.view = "chat"; location.hash = "#/chat/" + state.mirror.id; paintMain(); }
  state.thread = null; state.messages = []; state.suggestions = [];
  store(threadKey(), null); closeNav(); paintChat(); paintSidebar(); loadAvatar(); $("#composer")?.focus();
  loadSuggestions(conversationContext());
}
// Επεξήγηση: Το Κείμενο ζητά γραπτή απάντηση, ενώ Φωνή και Avatar ενεργοποιούν την ηχητική διαδρομή.
async function send(text) {
  // Send is also the finish button for dictation. Lock the hand-off before any
  // await so a second click cannot create another turn or send an old draft.
  if (state.rec) return stopRecord(false, true);
  if (state.transcribing) { state.submitAfterTranscript = true; paintVoiceControls(); return; }
  if (state.micPending) return;
  const box = $("#composer");
  const question = (text ?? box?.value ?? "").trim();
  if (!question || state.busy || !state.session || !state.mirror || !box) return;
  const ctx = conversationContext();
  box.value = ""; autosize(box);
  const responseMode = mode(), voiceTurn = state.voiceTurn, fromVoiceDialog = state.voiceOpen; state.voiceTurn = null; voiceHint();
  state.busy = true; state.messages.push({ role: "user", text: question, voice: !!voiceTurn }, { role: "typing" }); paintChat();
  try {
    if (voiceTurn) {
      const r = await api(`/api/voice/${voiceTurn}/confirm`, { text: question, channel: state.channel }, ctx);
      state.messages.splice(-1, 1, { role: "ai", text: r.answer, fresh: true, explain: r.explain, voiceTurn: r.has_audio ? voiceTurn : null }); state.offline = false;
      const vt = state.threads.find(x => String(x.conversation_id) === String(r.conversation_id ?? state.thread));
      if (vt) { vt.updated_at = new Date().toISOString(); vt.last_question = question; vt.last_answer = r.answer; vt.turns = (Number(vt.turns) || 0) + 1; state.threads = [vt, ...state.threads.filter(x => x !== vt)]; }
      if (r.has_audio) { if (!fromVoiceDialog || (state.voiceOpen && state.voiceContinuous)) loadAvatar(voiceTurn); } else { state.voiceContinuous = false; toast("Η απάντηση είναι έτοιμη· η φωνή δεν ήταν διαθέσιμη αυτή τη φορά."); }
    } else {
      if (!state.thread) {
        const t = await api(`/api/mirrors/${ctx.mirror}/conversations`, { title: question.slice(0, 60) }, ctx);
        state.thread = String(t.conversation_id); store(threadKey(), state.thread); state.threads.unshift(t);
      }
      const spoken = responseMode !== "text";
      const endpoint = spoken ? `/api/mirrors/${ctx.mirror}/spoken-ask` : `/api/mirrors/${ctx.mirror}/ask`;
      const r = await api(endpoint, { question, conversation_id: state.thread, channel: state.channel }, ctx);
      state.messages.splice(-1, 1, { role: "ai", text: r.answer, fresh: true, explain: r.explain, voiceTurn: r.has_audio ? r.turn_id : null }); state.offline = false;
      if (r.has_audio && mode() === responseMode) loadAvatar(r.turn_id);
      else if (spoken && !r.has_audio) toast("Η απάντηση είναι έτοιμη. Η φωνή δεν ήταν διαθέσιμη αυτή τη φορά.");
      const t = state.threads.find(x => String(x.conversation_id) === state.thread);
      if (t) { t.updated_at = new Date().toISOString(); t.last_question = question; t.last_answer = r.answer; t.turns = (Number(t.turns) || 0) + 1; state.threads = [t, ...state.threads.filter(x => x !== t)]; }
    }
  } catch (error) {
    if (!currentContext(ctx)) return;
    state.voiceContinuous = false; state.messages.splice(-1, 1, { role: "note", text: error.message });
    if (error.code === "provider") state.offline = true;
  } finally {
    if (currentContext(ctx)) { state.busy = false; paintChat(); paintSidebar(); paintStatus(); if (box.isConnected && !state.voiceOpen) box.focus(); }
  }
}

/* ---------- rendering ---------- */
function render() {
  const root = $("#root");
  if (!state.session) { fill(root, loginView()); return; }
  const u = state.session.user;
  const menu = h("div", { class: "menu", role: "menu" },
    h("button", { role: "menuitem", onclick: toggleTheme }, icon(I.moon, 16), "Αλλαγή θέματος"),
    h("button", { role: "menuitem", onclick: logout }, icon(I.out, 16), "Αποσύνδεση"));
  fill(root, h("div", { class: "app", id: "app" },
    h("aside", { class: "sidebar", "aria-label": "Συζητήσεις" },
      h("div", { class: "top" }, wordmark(), h("button", { class: "iconbtn mobile-close", "aria-label": "Κλείσιμο μενού", onclick: closeNav }, icon(I.close))),
      h("div", { class: "section" }, h("div", { class: "label" }, "Μίλα με"), h("div", { id: "people" })),
      h("div", { class: "label", style: { margin: "14px 18px 6px" } }, "Πρόσφατες"),
      h("label", { class: "thread-search" }, icon(I.search, 15),
        h("input", { id: "thread-search", type: "search", placeholder: "Αναζήτηση συζητήσεων", "aria-label": "Αναζήτηση συζητήσεων", maxlength: "80",
          value: state.threadQuery, oninput: e => { state.threadQuery = e.target.value; paintThreads(); } })),
      h("nav", { class: "threads", id: "threads" }),
      h("div", { class: "me-wrap" }, menu,
        h("button", { class: "me", "aria-haspopup": "menu", onclick: e => { e.stopPropagation(); menu.classList.toggle("on"); } },
          avatar(u), h("span", { class: "who" }, u.name, h("small", {}, u.job_title)), icon(I.dots, 16)))),
    h("div", { class: "scrim", onclick: closeNav }),
    h("main", { class: "main-area", id: "main" })));
  paintSidebar(); paintMain();
}
// Επεξήγηση: Χτίζει τη συνομιλία, το πεδίο μηνύματος και τα προαιρετικά χειριστήρια ήχου.
function paintMain() {
  const main = $("#main"); if (!main) return;
  if (state.view === "home") { fill(main, homeView()); return; }
  fill(main, h("div", { class: "chat-shell", id: "chat-shell" }, h("div", { class: "chat" },
    h("header", { class: "chat-head", id: "head" }),
    h("div", { class: "scroll", id: "scroll", onscroll: e => { const el = e.target; $("#to-bottom")?.classList.toggle("on", el.scrollHeight - el.clientHeight - el.scrollTop > 240); } },
      h("div", { class: "thread-view", id: "messages", role: "log", "aria-live": "polite" })),
    h("button", { class: "to-bottom", id: "to-bottom", type: "button", "aria-label": "Στα νεότερα μηνύματα", title: "Στα νεότερα μηνύματα",
      onclick: () => { const sc = $("#scroll"); sc.scrollTop = sc.scrollHeight; } }, icon(["M12 5v14", "M6 13l6 6 6-6"], 18)),
    h("div", { class: "composer" },
      h("div", { class: "followups", id: "followups", role: "group", "aria-label": "Γρήγορες συνέχειες" }),
      h("div", { class: "voice-hint", id: "voice-hint", hidden: true, role: "status" }),
      h("form", { class: "composer-box", onsubmit: e => { e.preventDefault(); send(); } },
        h("textarea", { id: "composer", rows: "1", maxlength: "4000", "aria-label": "Μήνυμα", placeholder: "Γράψε ένα μήνυμα…",
          oninput: e => { autosize(e.target); paintCount(); if (!e.target.value.trim() && state.voiceTurn) { state.voiceTurn = null; voiceHint(); } },
          onkeydown: e => {
            if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); send(); }
            else if (e.key === "ArrowUp" && !e.target.value) { const q = [...state.messages].reverse().find(m => m.role === "user"); if (q) { e.preventDefault(); e.target.value = q.text; autosize(e.target); paintCount(); } }
          } }),
        h("button", { class: "mic", id: "mic", type: "button", "aria-label": "Μίλησε (έως 30 δευτερόλεπτα)", title: "Υπαγόρευση με φωνή", onclick: toggleRecord }, icon(I.mic)),
        h("button", { class: "send", type: "submit", "aria-label": "Αποστολή", title: "Αποστολή (Enter)" }, icon(I.send))),
      h("div", { class: "composer-foot" },
        h("label", { class: "style-pick", title: "Σε ποιο ύφος να απαντήσει το AI" }, "Ύφος",
          h("select", { id: "channel", "aria-label": "Ύφος απάντησης", onchange: e => { state.channel = e.target.value; store("mirror-channel", state.channel); } },
            CHANNELS.map(([v, label]) => h("option", { value: v, selected: v === state.channel }, label)))),
        h("button", { class: "voice-live", id: "open-voice", type: "button", onclick: openVoice, title: "Φωνητική συζήτηση χωρίς χέρια: μιλάς, ακούει, απαντά, ξανακούει" },
          h("i", { class: "live-dot", "aria-hidden": "true" }), h("span", {}, "Voice avatar")),
        h("span", { class: "bar-gap" }),
        h("span", { class: "char-count", id: "char-count", "aria-live": "off" }),
        h("p", { class: "response-hint", id: "response-hint" })),
      h("p", { class: "disclaimer" }, "Το MIRROR είναι AI και μπορεί να κάνει λάθη. Τις εγκρίσεις τις κάνουν πάντα άνθρωποι."))),
    h("aside", { class: "avatar-panel", id: "avatar-panel", hidden: true, "aria-label": "Ανθρώπινο avatar" },
      h("iframe", { id: "avatar-frame", title: "MIRROR avatar", allow: "autoplay", src: "about:blank" })), voiceDialog()));
  paintHead(); paintChat(); loadAvatar();
  setTimeout(() => $("#composer")?.focus(), 40);
}
function paintSidebar() {
  const people = $("#people"), threads = $("#threads");
  if (!people) return;
  fill(people, state.session.mirrors.map(m => {
    const p = personFor(m);
    const own = m.id === state.session.user.employee_id;
    return h("button", { class: "person", "aria-current": String(state.view === "chat" && state.mirror?.id === m.id), onclick: () => state.mirror?.id === m.id && state.view === "chat" ? newChat() : openMirror(m) },
      avatar(p, "", true), h("span", {}, h("b", {}, p.name), h("small", {}, own ? "Το δικό σου Mirror" : p.job_title)));
  }));
  paintThreads();
}
/* History: grouped by day, with the owner's last question as a preview, searchable and renamable. */
const fold = text => String(text || "").normalize("NFD").replace(/\p{M}/gu, "").toLocaleLowerCase("el");
function dayGroup(value) {
  const d = new Date(value), start = new Date(); start.setHours(0, 0, 0, 0);
  const days = Math.round((start - new Date(d.getFullYear(), d.getMonth(), d.getDate())) / 86400000);
  return days <= 0 ? "Σήμερα" : days === 1 ? "Χθες" : days < 7 ? "Τελευταίες 7 ημέρες" : "Παλαιότερα";
}
function paintThreads() {
  const threads = $("#threads"); if (!threads) return;
  const search = $("#thread-search"); if (search) search.closest(".thread-search").hidden = !state.threads.length;
  if (!state.threads.length) { fill(threads, h("p", { class: "empty-threads" }, "Οι συζητήσεις σου θα εμφανίζονται εδώ.")); return; }
  const query = fold(state.threadQuery.trim());
  const shown = state.threads.filter(t => !query || fold(`${t.title} ${t.last_question || ""} ${t.last_answer || ""}`).includes(query));
  if (!shown.length) { fill(threads, h("p", { class: "empty-threads" }, "Καμία συζήτηση δεν ταιριάζει στην αναζήτηση.")); return; }
  const groups = new Map();
  for (const t of shown) { const g = dayGroup(t.updated_at); if (!groups.has(g)) groups.set(g, []); groups.get(g).push(t); }
  fill(threads, [...groups].map(([label, items]) => h("section", { class: "thread-group", "aria-label": label },
    h("h3", { class: "thread-day" }, label),
    items.map(t => {
      // Same question, same title: the start of the answer is what tells such threads apart.
      const question = (t.last_question || "").trim(), count = Number(t.turns) || 0;
      const asked = question && fold(question) !== fold(t.title), preview = asked ? question : (t.last_answer || "").trim();
      return h("div", { class: "thread", "aria-current": String(String(t.conversation_id) === state.thread) },
        h("button", { onclick: () => openThread(t.conversation_id), title: t.title },
          h("span", { class: "title" }, t.title),
          preview ? h("span", { class: "preview" }, h("b", {}, asked ? "Εσύ: " : "AI: "), preview) : null,
          h("small", { class: "when" }, when(t.updated_at) + (count ? ` · ${count} ${count === 1 ? "ερώτηση" : "ερωτήσεις"}` : ""))),
        h("button", { class: "ren", "aria-label": "Μετονομασία συζήτησης", title: "Μετονομασία", onclick: () => renameThread(t) }, icon(I.edit, 15)),
        h("button", { class: "del", "aria-label": "Διαγραφή συζήτησης", title: "Διαγραφή", onclick: () => removeThread(t) }, icon(I.trash, 15)));
    }))));
}
function renameThread(t) {
  const ctx = conversationContext();
  showOverlay(done => {
    const input = h("input", { class: "input", value: t.title, maxlength: "120", required: true, "aria-label": "Τίτλος συζήτησης" });
    setTimeout(() => input.select(), 30);
    return { focus: input, node: h("form", { class: "dialog", role: "dialog", "aria-modal": "true", "aria-label": "Μετονομασία συζήτησης",
        onsubmit: e => { e.preventDefault(); done(input.value); } },
      h("h4", {}, "Μετονομασία συζήτησης"), input,
      h("div", { class: "row" }, h("button", { class: "btn", type: "button", onclick: () => done(false) }, "Άκυρο"),
        h("button", { class: "btn primary", type: "submit" }, "Αποθήκευση"))) };
  }, async value => {
    if (value === false || !currentContext(ctx)) return;
    const title = String(value).trim().replace(/\s+/g, " ");
    if (!title || title === t.title) return;
    try {
      const r = await api(`/api/mirrors/${ctx.mirror}/conversations/${t.conversation_id}/rename`, { title }, ctx);
      t.title = r.title; paintThreads(); toast("Η συζήτηση μετονομάστηκε.");
    } catch (error) { if (currentContext(ctx)) toast(error.message, true); }
  });
}
function paintHead() {
  const head = $("#head"); if (!head) return;
  const p = state.mirror ? personFor(state.mirror) : null;
  fill(head, h("button", { class: "iconbtn menu-toggle", "aria-label": "Μενού", onclick: () => $("#app").classList.add("nav-open") }, icon(I.menu)),
    h("button", { class: "iconbtn", "aria-label": "Πίσω στην ομάδα", title: "Πίσω στην ομάδα", onclick: goHome }, icon(I.back)),
    p ? [avatar(p, "", true), h("div", {}, h("b", {}, p.name), h("small", {}, `AI αντίγραφο · ${p.job_title}`))] : h("b", {}, "MIRROR"),
    h("div", { class: "mode-switch", id: "mode-switch", role: "group", "aria-label": "Τρόπος απάντησης", "data-mode": mode() },
      h("span", { class: "mode-glider", "aria-hidden": "true" }),
      [["text", "Κείμενο", I.chat, "Απάντηση με κείμενο"], ["voice", "Φωνή", I.speaker, "Απάντηση με τη φωνή του προσώπου"],
       ["avatar", "Avatar", I.face, "Απάντηση με φωνή και ζωντανό πρόσωπο"]].map(([value, label, glyph, tip]) =>
        h("button", { type: "button", "data-mode": value, title: tip, "aria-pressed": String(mode() === value), onclick: () => setMode(value) }, icon(glyph, 14), h("span", {}, label)))),
    h("button", { class: "iconbtn face-toggle", id: "face-toggle", hidden: true, "aria-label": "Εμφάνιση/απόκρυψη avatar", title: "Avatar", onclick: () => $("#chat-shell")?.classList.toggle("show-face") }, icon(I.face)),
    h("span", { class: "sr-only", id: "status", role: "status", "aria-live": "polite" }, state.offline ? "Εκτός σύνδεσης" : "Διαθέσιμο"));
}

/* ---------- 3D avatar & voice (avatar branch) ---------- */
async function lookFor(mid, ctx) {
  if (!(mid in state.looks)) state.looks[mid] = await api(`/api/mirrors/${mid}/avatar`, undefined, ctx);
  return state.looks[mid];
}
/* Text is the default after sign-in or reload; voice and human avatar are explicit choices that then
   stay selected for new chats, older threads and other Mirrors until another button or sign-out. */
function mode() { return state.mode || "text"; }
// Επεξήγηση: Η αλλαγή τρόπου απάντησης ακυρώνει εκκρεμή ηχογράφηση πριν συνεχίσει.
function setMode(next) {
  if (!["voice", "avatar", "text"].includes(next)) return;
  if (next === mode()) return;  // the selected reply button stays selected; another button changes it
  if (state.rec || state.micPending || state.transcribing) stopRecord(true);
  closeVoice(); state.mode = next; state.voiceTurn = null;
  unlockVoiceAudio(); paintVoiceControls();
  loadAvatar();
}

/* The orb uses the same authenticated record → transcribe → confirm pipeline as
   the composer; it never substitutes a canned response or a browser TTS voice. */
function voiceDialog() {
  return h("dialog", { id: "voice-dialog", class: "voice-dialog", "aria-labelledby": "voice-title",
    oncancel: e => { e.preventDefault(); closeVoice(); } },
    h("header", { class: "voice-dialog-head" }, h("span", { class: "voice-eyebrow" }, "MIRROR / VOICE"),
      h("button", { class: "iconbtn", type: "button", "aria-label": "Κλείσιμο φωνητικής συνομιλίας", onclick: closeVoice }, icon(I.close, 22))),
    h("div", { class: "voice-person" }, h("h2", { id: "voice-title" }, personFor(state.mirror).name),
      h("p", {}, "Το AI αντίγραφο της ομάδας σου")),
    h("div", { class: "voice-orbit" },
      h("button", { id: "voice-orb", class: "voice-orb", type: "button", onclick: orbAction, "aria-describedby": "voice-instruction" },
        h("span", { class: "orb-halo", "aria-hidden": "true" }), h("span", { class: "orb-ring", "aria-hidden": "true" }),
        h("span", { class: "orb-core", "aria-hidden": "true" }, h("span"), h("span"), h("span")),
        h("span", { class: "orb-symbol", id: "orb-symbol", "aria-hidden": "true" }, icon(I.mic, 30)))),
    h("p", { class: "voice-state", id: "voice-state", role: "status", "aria-live": "polite" }),
    h("p", { class: "voice-instruction", id: "voice-instruction" }),
    h("div", { class: "voice-transcript", id: "voice-transcript", "aria-label": "Τελευταία μηνύματα" }),
    h("button", { class: "voice-cancel", id: "voice-cancel", type: "button", onclick: pauseVoice }, "Παύση συνομιλίας"),
    h("p", { class: "voice-privacy" }, icon(I.lock, 12), "Μετά την απάντηση ακούει ξανά. Παύση ή κλείσιμο σταματά το μικρόφωνο."));
}
let voiceAudioContext = null, playbackMeter = null;
function unlockVoiceAudio() {
  try {
    voiceAudioContext ||= new AudioContext();
    voiceAudioContext.resume().catch(() => {});
  } catch { /* Audio playback still works without the visual meter. */ }
}
// Επεξήγηση: Η συνεχής φωνητική συνομιλία ξεκινά μόνο μετά από επιλογή του χρήστη.
function openVoice() {
  if (mode() !== "voice") setMode("voice");
  state.voiceOpen = true; unlockVoiceAudio(); paintVoiceControls();
  const dialog = $("#voice-dialog"); if (dialog && !dialog.open) dialog.showModal();
  $("#voice-orb")?.focus();
}
function closeVoice() {
  state.voiceOpen = false; state.voiceContinuous = false;
  if (state.rec || state.micPending || state.transcribing) stopRecord(true);
  stopVoice(); $("#voice-dialog")?.close();
  $('#mode-switch [data-mode="voice"]')?.focus();
}
function orbAction() {
  if (state.busy || state.transcribing || state.micPending) return;
  if (state.rec) return stopRecord(false, true);
  state.voiceContinuous = true; stopVoice(); toggleRecord();
}
function pauseVoice() {
  state.voiceContinuous = false; stopRecord(true); stopVoice(); paintVoiceControls();
}
function orbLevel(level) {
  $("#voice-orb")?.style.setProperty("--level", reduceMotion ? 0 : Math.min(1, level).toFixed(3));
}
// Επεξήγηση: Συγχρονίζει κουμπιά και ενδείξεις με ηχογράφηση, μεταγραφή και αναμονή απάντησης.
function paintVoiceControls() {
  document.querySelectorAll("#mode-switch [data-mode]").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.mode === mode())));
  $("#mode-switch")?.setAttribute("data-mode", mode());
  const live = $("#open-voice"); if (live) live.setAttribute("aria-pressed", String(state.voiceOpen));
  const responseHint = $("#response-hint");
  if (responseHint) responseHint.textContent = mode() === "text" ? "🎤 Υπαγόρευση → έλεγχος κειμένου → αποστολή · Η απάντηση παραμένει γραπτή" : mode() === "voice" ? "Γράψε ή πάτα 🎤 — η απάντηση ακούγεται με τη φωνή του προσώπου" : "Γράψε ή πάτα 🎤 — η απάντηση έρχεται με φωνή και ζωντανό πρόσωπο";
  const pending = state.transcribing || state.micPending;
  const mic = $("#mic"), submit = $(".send"), box = $("#composer");
  if (mic) {
    mic.disabled = state.busy || pending; mic.setAttribute("aria-pressed", String(!!state.rec));
    mic.setAttribute("aria-label", state.rec ? "Σταμάτημα υπαγόρευσης για έλεγχο" : "Μίλησε (έως 30 δευτερόλεπτα)");
  }
  if (submit) {
    submit.disabled = state.busy || state.micPending || (state.transcribing && state.submitAfterTranscript);
    submit.title = state.rec ? "Σταμάτημα και αποστολή" : state.transcribing ? "Αποστολή μόλις ολοκληρωθεί η μεταγραφή" : "Αποστολή";
  }
  if (box) { box.readOnly = state.transcribing; box.placeholder = mode() === "text" ? "Γράψε ένα μήνυμα…" : "Γράψε ή πάτα το μικρόφωνο για να μιλήσεις…"; }
  const orb = $("#voice-orb"); if (!orb) return;
  const phase = state.rec ? "listening" : state.micPending ? "permission" : state.transcribing ? "transcribing" : state.busy ? "thinking" : state.audio && !state.audio.paused ? "speaking" : "idle";
  const labels = {
    idle: ["Έτοιμο για συζήτηση", "Πάτα τον κύκλο για να ξεκινήσεις. Μετά από κάθε απάντηση θα ακούω ξανά.", "Έναρξη φωνητικής ηχογράφησης"],
    listening: ["Σε ακούω…", "Κάνε μια παύση ή πάτα τον κύκλο για άμεση αποστολή.", "Σταμάτημα και αποστολή φωνητικού μηνύματος"],
    permission: ["Άνοιγμα μικροφώνου…", "Επίτρεψε την πρόσβαση στο μικρόφωνο στον browser.", "Αναμονή άδειας μικροφώνου"],
    transcribing: ["Μια στιγμή…", "Ολοκληρώνω το μήνυμά σου.", "Μεταγραφή φωνητικού μηνύματος"],
    thinking: ["Σκέφτομαι την απάντηση…", "Η απάντηση θα εμφανιστεί και στο chat.", "Αναμονή απάντησης"],
    speaking: ["Μιλάω…", "Πάτα τον κύκλο για να με διακόψεις και να μιλήσεις.", "Διακοπή απάντησης και νέα ηχογράφηση"],
  };
  const [label, instruction, action] = labels[phase];
  orb.dataset.state = phase; orb.disabled = state.busy || pending; orb.setAttribute("aria-label", action);
  orb.setAttribute("aria-pressed", String(phase === "listening"));
  $("#voice-state").textContent = label; $("#voice-instruction").textContent = instruction;
  fill($("#orb-symbol"), icon(phase === "listening" ? I.send : phase === "speaking" ? I.speaker : I.mic, 30));
  const cancel = $("#voice-cancel"); cancel.hidden = !(state.rec || pending || state.voiceContinuous);
  cancel.textContent = state.voiceContinuous ? "Παύση συνομιλίας" : state.transcribing ? "Ακύρωση αποστολής" : "Ακύρωση ηχογράφησης";
  const latest = state.messages.filter(m => ["user", "ai", "note"].includes(m.role)).slice(-2);
  fill($("#voice-transcript"), latest.map(m => h("p", { class: m.role }, h("small", {}, m.role === "user" ? "ΕΣΥ" : m.role === "ai" ? "MIRROR" : "ΕΝΗΜΕΡΩΣΗ"), m.text)));
  if (!["speaking", "listening"].includes(phase)) orbLevel(0);
}
function stopPlaybackMeter() {
  if (playbackMeter) { cancelAnimationFrame(playbackMeter.frame); playbackMeter.source.disconnect(); playbackMeter.analyser.disconnect(); playbackMeter = null; }
  orbLevel(0);
}
function meterPlayback(audio) {
  // Only connect a running, gesture-unlocked context: a suspended Web Audio
  // graph would otherwise silence the HTML audio element.
  if (!voiceAudioContext || voiceAudioContext.state !== "running") return;
  try {
    const source = voiceAudioContext.createMediaElementSource(audio), analyser = voiceAudioContext.createAnalyser();
    analyser.fftSize = 256; source.connect(analyser); analyser.connect(voiceAudioContext.destination);
    const meter = { source, analyser, frame: 0 }, values = new Uint8Array(analyser.fftSize); playbackMeter = meter;
    const tick = () => {
      if (playbackMeter !== meter) return;
      analyser.getByteTimeDomainData(values);
      const rms = Math.sqrt(values.reduce((sum, n) => sum + ((n - 128) / 128) ** 2, 0) / values.length);
      orbLevel(rms * 5); meter.frame = requestAnimationFrame(tick);
    }; tick();
  } catch { /* Keep the voice playable even without an amplitude meter. */ }
}
// Επεξήγηση: Διακόπτει αναπαραγωγή και καθαρίζει τους προσωρινούς πόρους ήχου.
function stopVoice({ keepAvatar = false } = {}) {
  const frame = $("#avatar-frame");
  if (frame && !keepAvatar) { frame.contentWindow?.postMessage("mirror:stop",location.origin); frame.src="about:blank"; }
  playbackRequest++; stopPlaybackMeter();
  const a = state.audio; state.audio = null;
  if (a) { a.pause(); URL.revokeObjectURL(a.src); a.removeAttribute("src"); a.load(); }
  $("#chat-shell")?.classList.remove("speaking"); paintStatus(); paintVoiceControls();
}
async function resumeVoiceListening(ctx, request) {
  const active = () => currentContext(ctx) && playbackRequest === request && state.voiceOpen
    && state.voiceContinuous && mode() === "voice" && !state.busy && !state.rec && !state.micPending;
  if (!active()) return;
  try {
    // Revalidate before reopening a microphone, including access revoked while
    // the previous answer was playing. This does not invoke an AI provider.
    const caps = await api(`/api/mirrors/${ctx.mirror}/avatar`, undefined, ctx);
    if (!active()) return;
    if (caps.voice) toggleRecord(); else { state.voiceContinuous = false; paintVoiceControls(); }
  } catch { if (active()) { state.voiceContinuous = false; paintVoiceControls(); } }
}
async function playVoice(turn, keepAvatar = false) {
  stopVoice({ keepAvatar });
  const ctx = conversationContext(), request = playbackRequest;
  try {
    const res = await fetch(`/api/voice/${encodeURIComponent(turn)}/audio`, { credentials: "same-origin", signal: ctx.signal });
    if (!res.ok) {
      const error = await res.json().catch(() => ({}));
      if (currentContext(ctx) && res.status === 401) {
        clearSession(); toast("Η σύνδεση έληξε. Μπες ξανά.", true); return;
      }
      if (currentContext(ctx) && res.status === 403 && error.code === "mirror_access") withdrawMirror(error.mirror_id);
      throw new Error();
    }
    const blob = await res.blob();
    if (!currentContext(ctx) || request !== playbackRequest) return;
    const audio = new Audio(URL.createObjectURL(blob));
    state.audio = audio;
    audio.onended = () => {
      if (state.audio !== audio) return;
      stopVoice({ keepAvatar });
      const endedRequest = playbackRequest;
      // Only a naturally completed answer may reopen an explicitly started
      // conversation. Close, pause, navigation and interruption invalidate it.
      if (state.voiceOpen && state.voiceContinuous && currentContext(ctx)) {
        setTimeout(() => resumeVoiceListening(ctx, endedRequest), 180);
      }
    };
    audio.onerror = () => {
      if (state.audio === audio) { state.voiceContinuous = false; stopVoice({ keepAvatar }); }
    };
    audio.onplay = () => { if (!currentContext(ctx) || state.audio !== audio) return; meterPlayback(audio); paintVoiceControls(); $("#chat-shell")?.classList.add("speaking"); const st = $("#status"); if (st) st.textContent = "Μιλάει…"; };
    await audio.play().catch(() => { if (currentContext(ctx) && state.audio === audio) { state.voiceContinuous = false; stopVoice({ keepAvatar }); toast("Πάτα 🔊 στην απάντηση για να την ακούσεις."); } });
  } catch { if (currentContext(ctx) && request === playbackRequest) { state.voiceContinuous = false; paintVoiceControls(); toast("Η φωνή δεν είναι διαθέσιμη για αυτή την απάντηση.", true); } }
}
// Επεξήγηση: Στο Κείμενο παραμένει διαθέσιμη η υπαγόρευση, χωρίς φόρτωση βίντεο.
async function loadAvatar(turn) {
  const ctx = conversationContext(), mid = ctx.mirror, request = ++avatarRequest; if (!mid) return;
  const panel = $("#avatar-panel"), frame = $("#avatar-frame");
  if (!panel || !frame) return;
  if (mode() === "text") {
    panel.hidden = true; frame.src = "about:blank"; $("#chat-shell")?.classList.add("voice-only");
    $("#mic").hidden = !navigator.mediaDevices?.getUserMedia; $("#face-toggle").hidden = true; paintVoiceControls(); return;
  }
  let look;
  try { look = await lookFor(mid, ctx); } catch { if (!currentContext(ctx)) return; look = { available: false, voice: false }; }
  if (!currentContext(ctx) || request !== avatarRequest) return;
  const switcher = $("#mode-switch"); if (switcher) switcher.hidden = false;
  $("#mic") && ($("#mic").hidden = !look.voice || !navigator.mediaDevices?.getUserMedia);
  const voiceOnly = mode() === "voice" || !look.available;
  panel.hidden = voiceOnly; $("#chat-shell")?.classList.toggle("voice-only", voiceOnly); $("#face-toggle") && ($("#face-toggle").hidden = voiceOnly);
  if (voiceOnly) { frame.src = "about:blank"; if (turn) playVoice(turn); return; }
  stopVoice();
  // Reveal the selected portrait immediately, including on compact screens.
  // Live Simli sessions still require the separate explicit start button.
  $("#chat-shell")?.classList.add("show-face");
  const simli = look.avatar_provider === "simli";
  const surface = simli ? "simli-avatar.html" : "avatar.html";
  // A turn reaches here only from a click (send, replay, choosing 3D avatar), so the Simli face starts by
  // itself; the server still caps Simli seconds per day and month. Its own audio carries the voice.
  frame.src = `/${surface}?m=${encodeURIComponent(mid)}&name=${encodeURIComponent(personFor(state.mirror).name)}&cid=${encodeURIComponent(state.thread || "")}${turn ? "&turn=" + encodeURIComponent(turn) : ""}${turn && simli ? "&auto=1" : ""}&v=${request}`;
  if (turn && simli) awaitAvatar(turn, String(request), ctx);
}
/* If the Simli face cannot start (limit reached, network, script), the answer is still heard. */
let avatarFallback = null;
function clearAvatarFallback() { if (avatarFallback) clearTimeout(avatarFallback.timer); avatarFallback = null; }
function awaitAvatar(turn, view, ctx) {
  clearAvatarFallback();
  const pending = { turn, view, timer: 0 };
  pending.timer = setTimeout(() => avatarFellBack(pending, ctx), 8000);  // the face never even began
  avatarFallback = pending;
}
function avatarFellBack(pending, ctx) {
  if (avatarFallback !== pending) return;
  clearAvatarFallback();
  if (currentContext(ctx) && mode() === "avatar") playVoice(pending.turn, true);
}
function voiceHint(text, opts = {}) {
  const el = $("#voice-hint"); if (!el) return;
  if (!text && state.voiceTurn) text = "Έλεγξε τη μεταγραφή, διόρθωσε αν χρειάζεται και πάτα αποστολή.";
  el.hidden = !text; if (!text) return;
  fill(el, opts.rec ? h("i", { class: "rec-dot" }) : icon(I.mic, 14), h("span", {}, text),
    state.voiceTurn || opts.review || opts.rec || state.transcribing ? h("button", { type: "button", onclick: () => { if (state.rec || state.transcribing || state.micPending) stopRecord(true); state.voiceTurn = null; const c = $("#composer"); if (c && !opts.rec) { c.value = ""; autosize(c); } voiceHint(); } }, "Ακύρωση") : null);
}
// Επεξήγηση: Ζητά μικρόφωνο μόνο με πάτημα και συλλέγει προσωρινά τον ήχο.
async function toggleRecord() {
  if (state.rec) return stopRecord(false, state.voiceOpen);
  if (state.busy || state.transcribing || state.micPending || !state.session || state.view !== "chat") return;
  if (!navigator.mediaDevices?.getUserMedia) return toast("Ο browser δεν υποστηρίζει μικρόφωνο εδώ.", true);
  const ctx = conversationContext(), request = ++recordingRequest;
  state.micPending = true; stopVoice(); unlockVoiceAudio(); paintVoiceControls();
  let stream, audioContext;
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true } });
    if (!currentContext(ctx) || request !== recordingRequest) { stream.getTracks().forEach(t => t.stop()); return; }
    try { audioContext = new AudioContext({ sampleRate: 16000 }); } catch { audioContext = new AudioContext(); }
    await audioContext.resume();
    if (!currentContext(ctx) || request !== recordingRequest) { stream.getTracks().forEach(t => t.stop()); await audioContext.close(); return; }
    const source = audioContext.createMediaStreamSource(stream), node = audioContext.createScriptProcessor(2048, 1, 1), chunks = [];
    const started = Date.now();
    const rec = { stream, ctx: audioContext, context: ctx, source, node, chunks, started, speechMs: 0, lastSpeech: started, timer: null };
    node.onaudioprocess = e => {
      if (state.rec !== rec) return;
      const chunk = new Float32Array(e.inputBuffer.getChannelData(0)); chunks.push(chunk);
      const rms = Math.sqrt(chunk.reduce((sum, n) => sum + n * n, 0) / chunk.length);
      orbLevel(rms * 7);
      if (rms > .018) { rec.speechMs += chunk.length / audioContext.sampleRate * 1000; rec.lastSpeech = Date.now(); }
      // Silence detection is exclusive to the conversational orb. Dictation
      // remains editable until the user presses Send or the stop button.
      if (state.voiceOpen && rec.speechMs >= 350 && Date.now() - rec.lastSpeech > 900) stopRecord(false, true);
    };
    state.rec = rec; state.micPending = false; state.voiceTurn = null;
    source.connect(node); node.connect(audioContext.destination);
    rec.timer = setInterval(() => {
      const secs = Math.floor((Date.now() - rec.started) / 1000);
      voiceHint(`Ηχογράφηση… ${secs}″ · πάτα αποστολή για να σταλεί`, { rec: true });
      if (secs >= 29) {
        if (state.voiceOpen && rec.speechMs < 350) {
          stopRecord(true); toast("Δεν ακούστηκε ομιλία. Πάτα τον κύκλο για να δοκιμάσεις ξανά.");
        } else stopRecord(false, state.voiceOpen);
      }
    }, 250);
    $("#mic")?.classList.add("on"); fill($("#mic"), icon(I.stop)); voiceHint("Ηχογράφηση… πάτα αποστολή για να σταλεί", { rec: true }); paintVoiceControls();
  } catch {
    stream?.getTracks().forEach(t => t.stop()); audioContext?.close().catch(() => {});
    if (currentContext(ctx) && request === recordingRequest) { state.voiceContinuous = false; toast("Δεν δόθηκε πρόσβαση στο μικρόφωνο.", true); }
  } finally { if (currentContext(ctx) && request === recordingRequest) { state.micPending = false; paintVoiceControls(); } }
}
// Επεξήγηση: Σταματά το μικρόφωνο και ελέγχει ότι η μεταγραφή αφορά ακόμη την τρέχουσα συζήτηση.
async function stopRecord(cancel = false, submit = false) {
  const request = ++recordingRequest;
  state.micPending = false;
  if (cancel) { state.voiceContinuous = false; state.transcribing = false; state.submitAfterTranscript = false; }
  const rec = state.rec; state.rec = null;
  if (!rec) { if (cancel) { voiceHint(); paintVoiceControls(); } return; }
  state.transcribing = !cancel; state.submitAfterTranscript = !cancel && submit;
  clearInterval(rec.timer); rec.node.disconnect(); rec.source.disconnect(); rec.stream.getTracks().forEach(t => t.stop());
  const rate = rec.ctx.sampleRate, ctx = rec.context, textOnly = mode() === "text", active = () => currentContext(ctx) && request === recordingRequest;
  const mic = $("#mic"); if (mic) { mic.classList.remove("on"); fill(mic, icon(I.mic)); }
  orbLevel(0); paintVoiceControls();
  await rec.ctx.close().catch(() => {});
  if (!active()) return;
  if (cancel) { voiceHint(); return; }
  try {
    const length = rec.chunks.reduce((n, c) => n + c.length, 0);
    if (length / rate < .6) { state.voiceContinuous = false; voiceHint(); toast("Πολύ σύντομη ηχογράφηση. Κράτα το λίγο περισσότερο."); return; }
    const samples = new Float32Array(length); let o = 0; for (const c of rec.chunks) { samples.set(c, o); o += c.length; }
    voiceHint("Μεταγραφή…");
    if (!textOnly && !state.thread) {
      const t = await api(`/api/mirrors/${ctx.mirror}/conversations`, { title: "Φωνητική συζήτηση" }, ctx);
      if (!active()) return;
      state.thread = String(t.conversation_id); store(threadKey(), state.thread); state.threads.unshift(t); paintSidebar();
    }
    // Text dictation only transcribes; sending follows the normal text-chat path.
    const endpoint = textOnly ? "/api/voice/transcribe" : `/api/mirrors/${ctx.mirror}/voice?conversation_id=${encodeURIComponent(state.thread)}`;
    const res = await fetch(endpoint,
      { method: "POST", credentials: "same-origin", signal: ctx.signal, headers: { "Content-Type": "audio/wav", "X-Mirror-Request": "1" }, body: encodeWav(samples, rate) });
    const data = await res.json().catch(() => ({}));
    if (!active()) return;
    if (!res.ok) {
      if (res.status === 401) clearSession();
      if (res.status === 403 && data.code === "mirror_access") withdrawMirror(data.mirror_id);
      throw new Error(friendly(res.status, data));
    }
    const transcript = (textOnly ? data.text : data.transcript)?.trim();
    if (!transcript || (!textOnly && !data.turn_id)) throw new Error("Δεν ακούστηκε κάποιο μήνυμα. Δοκίμασε ξανά.");
    const box = $("#composer");
    const draft = textOnly ? [box.value.trim(), transcript].filter(Boolean).join("\n") : transcript;
    if (draft.length > 4000) throw new Error("Η μεταγραφή μαζί με το μήνυμα ξεπερνά τους 4.000 χαρακτήρες. Συντόμευσε το κείμενο και δοκίμασε ξανά.");
    state.voiceTurn = textOnly ? null : data.turn_id;
    box.value = draft; autosize(box); paintCount();
    const shouldSend = state.submitAfterTranscript;
    state.transcribing = false; state.submitAfterTranscript = false;
    voiceHint(textOnly ? "Έλεγξε τη μεταγραφή, διόρθωσε αν χρειάζεται και πάτα αποστολή. Η απάντηση θα είναι γραπτή." : undefined, { review: textOnly }); paintVoiceControls();
    if (shouldSend) await send(); else if (!state.voiceOpen) box.focus();
  } catch (error) { if (active()) { state.voiceContinuous = false; state.voiceTurn = null; voiceHint(); toast(error.message, true); } }
  finally { if (active()) { state.transcribing = false; state.submitAfterTranscript = false; paintVoiceControls(); } }
}
// Επεξήγηση: Κωδικοποιεί τα δείγματα μικροφώνου σε WAV για τον server.
function encodeWav(samples, rate) {
  const buffer = new ArrayBuffer(44 + samples.length * 2), v = new DataView(buffer);
  const tag = (o, t) => { for (let i = 0; i < t.length; i++) v.setUint8(o + i, t.charCodeAt(i)); };
  tag(0, "RIFF"); v.setUint32(4, 36 + samples.length * 2, true); tag(8, "WAVE"); tag(12, "fmt ");
  v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true); v.setUint32(24, rate, true);
  v.setUint32(28, rate * 2, true); v.setUint16(32, 2, true); v.setUint16(34, 16, true); tag(36, "data"); v.setUint32(40, samples.length * 2, true);
  let o = 44; for (const x of samples) { const c = Math.max(-1, Math.min(1, x)); v.setInt16(o, c < 0 ? c * 0x8000 : c * 0x7fff, true); o += 2; }
  return new Blob([buffer], { type: "audio/wav" });
}
function paintStatus() { const st = $("#status"); if (st) st.textContent = state.offline ? "Εκτός σύνδεσης" : "Διαθέσιμο"; }
/* ---------- team pyramid (home) ---------- */
function layoutTree(people) {
  const kids = id => people.filter(p => p.manager_id === id);
  const pos = {}; let leaf = 0, depthMax = 0;
  const walk = (p, depth) => {
    depthMax = Math.max(depthMax, depth);
    const children = kids(p.id);
    if (!children.length) { pos[p.id] = { x: leaf++, depth }; return; }
    children.forEach(c => walk(c, depth + 1));
    pos[p.id] = { x: children.reduce((a, c) => a + pos[c.id].x, 0) / children.length, depth };
  };
  people.filter(p => !p.manager_id || !people.some(q => q.id === p.manager_id)).forEach(r => walk(r, 0));
  for (const id in pos) { pos[id].x = (pos[id].x + .5) / Math.max(leaf, 1); pos[id].y = (pos[id].depth + .5) / (depthMax + 1); }
  return { pos, leaves: leaf };
}
/* The server says why an AI is not available (it owns the access rules); the UI only words it. */
const DEPARTMENTS = { executive: "Διοίκηση", sales: "Πωλήσεις", finance: "Οικονομικά" };
const RELATIONS = { manager: "Ο άμεσος προϊστάμενός σου", above: "Ανώτερος στη γραμμή αναφοράς σου" };
const REASONS = {
  self: "Πάτησε για self-test. Για συνομιλία, διάλεξε το δικό σου Mirror από το μενού.",
  self_no_ai: "Εσύ · δεν έχεις ακόμα δικό σου AI αντίγραφο· μιλάς με το AI των προϊσταμένων σου",
  no_ai: "Δεν έχει AI αντίγραφο",
  below: "Αναφέρεται σε σένα · η συνομιλία γίνεται μόνο προς τα πάνω",
  other_line: "Άλλη γραμμή αναφοράς · μιλάς μόνο με τους προϊσταμένους σου",
  not_permitted: "Ο λογαριασμός σου δεν έχει πρόσβαση σε αυτό το AI",
};
const silentEmployeeAccess = p => p.reason === "not_permitted" && ["sales_employee", "finance_employee"].includes(p.role_name);
const personNote = p => silentEmployeeAccess(p) ? "" : p.can_chat ? RELATIONS[p.relation] || "Διαθέσιμο για συνομιλία" : REASONS[p.reason] || REASONS.not_permitted;
// Επεξήγηση: Η οθόνη συγκρίνει ανθρώπινη απάντηση με AI και παρέχει χωριστή έγκριση εταιρικών κανόνων.
async function startSelfTest() {
  let initial;
  try { initial = await api("/api/self-test"); }
  catch (error) { toast(error.message, true); return; }
  if (!initial.mirror) { infoBox("Self-test", "Δεν υπάρχει διαθέσιμο AI αντίγραφο για self-test."); return; }

  showOverlay(done => {
    const model = { snapshot: initial, phase: "choose", current: null, answer: "", correction: "", correctionOpen: false,
      publicationsOpen: false, customDraft: "", chosenQuestion: "", chosenQuestionTopic: "", selectedTopic: initial.next_topic || initial.topics[0]?.topic || "", busy: false, error: "", lastFeedback: null };
    const panel = h("div", { class: "self-test-panel" });
    const close = h("button", { class: "iconbtn", type: "button", "aria-label": "Κλείσιμο self-test", onclick: () => done(false) }, icon(I.close));
    const frame = h("section", { class: "dialog self-test-dialog", role: "dialog", "aria-modal": "true", "aria-labelledby": "self-test-title" },
      h("header", { class: "self-test-header" }, h("div", {}, h("p", { class: "self-test-eyebrow" }, "MIRROR / SELF-TEST"),
        h("h2", { id: "self-test-title" }, `Δοκίμασε το AI αντίγραφό σου`),
        h("p", { class: "self-test-subtitle" }, `${initial.mirror.name} · Απάντησε πρώτα εσύ, μετά σύγκρινε την απάντηση του AI.`)), close), panel);

    const progress = () => h("div", { class: "self-test-topics", "aria-label": "Πρόοδος ανά θέμα" },
      model.snapshot.topics.map(t => h("div", { class: "self-topic" + (t.verified ? " verified" : "") },
        h("span", { class: "self-topic-name" }, t.topic),
        h("span", { class: "self-topic-status" }, t.verified ? "Επαληθευμένο" : `${t.streak}/3 σωστές`))));
    const history = () => h("section", { class: "self-test-history" }, h("h3", {}, "Πρόσφατα τεστ"),
      model.snapshot.events.length ? model.snapshot.events.map(event => h("article", { class: "self-test-event" + (event.undone_at ? " undone" : "") },
        h("div", { class: "self-test-event-copy" }, h("b", {}, event.topic),
          h("p", {}, event.question),
          h("small", {}, event.undone_at ? "Training αναιρεμένο" : event.feedback === "correct" ? "Σωστή απάντηση" : event.feedback === "wrong" ? "Χρειάζεται training" : "Περιμένει αξιολόγηση"),
          event.correction ? h("small", { class: "self-test-correction-preview" }, `Διόρθωση: ${event.correction}`) : null),
        event.feedback && !event.undone_at ? h("button", { class: "btn compact", type: "button", disabled: model.busy,
          onclick: () => undo(event.event_id) }, "Αναίρεση") : null))
        : h("p", { class: "self-test-empty" }, "Οι ερωτήσεις και η πρόοδός σου εμφανίζονται μόνο σε εσένα."));

    async function publishRule(rule) {
      model.busy = true; model.error = ""; render();
      try {
        const result = await api(`/api/profile/traits/${encodeURIComponent(rule.id)}/publication`,
          { published: !rule.published, content_hash: rule.content_hash });
        model.snapshot.company_rules = result.rules;
      } catch (error) { setError(error); }
      finally { model.busy = false; render(); }
    }
    const publications = () => h("details", { class: "self-test-history publication-review", open: model.publicationsOpen, ontoggle: e => { model.publicationsOpen = e.target.open; } },
      h("summary", {}, "Εταιρικοί κανόνες για την ομάδα"),
      h("p", { class: "muted" }, "Μόνο όσα δημοσιεύεις εδώ χρησιμοποιούνται από άλλους και κληρονομούνται. Έλεγξε όλο το κείμενο: οι ιδιωτικές πηγές δεν κοινοποιούνται. Αλλαγή κανόνα απαιτεί νέα δημοσίευση."),
      ...(model.snapshot.company_rules || []).map(rule => h("article", { class: "self-test-event" },
        h("div", { class: "self-test-event-copy" }, h("b", {}, rule.text),
          ...[rule.content?.first_person && rule.content.first_person !== rule.text ? `Διατύπωση: ${rule.content.first_person}` : "",
              rule.content?.when ? `Πότε ισχύει: ${rule.content.when}` : "",
              rule.content?.prefers?.length ? `Προτιμά: ${rule.content.prefers.join(", ")}` : "",
              rule.content?.avoids?.length ? `Αποφεύγει: ${rule.content.avoids.join(", ")}` : ""].filter(Boolean).map(text => h("p", {}, text)),
          h("small", {}, rule.published ? "Δημοσιευμένο στην ομάδα" : "Δεν έχει δημοσιευτεί")),
        h("button", { class: "btn compact", type: "button", disabled: model.busy,
          onclick: () => publishRule(rule) }, rule.published ? "Ανάκληση δημοσίευσης" : "Έγκριση και δημοσίευση"))));

    function setError(error) { model.error = error?.message || "Κάτι πήγε στραβά. Δοκίμασε ξανά."; }
    async function undo(eventId) {
      model.busy = true; model.error = ""; render();
      try {
        model.snapshot = await api(`/api/self-test/events/${encodeURIComponent(eventId)}/undo`, {});
        model.selectedTopic = model.snapshot.next_topic || model.selectedTopic;
      }
      catch (error) { setError(error); }
      finally { model.busy = false; render(); }
    }
    async function makeQuestion(customQuestion = null, topic = model.selectedTopic) {
      model.busy = true; model.phase = "loading"; model.error = ""; model.current = null; render();
      try {
        model.current = await api("/api/self-test/question", { topic, ...(customQuestion ? { custom_question: customQuestion } : {}) });
        model.answer = ""; model.correction = ""; model.correctionOpen = false; model.phase = "answer";
      } catch (error) { setError(error); model.phase = "choose"; }
      finally { model.busy = false; render(); }
    }
    async function submitAnswer() {
      const answer = model.answer.trim();
      if (!answer) { model.error = "Γράψε πρώτα τη δική σου απάντηση."; render(); return; }
      model.busy = true; model.error = ""; render();
      try {
        model.current = await api("/api/self-test/answer", { topic: model.current.topic, question: model.current.question,
          question_source: model.current.question_source, user_answer: answer });
        model.phase = "review";
      } catch (error) { setError(error); }
      finally { model.busy = false; render(); }
    }
    async function rate(feedback, correction = "") {
      model.busy = true; model.error = ""; render();
      try {
        model.current.correction = correction;
        model.snapshot = await api(`/api/self-test/events/${encodeURIComponent(model.current.event_id)}/feedback`, { feedback, correction });
        model.selectedTopic = model.snapshot.next_topic || model.selectedTopic;
        model.lastFeedback = feedback; model.phase = "done"; model.correctionOpen = false;
      } catch (error) { setError(error); }
      finally { model.busy = false; render(); }
    }
    function render() {
      const topicSelect = h("select", { class: "input self-topic-select", "aria-label": "Θέμα ερώτησης", onchange: e => { model.selectedTopic = e.target.value; } },
        model.snapshot.topics.map(t => h("option", { value: t.topic, selected: t.topic === model.selectedTopic }, t.topic)));
      const error = model.error ? h("p", { class: "self-test-error", role: "alert" }, model.error) : null;
      let stage;
      if (model.phase === "loading") {
        stage = h("div", { class: "self-test-loading", role: "status" }, h("span", { class: "typing" }, h("i"), h("i"), h("i")), "Ετοιμάζω την ερώτηση…");
      } else if (model.phase === "choose") {
        const customSelect = model.snapshot.custom_questions.length ? h("div", { class: "self-custom-reuse" },
          h("label", {}, "Οι ερωτήσεις μου"),
          h("select", { class: "input", "aria-label": "Προηγούμενες δικές μου ερωτήσεις", onchange: e => {
            model.chosenQuestion = e.target.value; model.chosenQuestionTopic = model.snapshot.custom_questions.find(q => q.question === e.target.value)?.topic || model.selectedTopic;
          } },
            h("option", { value: "" }, "Διάλεξε προηγούμενη ερώτηση"),
            model.snapshot.custom_questions.map(q => h("option", { value: q.question, selected: q.question === model.chosenQuestion }, q.question))),
          h("button", { class: "btn", type: "button", disabled: model.busy || !model.chosenQuestion, onclick: () => makeQuestion(model.chosenQuestion, model.chosenQuestionTopic || model.selectedTopic) }, "Χρησιμοποίησε την")) : null;
        const custom = h("div", { class: "self-custom-entry" }, h("label", { for: "self-custom-question" }, "Ή γράψε δική σου ερώτηση"),
          h("textarea", { id: "self-custom-question", class: "input", rows: "2", maxlength: "2000", placeholder: "Γράψε μια ερώτηση για να ελέγξεις το AI αντίγραφό σου…",
            oninput: e => { model.customDraft = e.target.value; } }),
          h("button", { class: "btn", type: "button", disabled: model.busy || !model.customDraft.trim(), onclick: () => makeQuestion(model.customDraft.trim()) }, "Χρησιμοποίησε τη δική μου"));
        stage = h("div", { class: "self-test-stage" },
          h("p", {}, "Το σύστημα επιλέγει πρώτα θέματα που χρειάζονται training. Μπορείς να απαντήσεις σε ερώτηση που δημιουργεί το AI ή να δοκιμάσεις μία δική σου."),
          h("label", {}, "Θέμα"), topicSelect,
          h("button", { class: "btn primary", type: "button", disabled: model.busy, onclick: () => makeQuestion() }, "Δημιούργησε ερώτηση από AI"),
          customSelect, custom);
      } else if (model.phase === "answer") {
        const answer = h("textarea", { class: "input self-answer-input", rows: "4", maxlength: "4000", placeholder: "Γράψε πώς θα απαντούσες εσύ…",
          "aria-label": "Η δική σου απάντηση", oninput: e => { model.answer = e.target.value; } });
        answer.value = model.answer;
        stage = h("div", { class: "self-test-stage" }, h("p", { class: "self-topic-chip" }, model.current.topic),
          h("h3", { class: "self-question" }, model.current.question), answer,
          h("button", { class: "btn primary", type: "button", disabled: model.busy, onclick: submitAnswer }, model.busy ? "Ζητάω απάντηση…" : "Δες τι θα απαντούσε το AI"));
      } else if (model.phase === "review") {
        stage = h("div", { class: "self-test-stage" }, h("p", { class: "self-topic-chip" }, model.current.topic),
          h("h3", { class: "self-question" }, model.current.question),
          h("div", { class: "self-compare" }, h("section", {}, h("h4", {}, "Η απάντησή σου"), h("p", {}, model.current.user_answer)),
            h("section", {}, h("h4", {}, "Η απάντηση του AI"), h("p", {}, model.current.twin_answer))),
          h("p", {}, "Σε αντιπροσωπεύει η απάντηση του AI;"),
          h("div", { class: "self-test-actions" }, h("button", { class: "btn primary", type: "button", disabled: model.busy, onclick: () => rate("correct") }, "Ναι, είναι σωστή"),
            h("button", { class: "btn", type: "button", disabled: model.busy, onclick: () => { model.correctionOpen = true; render(); } }, "Όχι, χρειάζεται training")),
          model.correctionOpen ? h("div", { class: "self-correction" }, h("label", { for: "self-correction-text" }, "Προαιρετικά, γράψε τη σωστή εκδοχή"),
            h("textarea", { id: "self-correction-text", class: "input", rows: "3", maxlength: "4000", placeholder: "Τι θα έπρεπε να απαντήσει;",
              oninput: e => { model.correction = e.target.value; } }),
            h("div", { class: "self-test-actions" }, h("button", { class: "btn", type: "button", disabled: model.busy,
              onclick: () => rate("wrong") }, "Σήμανση λάθους μόνο"),
              h("button", { class: "btn primary", type: "button", disabled: model.busy || !model.correction.trim(),
                onclick: () => rate("wrong", model.correction.trim()) }, "Αποθήκευση διόρθωσης"))) : null);
      } else {
        const topic = model.snapshot.topics.find(t => t.topic === model.current.topic);
        stage = h("div", { class: "self-test-stage self-test-result", role: "status" },
          h("p", { class: "self-topic-chip" }, model.current.topic),
          h("h3", {}, model.lastFeedback === "correct" ? "Η απάντηση καταγράφηκε ως σωστή" : "Το feedback για training αποθηκεύτηκε"),
          h("p", {}, topic?.verified ? "Το θέμα είναι επαληθευμένο: 3 συνεχόμενες σωστές απαντήσεις." : `Πρόοδος θέματος: ${topic?.streak || 0}/3 συνεχόμενες σωστές απαντήσεις.`),
          model.lastFeedback === "wrong" ? h("p", {}, model.current.correction ? "Η διόρθωση μπήκε στο προφίλ σου ως επιβεβαιωμένη από εσένα γνώση· το AI σου τη χρησιμοποιεί από τώρα." : "Το λάθος καταγράφηκε. Χωρίς διόρθωση, το AI δεν προσθέτει νέα σωστή απάντηση.") : null,
          h("div", { class: "self-test-actions" }, h("button", { class: "btn primary", type: "button", onclick: () => { model.phase = "choose"; model.current = null; model.lastFeedback = null; render(); } }, "Επόμενη ερώτηση"),
            h("button", { class: "btn", type: "button", onclick: () => done(false) }, "Τέλος")));
      }
      fill(panel, progress(), error, stage, publications(), history(),
        h("p", { class: "self-test-privacy" }, "Η πρόοδος φαίνεται μόνο σε εσένα. Οι διορθώσεις σου γίνονται μέρος του προφίλ σου και μπορείς να τις αναιρέσεις."));
    }
    render();
    return { focus: close, node: frame };
  });
}
function talkTo(p) {
  if (!p.mirror_id) return;
  if (silentEmployeeAccess(p)) return;
  if (p.is_me) return startSelfTest();
  const m = state.session.mirrors.find(x => x.id === p.mirror_id);
  if (p.can_chat && m) return openMirror(m);
  const mine = state.session.mirrors.map(personFor)[0];
  const text = p.is_me ? "Αυτό είσαι εσύ. Το AI σου απαντά σε όσους αναφέρονται σε σένα· εσύ μιλάς με το AI των προϊσταμένων σου."
    : `Το AI αντίγραφο του προσώπου «${p.name}» δεν είναι διαθέσιμο για σένα: ${personNote(p).toLowerCase()}.`;
  infoBox(p.is_me ? "Εσύ" : p.name, text, mine ? { label: `Μίλα με ${mine.name}`, run: () => openMirror(state.session.mirrors[0]) } : null);
}
function personCard(p, extraClass = "") {
  const me = p.is_me ?? p.id === state.session.user.employee_id;
  const note = me ? REASONS[p.mirror_id ? "self" : "self_no_ai"] : personNote(p);
  const silent = silentEmployeeAccess(p);
  const pill = me ? (p.mirror_id ? h("span", { class: "pill go" }, icon(I.chat, 13), "Self-test") : null)
    : p.can_chat ? h("span", { class: "pill go" }, icon(I.chat, 13), "Συνομίλησε")
    : p.mirror_id ? h("span", { class: "pill locked" }, icon(I.lock, 12), "Μη διαθέσιμο") : null;
  const dept = DEPARTMENTS[(p.department || "").toLowerCase()];
  return h(p.mirror_id && !silent ? "button" : "div", { class: "pnode " + extraClass + (p.can_chat ? " can" : "") + (me ? " is-me" : "") + (p.mirror_id ? "" : " no-ai"),
      "aria-label": `${p.name}, ${p.job_title}${dept ? ", " + dept : ""}${note ? ". " + note : ""}`, onclick: p.mirror_id && !silent ? () => talkTo(p) : null },
    me ? h("span", { class: "tag" }, "εσύ") : null,
    h("div", { class: "r" }, avatar(p, "", p.can_chat), h("div", { class: "t" }, h("b", {}, p.name), h("span", { class: "role" }, p.job_title), dept ? h("span", { class: "dept" }, dept) : null)),
    note ? h("p", { class: "why" }, note) : null, pill);
}
function homeView() {
  const stage = h("div", { class: "stage", role: "group", "aria-label": "Πυραμίδα εταιρείας" });
  const draw = () => {
    const people = state.people;
    if (!people.length) {
      fill(stage, h("div", { class: "team-empty", role: "status" },
        h("p", {}, "Η ομάδα δεν είναι διαθέσιμη αυτή τη στιγμή."),
        state.hierarchyError ? h("button", { class: "btn", type: "button", onclick: e => retryHierarchy(e.currentTarget) }, "Δοκίμασε ξανά") : null));
      return;
    }
    const { pos, leaves } = layoutTree(people);
    stage.classList.remove("as-tree");
    const W = stage.clientWidth, H = stage.clientHeight;
    stage.style.setProperty("--card-w", Math.round(Math.max(220, Math.min(300, W / Math.max(leaves, 1) - 28))) + "px");
    if (W / Math.max(leaves, 1) < 248) {
      const kids = id => people.filter(p => p.manager_id === id);
      const item = p => h("li", {}, personCard(p, "flat"), kids(p.id).length ? h("ul", {}, kids(p.id).map(item)) : null);
      stage.classList.add("as-tree");
      fill(stage, h("ul", { class: "tree" }, people.filter(p => !p.manager_id).map(item)));
      return;
    }
    stage.classList.remove("as-tree");
    const css = v => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
    const svg = s("svg", { class: "links", viewBox: `0 0 ${W} ${H}`, "aria-hidden": "true" },
      s("defs", {}, s("linearGradient", { id: "pg", gradientUnits: "userSpaceOnUse", x1: 0, y1: 0, x2: 0, y2: H },
        s("stop", { offset: 0, "stop-color": css("--violet"), "stop-opacity": ".7" }), s("stop", { offset: 1, "stop-color": css("--teal"), "stop-opacity": ".25" }))));
    const cards = Object.fromEntries(people.map(p => { const n = personCard(p); n.dataset.personId = p.id; n.style.left = pos[p.id].x * 100 + "%"; n.style.top = pos[p.id].y * 100 + "%"; return [p.id, n]; }));
    fill(stage, svg, Object.values(cards));
    people.forEach(p => {
      if (!p.manager_id || !pos[p.manager_id]) return;
      const a = [pos[p.manager_id].x * W, pos[p.manager_id].y * H + cards[p.manager_id].offsetHeight / 2], b = [pos[p.id].x * W, pos[p.id].y * H - cards[p.id].offsetHeight / 2], my = (a[1] + b[1]) / 2;
      const d = `M${a[0]},${a[1]} C${a[0]},${my} ${b[0]},${my} ${b[0]},${b[1]}`;
      svg.appendChild(s("path", { d, "data-parent": p.manager_id, "data-child": p.id, stroke: "url(#pg)", "stroke-width": "1.5", fill: "none" }));
      if (!reduceMotion) svg.appendChild(s("circle", { r: 3, fill: css("--teal") },
        s("animateMotion", { dur: "3.4s", repeatCount: "indefinite", path: d }), s("animate", { attributeName: "opacity", values: "0;1;0", dur: "3.4s", repeatCount: "indefinite" })));
    });
  };
  let drawPending = false;
  const scheduleDraw = () => {
    if (drawPending) return;
    drawPending = true;
    requestAnimationFrame(() => { drawPending = false; if (stage.isConnected) draw(); });
  };
  scheduleDraw();
  document.fonts?.ready.then(scheduleDraw);
  state.redraw = scheduleDraw;
  return h("div", { class: "home" },
    h("header", { class: "home-head" },
      h("button", { class: "iconbtn menu-toggle", "aria-label": "Μενού", onclick: () => $("#app").classList.add("nav-open") }, icon(I.menu))),
    h("div", { class: "home-body" }, stage,
      h("div", { class: "legend" }, h("span", {}, h("i", { class: "dot go" }), "Μπορείς να μιλήσεις"), h("span", {}, h("i", { class: "dot locked" }), "Μη διαθέσιμο για σένα · η αιτία γράφεται στην κάρτα"))));
}
function dismissOverlay() { overlayCloser?.(false); }
function showOverlay(build, finish = () => {}) {
  dismissOverlay();
  const overlay = $("#overlay"), root = $("#root"), previous = document.activeElement;
  const wasInert = root.inert;
  let open = true;
  const focusable = () => [...overlay.querySelectorAll('button,[href],input,textarea,select,[tabindex]:not([tabindex="-1"])')]
    .filter(el => !el.disabled && el.getClientRects().length && getComputedStyle(el).visibility !== "hidden");
  const done = value => {
    if (!open) return;
    open = false; overlayCloser = null;
    overlay.classList.remove("on"); fill(overlay); overlay.onclick = null;
    document.removeEventListener("keydown", keydown, true);
    document.removeEventListener("focusin", focusin, true);
    root.inert = wasInert;
    if (previous?.isConnected) previous.focus();
    finish(value);
  };
  const keydown = event => {
    if (event.key === "Escape") { event.preventDefault(); event.stopPropagation(); done(false); return; }
    if (event.key !== "Tab") return;
    const items = focusable(), first = items[0], last = items.at(-1);
    if (!first) { event.preventDefault(); return; }
    const outside = !overlay.contains(document.activeElement);
    if (event.shiftKey && (document.activeElement === first || outside)) { event.preventDefault(); last.focus(); }
    else if (!event.shiftKey && (document.activeElement === last || outside)) { event.preventDefault(); first.focus(); }
  };
  const focusin = event => { if (!overlay.contains(event.target)) focusable()[0]?.focus(); };
  const { node, focus } = build(done);
  fill(overlay, node); overlay.classList.add("on"); root.inert = true;
  overlayCloser = done;
  overlay.onclick = event => { if (event.target === overlay) done(false); };
  document.addEventListener("keydown", keydown, true);
  document.addEventListener("focusin", focusin, true);
  setTimeout(() => { if (open) focus.focus(); }, 20);
}
function infoBox(title, text, action) {
  showOverlay(done => {
    const primary = action ? h("button", { class: "btn primary", onclick: () => { done(false); action.run(); } }, action.label) : h("button", { class: "btn primary", onclick: () => done(false) }, "Εντάξει");
    return { focus: primary, node: h("div", { class: "dialog", role: "dialog", "aria-modal": "true", "aria-label": title }, h("h4", {}, title), h("p", {}, text),
      h("div", { class: "row" }, action ? h("button", { class: "btn", onclick: () => done(false) }, "Κλείσιμο") : null, primary)) };
  });
}
/* Keyboard: "/" writes a message, Esc stops any voice, as in the earlier MIRROR chat. */
document.addEventListener("keydown", e => {
  const typing = /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement?.tagName || "") || document.activeElement?.isContentEditable;
  if (e.key === "/" && !typing && state.view === "chat" && !$("#overlay")?.classList.contains("on")) { e.preventDefault(); $("#composer")?.focus(); }
  if (e.key === "Escape" && (speaking || state.audio) && !$("#overlay")?.classList.contains("on")) { stopSpeaking(); stopVoice({ keepAvatar: true }); }
});
let resizeTimer;
window.addEventListener("resize", () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(() => state.view === "home" && state.redraw && state.redraw(), 120); });

/* ---------- answers: confidence, evidence chips and actions inside the answer (as in the earlier MIRROR chat) ---------- */
function showEvidence(x, p, focus) {
  showOverlay(done => {
    const close = h("button", { class: "iconbtn", type: "button", "aria-label": "Κλείσιμο", onclick: () => done(false) }, icon(I.close));
    const traits = focus ? [focus, ...x.traits.filter(t => t !== focus)] : x.traits;
    return { focus: close, node: h("section", { class: "dialog evidence-dialog", role: "dialog", "aria-modal": "true", "aria-label": "Από πού το ξέρω" },
      h("header", { class: "evidence-head" }, h("div", {}, h("p", { class: "self-test-eyebrow" }, "MIRROR / ΑΠΟΔΕΙΞΕΙΣ"),
        h("h3", {}, "Από πού το ξέρω"), h("p", { class: "muted small" }, `Τι χρησιμοποίησε το AI αντίγραφο του προσώπου «${p.name}» για αυτή την απάντηση.`)), close),
      x.why ? h("p", { class: "why-text" }, x.why) : null,
      traits.length ? h("div", { class: "why-group" }, h("h5", {}, "Χαρακτηριστικά του προσώπου"),
        traits.map(t => h("div", { class: "why-trait" + (t.inherited_from ? " inherited" : "") + (t === focus ? " focus" : "") },
          h("small", {}, t.inherited_from ? `Κανόνας εταιρείας από ${t.inherited_from}` : t.kind), h("span", {}, t.text)))) : null,
      x.sources.length ? h("div", { class: "why-group" }, h("h5", {}, "Πραγματικά μηνύματα και έγγραφα"),
        x.sources.map(src => h("blockquote", { class: "why-src" }, h("p", {}, "«" + src.quote + "»"), h("small", {}, (src.own ? "Δικό του/της · " : "") + src.label)))) : null,
      !traits.length && !x.sources.length ? h("p", { class: "muted" }, "Δεν υπάρχουν αποδείξεις για αυτή την απάντηση· γι' αυτό το AI δηλώνει ότι δεν είναι σίγουρο.") : null,
      h("div", { class: "row" }, h("button", { class: "btn primary", type: "button", onclick: () => done(false) }, "Εντάξει"))) };
  });
}
function answerMeta(m, p) {
  const x = m.explain; if (!x) return null;
  const pct = typeof x.confidence === "number" ? Math.round(x.confidence * 100) : null;
  return h("div", { class: "bubble-meta" },
    x.boundary ? h("span", { class: "chip warn" }, icon(I.lock, 12), "Προσωπικό όριο")
      : pct !== null ? h("span", { class: "chip conf", title: "Πόσο στηρίζεται η απάντηση στα δεδομένα του προσώπου" }, h("i", { style: { "--p": pct + "%" } }), `${pct}%`) : null,
    x.unsure && !x.boundary ? h("span", { class: "chip warn" }, "δεν είναι σίγουρο") : null,
    x.traits.slice(0, 3).map(t => h("button", { type: "button", class: "chip chip-btn" + (t.inherited_from ? " co" : ""), title: t.text, onclick: () => showEvidence(x, p, t) },
      icon(I.search, 12), t.inherited_from ? `κανόνας από ${t.inherited_from}` : t.kind.toLowerCase())),
    x.sources.length ? h("button", { type: "button", class: "chip chip-btn", onclick: () => showEvidence(x, p) }, icon(I.chat, 12), `${x.sources.length} ${x.sources.length === 1 ? "απόδειξη" : "αποδείξεις"}`) : null);
}
/* Read any answer aloud: the person's own voice (ElevenLabs) when the server has it, otherwise the browser's Greek voice. */
let speaking = null;
function stopSpeaking() {
  if (speaking?.audio) { speaking.audio.pause(); URL.revokeObjectURL(speaking.audio.src); }
  try { speechSynthesis.cancel(); } catch { /* not supported */ }
  const btn = speaking?.btn; speaking = null; if (btn) { btn.setAttribute("aria-pressed", "false"); fill(btn, icon(I.speaker, 15)); }
}
async function speakText(text, btn) {
  if (speaking?.btn === btn) { stopSpeaking(); return; }
  stopSpeaking(); stopVoice();
  const mine = speaking = { btn, audio: null };
  btn.setAttribute("aria-pressed", "true"); fill(btn, icon(I.stop, 15));
  const done = () => { if (speaking === mine) stopSpeaking(); };
  try {
    const res = await fetch("/api/voice/speak", { method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-Mirror-Request": "1" }, body: JSON.stringify({ text, target: state.mirror?.id }) });
    if (!res.ok) throw new Error("no premium voice");
    const blob = await res.blob(); if (speaking !== mine) return;
    mine.audio = new Audio(URL.createObjectURL(blob)); mine.audio.onended = done; await mine.audio.play();
  } catch {
    if (speaking !== mine) return;
    try {
      const u = new SpeechSynthesisUtterance(text); u.lang = "el-GR"; u.onend = done; u.onerror = done; speechSynthesis.speak(u);
    } catch { done(); toast("Η φωνή δεν είναι διαθέσιμη σε αυτόν τον browser.", true); }
  }
}
function paintFollowups() {
  const box = $("#followups"); if (!box) return;
  const lastMsg = state.messages[state.messages.length - 1];
  const show = !state.busy && lastMsg?.role === "ai" && !lastMsg.explain?.boundary;
  box.hidden = !show; if (!show) { fill(box); return; }
  const q = [...state.messages].reverse().find(m => m.role === "user")?.text || "";
  const followups = lastMsg.explain?.mode === "verified"
    ? (q === "γιατί;" ? [] : ["γιατί;"])
    : ["γιατί;", "και τι άλλο;", q ? "Πώς θα το έλεγες σε πελάτη;" : null].filter(Boolean);
  box.hidden = followups.length === 0;
  fill(box, followups
    .map(f => h("button", { type: "button", class: "chip chip-btn", onclick: () => send(f) }, f)));
}
function paintCount() {
  const box = $("#composer"), out = $("#char-count"); if (!box || !out) return;
  const n = box.value.length; out.textContent = n > 3200 ? `${n}/4000` : "";
}
function editQuestion(text) {
  const box = $("#composer"); if (!box || state.busy) return;
  box.value = text; autosize(box); paintCount(); box.focus(); box.setSelectionRange(text.length, text.length);
  toast("Διόρθωσε την ερώτηση και πάτα Enter.");
}
// Επεξήγηση: Αποδίδει το ιστορικό ως κείμενο μαζί με εξηγήσεις και διαθέσιμες ενέργειες.
function paintChat() {
  const list = $("#messages"); if (!list) return;
  paintVoiceControls();
  if (!state.mirror) { fill(list, h("div", { class: "welcome" }, logo(64), h("h2", {}, "Δεν υπάρχει διαθέσιμο AI"), h("p", {}, "Ο ρόλος σου δεν έχει ακόμη πρόσβαση σε κάποιο πρόσωπο."))); return; }
  const p = personFor(state.mirror);
  if (!state.messages.length) {
    fill(list, h("div", { class: "welcome" }, avatar(p, "lg", true),
      h("h2", {}, new Date().getHours() < 12 ? "Καλημέρα!" : "Καλησπέρα!"),
      h("p", {}, `Είσαι σε συνομιλία με το AI αντίγραφο του προσώπου «${p.name}». Ρώτα ό,τι θα ρωτούσες κι από κοντά, και μετά ρώτα «γιατί;» για να δεις από πού το ξέρει.`),
      h("div", { class: "ideas" }, (state.suggestions || []).map(q => h("button", { onclick: () => send(q) }, q)))));
    return;
  }
  const last = state.messages.length - 1;
  const lastQuestion = [...state.messages].reverse().find(m => m.role === "user")?.text;
  fill(list, state.messages.map((m, i) => {
    if (m.role === "loading") return h("div", {}, h("div", { class: "skeleton", style: { width: "60%" } }), h("div", { class: "skeleton", style: { width: "40%" } }));
    if (m.role === "user") return h("div", { class: "row-msg user" },
      h("button", { class: "edit-q", type: "button", "aria-label": "Επεξεργασία και ξανά", title: "Επεξεργασία και ξανά", onclick: () => editQuestion(m.text) }, icon(I.edit, 14)),
      h("div", { class: "bubble" }, m.voice ? h("span", { class: "voice-tag", "aria-label": "φωνητικό" }, icon(I.mic, 13)) : null, m.text));
    if (m.role === "typing") return h("div", { class: "row-msg ai" }, avatar(p), h("span", { class: "typing", "aria-label": "Γράφει…" }, h("i"), h("i"), h("i")));
    if (m.role === "note") return h("div", { class: "row-msg note" }, h("div", { class: "bubble" }, m.text));
    const text = h("div", { class: "bubble-text" });
    if (m.fresh && !reduceMotion) { m.fresh = false; typewrite(text, m.text); } else text.textContent = m.text;
    const up = h("button", { "aria-label": "Μοιάζει με το πρόσωπο", title: "Μοιάζει με το πρόσωπο" }, icon(I.up, 15));
    const down = h("button", { "aria-label": "Δεν μοιάζει με το πρόσωπο", title: "Δεν μοιάζει με το πρόσωπο" }, icon(I.down, 15));
    const rate = (btn, other, rating, label) => async () => {
      const ctx = conversationContext(); btn.disabled = true;
      try {
        await api(`/api/mirrors/${ctx.mirror}/persona-feedback`, { rating }, ctx);
        btn.setAttribute("aria-pressed", "true"); other.setAttribute("aria-pressed", "false"); m.rated = rating; toast(label);
      } catch (error) { if (currentContext(ctx)) toast(error.message, true); }
      finally { if (currentContext(ctx)) btn.disabled = false; }
    };
    up.onclick = rate(up, down, "faithful", "Ευχαριστούμε! Σημειώθηκε ότι μοιάζει."); down.onclick = rate(down, up, "uncharacteristic", "Ευχαριστούμε. Σημειώθηκε ότι δεν μοιάζει.");
    if (m.rated) (m.rated === "faithful" ? up : down).setAttribute("aria-pressed", "true");
    const listen = h("button", { "aria-label": "Άκουσε", title: "Άκουσε" }, icon(I.speaker, 15));
    listen.onclick = () => m.voiceTurn && mode() !== "text" ? loadAvatar(m.voiceTurn) : speakText(m.text, listen);
    return h("div", { class: "row-msg ai" + (i === last ? " latest" : "") }, avatar(p), h("div", { class: "body" },
      h("div", { class: "bubble twin" }, text, answerMeta(m, p),
        h("div", { class: "actions" }, listen,
          h("button", { "aria-label": "Αντιγραφή", title: "Αντιγραφή", onclick: async () => toast(...(await copyText(m.text) ? ["Αντιγράφηκε."] : ["Δεν επιτράπηκε η αντιγραφή.", true])) }, icon(I.copy, 15)),
          up, down,
          i === last && lastQuestion ? h("button", { class: "again", "aria-label": "Ξαναρώτα", title: "Ξαναρώτα την ίδια ερώτηση", onclick: () => send(lastQuestion) }, icon(I.back, 15), h("span", {}, "Ξανά")) : null))));
  }));
  paintFollowups();
  const sc = $("#scroll"); sc.scrollTop = sc.scrollHeight;
}
function typewrite(node, text) {
  const ctx = conversationContext();
  let i = 0; node.classList.add("caret");
  const step = Math.max(2, Math.round(text.length / 90));
  const timer = setInterval(() => {
    if (!node.isConnected || !currentContext(ctx)) { clearInterval(timer); return; }
    const sc = $("#scroll"), follow = sc && sc.scrollHeight - sc.clientHeight - sc.scrollTop < 48;
    i += step; node.textContent = text.slice(0, i);
    if (follow) sc.scrollTop = sc.scrollHeight;
    if (i >= text.length) { clearInterval(timer); node.textContent = text; node.classList.remove("caret"); } }, 16);
}
/* Clipboard API first; when the browser denies it (permissions, older engines), copy via a selection. */
async function copyText(text) {
  try { await navigator.clipboard.writeText(text); return true; } catch { /* fall back below */ }
  const area = h("textarea", { readonly: true, "aria-hidden": "true", style: { position: "fixed", opacity: "0", top: "0", left: "0" } });
  area.value = text; document.body.appendChild(area); area.select();
  let ok = false; try { ok = document.execCommand("copy"); } catch { ok = false; }
  area.remove(); return ok;
}
function autosize(t) { t.style.height = "auto"; t.style.height = Math.min(t.scrollHeight, 180) + "px"; }
async function removeThread(t) {
  const ctx = conversationContext();
  if (!(await confirmBox("Διαγραφή συζήτησης;", `Η «${t.title}» θα διαγραφεί οριστικά.`))) return;
  if (!currentContext(ctx)) return;
  try {
    await api(`/api/mirrors/${ctx.mirror}/conversations/${t.conversation_id}/delete`, {}, ctx);
    state.threads = state.threads.filter(x => x !== t);
    if (String(t.conversation_id) === state.thread) newChat(); else paintSidebar();
    toast("Η συζήτηση διαγράφηκε.");
  } catch (error) { if (currentContext(ctx)) toast(error.message, true); }
}
function confirmBox(title, text) {
  return new Promise(resolve => showOverlay(done => {
    const yes = h("button", { class: "btn primary", onclick: () => done(true) }, "Διαγραφή");
    return { focus: yes, node: h("div", { class: "dialog", role: "alertdialog", "aria-modal": "true", "aria-label": title }, h("h4", {}, title), h("p", {}, text),
      h("div", { class: "row" }, h("button", { class: "btn", onclick: () => done(false) }, "Άκυρο"), yes)) };
  }, resolve));
}
function closeNav() { $("#app")?.classList.remove("nav-open"); }
function toggleTheme() { const r = document.documentElement; r.dataset.theme = r.dataset.theme === "light" ? "dark" : "light"; store("mirror-theme", r.dataset.theme); $(".menu")?.classList.remove("on"); }
// Επεξήγηση: Η αποσύνδεση κλείνει τη συνεδρία και ακυρώνει τους ενεργούς πόρους της διεπαφής.
async function logout() {
  const session = state.session;
  $(".menu")?.classList.remove("on");
  invalidateConversation();
  state.messages = state.messages.filter(message => !["typing", "loading"].includes(message.role));
  paintChat();
  try { await api("/api/logout", {}); }
  catch (error) {
    if (state.session === session) toast("Η αποσύνδεση δεν ολοκληρώθηκε. Έλεγξε τη σύνδεσή σου και δοκίμασε ξανά.", true);
    return;
  }
  if (state.session === session) clearSession();
}
window.addEventListener("pagehide", () => invalidateConversation());
window.addEventListener("message", event => {
  const frame = $("#avatar-frame");
  if (event.origin === location.origin && frame && event.source === frame.contentWindow
      && event.data?.type === "mirror:avatar-start" && event.data.mirror_id === state.mirror?.id
      && event.data.view_id === new URL(frame.src, location.href).searchParams.get("v")) {
    stopVoice({ keepAvatar: true });
    if (avatarFallback?.view === event.data.view_id) clearTimeout(avatarFallback.timer);  // started: wait for its own outcome
  }
  if (event.origin === location.origin && frame && event.source === frame.contentWindow
      && event.data?.type === "mirror:avatar-fallback" && event.data.mirror_id === state.mirror?.id
      && event.data.view_id === new URL(frame.src, location.href).searchParams.get("v")
      && avatarFallback?.view === event.data.view_id && avatarFallback.turn === event.data.turn) {
    avatarFellBack(avatarFallback, conversationContext());
  }
  if (event.origin === location.origin && frame && event.source === frame.contentWindow
      && event.data?.type === "mirror:access-denied" && event.data.mirror_id === state.mirror?.id
      && event.data.view_id === new URL(frame.src, location.href).searchParams.get("v")) {
    withdrawMirror(event.data.mirror_id);
  }
});


document.addEventListener("click", e => { if (!e.target.closest(".me-wrap")) $(".menu")?.classList.remove("on"); });
document.addEventListener("keydown", e => {
  if (e.key === "Escape") { closeNav(); $(".menu")?.classList.remove("on"); }
  if (e.key === "/" && state.session && !state.voiceOpen && !e.target.closest("input,textarea")) { e.preventDefault(); $("#composer")?.focus(); }
});
(async function boot() {
  document.documentElement.dataset.theme = load("mirror-theme") || (matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark");
  try { const s = await api("/api/session"); state.session = s.user ? s : null; } catch { state.session = null; }
  if (state.session) await start(); else render();
})();
