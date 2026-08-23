import React from "react";

const paths = {
  dashboard: <><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></>,
  file: <><path d="M6 2h9l5 5v15H6z"/><path d="M14 2v6h6"/><path d="M9 13h7M9 17h7"/></>,
  claims: <><path d="M4 5h16v15H4z"/><path d="M8 9h8M8 13h5"/></>,
  docs: <><path d="M5 3h10l4 4v14H5z"/><path d="M15 3v5h4M8 13h8M8 17h6"/></>,
  appeal: <><path d="M4 20l4-1 10-10a2 2 0 0 0-3-3L5 16z"/><path d="M13 7l3 3"/></>,
  insight: <><path d="M4 19V9M10 19V5M16 19v-8M22 19V3"/></>,
  shield: <><path d="M12 2l8 3v6c0 5-3.5 9-8 11-4.5-2-8-6-8-11V5z"/><path d="M12 8v8M8 12h8"/></>,
  report: <><path d="M5 20V10M12 20V4M19 20v-7"/><path d="M3 20h18"/></>,
  users: <><circle cx="9" cy="8" r="3"/><circle cx="17" cy="10" r="2.5"/><path d="M3 20c0-3.5 2.5-5 6-5s6 1.5 6 5M14 16c4.5-.5 6 1.5 6 4"/></>,
  settings: <><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1-2 2-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.6V21h-3v-.2a1.7 1.7 0 0 0-1-1.6 1.7 1.7 0 0 0-1.9.3l-.1.1-2-2 .1-.1A1.7 1.7 0 0 0 7.2 15a1.7 1.7 0 0 0-1.6-1H5v-3h.2a1.7 1.7 0 0 0 1.6-1 1.7 1.7 0 0 0-.3-1.9l-.1-.1 2-2 .1.1a1.7 1.7 0 0 0 1.9.3 1.7 1.7 0 0 0 1-1.6V4h3v.2a1.7 1.7 0 0 0 1 1.6 1.7 1.7 0 0 0 1.9-.3l.1-.1 2 2-.1.1a1.7 1.7 0 0 0-.3 1.9 1.7 1.7 0 0 0 1.6 1h.2v3h-.2a1.7 1.7 0 0 0-1.6 1z"/></>,
  search: <><circle cx="10.5" cy="10.5" r="6.5"/><path d="M16 16l5 5"/></>,
  bell: <><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4"/></>,
  upload: <><path d="M12 16V4M8 8l4-4 4 4"/><path d="M5 15v5h14v-5"/></>,
  plus: <><path d="M12 5v14M5 12h14"/></>,
  track: <><circle cx="12" cy="12" r="8"/><path d="M12 8v5l3 2"/></>,
  check: <><circle cx="12" cy="12" r="9"/><path d="M8 12l2.5 2.5L16 9"/></>,
  money: <><circle cx="12" cy="12" r="9"/><path d="M12 7v10M15 9.5c-.7-.7-1.7-1-3-1-1.7 0-3 1-3 2.3 0 3.4 6 1.7 6 4.7 0 1.4-1.2 2.5-3 2.5-1.3 0-2.4-.4-3.2-1.1"/></>,
  arrow: <><path d="M5 12h14M13 6l6 6-6 6"/></>,
  filter: <><path d="M4 5h16M7 12h10M10 19h4"/></>,
  close: <><path d="M6 6l12 12M18 6L6 18"/></>,
  chevron: <path d="M8 10l4 4 4-4"/>,
  menu: <><path d="M4 7h16M4 12h16M4 17h16"/></>,
  bot: <><rect x="4" y="6" width="16" height="13" rx="3"/><path d="M12 2v4M8 11h.01M16 11h.01M8 15h8"/></>,
  calendar: <><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M7 3v4M17 3v4M3 10h18"/></>,
  external: <><path d="M14 4h6v6M20 4l-9 9"/><path d="M18 13v5a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h5"/></>,
};

export default function Icon({ name, size=18, strokeWidth=1.8 }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name] || paths.file}</svg>;
}
