export class ApiError extends Error { constructor(public readonly status:number,message:string){super(message)} }
export async function apiJson<T>(url:string, options:RequestInit & {token?:string;timeoutMs?:number} = {}):Promise<T>{
 const {token,timeoutMs=30000,...init}=options; const controller=new AbortController(); const timeout=setTimeout(()=>controller.abort(),Math.min(Math.max(timeoutMs,1),120000)); const headers=new Headers(init.headers); headers.set("content-type","application/json"); if(token) headers.set("x-harnessforge-token",token);
 try { const response=await fetch(url,{...init,headers,signal:init.signal||controller.signal}); if(!response.ok) throw new ApiError(response.status,`request failed: ${response.status}`); return response.json() as Promise<T>; } finally { clearTimeout(timeout); }
}
