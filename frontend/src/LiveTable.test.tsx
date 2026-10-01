import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, it } from 'vitest'
import { MemoryRouter, useLocation } from 'react-router-dom'
import { LiveTable } from './LiveTable'
import { Reference } from './RecordDrawer'

afterEach(cleanup)
function Location() {
  return <output aria-label="URL">{useLocation().search}</output>
}
function View({ initial = '/' }: { initial?: string }) {
  return (
    <MemoryRouter initialEntries={[initial]}>
      <Location />
      <LiveTable id="risks">
        <thead>
          <tr>
            <th>Reference</th>
            <th>Score</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>
              <Reference value="RISK-002" />
            </td>
            <td>20</td>
          </tr>
          <tr>
            <td>
              <Reference value="RISK-001" />
            </td>
            <td>4</td>
          </tr>
        </tbody>
      </LiveTable>
    </MemoryRouter>
  )
}
it('restores shared search and finds references rendered by components', () => {
  render(<View initial="/?risks.q=RISK-001" />)
  expect(screen.getAllByRole('row')).toHaveLength(2)
  expect(screen.getByRole('link', { name: 'RISK-001' })).toBeTruthy()
  fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'RISK-002' } })
  expect(screen.getByLabelText('URL').textContent).toContain('risks.q=RISK-002')
  expect(screen.getByRole('link', { name: 'RISK-002' })).toBeTruthy()
})
it('sorts numeric cells and preserves unrelated URL state', () => {
  render(<View initial="/?module=active" />)
  fireEvent.click(screen.getByRole('button', { name: 'Score' }))
  expect(screen.getAllByRole('row')[1].textContent).toContain('RISK-001')
  expect(screen.getByLabelText('URL').textContent).toContain('module=active')
  fireEvent.click(screen.getByRole('button', { name: 'Score' }))
  expect(screen.getAllByRole('row')[1].textContent).toContain('RISK-002')
})
it('hides columns, resets view and supports row keyboard navigation', () => {
  render(<View />)
  fireEvent.click(screen.getByLabelText('Score'))
  expect(screen.queryByRole('columnheader', { name: 'Score' })).toBeNull()
  fireEvent.click(screen.getByRole('button', { name: 'Reset view' }))
  const rows = screen.getAllByRole('row')
  rows[1].focus()
  fireEvent.keyDown(rows[1], { key: 'ArrowDown' })
  expect(document.activeElement).toBe(rows[2])
  fireEvent.keyDown(rows[2], { key: 'Home' })
  expect(document.activeElement).toBe(rows[1])
})
