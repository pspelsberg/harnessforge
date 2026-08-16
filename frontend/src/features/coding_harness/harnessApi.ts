import { apiJson } from "../../shared/api";
export type Template={contract_version:"1";template_id:string;version:string;content_hash:string;signature:string;capabilities:string[];steps:{step_id:string;action:string;requires_gate:boolean;max_attempts:number}[];description:string};
export function listHarnesses(token:string):Promise<{templates:Template[]} >{return apiJson("/api/harness/templates",{token})}
export function importHarness(template:Template,token:string){return apiJson("/api/harness/templates",{method:"POST",token,body:JSON.stringify({template,read_only:true,enable_push:false})})}
export function advanceHarness(request:unknown,token:string){return apiJson("/api/harness/plans/advance",{method:"POST",token,body:JSON.stringify(request)})}
