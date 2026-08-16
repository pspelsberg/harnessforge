import { apiJson } from "../../shared/api";
export type IndexStatus={contract_version:"1";status:"idle"|"queued"|"running"|"succeeded"|"failed"|"paused";version:number;indexed_files:number;queue_depth:number;last_sync:string|null;error:string|null};
export function indexStatus(token:string):Promise<IndexStatus>{return apiJson("/api/index/status",{token})}
export function rebuildIndex(sessionId:string,workspaceRealpath:string,token:string){return apiJson("/api/index/rebuild?session_id="+encodeURIComponent(sessionId)+"&workspace_realpath="+encodeURIComponent(workspaceRealpath),{method:"POST",token})}
export function pauseIndex(token:string){return apiJson<IndexStatus>("/api/index/pause",{method:"POST",token})}
export function resumeIndex(token:string){return apiJson<IndexStatus>("/api/index/resume",{method:"POST",token})}
