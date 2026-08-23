import React, { useEffect, useState } from "react";
import Icon from "../icons";
import { api } from "../api";

const nice = (s) =>
  String(s || "")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());

export default function WorkspacePage({ type, open, onUpload }) {
  const [data, setData] = useState([]);
  const [reviews, setReviews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let f;

    if (type === "appeals") {
      f = api.appeals;
    } else if (type === "documents") {
      f = api.documents;
    } else if (type === "rules") {
      f = api.payerRules;
    } else if (type === "users") {
      f = api.users;
    } else if (type === "denials") {
      f = api.denials;
    } else if (type === "claims") {
      f = api.claims;
    } else {
      f = api.notifications;
    }

    setLoading(true);
    setError("");

    Promise.all([
      f(),
      type === "appeals" ? api.reviewQueue() : Promise.resolve([]),
    ])
      .then(([items, pending]) => {
        setData(items || []);
        setReviews(pending || []);
      })
      .catch((e) => {
        setError(e?.message || "Failed to load data");
      })
      .finally(() => {
        setLoading(false);
      });
  }, [type]);

  const title =
    {
      denials: "Denials",
      claims: "Claims",
      documents: "Documents",
      appeals: "Appeals",
      insights: "AI Insights",
      rules: "Payer Rules",
      reports: "Reports",
      users: "Users",
      settings: "Settings",
      notifications: "Notifications",
    }[type] || nice(type);

  if (type === "insights") {
    return <Insights />;
  }

  if (type === "reports") {
    return <Reports />;
  }

  if (type === "settings") {
    return <Settings />;
  }

  return (
    <section className="workspace">
      <div className="workspaceHead">
        <div>
          <div className="eyebrow">RECOVERY DESK</div>
          <h1>{title}</h1>
          <p>Manage real workflow data, not static mockups.</p>
        </div>

        {type === "documents" && (
          <button onClick={onUpload}>
            <Icon name="upload" /> Upload Document
          </button>
        )}
      </div>

      {type === "appeals" && (
        <div className="panel reviewStrip">
          <div className="panelTitle">
            <h2>Human Review Queue</h2>
            <span>{reviews.length} pending</span>
          </div>

          {reviews.length ? (
            <div className="reviewInline">
              {reviews.map((x) => (
                <div key={x.id}>
                  <div>
                    <b>
                      DR-{String(x.denial_id).padStart(4, "0")}
                    </b>
                    <small>{x.reason}</small>
                  </div>

                  <button
                    className="casePrimary"
                    onClick={async () => {
                      await api.decideReview(
                        x.id,
                        "APPROVE",
                        "Approved in Appeals workspace"
                      );
                      window.location.reload();
                    }}
                  >
                    Approve
                  </button>

                  <button
                    className="secondary miniAction"
                    onClick={() => open(x.denial_id)}
                  >
                    Inspect
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <p className="emptyState">
              Nothing waiting for human review.
            </p>
          )}
        </div>
      )}

      {loading ? (
        <div className="panel emptyState">
          Loading {title.toLowerCase()}…
        </div>
      ) : error ? (
        <div className="panel emptyState errorText">
          {error}
        </div>
      ) : (
        <div className="panel tablePanel">
          <table>
            <thead>
              <tr>
                {type === "appeals" ? (
                  <>
                    <th>Claim</th>
                    <th>Payer</th>
                    <th>Reason</th>
                    <th>Score</th>
                    <th>Status</th>
                    <th>Created</th>
                  </>
                ) : type === "documents" ? (
                  <>
                    <th>Document</th>
                    <th>Type</th>
                    <th>Case</th>
                    <th>Status</th>
                    <th>Created</th>
                  </>
                ) : type === "rules" ? (
                  <>
                    <th>Policy</th>
                    <th>File</th>
                    <th>Size</th>
                    <th>Index</th>
                  </>
                ) : type === "users" ? (
                  <>
                    <th>User</th>
                    <th>Email</th>
                    <th>Role</th>
                  </>
                ) : (
                  <>
                    <th>Time</th>
                    <th>Title</th>
                    <th>Message</th>
                    <th>Type</th>
                  </>
                )}
              </tr>
            </thead>

            <tbody>
              {data.map((x) => (
                <tr key={x.id || x.file || x.name}>
                  <td>
                    {type === "appeals" ? (
                      <button
                        className="tableLink"
                        onClick={() => open(x.denial_id)}
                      >
                        {x.claim_no}
                      </button>
                    ) : type === "documents" ? (
                      x.name
                    ) : type === "rules" ? (
                      x.name
                    ) : (
                      new Date(x.created_at).toLocaleString()
                    )}
                  </td>

                  {type === "appeals" ? (
                    <>
                      <td>{x.payer}</td>

                      <td>{nice(x.reason)}</td>

                      <td>
                        {Math.round(x.score || 0)}/100
                      </td>

                      <td>
                        <span
                          className={`status ${String(
                            x.status || ""
                          ).toLowerCase()}`}
                        >
                          {nice(x.status)}
                        </span>
                      </td>

                      <td>
                        {new Date(
                          x.created_at
                        ).toLocaleDateString()}
                      </td>
                    </>
                  ) : type === "documents" ? (
                    <>
                      <td>{nice(x.document_type)}</td>

                      <td>
                        {x.denial_id
                          ? `DR-${String(x.denial_id).padStart(
                              4,
                              "0"
                            )}`
                          : "—"}
                      </td>

                      <td>
                        <span className="status uploaded">
                          {nice(x.status)}
                        </span>
                      </td>

                      <td>
                        {new Date(
                          x.created_at
                        ).toLocaleDateString()}
                      </td>
                    </>
                  ) : type === "rules" ? (
                    <>
                      <td>{x.file}</td>

                      <td>
                        {Math.round((x.size || 0) / 1024)} KB
                      </td>

                      <td>
                        <span className="status approved">
                          Indexed
                        </span>
                      </td>
                    </>
                  ) : type === "users" ? (
                    <>
                      <td>{x.email}</td>

                      <td>
                        <span className="status approved">
                          {nice(x.role)}
                        </span>
                      </td>
                    </>
                  ) : (
                    <>
                      <td>{x.title}</td>
                      <td>{x.message}</td>
                      <td>{nice(x.kind)}</td>
                    </>
                  )}
                </tr>
              ))}
            </tbody>
          </table>

          {!data.length && (
            <div className="emptyState">
              Nothing here yet.
            </div>
          )}
        </div>
      )}
    </section>
  );
}

function Insights() {
  return (
    <section className="workspace">
      <div className="workspaceHead">
        <div>
          <div className="eyebrow">AI OPERATIONS</div>

          <h1>AI Insights</h1>

          <p>
            Quality, confidence and recovery signals from the real
            workflow.
          </p>
        </div>
      </div>

      <div className="insightCards">
        <div className="panel">
          <span>Human Review Rate</span>

          <strong>Deterministic</strong>

          <p>
            Cases below confidence/validation gates are routed to a
            reviewer.
          </p>
        </div>

        <div className="panel">
          <span>AI Architecture</span>

          <strong>RAG + Critic</strong>

          <p>
            Policy and evidence retrieval are surfaced with source
            citations.
          </p>
        </div>

        <div className="panel">
          <span>Safety</span>

          <strong>Human-in-the-loop</strong>

          <p>
            No healthcare appeal is blindly submitted when human
            approval is enabled.
          </p>
        </div>
      </div>
    </section>
  );
}

function Reports() {
  const [r, setR] = useState(null);

  useEffect(() => {
    api.report().then(setR).catch(() => setR(null));
  }, []);

  function download() {
    if (!r) return;

    const blob = new Blob(
      [JSON.stringify(r, null, 2)],
      {
        type: "application/json",
      }
    );

    const a = document.createElement("a");

    a.href = URL.createObjectURL(blob);
    a.download = "denial-recovery-report.json";

    a.click();

    URL.revokeObjectURL(a.href);
  }

  return (
    <section className="workspace">
      <div className="workspaceHead">
        <div>
          <div className="eyebrow">REPORTING</div>

          <h1>Reports</h1>

          <p>
            Export a snapshot of recovery operations.
          </p>
        </div>

        <button onClick={download} disabled={!r}>
          <Icon name="report" /> Download Report
        </button>
      </div>

      <div className="reportGrid">
        {r &&
          Object.entries(r.stats || {}).map(([k, v]) => (
            <div className="panel" key={k}>
              <span>
                {k.replaceAll("_", " ")}
              </span>

              <strong>
                {typeof v === "number"
                  ? v.toLocaleString("en-IN")
                  : String(v)}
              </strong>
            </div>
          ))}
      </div>
    </section>
  );
}

function Settings() {
  return (
    <section className="workspace">
      <div className="workspaceHead">
        <div>
          <div className="eyebrow">SYSTEM</div>

          <h1>Settings</h1>

          <p>
            Runtime settings are controlled by the FastAPI
            environment configuration.
          </p>
        </div>
      </div>

      <div className="settingsGrid">
        <div className="panel">
          <h2>AI Safety</h2>

          <p>
            Human approval remains enabled by default. Completion is
            based on verified payment, not LLM opinion.
          </p>

          <span className="status approved">
            Protected
          </span>
        </div>

        <div className="panel">
          <h2>Local-first AI</h2>

          <p>
            Ollama is the primary provider with deterministic
            fallback chains for offline demos.
          </p>

          <span className="status uploaded">
            Local
          </span>
        </div>

        <div className="panel">
          <h2>Audit & Checkpoints</h2>

          <p>
            LangGraph state is checkpointed and important events
            are stored in the audit trail.
          </p>

          <span className="status approved">
            Enabled
          </span>
        </div>
      </div>
    </section>
  );
}