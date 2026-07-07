"use strict";

const HEADLINE_COUNT = 10;
const SOURCE_PRIMARY = "data.json";
const SOURCE_FALLBACK = "data.json";

const state = {
  articles: [],
  sources: [],
  errors: {},
  filter: "all",
  query: "",
  sort: "new",
};

const els = {
  updated: document.getElementById("updated"),
  refresh: document.getElementById("refresh"),
  briefingGrid: document.getElementById("briefing-grid"),
  headlines: document.getElementById("headlines"),
  headlinesToggle: document.getElementById("headlines-toggle"),
  headlinesList: document.getElementById("headlines-list"),
  search: document.getElementById("search"),
  sort: document.getElementById("sort"),
  filters: document.getElementById("filters"),
  status: document.getElementById("status"),
  cards: document.getElementById("cards"),
  countFoot: document.getElementById("count-foot"),
};

function escapeHtml(str) {
  return String(str ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

function compactNumber(value) {
  const n = Number(value || 0);
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

function timeAgo(ts) {
  if (!ts) return "";
  const diff = Math.max(0, Math.floor(Date.now() / 1000) - ts);
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  if (diff < 2592000) return `${Math.floor(diff / 86400)}d ago`;
  return new Date(ts * 1000).toLocaleDateString();
}

async function loadData() {
  els.refresh.classList.add("spinning");
  els.status.textContent = "Loading X channel snapshot…";
  try {
    const data = await tryFetch(SOURCE_PRIMARY, true) || await tryFetch(SOURCE_FALLBACK, false);
    if (!data) throw new Error("No data source responded");
    state.articles = data.articles || [];
    state.sources = data.sources || [];
    state.errors = data.errors || {};
    render();
    els.updated.textContent = data.generated_ts ? `Updated ${timeAgo(data.generated_ts)}` : "Snapshot loaded";
    const errorCount = Object.keys(state.errors).length;
    els.status.textContent = errorCount ? `${errorCount} channel(s) had refresh errors; showing available data.` : "";
  } catch (err) {
    els.status.textContent = `Load failed: ${err.message}`;
    els.cards.innerHTML = `<div class="empty">Could not load the radar snapshot.</div>`;
  } finally {
    els.refresh.classList.remove("spinning");
  }
}

async function tryFetch(url, bustCache) {
  try {
    const u = bustCache ? `${url}${url.includes("?") ? "&" : "?"}t=${Date.now()}` : url;
    const res = await fetch(u, { cache: "no-store" });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

function filtered() {
  const q = state.query.trim().toLowerCase();
  const list = state.articles.filter((a) => {
    if (state.filter !== "all" && a.source_id !== state.filter) return false;
    if (!q) return true;
    const haystack = [
      a.title, a.summary, a.source, a.handle, a.lane,
      ...(a.categories || []), ...(a.tickers || []),
    ].join(" ").toLowerCase();
    return haystack.includes(q);
  });
  return list.sort((a, b) => {
    if (state.sort === "hot") {
      return (b.metrics?.hot_score || 0) - (a.metrics?.hot_score || 0);
    }
    return (b.published_ts || 0) - (a.published_ts || 0);
  });
}

function renderBriefing() {
  const topTickers = new Map();
  const topTags = new Map();
  for (const a of state.articles) {
    for (const t of a.tickers || []) topTickers.set(t, (topTickers.get(t) || 0) + 1);
    for (const t of a.categories || []) topTags.set(t, (topTags.get(t) || 0) + 1);
  }
  const latest = state.articles[0];
  const hottest = [...state.articles].sort((a, b) => (b.metrics?.hot_score || 0) - (a.metrics?.hot_score || 0))[0];
  const cards = [
    ["Channels", state.sources.length, "tracked X accounts"],
    ["Posts", state.articles.length, latest ? `latest from @${latest.handle}` : "no posts"],
    ["Top themes", mapTop(topTags), "by recent mentions"],
    ["Tickers", mapTop(topTickers), "most repeated"],
    ["Hottest", hottest ? `@${hottest.handle}` : "-", hottest ? compactNumber(hottest.metrics?.views) + " views" : ""],
  ];
  els.briefingGrid.innerHTML = cards.map(([label, value, hint]) => `
    <div class="brief-card">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(value)}</strong>
      <small>${escapeHtml(hint)}</small>
    </div>
  `).join("");
}

function mapTop(map) {
  const items = [...map.entries()].sort((a, b) => b[1] - a[1]).slice(0, 3).map(([k]) => k);
  return items.length ? items.join(" · ") : "-";
}

function renderFilters() {
  const total = state.articles.length;
  const chips = [`<button class="chip ${state.filter === "all" ? "active" : ""}" data-id="all">All<span>${total}</span></button>`];
  for (const s of state.sources) {
    chips.push(`<button class="chip ${state.filter === s.id ? "active" : ""}" data-id="${escapeHtml(s.id)}">${escapeHtml(s.name)}<span>${s.count ?? 0}</span></button>`);
  }
  els.filters.innerHTML = chips.join("");
  els.filters.querySelectorAll(".chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      state.filter = chip.dataset.id;
      render();
    });
  });
}

function renderHeadlines() {
  const top = [...state.articles]
    .sort((a, b) => (b.metrics?.hot_score || 0) - (a.metrics?.hot_score || 0))
    .slice(0, HEADLINE_COUNT);
  els.headlinesList.innerHTML = top.map((a, i) => `
    <li>
      <span class="hl-rank">${i + 1}</span>
      <a class="hl-link" href="${escapeHtml(a.link)}" target="_blank" rel="noopener">${escapeHtml(a.title)}</a>
      <span class="hl-src">@${escapeHtml(a.handle)} · ${timeAgo(a.published_ts)} · ${compactNumber(a.metrics?.views)} views</span>
    </li>
  `).join("");
}

function cardHtml(a) {
  const tags = [...(a.categories || []), ...(a.tickers || [])].slice(0, 8)
    .map((t) => `<span class="tag">${escapeHtml(t)}</span>`)
    .join("");
  const media = (a.media || [])[0] ? `<img class="media" src="${escapeHtml(a.media[0])}" alt="" loading="lazy" />` : "";
  return `<article class="card">
    <div class="card-top">
      <span class="badge">${escapeHtml(a.source)}</span>
      <span class="lane">${escapeHtml(a.lane)}</span>
      <span class="card-time">${timeAgo(a.published_ts)}</span>
    </div>
    <a class="card-title" href="${escapeHtml(a.link)}" target="_blank" rel="noopener">${escapeHtml(a.title)}</a>
    <p class="card-summary">${escapeHtml(a.summary)}</p>
    ${media}
    <div class="metrics">
      <span>${compactNumber(a.metrics?.views)} views</span>
      <span>${compactNumber(a.metrics?.likes)} likes</span>
      <span>${compactNumber(a.metrics?.retweets)} reposts</span>
    </div>
    <div class="card-foot">${tags}</div>
  </article>`;
}

function renderCards() {
  const list = filtered();
  els.countFoot.textContent = `${state.articles.length} posts in snapshot`;
  if (!list.length) {
    els.cards.innerHTML = `<div class="empty">No matching posts.</div>`;
    return;
  }
  els.cards.innerHTML = list.map(cardHtml).join("");
}

function render() {
  renderBriefing();
  renderFilters();
  renderHeadlines();
  renderCards();
}

els.headlinesToggle.addEventListener("click", () => {
  const collapsed = els.headlines.classList.toggle("collapsed");
  els.headlinesToggle.setAttribute("aria-expanded", String(!collapsed));
});

let searchTimer;
els.search.addEventListener("input", (event) => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    state.query = event.target.value;
    renderCards();
  }, 120);
});

els.sort.addEventListener("change", (event) => {
  state.sort = event.target.value;
  renderCards();
});

els.refresh.addEventListener("click", loadData);

loadData();
