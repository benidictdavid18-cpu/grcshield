"""End-to-end smoke test against a running GRCShield instance.

Checks four things, in this order, because each depends on the last:

  1. The service is up and the database is seeded.
  2. Authentication works, and unauthenticated reads are refused.
  3. The read-only role really is read-only.
  4. The RISK-004 traceability chain resolves end to end, across all six phases.

Exits non-zero on the first failure, so it is usable as a deployment gate.

    python scripts/smoke_test.py [--base-url http://localhost:8000]
"""

import argparse
import json
import sys
import urllib.error
import urllib.request

DEFAULT_BASE = "http://localhost:8000"
AUDITOR = ("auditor", "auditor-demo-2026")
MANAGER = ("isms.manager", "manager-demo-2026")

_passed = 0
_failed: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> bool:
    global _passed
    if condition:
        _passed += 1
        print(f"  PASS  {name}")
    else:
        _failed.append(f"{name}{f' — {detail}' if detail else ''}")
        print(f"  FAIL  {name}{f' — {detail}' if detail else ''}")
    return condition


def request(base: str, path: str, token: str | None = None, method: str = "GET", body=None):
    """Return (status, parsed_body_or_bytes)."""
    url = f"{base}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            raw = response.read()
            if response.headers.get("Content-Type", "").startswith("application/json"):
                return response.status, json.loads(raw)
            return response.status, raw
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, raw
    except urllib.error.URLError as exc:
        return 0, str(exc)


