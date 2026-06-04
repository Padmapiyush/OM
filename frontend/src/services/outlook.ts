declare const Office: any;
export async function getCurrentEmailPayload(){
  const item = Office?.context?.mailbox?.item;
  if(!item) return null;
  const body = await new Promise<string>((resolve)=> item.body.getAsync('text', (r:any)=> resolve(r.value || '')));
  return { graph_id: item.itemId || crypto.randomUUID(), conversation_id: item.conversationId, folder:'Inbox', sender:item.from?.emailAddress, subject:item.subject || '', body_preview: body.slice(0,500), body, attachments:[], received_at: item.dateTimeCreated || new Date().toISOString(), is_read:true };
}
export function ready(cb:()=>void){ if(typeof Office !== 'undefined') Office.onReady(cb); else cb(); }
