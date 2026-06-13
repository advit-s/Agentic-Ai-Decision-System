// __tests__/setup.js — Test environment setup

// localStorage
if (typeof globalThis.localStorage === "undefined") {
  const store = {};
  globalThis.localStorage = {
    getItem: (key) => store[key] || null,
    setItem: (key, value) => { store[key] = String(value); },
    removeItem: (key) => { delete store[key]; },
    clear: () => { Object.keys(store).forEach((k) => delete store[k]); },
  };
}

// ResizeObserver (used by MiniMap / Controls in React Flow)
if (typeof globalThis.ResizeObserver === "undefined") {
  globalThis.ResizeObserver = class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
}

// DataTransfer (used by drag-and-drop in NodePalette)
if (typeof DataTransfer === "undefined") {
  globalThis.DataTransfer = class DataTransfer {
    constructor() { this._data = {}; }
    getData(format) { return this._data[format] || ""; }
    setData(format, data) { this._data[format] = String(data); }
    clearData(format) { if (format) delete this._data[format]; else this._data = {}; }
    get types() { return Object.keys(this._data); }
    dropEffect = "none";
    effectAllowed = "all";
    files = [];
    items = [];
  };
}

// Ensure drag events have dataTransfer (jsdom doesn't always set it)
const origDispatch = EventTarget.prototype.dispatchEvent;
EventTarget.prototype.dispatchEvent = function (event) {
  if (!event.dataTransfer && (event.type === "dragstart" || event.type === "dragover" || event.type === "drop")) {
    event.dataTransfer = new DataTransfer();
  }
  return origDispatch.call(this, event);
};
