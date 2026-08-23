import React, { useState } from "react";
import { api } from "../api";
import { useToast } from "../Toast";

export default function UploadModal({ onClose, onDone }) {
  const [file, setFile] = useState(null);
  const [claimNo, setClaimNo] = useState("");
  const [payer, setPayer] = useState("");
  const [amount, setAmount] = useState("");
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [drag, setDrag] = useState(false);
  const toast = useToast();

  function pick(f) {
    if (!f) return;
    setFile(f);
    if (!claimNo) setClaimNo(`CLM-${Math.floor(1000 + Math.random() * 9000)}`);
  }

  async function submit(e) {
    e.preventDefault();
    if (!file) return toast("Attach a PDF or image of the denial letter first.", "warn");
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("claim_no", claimNo);
      fd.append("payer", payer || "Unspecified Payer");
      fd.append("amount", amount || 0);
      fd.append("denial_text", text);
      const denial = await api.uploadDenial(fd);
      toast(`DR-${String(denial.id).padStart(4, "0")} processed through the pipeline.`, "good");
      onDone(denial.id);
    } catch (err) {
      toast(err.message || "Upload failed.", "warn");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="modalBackdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="panelHead">
          <h2>New denial</h2>
          <button className="link" onClick={onClose}>
            ✕
          </button>
        </div>
        <form onSubmit={submit} className="uploadForm">
          <label
            className={"dropzone" + (drag ? " drag" : "")}
            onDragOver={(e) => {
              e.preventDefault();
              setDrag(true);
            }}
            onDragLeave={() => setDrag(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDrag(false);
              pick(e.dataTransfer.files?.[0]);
            }}
          >
            <input type="file" accept=".pdf,.png,.jpg,.jpeg,.webp,.tiff" onChange={(e) => pick(e.target.files?.[0])} />
            {file ? <span>{file.name}</span> : <span>Drop a PDF or image, or click to browse</span>}
          </label>

          <div className="formRow">
            <input value={claimNo} onChange={(e) => setClaimNo(e.target.value)} placeholder="Claim #" required />
            <input value={payer} onChange={(e) => setPayer(e.target.value)} placeholder="Payer name" />
          </div>
          <div className="formRow">
            <input value={amount} onChange={(e) => setAmount(e.target.value)} placeholder="Billed amount ($)" type="number" min="0" />
          </div>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Paste denial letter text here (used if OCR can't read the file, or as extra context)"
            rows={4}
          />
          <div className="actions">
            <button disabled={busy}>{busy ? "Running pipeline…" : "Run denial pipeline"}</button>
            <button type="button" className="secondary" onClick={onClose}>
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
