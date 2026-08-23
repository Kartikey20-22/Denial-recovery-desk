import React, { createContext, useCallback, useContext, useRef, useState } from "react";

const ToastCtx = createContext(null);
let uid = 0;

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const timers = useRef({});

  const dismiss = useCallback((id) => {
    setToasts((t) => t.filter((x) => x.id !== id));
    clearTimeout(timers.current[id]);
    delete timers.current[id];
  }, []);

  const push = useCallback(
    (message, tone = "info") => {
      const id = ++uid;
      setToasts((t) => [...t, { id, message, tone }]);
      timers.current[id] = setTimeout(() => dismiss(id), 4200);
    },
    [dismiss]
  );

  return (
    <ToastCtx.Provider value={push}>
      {children}
      <div className="toastStack">
        {toasts.map((t) => (
          <div key={t.id} className={`toast toast-${t.tone}`} onClick={() => dismiss(t.id)}>
            {t.message}
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
}

export function useToast() {
  return useContext(ToastCtx);
}
