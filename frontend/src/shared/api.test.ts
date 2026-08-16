import {describe,it,expect,vi} from "vitest"; import {apiJson,ApiError} from "./api";
describe("api boundary",()=>{it("adds token and parses JSON",async()=>{const fetcher=vi.spyOn(globalThis,"fetch").mockResolvedValue(new Response(JSON.stringify({ok:true}),{status:200})); expect(await apiJson<{ok:boolean}>("/health",{token:"t"})).toEqual({ok:true}); expect((fetcher.mock.calls[0][1] as RequestInit).headers).toBeDefined(); fetcher.mockRestore();}); it("normalizes errors",async()=>{vi.spyOn(globalThis,"fetch").mockResolvedValue(new Response("x",{status:403})); await expect(apiJson("/x")).rejects.toBeInstanceOf(ApiError); vi.restoreAllMocks();});});

it("does not expose response bodies in normalized errors",async()=>{vi.spyOn(globalThis,"fetch").mockResolvedValue(new Response("secret stack",{status:500}));await expect(apiJson("/x")).rejects.toThrow("request failed: 500");await expect(apiJson("/x")).rejects.not.toThrow("secret stack");vi.restoreAllMocks();});


it("uses documented API route names",async()=>{const f=vi.spyOn(globalThis,"fetch").mockResolvedValue(new Response(JSON.stringify({status:"ready"}),{status:200}));await apiJson("/ready");expect(f.mock.calls[0][0]).toBe("/ready");f.mockRestore();});
