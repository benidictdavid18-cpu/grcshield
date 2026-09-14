import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { api, ApiValidationError, type RiskDetail } from '../api'
import { ResidualForm } from './ResidualForm'

const RISK: RiskDetail = {
  risk_ref: 'RISK-019',
  title: 'Undocumented processing activity',
  category: 'COMPLIANCE',
  category_label: 'Compliance',
  owner_role: 'Data Protection Officer',
  status: 'OPEN',
  treatment_decision: 'MITIGATE',
  inherent: { likelihood: 3, impact: 3, score: 9, band: 'MEDIUM' },
  residual: { likelihood: 3, impact: 3, score: 9, band: 'MEDIUM' },
  appetite: { max_acceptable_band: 'LOW', approver_role: 'x', exceeds_appetite: true },
  justification_outstanding: false,
  has_uncredited_controls: true,
  description: '',
  asset: '',
  threat: '',
  vulnerability: '',
  residual_justification: 'No reduction is claimed.',
  treatment_summary: '',
  date_identified: '2026-01-12',
  last_reviewed: null,
  next_review: null,
  controls: [
    {
      control_id: 'DP-003',
      title: 'Classification',
      control_family: 'DP',
      owner_role: 'x',
      annex_a_refs: [],
      effectiveness_basis: 'NOT_TESTED',
      credits_reduction: false,
      note: null,
    },
  ],
}

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

describe('ResidualForm', () => {
  it('puts the refusal under the field the API names and saves nothing', async () => {
    const spy = vi
      .spyOn(api, 'updateResidual')
      .mockRejectedValue(
        new ApiValidationError(422, '1 problem with this change.', [
          { field: 'residual_justification', message: 'residual_justification is required.' },
        ]),
      )
    const onSaved = vi.fn()
    render(<ResidualForm risk={RISK} onSaved={onSaved} />)

    fireEvent.click(screen.getByRole('button', { name: /re-score residual risk/i }))
    fireEvent.change(screen.getByLabelText(/residual justification/i), {
      target: { value: '   ' },
    })
    fireEvent.click(screen.getByRole('button', { name: /save residual score/i }))

    await waitFor(() => expect(screen.getByRole('alert')).toBeTruthy())
    expect(screen.getByRole('alert').textContent).toBe('residual_justification is required.')
    expect(spy).toHaveBeenCalledWith('RISK-019', {
      residual_likelihood: 3,
      residual_impact: 3,
      residual_justification: '   ',
    })
    expect(onSaved).not.toHaveBeenCalled()
    // The form stays open so the analyst can fix it.
    expect(screen.getByRole('button', { name: /save residual score/i })).toBeTruthy()
  })

  it('shows a plain-sentence refusal as a banner', async () => {
    vi.spyOn(api, 'updateResidual').mockRejectedValue(
      new ApiValidationError(422, 'Residual score 3 is below the inherent score 9.', []),
    )
    render(<ResidualForm risk={RISK} onSaved={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: /re-score residual risk/i }))
    fireEvent.change(screen.getByLabelText(/residual likelihood/i), { target: { value: '1' } })
    fireEvent.click(screen.getByRole('button', { name: /save residual score/i }))
    await waitFor(() =>
      expect(screen.getByRole('alert').textContent).toContain('below the inherent score'),
    )
  })

  it('closes and reports back on a successful save', async () => {
    vi.spyOn(api, 'updateResidual').mockResolvedValue(RISK)
    const onSaved = vi.fn()
    render(<ResidualForm risk={RISK} onSaved={onSaved} />)
    fireEvent.click(screen.getByRole('button', { name: /re-score residual risk/i }))
    fireEvent.click(screen.getByRole('button', { name: /save residual score/i }))
    await waitFor(() => expect(onSaved).toHaveBeenCalledWith(RISK))
    expect(screen.queryByRole('button', { name: /save residual score/i })).toBeNull()
  })
})
