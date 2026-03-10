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
    let races = allRaces;

    // Search
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      races = races.filter((r) => r.st.includes(q));
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
    const card = document.createElement("div");
    card.className = "race-card";

    // Series tags
    let seriesHtml = "";
    if (r.sm && r.sm.length > 0) {
      const tags = r.sm
        .map((s) => {
          const label = SERIES_LABELS[s] || s.replace(/_/g, " ");
          const span = document.createElement("span");
          span.className = "series-tag";
          span.textContent = label;
          return span.outerHTML;
        })
        .join("");
      seriesHtml = '<div class="series-tags">' + tags + "</div>";
    }

    const distText = r.d ? r.d + "km" : "";
    const elevText = r.el ? r.el + "m" : "—";
    const foundedText = r.yr ? r.yr : "—";
    const tierClass = "t" + r.t;

    // Use textContent for user-derived values to prevent XSS
    const nameEl = document.createElement("h3");
    nameEl.textContent = r.dn || r.n;

    const taglineEl = document.createElement("div");
    taglineEl.className = "race-tagline";
    taglineEl.textContent = r.tg;

    card.innerHTML =
      '<div class="race-card-header">' +
      '<h3></h3>' +
      '<span class="tier-badge ' + tierClass + '">' + r.tl + "</span>" +
      "</div>" +
      '<div class="race-card-body">' +
      '<div class="race-tagline"></div>' +
      '<div class="race-meta">' +
      '<span class="label">Location</span><span class="value"></span>' +
      '<span class="label">Distance</span><span class="value">' + distText + "</span>" +
      '<span class="label">Elevation</span><span class="value">' + elevText + "</span>" +
      '<span class="label">When</span><span class="value"></span>' +
      '<span class="label">Field</span><span class="value"></span>' +
      '<span class="label">Founded</span><span class="value">' + foundedText + "</span>" +
      "</div>" +
      "</div>" +
      seriesHtml +
      '<div class="race-card-footer">' +
      '<span class="discipline-badge ' + r.di + '">' + r.di + "</span>" +
      '<span class="score-display">' + r.sc + "%</span>" +
      "</div>";

    // Set text content safely
    card.querySelector("h3").textContent = r.dn || r.n;
    card.querySelector(".race-tagline").textContent = r.tg;

    // Set location, date, field safely
    const values = card.querySelectorAll(".race-meta .value");
    values[0].textContent = r.lb || r.loc;
    values[3].textContent = r.dt;
    values[4].textContent = r.fs;

    return card;
  }

  function render() {
    const races = getFilteredRaces();
    const grid = document.getElementById("raceGrid");
    grid.innerHTML = "";

    for (const r of races) {
      grid.appendChild(createCard(r));
    }

    document.getElementById("resultsInfo").textContent =
      races.length + " of " + allRaces.length + " races";
  }

  function bindEvents() {
    // Search
    const searchInput = document.getElementById("searchInput");
    let debounce;
    searchInput.addEventListener("input", function () {
      clearTimeout(debounce);
      debounce = setTimeout(function () {
        searchQuery = searchInput.value.trim();
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
  }

  document.addEventListener("DOMContentLoaded", init);
})();
