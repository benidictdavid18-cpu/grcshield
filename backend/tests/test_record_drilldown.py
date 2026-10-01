def test_test008_cascade_is_retained(auditor_client):
    response = auditor_client.get('/internal-controls/DP-005/trace')
    assert response.status_code == 200
    body = response.json()
    assert body['design_effectiveness'] == 'DEFICIENT'
    assert {'RISK-008', 'RISK-018'} <= {row['risk_ref'] for row in body['risks']}
    assert any(row['test_ref'] == 'TEST-008' and row['finding_ref'] == 'FIND-003'
               for row in body['tests'])
    assert all(not row['credits_reduction'] for row in body['risks'])
    assert body['disclaimer'] == 'Sample / Portfolio Assessment'


def test_drilldown_requires_authentication(anon_client):
    assert anon_client.get('/internal-controls/DP-005/trace').status_code == 401
    assert anon_client.get('/records/evidence/EV-001').status_code == 401


def test_drilldown_returns_metadata_and_missing_reference(auditor_client):
    evidence = auditor_client.get('/records/evidence/EV-001')
    assert evidence.status_code == 200
    assert evidence.json()['evidence_ref'] == 'EV-001'
    assert 'content' not in evidence.json()
    assert auditor_client.get('/records/remediation/REM-001').status_code == 200
    assert auditor_client.get('/records/evidence/MISSING').status_code == 404
    assert auditor_client.get('/records/users/admin').status_code == 404
