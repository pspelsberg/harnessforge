from app.core.extension_contracts import ExtensionEvent
def index_event(name:str,run_id:str|None=None,payload:dict|None=None)->ExtensionEvent:return ExtensionEvent(namespace="workspace_indexer",name=name,run_id=run_id,phase="progress",payload=payload or {})
