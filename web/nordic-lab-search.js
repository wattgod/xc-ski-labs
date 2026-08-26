/**
 * Nordic Lab — Race Search UI
 * Loads race-index.json, renders filterable/searchable race cards.
 */

(function () {
  "use strict";

  let allRaces = [];
  let activeFilter = "all";
  let activeCountry = "";
  let activeSort = "score";
  let searchQuery = "";
  let lastTrackedSignature = "";

  function normalizeSearchQuery(value) {
    return String(value || "").trim().replace(/\s+/g, " ").toLowerCase();
  }

  function loadStateFromURL() {
    const params = new URLSearchParams(window.location.search);
    searchQuery = normalizeSearchQuery(params.get("q"));
    activeFilter = params.get("filter") || "all";
    activeCountry = params.get("country") || "";
    activeSort = params.get("sort") || "score";

    document.getElementById("searchInput").value = searchQuery;
    document.getElementById("countryFilter").value = activeCountry;
    document.getElementById("sortSelect").value = activeSort;
    document.querySelectorAll(".filter-btn").forEach(function (button) {
      button.classList.toggle("active", button.dataset.filter === activeFilter);
    });
  }

  function saveStateToURL() {
    const params = new URLSearchParams();
    if (searchQuery) params.set("q", searchQuery);
    if (activeFilter !== "all") params.set("filter", activeFilter);
    if (activeCountry) params.set("country", activeCountry);
    if (activeSort !== "score") params.set("sort", activeSort);
    const query = params.toString();
    window.history.replaceState({}, "", window.location.pathname + (query ? "?" + query : ""));
  }

  function track(eventName, params) {
    if (typeof gtag !== "function") return;
    gtag("event", eventName, params || {});
  }

  const SERIES_LABELS = {
    worldloppet: "Worldloppet",
    ski_classics_pro_tour: "Ski Classics",
    ski_classics_grand_classic: "Grand Classic",
    ski_classics_challengers: "Challengers",
    euroloppet: "Euroloppet",
    asm_series: "ASM Series",
    estoloppet: "Estoloppet",
    latloppet: "Latloppet",
    swiss_loppet: "Swiss Loppet",
  };

  async function init() {
    try {
      const resp = await fetch("race-index.json");
      const data = await resp.json();
      allRaces = data.races;
      populateCountryFilter();
      loadStateFromURL();
      updateStats();
      render();
      bindEvents();
    } catch (err) {
      document.getElementById("raceGrid").textContent =
        "Failed to load race data.";
    }
  }

  function populateCountryFilter() {
    const countries = new Map();
    for (const r of allRaces) {
      if (r.cc && !countries.has(r.cc)) {
        countries.set(r.cc, r.co);
      }
    }
    const sorted = [...countries.entries()].sort((a, b) =>
      a[1].localeCompare(b[1])
    );
    const sel = document.getElementById("countryFilter");
    for (const [code, name] of sorted) {
      const opt = document.createElement("option");
      opt.value = code;
      opt.textContent = name;
      sel.appendChild(opt);
    }
  }

  function updateStats() {
    const countries = new Set(allRaces.map((r) => r.cc));
    const tiers = { 1: 0, 2: 0, 3: 0, 4: 0 };
    for (const r of allRaces) tiers[r.t]++;

    document.getElementById("stat-races").textContent =
      allRaces.length + " races";
    document.getElementById("stat-countries").textContent =
      countries.size + " countries";
    document.getElementById("stat-tiers").textContent =
      "T1: " + tiers[1] + " | T2: " + tiers[2] + " | T3: " + tiers[3] + " | T4: " + tiers[4];
  }

  function getFilteredRaces() {
    let races = allRaces.slice();

    // Search
    if (searchQuery) {
      races = races.filter((r) => r.st.includes(searchQuery));
    }

    // Tier/discipline filter
    if (activeFilter === "t1") races = races.filter((r) => r.t === 1);
    else if (activeFilter === "t2") races = races.filter((r) => r.t === 2);
    else if (activeFilter === "t3") races = races.filter((r) => r.t === 3);
    else if (activeFilter === "t4") races = races.filter((r) => r.t === 4);
    else if (activeFilter === "classic")
      races = races.filter((r) => r.di === "classic");
    else if (activeFilter === "skate")
      races = races.filter((r) => r.di === "skate");
    else if (activeFilter === "both")
      races = races.filter((r) => r.di === "both");

    // Country filter
    if (activeCountry) {
      races = races.filter((r) => r.cc === activeCountry);
    }

    // Sort
    if (activeSort === "score")
      races.sort((a, b) => b.sc - a.sc || a.n.localeCompare(b.n));
    else if (activeSort === "name")
      races.sort((a, b) => a.n.localeCompare(b.n));
    else if (activeSort === "distance")
      races.sort((a, b) => (b.d || 0) - (a.d || 0));
    else if (activeSort === "founded")
      races.sort((a, b) => (a.yr || 9999) - (b.yr || 9999));
    else if (activeSort === "country")
      races.sort((a, b) => a.co.localeCompare(b.co) || b.sc - a.sc);

    return races;
  }

  function createCard(r) {
    const row = document.createElement("tr");
    const distText = r.d ? r.d + "km" : "";
    const tierClass = "t" + r.t;

    const nameCell = document.createElement("td");
    const tier = document.createElement("span");
    tier.className = "tier-badge " + tierClass;
    tier.textContent = "T" + r.t;
    const name = document.createElement("span");
    name.className = "race-name";
    name.textContent = r.dn || r.n;
    nameCell.append(tier, name);

    const country = document.createElement("td");
    country.textContent = r.co;
    const distance = document.createElement("td");
    distance.className = "mono r";
    distance.textContent = distText;
    const discipline = document.createElement("td");
    discipline.textContent = r.di;
    const score = document.createElement("td");
    score.className = "mono r score-display " + tierClass;
    score.textContent = r.sc;
    const linkCell = document.createElement("td");
    linkCell.className = "r";
    const link = document.createElement("a");
    link.className = "rowlink";
    link.href = "/race/" + encodeURIComponent(r.s) + "/";
    link.textContent = "READ →";
    linkCell.appendChild(link);
    row.append(nameCell, country, distance, discipline, score, linkCell);

    return row;
  }

  function render() {
    const races = getFilteredRaces();
    const grid = document.getElementById("raceGrid");
    grid.replaceChildren();

    for (const r of races) {
      grid.appendChild(createCard(r));
    }

    if (races.length === 0) {
      const row = document.createElement("tr");
      const cell = document.createElement("td");
      cell.colSpan = 6;
      cell.className = "empty-state";
      cell.textContent = "No races match. Try a broader search or clear a filter.";
      row.appendChild(cell);
      grid.appendChild(row);
    }

    document.getElementById("resultsInfo").textContent =
      races.length + " of " + allRaces.length + " races";
    saveStateToURL();

    const signature = [searchQuery, activeFilter, activeCountry, activeSort].join("|");
    if (signature !== lastTrackedSignature && signature.replace(/\|/g, "")) {
      lastTrackedSignature = signature;
      track("race_search", {
        search_term: searchQuery,
        filter: activeFilter,
        country: activeCountry,
        sort: activeSort,
        result_count: races.length
      });
    }
  }

  function bindEvents() {
    // Search
    const searchInput = document.getElementById("searchInput");
    let debounce;
    searchInput.addEventListener("input", function () {
      clearTimeout(debounce);
      debounce = setTimeout(function () {
        searchQuery = normalizeSearchQuery(searchInput.value);
        render();
      }, 200);
    });

    // Filter buttons
    document.querySelectorAll(".filter-btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        document
          .querySelectorAll(".filter-btn")
          .forEach(function (b) { b.classList.remove("active"); });
        btn.classList.add("active");
        activeFilter = btn.dataset.filter;
        render();
      });
    });

    // Country filter
    document
      .getElementById("countryFilter")
      .addEventListener("change", function (e) {
        activeCountry = e.target.value;
        render();
      });

    // Sort
    document
      .getElementById("sortSelect")
      .addEventListener("change", function (e) {
        activeSort = e.target.value;
        render();
      });

    document.getElementById("raceGrid").addEventListener("click", function (event) {
      const link = event.target.closest("a.rowlink");
      if (!link) return;
      const match = (link.getAttribute("href") || "").match(/\/race\/([^/?#]+)/);
      if (match) {
        track("race_result_click", {
          race_slug: match[1],
          search_term: searchQuery,
          filter: activeFilter,
          country: activeCountry,
          sort: activeSort
        });
      }
    });
  }

  document.addEventListener("DOMContentLoaded", init);
})();
