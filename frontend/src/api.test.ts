import { afterEach, describe, expect, it, vi } from 'vitest'

import { api, ApiValidationError } from './api'

function respond(status: number, body: unknown) {
  return vi.fn().mockResolvedValue({
    status,
    ok: status >= 200 && status < 300,
    statusText: 'x',
    json: async () => body,
  })
}

afterEach(() => vi.unstubAllGlobals())

describe('a refused write reaches the form with its fields named', () => {
  it('parses the rule-service shape, [{field, message}]', async () => {
    vi.stubGlobal(
      'fetch',
      respond(422, {
        detail: [
          { field: 'justification_inclusion', message: 'Circular.' },
          { field: 'linked_remediation_ids', message: 'A gap needs a remediation item.' },
        ],
      }),
    )
    const err = await api.updateSoAEntry('A.8.13', { applicable: true }).catch((e) => e)
    expect(err).toBeInstanceOf(ApiValidationError)
    expect(err.status).toBe(422)
    expect(err.for('justification_inclusion')).toBe('Circular.')
    expect(err.for('linked_remediation_ids')).toBe('A gap needs a remediation item.')
    expect(err.for('owner')).toBeNull()
    expect(err.message).toBe('2 problems with this change.')
  })

  it('parses the Pydantic shape, [{loc, msg}], and drops the "Value error" prefix', async () => {
    vi.stubGlobal(
      'fetch',
      respond(422, {
        detail: [
          {
            loc: ['body', 'residual_justification'],
            msg: 'Value error, residual_justification is required.',
            type: 'value_error',
          },
        ],
      }),
    )
    const err = await api
      .updateResidual('RISK-004', {
        residual_likelihood: 1,
        residual_impact: 1,
        residual_justification: '',
      })
      .catch((e) => e)
    expect(err).toBeInstanceOf(ApiValidationError)
    expect(err.for('residual_justification')).toBe('residual_justification is required.')
  })

  it('keeps a plain-sentence refusal as the message with no field errors', async () => {
    vi.stubGlobal(
      'fetch',
      respond(422, { detail: 'Residual score 3 is below the inherent score 9.' }),
    )
    const err = await api
      .updateResidual('RISK-019', {
        residual_likelihood: 1,
        residual_impact: 3,
        residual_justification: 'x',
      })
      .catch((e) => e)
    expect(err).toBeInstanceOf(ApiValidationError)
    expect(err.fieldErrors).toEqual([])
    expect(err.message).toBe('Residual score 3 is below the inherent score 9.')
  })

  it('surfaces a 403 with the role explanation the API gives', async () => {
    vi.stubGlobal('fetch', respond(403, { detail: 'The AUDITOR role is read-only.' }))
    const err = await api.updateSoAEntry('A.8.13', { owner: 'x' }).catch((e) => e)
    expect(err).toBeInstanceOf(ApiValidationError)
    expect(err.status).toBe(403)
    expect(err.message).toBe('The AUDITOR role is read-only.')
  })

  it('sends a PATCH with a JSON body', async () => {
    const fetchMock = respond(200, {})
    vi.stubGlobal('fetch', fetchMock)
    await api.updateSoAEntry('A.8.13', { owner: 'Head of Engineering' })
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/soa/A.8.13')
    expect(init.method).toBe('PATCH')
    expect(init.headers['Content-Type']).toBe('application/json')
    expect(JSON.parse(init.body)).toEqual({ owner: 'Head of Engineering' })
  })
})
