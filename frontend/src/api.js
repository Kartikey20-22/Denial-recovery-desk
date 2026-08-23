const API = import.meta.env.VITE_API_URL || "http://localhost:8000";
class ApiError extends Error { constructor(message,status){super(message);this.status=status;} }
async function req(path,opts={}){
  const token=localStorage.getItem("token");
  const headers={...(opts.headers||{})};
  if(token) headers.Authorization=`Bearer ${token}`;
  const r=await fetch(API+path,{...opts,headers});
  if(!r.ok){let msg=r.statusText;try{const b=await r.json();msg=b.detail||msg;}catch{}throw new ApiError(msg,r.status);}
  if(r.status===204)return null; return r.json();
}
function j(body){return {headers:{"Content-Type":"application/json"},body:JSON.stringify(body)}}
const qs=(obj)=>{const q=new URLSearchParams(Object.entries(obj||{}).filter(([,v])=>v!==undefined&&v!==null&&v!==""));return q.toString()?`?${q}`:""}
export const api={
 base:API, health:()=>req("/health"), login:(email,password)=>req("/api/auth/login",{method:"POST",...j({email,password})}),
 register:(email,password,name)=>req("/api/auth/register",{method:"POST",...j({email,password,name})}),
 denials:(p={})=>req(`/api/denials${qs(p)}`), denial:(id)=>req(`/api/denials/${id}`), denialEvents:(id)=>req(`/api/denials/${id}/events`),
 denialWorkflow:(id)=>req(`/api/denials/${id}/workflow`), analyzeDenial:(id)=>req(`/api/denials/${id}/analyze`,{method:"POST"}),
 uploadDenial:(fd)=>req("/api/denials/upload",{method:"POST",body:fd}),
 reviewDenial:(id,decision,notes="",editedDraft=null)=>req(`/api/denials/${id}/review`,{method:"POST",...j({decision,notes,edited_draft:editedDraft})}),
 reviewQueue:()=>req("/api/reviews"), decideReview:(id,decision,notes)=>req(`/api/reviews/${id}`,{method:"POST",...j({decision,notes})}),
 stats:()=>req("/api/dashboard/stats"), breakdown:()=>req("/api/dashboard/breakdown"), report:()=>req("/api/dashboard/report"), learning:()=>req("/api/dashboard/learning"), operations:()=>req("/api/dashboard/operations"), batchAnalyze:(ids=null,limit=25)=>req("/api/denials/batch-analyze",{method:"POST",...j({ids,limit})}), batchRuns:()=>req("/api/denials/batch-runs"), rocketrideStatus:()=>req("/api/denials/rocketride/status"),
 outcome:(id)=>req(`/api/denials/${id}/outcome`), payerResponse:(id,status,approved_amount,message)=>req(`/api/denials/${id}/payer-response`,{method:"POST",...j({status,approved_amount,message})}),
 payment:(id,amount,status="PAID",payment_reference=null)=>req(`/api/denials/${id}/payment`,{method:"POST",...j({amount,status,payment_reference})}),
 simulate:(id)=>req(`/api/denials/${id}/simulate`,{method:"POST"}), appeals:()=>req("/api/appeals"), documents:()=>req("/api/documents"), payerRules:()=>req("/api/payer-rules"),
 notifications:()=>req("/api/notifications"), copilotChat:(question,claim_no=null,history=[])=>req("/api/copilot/chat",{method:"POST",...j({question,claim_no,history})}), copilotExamples:()=>req("/api/copilot/examples"), readNotification:(id)=>req(`/api/notifications/${id}/read`,{method:"POST"}), users:()=>req("/api/users")
};
export {ApiError};
