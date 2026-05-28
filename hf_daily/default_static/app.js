(function () {
  const cards = Array.from(document.querySelectorAll(".paper-card"));
  const searchInput = document.getElementById("searchInput");
  const searchScope = document.getElementById("searchScope");
  const clearButton = document.getElementById("clearFilters");
  const filterButtons = Array.from(document.querySelectorAll(".tag-filter"));
  const activeFilter = document.getElementById("activeFilter");
  const layout = document.querySelector(".layout");
  const dateYear = document.getElementById("dateYear");
  const dateMonth = document.getElementById("dateMonth");
  const dateDay = document.getElementById("dateDay");
  const dateStatus = document.getElementById("dateStatus");
  const topicTrendToggle = document.getElementById("topicTrendToggle");
  const topicTrendPanel = document.getElementById("topicTrendPanel");
  const topicTrendReset = document.getElementById("topicTrendReset");
  const trendStartDate = document.getElementById("trendStartDate");
  const trendEndDate = document.getElementById("trendEndDate");
  const trendTopicSelect = document.getElementById("trendTopicSelect");
  const topicTrendChart = document.getElementById("topicTrendChart");
  const topicTrendLegend = document.getElementById("topicTrendLegend");
  const topicTrendSummary = document.getElementById("topicTrendSummary");
  const risingTopicList = document.getElementById("risingTopicList");
  const institutionTopicMatrix = document.getElementById("institutionTopicMatrix");
  const tagOverrideStorageKey = "hf_daily_tag_overrides";
  const tagSuggestions = buildTagSuggestions();

  let currentFilter = null;
  const availableDates = parseAvailableDates();
  let selectedDate = layout && layout.dataset.latestDate ? layout.dataset.latestDate : availableDates[0];

  function matchesCard(card) {
    const query = (searchInput && searchInput.value ? searchInput.value : "").trim().toLowerCase();
    const hasSearchQuery = Boolean(query);
    const searchScopeValue = searchScope ? searchScope.value : "all";
    const searchText = searchTextFor(card, searchScopeValue).toLowerCase();
    const matchesSearch = !query || searchText.includes(query);
    const matchesFilter =
      !currentFilter || card.dataset[currentFilter.type] === currentFilter.value;
    const matchesDate =
      currentFilter || hasSearchQuery || !layout ? true : card.dataset.date === selectedDate;
    return matchesSearch && matchesFilter && matchesDate;
  }

  function searchTextFor(card, scope) {
    switch (scope) {
      case "title":
        return card.dataset.title || "";
      case "summary":
        return card.dataset.summary || "";
      case "tag":
        return [card.dataset.topic, card.dataset.institution].join(" ");
      case "topic":
        return card.dataset.topic || "";
      case "institution":
        return card.dataset.institution || "";
      default:
        return [
          card.dataset.title,
          card.dataset.summary,
          card.dataset.topic,
          card.dataset.institution,
          card.textContent,
        ].join(" ");
    }
  }

  function render() {
    cards.forEach((card) => {
      card.classList.toggle("is-hidden", !matchesCard(card));
    });
    filterButtons.forEach((button) => {
      const isActive =
        currentFilter &&
        button.dataset.filterType === currentFilter.type &&
        button.dataset.filterValue === currentFilter.value;
      button.classList.toggle("is-active", Boolean(isActive));
    });
    if (activeFilter) {
      if (currentFilter) {
        activeFilter.textContent = `Filtering all dates by ${currentFilter.type}: ${currentFilter.value}`;
      } else {
        activeFilter.textContent = "";
      }
    }
    if (dateStatus) {
      if (currentFilter) {
        dateStatus.textContent = "Tag filter is showing matching papers from all dates";
      } else if (searchInput && searchInput.value.trim()) {
        dateStatus.textContent = "Search is showing matching papers from all dates";
      } else {
        dateStatus.textContent = `Showing ${selectedDate}`;
      }
    }
  }

  filterButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const next = {
        type: button.dataset.filterType,
        value: button.dataset.filterValue,
      };
      if (
        currentFilter &&
        currentFilter.type === next.type &&
        currentFilter.value === next.value
      ) {
        currentFilter = null;
      } else {
        currentFilter = next;
      }
      render();
    });
  });

  if (searchInput) {
    searchInput.addEventListener("input", render);
  }

  if (searchScope) {
    searchScope.addEventListener("change", render);
  }

  if (clearButton) {
    clearButton.addEventListener("click", () => {
      currentFilter = null;
      if (searchInput) {
        searchInput.value = "";
      }
      render();
    });
  }

  setupDateArchive();
  setupTopicTrends();
  setupInstitutionTopicMatrix();
  setupTagEditors();
  loadGlobalTagSuggestions();

  function parseAvailableDates() {
    if (!layout || !layout.dataset.availableDates) {
      return [];
    }
    try {
      const parsed = JSON.parse(layout.dataset.availableDates);
      return Array.isArray(parsed) ? parsed : [];
    } catch (error) {
      return [];
    }
  }

  function setupDateArchive() {
    if (!dateYear || !dateMonth || !dateDay || availableDates.length === 0) {
      return;
    }
    const latestDate = selectedDate || availableDates[0];
    populateSelect(dateYear, uniqueParts(0), latestDate.slice(0, 4));
    updateMonthOptions(latestDate.slice(5, 7));
    updateDayOptions(latestDate.slice(8, 10));
    renderSelectedDate();

    dateYear.addEventListener("change", () => {
      updateMonthOptions();
      updateDayOptions();
      renderSelectedDate();
    });
    dateMonth.addEventListener("change", () => {
      updateDayOptions();
      renderSelectedDate();
    });
    dateDay.addEventListener("change", renderSelectedDate);
  }

  function uniqueParts(index, year, month) {
    const values = availableDates
      .filter((date) => !year || date.slice(0, 4) === year)
      .filter((date) => !month || date.slice(5, 7) === month)
      .map((date) => date.split("-")[index]);
    return Array.from(new Set(values)).sort().reverse();
  }

  function populateSelect(select, values, selectedValue) {
    select.innerHTML = "";
    values.forEach((value) => {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = value;
      if (value === selectedValue) {
        option.selected = true;
      }
      select.appendChild(option);
    });
  }

  function updateMonthOptions(preferredMonth) {
    const months = uniqueParts(1, dateYear.value);
    const selected = months.includes(preferredMonth) ? preferredMonth : months[0];
    populateSelect(dateMonth, months, selected);
  }

  function updateDayOptions(preferredDay) {
    const days = uniqueParts(2, dateYear.value, dateMonth.value);
    const selected = days.includes(preferredDay) ? preferredDay : days[0];
    populateSelect(dateDay, days, selected);
  }

  function renderSelectedDate() {
    selectedDate = `${dateYear.value}-${dateMonth.value}-${dateDay.value}`;
    currentFilter = null;
    render();
  }

  function setupTagEditors() {
    const overrides = loadStoredTagOverrides();
    cards.forEach((card) => {
      const paperId = card.dataset.paperId;
      const form = card.querySelector(".tag-edit-form");
      const toggle = card.querySelector(".tag-edit-toggle");
      if (!paperId || !form || !toggle) {
        return;
      }

      if (overrides.paper_overrides[paperId]) {
        applyTagValues(card, overrides.paper_overrides[paperId]);
        fillTagForm(form, card);
      }

      setupTagAutocomplete(form);

      toggle.addEventListener("click", () => {
        const isOpen = form.hidden;
        form.hidden = !isOpen;
        toggle.setAttribute("aria-expanded", String(isOpen));
      });

      form.addEventListener("submit", (event) => {
        event.preventDefault();
        const nextValues = valuesFromTagForm(form);
        saveTagOverride(card, nextValues);
        if (isAdminMode()) {
          setTagEditStatus(form, "Saving to data/tags/tag_overrides.json...");
          saveTagOverrideToAdmin(card, nextValues)
            .then(() => {
              setTagEditStatus(form, "Saved to data/tags/tag_overrides.json and rebuilt site.");
            })
            .catch(() => {
              setTagEditStatus(form, "Local save failed. Use Export JSON instead.");
            });
        } else {
          setTagEditStatus(form, "Draft saved. Export JSON to apply it after rebuild.");
        }
      });

      const resetButton = form.querySelector(".tag-edit-reset");
      if (resetButton) {
        resetButton.addEventListener("click", () => {
          resetTagOverride(card);
          fillTagForm(form, card);
          setTagEditStatus(form, "Draft reset for this paper.");
        });
      }

      const copyButton = form.querySelector(".tag-edit-copy");
      if (copyButton) {
        copyButton.addEventListener("click", () => {
          copyTagOverrides()
            .then(() => setTagEditStatus(form, "Override JSON copied."))
            .catch(() => setTagEditStatus(form, "Copy failed. Use Export JSON instead."));
        });
      }

      const exportButton = form.querySelector(".tag-edit-export");
      if (exportButton) {
        exportButton.addEventListener("click", () => {
          exportTagOverrides();
          setTagEditStatus(form, "Override JSON exported.");
        });
      }
    });
  }

  function buildTagSuggestions() {
    const suggestions = {
      institution_tag: [],
      topic_tag: [],
    };
    cards.forEach((card) => {
      addTagSuggestionTo(suggestions, "institution_tag", card.dataset.institution);
      addTagSuggestionTo(suggestions, "topic_tag", card.dataset.topic);
    });
    return {
      institution_tag: suggestions.institution_tag,
      topic_tag: suggestions.topic_tag,
    };
  }

  function loadGlobalTagSuggestions() {
    fetch(papersJsonPath())
      .then((response) => response.json())
      .then((payload) => {
        const papers = Array.isArray(payload.papers) ? payload.papers : [];
        papers.forEach((paper) => {
          addTagSuggestion("institution_tag", paper.institution_tag);
          addTagSuggestion("topic_tag", paper.topic_tag);
        });
        refreshOpenTagSuggestions();
      })
      .catch(() => {});
  }

  function papersJsonPath() {
    return window.location.pathname.includes("/daily/") ? "../assets/papers.json" : "assets/papers.json";
  }

  function addTagSuggestion(field, tag) {
    addTagSuggestionTo(tagSuggestions, field, tag);
  }

  function addTagSuggestionTo(suggestions, field, tag) {
    const value = String(tag || "").trim();
    if (!value || suggestions[field].includes(value)) {
      return;
    }
    suggestions[field].push(value);
    suggestions[field].sort((a, b) => a.localeCompare(b));
  }

  function setupTagAutocomplete(form) {
    Array.from(form.querySelectorAll("[data-tag-field]")).forEach((input) => {
      const field = input.dataset.tagField;
      const list = form.querySelector(`[data-suggestion-list="${field}"]`);
      if (!field || !list) {
        return;
      }
      input.addEventListener("input", () => renderTagSuggestions(input, list, field));
      input.addEventListener("focus", () => {
        selectTagInputOnFocus(input);
        renderTagSuggestions(input, list, field);
      });
      input.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
          hideTagSuggestions(list);
        }
      });
      input.addEventListener("blur", () => {
        window.setTimeout(() => hideTagSuggestions(list), 120);
      });
    });
  }

  function refreshOpenTagSuggestions() {
    Array.from(document.querySelectorAll("[data-tag-field]")).forEach((input) => {
      const field = input.dataset.tagField;
      const list = input.closest("label") ? input.closest("label").querySelector(`[data-suggestion-list="${field}"]`) : null;
      if (field && list && !list.hidden) {
        renderTagSuggestions(input, list, field);
      }
    });
  }

  function selectTagInputOnFocus(input) {
    if (input.dataset.hasFocused === "true") {
      return;
    }
    input.dataset.hasFocused = "true";
    input.select();
  }

  function renderTagSuggestions(input, list, field) {
    const query = input.value.trim();
    const matches = tagSuggestions[field]
      .filter((tag) => suggestionMatches(tag, query))
      .filter((tag) => tag !== query)
      .slice(0, 6);

    list.innerHTML = "";
    if (!query || matches.length === 0) {
      hideTagSuggestions(list);
      return;
    }

    matches.forEach((tag) => {
      const button = document.createElement("button");
      button.className = "tag-suggestion";
      button.type = "button";
      button.textContent = tag;
      button.addEventListener("mousedown", (event) => {
        event.preventDefault();
        input.value = tag;
        hideTagSuggestions(list);
        input.dispatchEvent(new Event("input", { bubbles: true }));
      });
      list.appendChild(button);
    });
    list.hidden = false;
  }

  function suggestionMatches(tag, query) {
    const normalizedTag = tag.toLowerCase();
    const normalizedQuery = query.toLowerCase();
    return Boolean(normalizedQuery) && normalizedTag.includes(normalizedQuery);
  }

  function hideTagSuggestions(list) {
    list.hidden = true;
    list.innerHTML = "";
  }

  function fillTagForm(form, card) {
    const institutionInput = form.querySelector('[data-tag-field="institution_tag"]');
    const topicInput = form.querySelector('[data-tag-field="topic_tag"]');
    if (institutionInput) {
      institutionInput.value = card.dataset.institution || "";
    }
    if (topicInput) {
      topicInput.value = card.dataset.topic || "";
    }
  }

  function valuesFromTagForm(form) {
    const institutionInput = form.querySelector('[data-tag-field="institution_tag"]');
    const topicInput = form.querySelector('[data-tag-field="topic_tag"]');
    return {
      institution_tag: institutionInput ? institutionInput.value.trim() : "",
      topic_tag: topicInput ? topicInput.value.trim() : "",
    };
  }

  function saveTagOverride(card, values) {
    const paperId = card.dataset.paperId;
    if (!paperId) {
      return;
    }
    const overrides = loadStoredTagOverrides();
    const originalInstitution = card.dataset.originalInstitution || "";
    const originalTopic = card.dataset.originalTopic || "";
    const nextOverride = {};
    if (values.institution_tag && values.institution_tag !== originalInstitution) {
      nextOverride.institution_tag = values.institution_tag;
    }
    if (values.topic_tag && values.topic_tag !== originalTopic) {
      nextOverride.topic_tag = values.topic_tag;
    }
    if (Object.keys(nextOverride).length > 0) {
      overrides.paper_overrides[paperId] = nextOverride;
      applyTagValues(card, nextOverride);
    } else {
      delete overrides.paper_overrides[paperId];
      applyTagValues(card, {
        institution_tag: originalInstitution,
        topic_tag: originalTopic,
      });
    }
    persistTagOverrides(overrides);
    render();
  }

  function isAdminMode() {
    const hostname = window.location.hostname;
    return window.location.protocol === "http:" && (hostname === "127.0.0.1" || hostname === "localhost");
  }

  function saveTagOverrideToAdmin(card, values) {
    const overrideValues = overrideValuesForSave(card, values);
    return fetch("/api/tag-overrides", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        paper_id: card.dataset.paperId,
        institution_tag: overrideValues.institution_tag,
        topic_tag: overrideValues.topic_tag,
      }),
    }).then((response) => {
      if (!response.ok) {
        throw new Error("save failed");
      }
      return response.json();
    });
  }

  function overrideValuesForSave(card, values) {
    const originalInstitution = card.dataset.originalInstitution || "";
    const originalTopic = card.dataset.originalTopic || "";
    return {
      institution_tag: values.institution_tag && values.institution_tag !== originalInstitution ? values.institution_tag : "",
      topic_tag: values.topic_tag && values.topic_tag !== originalTopic ? values.topic_tag : "",
    };
  }

  function resetTagOverride(card) {
    const paperId = card.dataset.paperId;
    if (!paperId) {
      return;
    }
    const overrides = loadStoredTagOverrides();
    delete overrides.paper_overrides[paperId];
    persistTagOverrides(overrides);
    applyTagValues(card, {
      institution_tag: card.dataset.originalInstitution || "",
      topic_tag: card.dataset.originalTopic || "",
    });
    render();
  }

  function applyTagValues(card, values) {
    const institution = values.institution_tag || card.dataset.institution || "";
    const topic = values.topic_tag || card.dataset.topic || "";
    card.dataset.institution = institution;
    card.dataset.topic = topic;
    const institutionTag = card.querySelector('[data-tag-role="institution"]');
    const topicTag = card.querySelector('[data-tag-role="topic"]');
    if (institutionTag) {
      institutionTag.textContent = institution;
    }
    if (topicTag) {
      topicTag.textContent = topic;
    }
  }

  function loadStoredTagOverrides() {
    try {
      const parsed = JSON.parse(localStorage.getItem(tagOverrideStorageKey) || "{}");
      if (parsed && parsed.paper_overrides && typeof parsed.paper_overrides === "object") {
        return { paper_overrides: parsed.paper_overrides };
      }
    } catch (error) {
      return { paper_overrides: {} };
    }
    return { paper_overrides: {} };
  }

  function persistTagOverrides(overrides) {
    const cleaned = { paper_overrides: {} };
    Object.keys(overrides.paper_overrides || {})
      .sort()
      .forEach((paperId) => {
        const fields = overrides.paper_overrides[paperId] || {};
        const cleanFields = {};
        ["institution_tag", "topic_tag"].forEach((field) => {
          if (fields[field]) {
            cleanFields[field] = fields[field];
          }
        });
        if (Object.keys(cleanFields).length > 0) {
          cleaned.paper_overrides[paperId] = cleanFields;
        }
      });
    localStorage.setItem(tagOverrideStorageKey, JSON.stringify(cleaned, null, 2));
  }

  function tagOverridesJson() {
    return JSON.stringify(loadStoredTagOverrides(), null, 2) + "\n";
  }

  function copyTagOverrides() {
    const text = tagOverridesJson();
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(text);
    }
    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.setAttribute("readonly", "");
    textarea.style.position = "fixed";
    textarea.style.left = "-9999px";
    document.body.appendChild(textarea);
    textarea.select();
    const copied = document.execCommand("copy");
    document.body.removeChild(textarea);
    return copied ? Promise.resolve() : Promise.reject(new Error("copy failed"));
  }

  function exportTagOverrides() {
    const blob = new Blob([tagOverridesJson()], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "tag_overrides.json";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  function setTagEditStatus(form, message) {
    const status = form.querySelector(".tag-edit-status");
    if (status) {
      status.textContent = message;
    }
  }

  function setupTopicTrends() {
    if (
      !topicTrendToggle ||
      !topicTrendPanel ||
      !trendStartDate ||
      !trendEndDate ||
      !trendTopicSelect ||
      !topicTrendChart ||
      availableDates.length === 0
    ) {
      return;
    }

    const defaultTrendDates = defaultTrendRangeDates();
    populateSelect(trendStartDate, availableDates.slice().reverse(), defaultTrendDates[0]);
    populateSelect(trendEndDate, availableDates.slice().reverse(), defaultTrendDates[defaultTrendDates.length - 1]);
    populateTrendTopics();

    topicTrendToggle.addEventListener("click", () => {
      const isOpen = topicTrendPanel.hidden;
      topicTrendPanel.hidden = !isOpen;
      topicTrendToggle.setAttribute("aria-expanded", String(isOpen));
      if (isOpen) {
        renderTopicTrends();
      }
    });

    trendStartDate.addEventListener("change", renderTopicTrends);
    trendEndDate.addEventListener("change", renderTopicTrends);
    trendTopicSelect.addEventListener("change", renderTopicTrends);

    if (topicTrendReset) {
      topicTrendReset.addEventListener("click", () => {
        Array.from(trendTopicSelect.options).forEach((option) => {
          option.selected = false;
        });
        renderTopicTrends();
      });
    }
  }

  function populateTrendTopics() {
    const topics = Array.from(
      new Set(cards.map((card) => card.dataset.topic).filter(Boolean))
    ).sort((a, b) => a.localeCompare(b));
    trendTopicSelect.innerHTML = "";
    topics.forEach((topic) => {
      const option = document.createElement("option");
      option.value = topic;
      option.textContent = topic;
      trendTopicSelect.appendChild(option);
    });
  }

  function defaultTrendRangeDates() {
    return availableDates.slice(0, 15).reverse();
  }

  function renderTopicTrends() {
    const start = trendStartDate.value <= trendEndDate.value ? trendStartDate.value : trendEndDate.value;
    const end = trendStartDate.value <= trendEndDate.value ? trendEndDate.value : trendStartDate.value;
    const rangeDates = availableDates
      .filter((date) => date >= start && date <= end)
      .slice()
      .reverse();
    const selectedTopics = Array.from(trendTopicSelect.selectedOptions).map((option) => option.value);
    const topics = selectedTopics.length > 0 ? selectedTopics : topTopicsForRange(rangeDates).slice(0, 5);
    const series = buildTopicTrendSeries(rangeDates, topics);
    renderTopicTrendChart(series, rangeDates);
    renderTopicTrendLegend(series);
    renderTopicTrendSummary(series);
    renderRisingTopics(buildRisingTopics(rangeDates));
  }

  function topTopicsForRange(rangeDates) {
    const counts = new Map();
    cards.forEach((card) => {
      const topic = card.dataset.topic;
      if (!topic || !rangeDates.includes(card.dataset.date)) {
        return;
      }
      counts.set(topic, (counts.get(topic) || 0) + 1);
    });
    return Array.from(counts.entries())
      .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
      .map(([topic]) => topic);
  }

  function buildTopicTrendSeries(rangeDates, topics) {
    return topics.map((topic, index) => {
      const values = rangeDates.map((date) => {
        return cards.filter(
          (card) => card.dataset.date === date && card.dataset.topic === topic
        ).length;
      });
      const total = values.reduce((sum, value) => sum + value, 0);
      const peakValue = Math.max(0, ...values);
      const peakIndex = values.indexOf(peakValue);
      return {
        topic,
        color: trendColor(index),
        values,
        total,
        peakDate: peakIndex >= 0 ? rangeDates[peakIndex] : "",
        peakValue,
      };
    });
  }

  function previousRangeFor(rangeDates) {
    if (rangeDates.length === 0) {
      return [];
    }
    const ascendingDates = availableDates.slice().reverse();
    const firstIndex = ascendingDates.indexOf(rangeDates[0]);
    if (firstIndex <= 0) {
      return [];
    }
    const start = Math.max(0, firstIndex - rangeDates.length);
    return ascendingDates.slice(start, firstIndex);
  }

  function buildRisingTopics(rangeDates) {
    const previousDates = previousRangeFor(rangeDates);
    const topics = Array.from(
      new Set(cards.map((card) => card.dataset.topic).filter(Boolean))
    );
    return topics
      .map((topic) => {
        const currentCount = countTopicInRange(topic, rangeDates);
        const previousCount = countTopicInRange(topic, previousDates);
        const delta = currentCount - previousCount;
        const percent = previousCount === 0 ? null : Math.round((delta / previousCount) * 100);
        return { topic, currentCount, previousCount, delta, percent };
      })
      .filter((item) => item.currentCount > 0 || item.previousCount > 0)
      .sort((a, b) => b.delta - a.delta || b.currentCount - a.currentCount || a.topic.localeCompare(b.topic))
      .slice(0, 5);
  }

  function countTopicInRange(topic, rangeDates) {
    return cards.filter(
      (card) => card.dataset.topic === topic && rangeDates.includes(card.dataset.date)
    ).length;
  }

  function renderTopicTrendChart(series, rangeDates) {
    topicTrendChart.innerHTML = "";
    topicTrendChart.setAttribute("viewBox", "0 0 600 230");
    if (rangeDates.length === 0 || series.length === 0) {
      appendSvgText(topicTrendChart, "No topic data in this range", 300, 118, "middle");
      return;
    }

    const width = 600;
    const height = 230;
    const padding = { top: 18, right: 22, bottom: 34, left: 34 };
    const plotWidth = width - padding.left - padding.right;
    const plotHeight = height - padding.top - padding.bottom;
    const maxValue = Math.max(1, ...series.flatMap((item) => item.values));

    appendSvgLine(topicTrendChart, padding.left, padding.top, padding.left, padding.top + plotHeight, "#d7e0e5");
    appendSvgLine(topicTrendChart, padding.left, padding.top + plotHeight, padding.left + plotWidth, padding.top + plotHeight, "#d7e0e5");

    series.forEach((item) => {
      const points = item.values.map((value, index) => {
        const x = padding.left + (rangeDates.length === 1 ? plotWidth / 2 : (index / (rangeDates.length - 1)) * plotWidth);
        const y = padding.top + plotHeight - (value / maxValue) * plotHeight;
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      });
      const polyline = document.createElementNS("http://www.w3.org/2000/svg", "polyline");
      polyline.setAttribute("points", points.join(" "));
      polyline.setAttribute("fill", "none");
      polyline.setAttribute("stroke", item.color);
      polyline.setAttribute("stroke-width", "2.5");
      polyline.setAttribute("stroke-linecap", "round");
      polyline.setAttribute("stroke-linejoin", "round");
      topicTrendChart.appendChild(polyline);
    });

    appendSvgText(topicTrendChart, rangeDates[0], padding.left, height - 10, "start");
    appendSvgText(topicTrendChart, rangeDates[rangeDates.length - 1], width - padding.right, height - 10, "end");
    appendSvgText(topicTrendChart, String(maxValue), 10, padding.top + 5, "start");
    appendSvgText(topicTrendChart, "0", 16, padding.top + plotHeight + 4, "start");
  }

  function renderTopicTrendLegend(series) {
    if (!topicTrendLegend) {
      return;
    }
    topicTrendLegend.innerHTML = "";
    series.forEach((item) => {
      const label = document.createElement("span");
      label.className = "trend-legend-item";
      const swatch = document.createElement("span");
      swatch.className = "trend-swatch";
      swatch.style.background = item.color;
      label.appendChild(swatch);
      label.append(document.createTextNode(item.topic));
      topicTrendLegend.appendChild(label);
    });
  }

  function renderTopicTrendSummary(series) {
    if (!topicTrendSummary) {
      return;
    }
    topicTrendSummary.innerHTML = "";
    series.forEach((item) => {
      const row = document.createElement("div");
      row.className = "trend-summary-row";
      row.innerHTML = `<strong>${escapeHtml(item.topic)}</strong><span>${item.total} papers</span><span>Peak ${item.peakDate}: ${item.peakValue}</span>`;
      topicTrendSummary.appendChild(row);
    });
  }

  function renderRisingTopics(items) {
    if (!risingTopicList) {
      return;
    }
    risingTopicList.innerHTML = "";
    if (items.length === 0) {
      const empty = document.createElement("p");
      empty.className = "muted";
      empty.textContent = "No topic changes in this range.";
      risingTopicList.appendChild(empty);
      return;
    }
    items.forEach((item) => {
      const row = document.createElement("div");
      row.className = "rising-topic-row";
      const percentLabel = item.percent === null ? "new" : `${item.percent >= 0 ? "+" : ""}${item.percent}%`;
      row.innerHTML = [
        `<strong>${escapeHtml(item.topic)}</strong>`,
        `<span>${item.currentCount} now</span>`,
        `<span>${item.previousCount} before</span>`,
        `<span class="rising-topic-delta">${item.delta >= 0 ? "+" : ""}${item.delta} ${percentLabel}</span>`,
      ].join("");
      risingTopicList.appendChild(row);
    });
  }

  function setupInstitutionTopicMatrix() {
    if (!institutionTopicMatrix) {
      return;
    }
    loadPapersForMatrix()
      .then((papers) => {
        renderInstitutionTopicMatrix(buildInstitutionTopicMatrix(papers));
      })
      .catch(() => {
        institutionTopicMatrix.innerHTML = "";
        appendMatrixCell("Unable to load matrix data.", "matrix-head");
      });
  }

  function loadPapersForMatrix() {
    const embeddedData = document.getElementById("matrixPapersData");
    if (embeddedData && embeddedData.textContent) {
      return Promise.resolve(JSON.parse(embeddedData.textContent));
    }
    return fetch("assets/papers.json")
      .then((response) => response.json())
      .then((payload) => Array.isArray(payload.papers) ? payload.papers : []);
  }

  function buildInstitutionTopicMatrix(papers) {
    const institutionCounts = new Map();
    const topicCounts = new Map();
    papers.forEach((paper) => {
      const strippedInstitution = (paper.institution_tag || "").trim().toLowerCase();
      const institution = (paper.institution_tag || "").trim();
      const topic = (paper.topic_tag || "").trim();
      if (!institution || strippedInstitution !== "unknown") {
        if (institution && topic) {
          institutionCounts.set(institution, (institutionCounts.get(institution) || 0) + 1);
          topicCounts.set(topic, (topicCounts.get(topic) || 0) + 1);
        }
      }
    });

    const institutions = topKeys(institutionCounts).slice(0, 40);
    const globalTopics = topKeys(topicCounts).slice(0, 20);
    const localTopics = localTopTopicsForInstitutions(papers, institutions);
    const topics = Array.from(new Set([...globalTopics, ...localTopics]));
    const counts = new Map();
    papers.forEach((paper) => {
      const institution = (paper.institution_tag || "").trim();
      const topic = (paper.topic_tag || "").trim();
      if (!institutions.includes(institution) || !topics.includes(topic)) {
        return;
      }
      const key = `${institution}\u0000${topic}`;
      counts.set(key, (counts.get(key) || 0) + 1);
    });

    return { institutions, topics, counts };
  }

  function localTopTopicsForInstitutions(papers, institutions) {
    return institutions.flatMap((institution) => {
      const counts = new Map();
      papers.forEach((paper) => {
        const topic = (paper.topic_tag || "").trim();
        if (paper.institution_tag === institution && topic) {
          counts.set(topic, (counts.get(topic) || 0) + 1);
        }
      });
      return topKeys(counts).slice(0, 3);
    });
  }

  function topKeys(counts) {
    return Array.from(counts.entries())
      .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
      .map(([key]) => key);
  }

  function renderInstitutionTopicMatrix(matrix) {
    institutionTopicMatrix.innerHTML = "";
    institutionTopicMatrix.style.gridTemplateColumns = `minmax(170px, 1.2fr) repeat(${matrix.topics.length}, minmax(46px, 1fr))`;
    appendMatrixCell("Institution", "matrix-head matrix-corner");
    matrix.topics.forEach((topic) => appendMatrixCell(topic, "matrix-head"));
    const maxValue = Math.max(1, ...Array.from(matrix.counts.values()));

    matrix.institutions.forEach((institution) => {
      appendMatrixCell(institution, "matrix-institution");
      matrix.topics.forEach((topic) => {
        const value = matrix.counts.get(`${institution}\u0000${topic}`) || 0;
        const cell = appendMatrixCell(String(value || ""), "matrix-value");
        cell.style.background = matrixCellColor(value, maxValue);
        cell.title = `${institution} / ${topic}: ${value}`;
      });
    });
  }

  function appendMatrixCell(text, className) {
    const cell = document.createElement("div");
    cell.className = `matrix-cell ${className || ""}`.trim();
    cell.textContent = text;
    institutionTopicMatrix.appendChild(cell);
    return cell;
  }

  function matrixCellColor(value, maxValue) {
    if (!value) {
      return "#ffffff";
    }
    const intensity = Math.max(0.16, value / maxValue);
    return `rgba(15, 91, 120, ${intensity.toFixed(2)})`;
  }

  function appendSvgLine(svg, x1, y1, x2, y2, color) {
    const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
    line.setAttribute("x1", x1);
    line.setAttribute("y1", y1);
    line.setAttribute("x2", x2);
    line.setAttribute("y2", y2);
    line.setAttribute("stroke", color);
    svg.appendChild(line);
  }

  function appendSvgText(svg, text, x, y, anchor) {
    const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
    label.setAttribute("x", x);
    label.setAttribute("y", y);
    label.setAttribute("text-anchor", anchor);
    label.setAttribute("font-size", "11");
    label.setAttribute("fill", "#52616a");
    label.textContent = text;
    svg.appendChild(label);
  }

  function trendColor(index) {
    return ["#0f5b78", "#7b4ab0", "#be6b00", "#2f7d52", "#b2344d"][index % 5];
  }

  function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, (character) => {
      return {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
      }[character];
    });
  }
})();
