const POSTS = null/*##__POSTS__##*/;
const FEED_RESIZE_MESSAGE_TYPE = "embed-feed-resize";
let resizeBridgeInitialized = false;

const safeText = (value) => {
  return String(value == null ? "" : value);
};

const formatDate = (isoDate) => {
  var date = new Date(isoDate);
  if (Number.isNaN(date.getTime())) {
    return safeText(isoDate);
  }
  return date.toLocaleDateString();
};

const defineFeedSectionElement = () => {
  if (customElements.get("feed-section")) {
    return;
  }

  class FeedSectionElement extends HTMLElement {
    connectedCallback() {
      this.classList.add("feed");
      if (this.querySelector("[data-feed-list]")) {
        return;
      }

      var titleText = this.getAttribute("title-text") || "Recent posts";

      var header = document.createElement("div");
      header.className = "feed__header";

      var title = document.createElement("h2");
      title.className = "feed__title";
      title.textContent = titleText;
      header.appendChild(title);

      var list = document.createElement("ul");
      list.className = "feed__list";
      list.setAttribute("data-feed-list", "");

      var empty = document.createElement("p");
      empty.className = "feed__empty";
      empty.setAttribute("data-feed-empty", "");
      empty.hidden = true;
      empty.textContent = "No posts available.";

      this.appendChild(header);
      this.appendChild(list);
      this.appendChild(empty);
    }
  }

  customElements.define("feed-section", FeedSectionElement);
};

const defineFeedItemElement = () => {
  if (customElements.get("feed-item")) {
    return;
  }

  class FeedItemElement extends HTMLElement {
    setData(item) {
      this.className = "feed__item";

      this.textContent = "";

      var link = document.createElement("a");
      link.className = "feed__link";
      link.href = safeText(item.url);
      link.textContent = safeText(item.title);
      link.target = "_top";
      link.rel = "noopener noreferrer";
      this.appendChild(link);

      var meta = document.createElement("span");
      meta.className = "feed__meta";
      meta.textContent = formatDate(item.date);
      this.appendChild(meta);
    }
  }

  customElements.define("feed-item", FeedItemElement);
};

const getLimit = (maximumLimit) => {
  var params = new URLSearchParams(window.location.search);
  var requestedPosts = params.get("posts");

  if (!requestedPosts || !/^\d+$/.test(requestedPosts)) {
    return maximumLimit;
  }

  var requestedLimit = Number(requestedPosts);
  if (!Number.isSafeInteger(requestedLimit) || requestedLimit <= 0) {
    return maximumLimit;
  }

  return Math.min(requestedLimit, maximumLimit);
};

const render = (feedEl, data, limit) => {
  var listEl = feedEl.querySelector("[data-feed-list]");
  var emptyEl = feedEl.querySelector("[data-feed-empty]");
  if (!listEl) {
    return;
  }

  var items = Array.isArray(data.items) ? data.items.slice(0, limit) : [];

  listEl.innerHTML = "";

  if (!items.length) {
    if (emptyEl) {
      emptyEl.hidden = false;
    }
    return;
  }

  if (emptyEl) {
    emptyEl.hidden = true;
  }

  items.forEach(function (item) {
    var itemEl = document.createElement("feed-item");
    itemEl.setData(item);
    listEl.appendChild(itemEl);
  });
};

const notifyParentHeight = () => {
  if (window.parent === window) {
    return;
  }

  var root = document.documentElement;
  var body = document.body;
  var nextHeight = Math.ceil(
    Math.max(
      root ? root.scrollHeight : 0,
      body ? body.scrollHeight : 0,
    ),
  );

  window.parent.postMessage(
    {
      type: FEED_RESIZE_MESSAGE_TYPE,
      height: nextHeight,
    },
    "*",
  );
};

const setupResizeBridge = () => {
  if (resizeBridgeInitialized || window.parent === window) {
    return;
  }

  resizeBridgeInitialized = true;

  if ("ResizeObserver" in window) {
    var observer = new ResizeObserver(() => {
      notifyParentHeight();
    });

    if (document.documentElement) {
      observer.observe(document.documentElement);
    }
    if (document.body) {
      observer.observe(document.body);
    }
  }

  window.addEventListener("load", notifyParentHeight);
  window.addEventListener("resize", notifyParentHeight);
  setTimeout(notifyParentHeight, 0);
};

const boot = () => {
  var feedEl = document.querySelector("feed-section, .feed");
  if (!feedEl) {
    return;
  }

  var data = POSTS;
  var maximumLimit = Number(feedEl.getAttribute("data-default-limit")) || 5;

  if (data && typeof data.defaultLimit === "number" && !Number.isNaN(data.defaultLimit)) {
    maximumLimit = Math.max(1, Math.floor(data.defaultLimit));
    feedEl.setAttribute("data-default-limit", String(maximumLimit));
  }

  var limit = getLimit(maximumLimit);
  render(feedEl, data || { items: [] }, limit);
  notifyParentHeight();
};

const init = () => {
  defineFeedSectionElement();
  defineFeedItemElement();
  setupResizeBridge();

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
};

(() => {
  init();
})();