def login(base: str, username: str, password: str) -> str | None:
    status, body = request(
        base, "/auth/token", method="POST", body={"username": username, "password": password}
    )
    return body.get("access_token") if status == 200 and isinstance(body, dict) else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=DEFAULT_BASE)
    base = parser.parse_args().base_url.rstrip("/")

    print(f"GRCShield smoke test against {base}\n")

    # --- 1. Service and seed ------------------------------------------------
    print("Service")
    status, health = request(base, "/health")
    if not check("health endpoint responds", status == 200, str(health)[:120]):
        return report()
    check("database reachable", health.get("database") == "ok")
    check(
        "Annex A fully seeded",
        health.get("annex_a_controls") == 93,
        f"got {health.get('annex_a_controls')}",
    )
    check("health reports seeded", health.get("seeded") is True)
    check("portfolio disclaimer present", "fictional" in health.get("disclaimer", "").lower())

    # --- 2. Authentication ---------------------------------------------------
    print("\nAuthentication")
    status, _ = request(base, "/risks")
    check("unauthenticated read is refused", status == 401, f"got {status}")

    status, _ = request(base, "/risks", token="not-a-real-token")
    check("garbage token is refused", status == 401, f"got {status}")

    status, body = request(
        base, "/auth/token", method="POST",
        body={"username": AUDITOR[0], "password": "wrong-password"},
    )
    check("wrong password is refused", status == 401, f"got {status}")

    auditor = login(base, *AUDITOR)
    if not check("auditor can authenticate", auditor is not None):
        return report()
    manager = login(base, *MANAGER)
    if not check("ISMS manager can authenticate", manager is not None):
        return report()

    status, me = request(base, "/auth/me", token=auditor)
    check("auditor role is AUDITOR", me.get("role") == "AUDITOR", str(me))
    check("auditor cannot write", me.get("can_write") is False)

    # --- 3. Read-only really means read-only ---------------------------------
    print("\nAuthorisation")
    status, _ = request(base, "/risks", token=auditor)
    check("auditor can read the register", status == 200, f"got {status}")

    status, body = request(
        base, "/risks/RISK-001/residual", token=auditor, method="PATCH",
        body={
            "residual_likelihood": 1, "residual_impact": 1,
            "residual_justification": "smoke test should never persist this",
        },
    )
    check("auditor write is refused", status == 403, f"got {status}")

    status, _ = request(base, "/soa/A.8.13", token=auditor, method="PATCH", body={"owner": "x"})
    check("auditor SoA write is refused", status == 403, f"got {status}")

    # --- 4. The RISK-004 chain, end to end ------------------------------------
    print("\nRISK-004 traceability chain")
    status, risk = request(base, "/risks/RISK-004", token=auditor)
    if not check("risk resolves", status == 200, str(risk)[:120]):
        return report()
    check(
        "inherent scored 4x5=20 Critical",
        risk["inherent"]["score"] == 20 and risk["inherent"]["band"] == "CRITICAL",
        str(risk["inherent"]),
    )
    check(
        "residual scored 3x5=15 High",
        risk["residual"]["score"] == 15 and risk["residual"]["band"] == "HIGH",
        str(risk["residual"]),
    )
    check(
        "impact did not move — no single percentage could produce this",
        risk["inherent"]["impact"] == risk["residual"]["impact"] == 5,
    )
    check("treatment decision recorded", risk["treatment_decision"] == "MITIGATE")
    check("above Cybersecurity appetite", risk["appetite"]["exceeds_appetite"] is True)

    controls = {c["control_id"]: c for c in risk["controls"]}
    check("AC-002 linked", "AC-002" in controls)
    check(
        "AC-002 basis is tested-with-exceptions",
        controls.get("AC-002", {}).get("effectiveness_basis") == "TESTED_WITH_EXCEPTIONS",
    )
    check("A.8.5 reached from the control", "A.8.5" in controls.get("AC-002", {}).get("annex_a_refs", []))

    status, soa = request(base, "/soa/A.8.5", token=auditor)
    check("SoA entry resolves", status == 200)
    check("A.8.5 is a gap", soa.get("is_gap") is True)
    check("RISK-004 reachable from the SoA entry", "RISK-004" in [r["risk_ref"] for r in soa.get("risks", [])])
    evidence = {e["evidence_ref"]: e for e in soa.get("evidence", [])}
    check("EV-002 linked as evidence", "EV-002" in evidence)
    check("evidence shows 60% coverage", "60%" in evidence.get("EV-002", {}).get("description", ""))

    status, test = request(base, "/control-tests/TEST-003", token=auditor)
    check("workpaper resolves", status == 200)
    check("tested the full privileged population", test.get("sample_size") == 15)
    check("six exceptions found", test.get("exceptions_count") == 6)
    check("concluded pass with exceptions", test.get("conclusion") == "PASS_WITH_EXCEPTIONS")
    check("reviewer is not the tester", test.get("reviewed_by") != test.get("tester"))
    check("raised FIND-001", test.get("linked_finding_ref") == "FIND-001")

    status, finding = request(base, "/findings/FIND-001", token=auditor)
    check("finding resolves", status == 200)
    check("finding traces back to TEST-003", finding.get("source_test_ref") == "TEST-003")
    remediation = finding.get("remediation", [])
    check("finding carries remediation", len(remediation) >= 1)
    if remediation:
        check("remediation has an owner", bool(remediation[0]["owner"].strip()))
        check("remediation has a due date", bool(remediation[0]["due_date"]))

    status, exceptions = request(base, "/risk-exceptions", token=auditor)
    exc = [e for e in exceptions if e["risk_ref"] == "RISK-004"]
    check("acceptance request on record for RISK-004", len(exc) == 1)
    if exc:
        check("the acceptance was refused", exc[0]["status"] == "REJECTED", exc[0]["status"])

    status, nonconformities = request(base, "/isms/nonconformities", token=auditor)
    nc = [n for n in nonconformities if n.get("finding_ref") == "FIND-001"]
    check("nonconformity raised from the finding", len(nc) == 1)
    if nc:
        check("correction and corrective action are both recorded",
              bool(nc[0]["immediate_correction"]) and bool(nc[0]["corrective_action"]))

    status, kris = request(base, "/kris", token=auditor)
    mfa = [k for k in kris if k["kri_ref"] == "KRI-001"]
    check("KRI set resolves", status == 200 and len(kris) == 7, f"{len(kris) if isinstance(kris, list) else kris}")
    if mfa:
        check("MFA coverage KRI computes 60%", mfa[0]["current_value"] == 60.0, str(mfa[0]["current_value"]))
        check("and is red against target", mfa[0]["current_band"] == "RED")

    # --- Reports ---------------------------------------------------------------
    print("\nReports")
    for name, path in (
        ("Risk Register", "/reports/risk-register.pdf"),
        ("SoA + Gap Analysis", "/soa/report.pdf"),
        ("Executive Summary", "/reports/executive-summary.pdf"),
    ):
        status, pdf = request(base, path, token=auditor)
        check(
            f"{name} renders",
            status == 200 and isinstance(pdf, bytes) and pdf.startswith(b"%PDF-"),
            f"status {status}",
        )

    status, summary = request(base, "/executive-summary", token=auditor)
    if check("executive summary resolves", status == 200, f"status {status}"):
        check("posture statement present", bool(summary.get("posture_statement")))
        check("three priorities recommended", len(summary.get("priorities", [])) == 3)
        check(
            "no control identifiers in the board-facing prose",
            not any(
                token in summary["posture_statement"] + " ".join(
                    p["why"] for p in summary["priorities"]
                )
                for token in ("A.5.", "A.6.", "A.7.", "A.8.", "AC-0", "DP-0", "OP-0")
            ),
        )

    _ = manager
    return report()


def report() -> int:
    print(f"\n{_passed} passed, {len(_failed)} failed")
    if _failed:
        print("\nFailures:")
        for failure in _failed:
            print(f"  - {failure}")
        return 1
    print("\nAll smoke checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
