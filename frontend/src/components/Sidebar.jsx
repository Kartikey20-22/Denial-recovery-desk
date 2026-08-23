import React from "react";
import Icon from "../icons";
const items=[
 ["dashboard","Dashboard","dashboard"],["denials","Denials","file"],["claims","Claims","claims"],["documents","Documents","docs"],
 ["appeals","Appeals","appeal"],["review","Human Review","users"],["copilot","AI Copilot","bot"],["insights","AI Insights","insight"],["rules","Payer Rules","shield"],["reports","Reports","report"],
 ["users","Users","users"],["notifications","Notifications","bell"],["settings","Settings","settings"]
];
export default function Sidebar({tab,setTab,onUpload,onLogout,reviewCount,health,user}){
 return <aside className="sidebar">
   <div className="brandBlock"><div className="logoMark"><Icon name="shield" size={22}/></div><div><b>Denial</b><strong>Recovery Desk</strong></div></div>
   <button className="sidebarUpload" onClick={onUpload}><Icon name="upload" size={17}/> Upload Denial Letter</button>
   <nav>{items.map(([id,label,icon])=><button key={id} className={tab===id?"active":""} onClick={()=>setTab(id)}><Icon name={icon}/><span>{label}</span>{(id==="appeals"||id==="review")&&reviewCount>0?<em>{reviewCount}</em>:null}</button>)}</nav>
   <div className="confidenceGuide"><b>AI Confidence Guide</b><span><i className="dot green"/>90% and above <small>Auto Process</small></span><span><i className="dot blue"/>70%–89% <small>AI + Validation</small></span><span><i className="dot amber"/>50%–69% <small>Human Review</small></span><span><i className="dot red"/>Below 50% <small>Manual Review</small></span></div>
   <div className="orgCard"><div className="orgAvatar">CC</div><div><b>City Care Hospital</b><small>Switch Organization</small></div><Icon name="chevron" size={15}/></div>
   <button className="logout" onClick={onLogout}>Sign out</button>
 </aside>
}
