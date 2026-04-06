import React from "react";

const tabIcons = {
  welcome: (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M3 11.5 12 4l9 7.5v8a1.5 1.5 0 0 1-1.5 1.5H4.5A1.5 1.5 0 0 1 3 19.5z" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  ),
  profile: (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="8" r="3.5" fill="none" stroke="currentColor" strokeWidth="1.8" />
      <path d="M5 19a7 7 0 0 1 14 0" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  ),
  create: (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 5v14M5 12h14" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  ),
  insights: (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M5 18V9m7 9V5m7 13v-6" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  ),
  history: (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M4 12a8 8 0 1 0 2.2-5.5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      <path d="M4 5v4h4M12 8v5l3 2" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
};

export default function TabNav({ items, activeTab, onSelect }) {
  return (
    <nav className="module-nav" aria-label="App modules">
      {items.map((item) => (
        <button
          key={item.id}
          type="button"
          className={`module-tab${activeTab === item.id ? " is-active" : ""}`}
          aria-current={activeTab === item.id ? "page" : undefined}
          onClick={() => onSelect(item.id)}
        >
          <span className="module-tab__row">
            <span className="module-tab__icon">{tabIcons[item.id]}</span>
            <strong>{item.label}</strong>
          </span>
          <span className="module-tab__eyebrow">{item.eyebrow}</span>
        </button>
      ))}
    </nav>
  );
}
