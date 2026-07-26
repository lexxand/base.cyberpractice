(() => {
  "use strict";

  const STORAGE_KEY = "base.cyberpractice:reading:v1";
  const PANEL_ID = "kb-reading-panel";

  function emptyState() {
    return { version: 1, pages: {} };
  }

  function loadState() {
    try {
      const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY));
      if (parsed && parsed.version === 1 && parsed.pages) return parsed;
    } catch (error) {
      console.warn("Не удалось прочитать прогресс базы знаний", error);
    }
    return emptyState();
  }

  function saveState(state) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
      return true;
    } catch (error) {
      console.warn("Не удалось сохранить прогресс базы знаний", error);
      return false;
    }
  }

  function metaContent(name) {
    return document.querySelector(`meta[name="${name}"]`)?.content || "";
  }

  function normalizePath(value) {
    try {
      const url = new URL(value, window.location.href);
      if (url.origin !== window.location.origin) return null;

      let path = url.pathname.replace(/\/index\.html$/, "/");
      if (!/\.[a-z0-9]+$/i.test(path) && !path.endsWith("/")) path += "/";
      return path;
    } catch (_error) {
      return null;
    }
  }

  function currentPage() {
    const path = normalizePath(window.location.href);
    const pageMeta = document.getElementById("kb-page-meta")?.dataset || {};
    return {
      id: pageMeta.pageId || metaContent("kb-page-id") || `path:${path}`,
      path,
      updated: pageMeta.pageUpdated || metaContent("kb-page-updated") || "unknown",
      title: document.querySelector("article h1")?.textContent?.trim() || document.title,
    };
  }

  function exactRead(record, page) {
    return Boolean(record && record.updated === page.updated);
  }

  function recordsByPath(state) {
    const result = new Map();
    Object.values(state.pages).forEach((record) => {
      if (record.path) result.set(record.path, record);
    });
    return result;
  }

  function navigationPaths() {
    const paths = new Set();
    document.querySelectorAll("a.md-nav__link[href]").forEach((link) => {
      const path = normalizePath(link.href);
      if (path) paths.add(path);
    });
    return paths;
  }

  function annotateNavigation(state) {
    const byPath = recordsByPath(state);

    document.querySelectorAll("a.md-nav__link[href]").forEach((link) => {
      link.querySelectorAll(":scope > .kb-read-mark").forEach((mark) => mark.remove());
      const path = normalizePath(link.href);
      if (!path || !byPath.has(path)) return;

      const mark = document.createElement("span");
      mark.className = "kb-read-mark";
      mark.textContent = "✓";
      mark.setAttribute("aria-label", "Прочитано");
      mark.title = "Прочитано";
      link.append(mark);
    });
  }

  function progressText(state) {
    const paths = navigationPaths();
    const readPaths = new Set(
      Object.values(state.pages)
        .map((record) => record.path)
        .filter((path) => paths.has(path)),
    );
    return `Прочитано на сайте: ${readPaths.size} из ${paths.size}`;
  }

  function render() {
    document.getElementById(PANEL_ID)?.remove();

    const article = document.querySelector("article.md-content__inner");
    if (!article) return;

    const page = currentPage();
    const state = loadState();
    const record = state.pages[page.id];
    const isRead = exactRead(record, page);
    const isOutdated = Boolean(record && !isRead);

    // Стабильный id сохраняет отметку после перемещения файла. Обновляем путь,
    // чтобы галочка появилась рядом с новым адресом в навигации.
    if (isRead && record.path !== page.path) {
      record.path = page.path;
      saveState(state);
    }

    const panel = document.createElement("aside");
    panel.id = PANEL_ID;
    panel.className = "kb-reading-panel";
    panel.setAttribute("aria-label", "Статус прочтения страницы");

    const button = document.createElement("button");
    button.type = "button";
    button.className = "kb-reading-button";
    button.setAttribute("aria-pressed", String(isRead));
    button.textContent = isRead ? "✓ Прочитано" : "Отметить прочитанным";

    const details = document.createElement("span");
    details.className = "kb-reading-details";
    if (isOutdated) {
      details.textContent = "Материал изменился после прочтения";
      details.classList.add("kb-reading-details--outdated");
    } else if (isRead && record.readAt) {
      details.textContent = `Отмечено: ${new Date(record.readAt).toLocaleDateString("ru-RU")}`;
    } else {
      details.textContent = "Состояние хранится только в этом браузере";
    }

    const progress = document.createElement("span");
    progress.className = "kb-reading-progress";
    progress.textContent = progressText(state);

    button.addEventListener("click", () => {
      const nextState = loadState();
      const currentRecord = nextState.pages[page.id];

      if (exactRead(currentRecord, page)) {
        delete nextState.pages[page.id];
      } else {
        nextState.pages[page.id] = {
          id: page.id,
          path: page.path,
          title: page.title,
          updated: page.updated,
          readAt: new Date().toISOString(),
        };
      }

      if (saveState(nextState)) render();
    });

    panel.append(button, details, progress);
    article.prepend(panel);
    document.documentElement.dataset.kbPageRead = isRead ? "true" : "false";
    annotateNavigation(state);
  }

  if (typeof document$ !== "undefined") {
    document$.subscribe(render);
  } else if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", render, { once: true });
  } else {
    render();
  }
})();
