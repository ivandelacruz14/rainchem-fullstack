import { useState, useEffect } from "react";
import client from "../api/client";
import { useUI } from "../context/UIContext";

export default function FAQs() {
  const [faqs, setFaqs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const { toggleChat } = useUI();

  useEffect(() => {
    client.get("/api/chat/faq", { params: { all: "true" } })
      .then((res) => setFaqs(res.data.faqs))
      .finally(() => setLoading(false));
  }, []);

  const term = search.trim().toLowerCase();
  const visible = term ? faqs.filter((f) => `${f.question} ${f.answer}`.toLowerCase().includes(term)) : faqs;
  const groups = {};
  visible.forEach((f) => {
    (groups[f.category] = groups[f.category] || []).push(f);
  });

  return (
    <div className="container" style={{ paddingBottom: 80 }}>
      <div className="page-hero">
        <div className="eyebrow">FAQs</div>
        <h1>Frequently asked questions</h1>
        <p>Answers come from the same admin-approved knowledge base our AI assistant uses.</p>
      </div>

      <div className="shop-toolbar">
        <input placeholder="Search questions..." value={search} onChange={(e) => setSearch(e.target.value)} />
      </div>

      {loading ? null : visible.length === 0 ? (
        <div className="empty-state">No matching questions. Try asking the AI assistant instead.</div>
      ) : (
        Object.entries(groups).map(([name, items]) => (
          <div className="faq-group" key={name}>
            <h3>{name}</h3>
            {items.map((f) => (
              <details key={f.id} style={{ borderBottom: "1px solid rgba(24,20,15,.08)", padding: "14px 0" }}>
                <summary style={{ fontWeight: 700, cursor: "pointer" }}>{f.question}</summary>
                <p style={{ margin: "10px 0 0", color: "#57524c", fontSize: 14 }}>{f.answer}</p>
              </details>
            ))}
          </div>
        ))
      )}

      <button className="btn btn-primary" style={{ marginTop: 10 }} onClick={toggleChat}>Ask the AI Assistant</button>
    </div>
  );
}
