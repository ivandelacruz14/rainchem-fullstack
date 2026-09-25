import { useEffect, useState } from "react";
import client from "../../api/client";
import { useUI } from "../../context/UIContext";

export default function AccountHelp() {
  const [faqs, setFaqs] = useState([]);
  const { toggleChat } = useUI();

  useEffect(() => {
    client.get("/api/chat/faq").then((res) => setFaqs(res.data.faqs));
  }, []);

  return (
    <div>
      <h2>Help Center</h2>
      <p style={{ color: "#6b665f", marginBottom: 20 }}>
        Find quick answers below, or chat with our AI assistant for anything else.
      </p>

      <div className="panel" style={{ marginBottom: 20 }}>
        <h3 style={{ marginTop: 0 }}>Frequently Asked Questions</h3>
        {faqs.map((f) => (
          <details key={f.id} style={{ borderBottom: "1px solid rgba(24,20,15,.08)", padding: "12px 0" }}>
            <summary style={{ fontWeight: 700, cursor: "pointer" }}>{f.question}</summary>
            <p style={{ margin: "8px 0 0", color: "#57524c", fontSize: 14 }}>{f.answer}</p>
          </details>
        ))}
      </div>

      <div className="panel" style={{ marginBottom: 20 }}>
        <h3 style={{ marginTop: 0 }}>Chat with our AI Assistant</h3>
        <p>Available 24/7 for questions about products, orders, and mixing ratios.</p>
        <button className="btn btn-primary" onClick={toggleChat}>Open Chat</button>
      </div>

      <div className="panel">
        <h3 style={{ marginTop: 0 }}>Contact Us</h3>
        <p>Email: cs@raincheminternational.com<br />Phone: (02) 8888 6531<br />Paranaque City, Metro Manila</p>
      </div>
    </div>
  );
}