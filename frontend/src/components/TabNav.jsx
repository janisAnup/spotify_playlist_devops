export default function TabNav({ items, activeTab, onSelect }) {
  return (
    <nav className="module-nav" aria-label="App modules">
      {items.map((item) => (
        <button
          key={item.id}
          type="button"
          className={`module-tab${activeTab === item.id ? " is-active" : ""}`}
          onClick={() => onSelect(item.id)}
        >
          <span className="module-tab__eyebrow">{item.eyebrow}</span>
          <strong>{item.label}</strong>
        </button>
      ))}
    </nav>
  );
}
