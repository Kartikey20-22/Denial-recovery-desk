import React, { useEffect, useRef, useState } from "react";
import Icon from "../icons";
import { api } from "../api";

const starters = [
  "What evidence supports an appeal for CLM-1001?",
  "What is missing before we submit CLM-1005?",
  "Explain the payer policy for a prior authorization denial.",
  "Which cases look like duplicate claims?",
  "How much was recovered for CLM-1011?",
];

export default function Copilot() {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        "Hi! I’m the Denial Recovery AI Copilot. I use local RAG + Llama to answer from your policy and evidence corpus. Ask about a claim, denial reason, payer rule, or missing evidence.",
      sources: [],
    },
  ]);
  const [question, setQuestion] = useState("");
  const [claimNo, setClaimNo] = useState("");
  const [loading, setLoading] = useState(false);
  const [health, setHealth] = useState(null);
  const bottomRef = useRef(null);

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth(null));
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function send(text = question) {
    const q = text.trim();
    if (!q || loading) return;

    const userMessage = { role: "user", content: q };
    const history = messages
      .filter((m) => m.role === "user" || m.role === "assistant")
      .slice(-10)
      .map((m) => ({ role: m.role, content: m.content }));

    setMessages((m) => [...m, userMessage]);
    setQuestion("");
    setLoading(true);

    try {
      const result = await api.copilotChat(q, claimNo || null, history);
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          content: result.answer,
          sources: result.sources || [],
          model: result.model,
          provider: result.provider,
          claimNo: result.claim_no,
        },
      ]);
    } catch (e) {
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          content: `I couldn't reach the RAG Copilot API: ${e.message}`,
          sources: [],
          error: true,
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="copilotPage">
      <div className="copilotHeader">
        <div>
          <div className="eyebrow">LOCAL AI · RAG</div>
          <h1>AI Recovery Copilot</h1>
          <p>
            Ask questions against payer policies, claim records and supporting
            evidence. Answers are grounded in retrieved sources.
          </p>
        </div>

        <div className={`copilotModel ${health ? "online" : "offline"}`}>
          <span />
          <div>
            <b>{health?.llm_model || "Llama 3.1 8B"}</b>
            <small>{health ? "Ollama connected" : "Fallback ready"}</small>
          </div>
        </div>
      </div>

      <div className="copilotLayout">
        <div className="copilotChat panel">
          <div className="copilotMessages">
            {messages.map((m, i) => (
              <div
                key={i}
                className={`chatRow ${m.role === "user" ? "user" : "assistant"}`}
              >
                <div className="chatAvatar">
                  {m.role === "user" ? "PS" : <Icon name="bot" size={16} />}
                </div>

                <div className="chatBubble">
                  <div className="chatRole">
                    {m.role === "user" ? "You" : "AI Copilot"}
                  </div>

                  <div className="chatContent">{m.content}</div>

                  {m.sources?.length > 0 && (
                    <div className="sourceList">
                      <b>Retrieved sources</b>
                      {m.sources.map((s, j) => (
                        <span key={`${s.type}-${s.source}-${j}`}>
                          {s.type}: [{s.source}]
                        </span>
                      ))}
                    </div>
                  )}

                  {m.provider === "fallback" && (
                    <div className="fallbackNote">
                      Llama was unavailable; the answer was generated from the
                      local retrieved corpus without inventing facts.
                    </div>
                  )}
                </div>
              </div>
            ))}

            {loading && (
              <div className="chatRow assistant">
                <div className="chatAvatar">
                  <Icon name="bot" size={16} />
                </div>
                <div className="chatBubble typing">
                  Retrieving policy/evidence and asking Llama…
                </div>
              </div>
            )}

            <div ref={bottomRef} />
          </div>

          <div className="copilotComposer">
            <div className="claimInput">
              <label>Optional claim</label>
              <input
                value={claimNo}
                onChange={(e) => setClaimNo(e.target.value.toUpperCase())}
                placeholder="CLM-1001"
              />
            </div>

            <div className="messageInput">
              <textarea
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    send();
                  }
                }}
                placeholder="Ask about a denial, policy, evidence or recovery…"
                rows={2}
              />

              <button
                className="sendButton"
                disabled={!question.trim() || loading}
                onClick={() => send()}
              >
                <Icon name="arrow" size={17} />
              </button>
            </div>
          </div>
        </div>

        <aside className="copilotSide">
          <div className="panel copilotCard">
            <div className="panelTitle">
              <h2>Try an example</h2>
            </div>

            <div className="starterList">
              {starters.map((x) => (
                <button key={x} onClick={() => send(x)}>
                  <Icon name="bot" size={14} />
                  <span>{x}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="panel copilotCard">
            <div className="panelTitle">
              <h2>How RAG works</h2>
            </div>

            <div className="ragSteps">
              <span><b>1</b> Detect claim</span>
              <span><b>2</b> Retrieve payer policy</span>
              <span><b>3</b> Retrieve claim evidence</span>
              <span><b>4</b> Build grounded context</span>
              <span><b>5</b> Generate with Llama</span>
              <span><b>6</b> Show citations</span>
            </div>
          </div>

          <div className="panel copilotCard safetyCard">
            <span className="status approved">GROUNDED</span>
            <h2>No-source, no-claim</h2>
            <p>
              The Copilot is instructed not to invent clinical facts, payer
              rules, authorization numbers, payments or evidence.
            </p>
          </div>
        </aside>
      </div>
    </section>
  );
}
