import { useState } from "react";
import client from "../../api/client";

export default function AiTester() {
  const [question, setQuestion] = useState("");
  const [includePending, setIncludePending] = useState(false);
  const [result, setResult] = useState(null);

  async function runTest() {
    if (!question.trim()) return;
    const res = await client.post("/api/admin/knowledge/test", { question, includePending });
    setResult(res.data);
  }

  return (
    <div>
      <div className="admin-topbar"><div><h1>AI Response Tester</h1><p>Test sample questions before making knowledge live to users.</p></div></div>
      <div className="admin-panel">
        <div className="tester-shell">
          <div>
            <div className="field">
              <label>Sample Question</label>
              <textarea rows="3" placeholder="e.g. How often should I change my oil?" value={question} onChange={(e) => setQuestion(e.target.value)} />
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14 }}>
              <input type="checkbox" id="includePending" checked={includePending} onChange={(e) => setIncludePending(e.target.checked)} />
              <label htmlFor="includePending" style={{ fontSize: 13.5 }}>Include pending (unapproved) knowledge in test</label>
            </div>
            <button className="btn btn-primary" onClick={runTest}>Run Test</button>
          </div>
          <div>
            <h4 style={{ marginBottom: 10 }}>Result</h4>
            <div className="tester-result">
              {!result ? (
                <p style={{ color: "#8a8580" }}>Run a test question to see how the AI would respond, including confidence score and candidate matches.</p>
              ) : (
                <>
                  {result.matchedEntry && (
                    <div className="badge" style={{ marginBottom: 8 }}>
                      {result.matchedEntry.status === "approved" ? "Approved source" : "Pending source, not yet visible to users"}
                    </div>
                  )}
                  <p style={{ fontWeight: 600, marginBottom: 6 }}>{result.answer}</p>
                  <div style={{ fontSize: 12, color: "#8a8580" }}>Confidence: {result.confidence}%</div>
                  <div className="confidence-meter"><div className="confidence-fill" style={{ width: `${result.confidence}%` }} /></div>
                  <h4 style={{ margin: "16px 0 6px", fontSize: 13 }}>Top candidates</h4>
                  {result.candidates.map((c, i) => (
                    <div className="candidate-row" key={i}><span>{c.question}</span><span className="mono">{c.score}%</span></div>
                  ))}
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
