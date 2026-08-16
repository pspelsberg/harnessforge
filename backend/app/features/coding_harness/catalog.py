"""Read-only catalog of hash-validated harness templates."""
from app.features.coding_harness.contracts import HarnessImport,HarnessTemplate
from app.features.coding_harness.validator import HarnessValidator,HarnessValidationError
class HarnessCatalogError(RuntimeError):pass
class HarnessCatalog:
 def __init__(self):self._templates={};self.validator=HarnessValidator()
 def import_template(self,request:HarnessImport)->HarnessTemplate:
  try:template=self.validator.validate(request)
  except HarnessValidationError as exc:raise HarnessCatalogError("template rejected") from exc
  self._templates[template.template_id]=template;return template
 def get(self,template_id:str)->HarnessTemplate:
  if template_id not in self._templates:raise HarnessCatalogError("template unavailable")
  return self._templates[template_id]
 def list(self):return list(self._templates.values())
