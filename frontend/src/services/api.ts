import type { Dashboard, Task } from '../types';
const BASE = 'http://127.0.0.1:8765';
async function json<T>(path:string, init?:RequestInit):Promise<T>{ const r=await fetch(`${BASE}${path}`,{...init,headers:{'Content-Type':'application/json',...(init?.headers||{})}}); if(!r.ok) throw new Error(await r.text()); return r.json(); }
export const api = {
  dashboard:()=>json<Dashboard>('/api/dashboard'),
  tasks:()=>json<Task[]>('/api/tasks'),
  complete:(id:number)=>json<Task>(`/api/tasks/${id}/complete`,{method:'PATCH'}),
  draft:(email_id:number, mode:string, user_intent?:string)=>json<{draft:string;requires_user_approval:boolean}>('/api/draft',{method:'POST',body:JSON.stringify({email_id,mode,user_intent})}),
  ingestCurrent: (payload:unknown)=>json<Task>('/api/emails/ingest',{method:'POST',body:JSON.stringify(payload)})
};
