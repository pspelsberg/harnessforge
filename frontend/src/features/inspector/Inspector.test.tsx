import {render,screen,fireEvent,cleanup} from "@testing-library/react"; import {it,expect,vi,afterEach} from "vitest"; import {Inspector} from "./Inspector";
afterEach(cleanup);
it("renders config as text",()=>{render(<Inspector node={{id:"x",type:"start",position:{x:0,y:0},data:{config:{value:"<script>"},ui:{}}}}/>); expect(screen.getByRole("region",{name:"node inspector"}).textContent).toContain("<script>");});
it("edits config through a bounded JSON form",()=>{const on=vi.fn();render(<Inspector node={{id:"x",type:"start",position:{x:0,y:0},data:{config:{value:"old"},ui:{}}}} onConfigChange={on}/>);const field=screen.getByLabelText("node config"); fireEvent.change(field,{target:{value:'{"value":"new"}'}}); fireEvent.click(screen.getByRole("button",{name:"Apply config"})); expect(on).toHaveBeenCalledWith({value:"new"});});


it("does not apply secret-shaped config keys",()=>{const on=vi.fn();render(<Inspector node={{id:"x",type:"start",position:{x:0,y:0},data:{config:{},ui:{}}}} onConfigChange={on}/>);fireEvent.change(screen.getByLabelText("node config"),{target:{value:'{"api_key":"secret"}'}});fireEvent.click(screen.getByRole("button",{name:"Apply config"}));expect(on).not.toHaveBeenCalledWith(expect.objectContaining({api_key:"secret"}));});


it("shows validation error for malformed config",()=>{const on=vi.fn();render(<Inspector node={{id:"x",type:"start",position:{x:0,y:0},data:{config:{},ui:{}}}} onConfigChange={on}/>);fireEvent.change(screen.getByLabelText("node config"),{target:{value:"not-json"}});fireEvent.click(screen.getByRole("button",{name:"Apply config"}));expect(screen.getByRole("alert").textContent).toContain("Invalid");expect(on).not.toHaveBeenCalled();});
