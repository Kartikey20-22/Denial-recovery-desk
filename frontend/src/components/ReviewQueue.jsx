import React from "react";

export default function ReviewQueue({ tasks, open, review }) {
  return (
    <section className="panel">
      <div className="panelHead">
        <h2>Human Review Queue</h2>
        <span>{tasks.length} pending</span>
      </div>
      {!tasks.length && <div className="emptyChart">Nothing waiting on a human right now. 🎉</div>}
      <ul className="reviewList">
        {tasks.map((t) => (
          <li key={t.id}>
            <div>
              <b>DR-{String(t.denial_id).padStart(4, "0")}</b>
              <p>{t.reason}</p>
            </div>
            <div className="reviewActions">
              <button className="link" onClick={() => open(t.denial_id)}>
                Inspect →
              </button>
              <button className="good" onClick={() => review(t.denial_id, "APPROVE")}>
                Approve
              </button>
              <button className="danger" onClick={() => review(t.denial_id, "REJECT")}>
                Reject
              </button>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
