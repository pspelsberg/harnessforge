from app.core.security.redaction import redact
def artifact_text(value:str)->str:return redact(value,limit=131072)
