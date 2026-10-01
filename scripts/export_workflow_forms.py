"""Export only maintained register write contracts for the operations workspace."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.main import app  # noqa: E402
from app.services.assurance import REVIEW_INPUTS  # noqa: E402
from app.services.operations import KINDS  # noqa: E402

GROUPS = {
    "incidents": ["/incidents"],
    "suppliers": ["/suppliers"],
    "obligations": ["/obligations"],
    "context": ["/isms/context", "/isms/scope-revisions"],
    "documents": ["/documents", "/document-revisions"],
    "treatment": ["/treatment-plans", "/treatment-milestones"],
    "plans": ["/isms/plans"],
    "assurance": ["/isms/assurance"],
    "competence": ["/people/requirements"],
    "communications": ["/people/communications"],
    "monitoring": ["/monitoring/plans"],
    "observations": ["/monitoring/observations"],
    "revisions": ["/operations/revisions", "/operations/reassessments"],
    "coverage": ["/operations/coverage"],
    "exercises": ["/operations/exercises"],
    "reassessments": ["/reassessments"],
    "notifications": ["/notifications"],
    "attachments": ["/evidence/", "/evidence-attachments"],
    "soa-releases": ["/soa-releases"],
    "acceptances": ["/risk-exceptions", "/acceptance-authorities"],
    "proof": ["/risks/{risk_ref}/controls", "/control-tests"],
}


def catalogue():
    spec = app.openapi()
    definitions = spec["components"]["schemas"]

    def expand(value):
        if isinstance(value, list):
            return [expand(x) for x in value]
        if not isinstance(value, dict):
            return value
        if "$ref" in value:
            return expand(definitions[value["$ref"].rsplit("/", 1)[1]])
        return {k: expand(v) for k, v in value.items()}

    workflows = []
    for path, methods in spec["paths"].items():
        group = next((g for g, prefixes in GROUPS.items() if any(path.startswith(p) for p in prefixes)), None)
        if not group:
            continue
        for method, operation in methods.items():
            if method not in ("post", "put", "patch"):
                continue
            params = [expand(p) for p in operation.get("parameters", []) if p["in"] == "path"]
            for param in params:
                if param["name"] == "category":
                    param["schema"] = {"type": "string", "enum": list(REVIEW_INPUTS)}
                if param["name"] == "action":
                    param["schema"] = {"type": "string", "enum": ["approve", "publish", "withdraw"]}
            body = expand(operation.get("requestBody", {}).get("content", {}).get("application/json", {}).get("schema", {"type": "object", "properties": {}}))
            if path == "/operations/revisions":
                body["properties"]["content"]["variants"] = {
                    kind: model.model_json_schema() for kind, (_, _, model) in KINDS.items()
                }
                for variant in body["properties"]["content"]["variants"].values():
                    local = variant.pop("$defs", {})
                    def resolve(v):
                        if isinstance(v, list):
                            return [resolve(x) for x in v]
                        if isinstance(v, dict):
                            if "$ref" in v:
                                return resolve(local[v["$ref"].split("/")[-1]])
                            return {k: resolve(x) for k, x in v.items()}
                        return v
                    resolved = resolve(variant)
                    variant.clear()
                    variant.update(resolved)
            workflows.append({"group": group, "method": method.upper(), "path": path, "parameters": params, "body": body})
    return workflows


if __name__ == "__main__":
    target = ROOT / "frontend/src/workflow-contracts.json"
    content = json.dumps(catalogue(), indent=2, ensure_ascii=False) + "\n"
    if "--check" in sys.argv:
        if target.read_text(encoding="utf-8") != content:
            raise SystemExit("Workflow contracts are stale; run scripts/export_workflow_forms.py")
    else:
        target.write_text(content, encoding="utf-8")
