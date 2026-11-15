const TITLES = {
  prioritize: "Prioritize",
  restock: "May need restocking",
  promote: "Needs promotion",
  attention: "Needs attention",
};

export default function Recommendations({ items }) {
  if (items.length === 0) {
    return <p className="field-hint">No recommendations yet. They appear once there are recorded sales to base them on.</p>;
  }
  return (
    <ul className="reco-list">
      {items.map((item, index) => (
        <li key={`${item.type}-${item.productId}-${index}`} className={`reco-item ${item.type}`}>
          <span className="badge">{TITLES[item.type]}</span>
          <strong>{item.name}</strong>
          <span>{item.message}</span>
        </li>
      ))}
    </ul>
  );
}
