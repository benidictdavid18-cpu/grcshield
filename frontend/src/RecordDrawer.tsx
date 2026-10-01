import { CascadeGraph } from './CascadeGraph'
import { useEffect, useRef, type ReactNode } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api } from './api'
import { useAsync } from './useAsync'

export function useDrawerAccessibility(onClose: () => void) {
  const ref = useRef<HTMLElement>(null)
  const close = useRef(onClose)
  close.current = onClose
  useEffect(() => {
    const before = document.activeElement as HTMLElement | null
    const root = ref.current
    if (!root) return
    root.setAttribute('role', 'dialog')
    root.setAttribute('aria-modal', 'true')
    root.setAttribute('aria-label', root.querySelector('h2')?.textContent ?? 'Record details')
    const focusable = () =>
      Array.from(
        root.querySelectorAll<HTMLElement>(
          'a[href],button:not(:disabled),input:not(:disabled),select,textarea,summary,[tabindex="0"]',
        ),
      ).filter((el) => el.getClientRects().length > 0)
    const main = document.querySelector('main')
    // The drawer can be nested inside main; only inert siblings of its ancestors.
    const siblings: HTMLElement[] = []
    let current: HTMLElement | null = root
    while (current && current !== document.body) {
      for (const sibling of Array.from(current.parentElement?.children ?? [])) {
        if (sibling !== current && sibling instanceof HTMLElement && !sibling.inert) {
          sibling.inert = true
          siblings.push(sibling)
        }
      }
      current = current.parentElement
    }
    const oldOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    root.tabIndex = -1
    ;(focusable()[0] ?? root).focus()
    const handle = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault()
        event.stopPropagation()
        close.current()
      }
      if (event.key === 'Tab') {
        const nodes = focusable(),
          first = nodes[0],
          last = nodes.at(-1)
        if (!first) {
          event.preventDefault()
          root.focus()
        } else if (
          event.shiftKey &&
          (document.activeElement === first || document.activeElement === root)
        ) {
          event.preventDefault()
          last?.focus()
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault()
          first.focus()
        }
      }
    }
    root.addEventListener('keydown', handle)
    return () => {
      root.removeEventListener('keydown', handle)
      siblings.forEach((el) => {
        el.inert = false
      })
      document.body.style.overflow = oldOverflow
      if (before?.isConnected) before.focus()
      else main?.focus()
    }
  }, [])
  return ref
}

export function Reference({ value, children }: { value: string; children?: ReactNode }) {
  const [params] = useSearchParams()
  const next = new URLSearchParams(params)
  next.set('record', value)
  return (
    <a
      href={`?${next}`}
      onClick={(event) => {
        // Handled by the app's reference boundary; normal modified clicks stay shareable.
        if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return
      }}
    >
      {children ?? value}
    </a>
  )
}

const REF =
  /^(?:RISK|TEST|FIND|REM|EVT|SUP|OBL|EV|EVID|AST|ASSET|ROPA|DPIA|BIA|EXC|KRI|IAM|AC|DP|TP|BC|IR|NET|LOG|VUL|HR|GOV|GV|OP|SD|VM|PE|SEC|CHG|PHY|DEV|AUD|MR|NC)[-]?\d+$|^A\.[5-8]\.\d+$/
export function RecordFields({ value }: { value: unknown }) {
  if (value === null || value === undefined) return <span className="muted">Not recorded</span>
  if (Array.isArray(value))
    return value.length ? (
      <div className="record-array">
        {value.map((item, i) => (
          <div key={i}>
            <RecordFields value={item} />
          </div>
        ))}
      </div>
    ) : (
      <span className="muted">None recorded</span>
    )
  if (typeof value === 'object')
    return (
      <dl className="record-fields">
        {Object.entries(value)
          .filter(([key]) => !['id', 'disclaimer'].includes(key))
          .map(([key, entry]) => (
            <div key={key}>
              <dt>{key.replace(/_/g, ' ')}</dt>
              <dd>
                <RecordFields value={entry} />
              </dd>
            </div>
          ))}
      </dl>
    )
  if (typeof value === 'boolean') return <span>{value ? 'Yes' : 'No'}</span>
  if (typeof value === 'string' && REF.test(value)) return <Reference value={value} />
  return (
    <span className={String(value).includes('TODO AUTHOR:BENNY') ? 'todo-text' : ''}>
      {String(value)}
    </span>
  )
}

export async function loadRecord(ref: string): Promise<unknown> {
  if (ref.startsWith('RISK')) return api.risk(ref)
  if (ref.startsWith('AUD')) return api.read(`/isms/audits/${encodeURIComponent(ref)}`)
  if (ref.startsWith('MR')) return api.read(`/isms/management-reviews/${encodeURIComponent(ref)}`)
  if (ref.startsWith('NC')) return api.read(`/isms/nonconformities/${encodeURIComponent(ref)}`)
  if (ref.startsWith('REM')) return api.read(`/records/remediation/${encodeURIComponent(ref)}`)
  if (/^EV-?\d+$/.test(ref)) return api.read(`/records/evidence/${encodeURIComponent(ref)}`)
  if (ref.startsWith('TEST')) return api.controlTest(ref)
  if (ref.startsWith('A.')) return api.soaEntry(ref)
  if (ref.startsWith('EVT')) return api.read(`/incidents/${encodeURIComponent(ref)}`)
  if (ref.startsWith('SUP')) return api.read(`/suppliers/${encodeURIComponent(ref)}`)
  if (ref.startsWith('OBL')) return api.read(`/obligations/${encodeURIComponent(ref)}`)
  const sources: [string, () => Promise<unknown[]>][] = [
    ['FIND', api.findings],
    ['EXC', api.riskExceptions],
    ['ROPA', api.ropa],
    ['DPIA', api.dpias],
    ['BIA', api.bia],
    ['ASSET', api.assets],
    ['AST', api.assets],
    ['KRI', api.kris],
  ]
  const source = sources.find(([prefix]) => ref.startsWith(prefix))
  const records = source ? await source[1]() : await api.internalControls()
  const record = records.find((item) =>
    Object.entries(item as Record<string, unknown>).some(
      ([key, value]) => (key.endsWith('_ref') || key === 'control_id') && value === ref,
    ),
  )
  if (!record)
    throw new Error(
      `No accessible record found for ${ref}. Check the reference and your access rights.`,
    )
  return record
}

export function RecordDrawer({ record, onClose }: { record: string; onClose: () => void }) {
  const [attempt, setAttempt] = useSearchParams()
  const retry = attempt.get('retry') ?? ''
  const { data, loading, error } = useAsync(() => loadRecord(record), [record, retry])
  const ref = useDrawerAccessibility(onClose)
  return (
    <aside ref={ref} className="drawer reference-drawer">
      <div className="drawer-head">
        <div>
          <span className="eyebrow">Sample / Portfolio Assessment</span>
          <h2>{record}</h2>
        </div>
        <button type="button" onClick={onClose} aria-label="Close record details">
          ×
        </button>
      </div>
      {loading && (
        <div className="skeleton" role="status">
          Loading record…
        </div>
      )}
      {error && (
        <div role="alert" className="error">
          <p>{error}</p>
          <button
            onClick={() =>
              setAttempt(
                (old) => {
                  const next = new URLSearchParams(old)
                  next.set('retry', String(Date.now()))
                  return next
                },
                { replace: true },
              )
            }
          >
            Try again
          </button>
        </div>
      )}
      {record.startsWith('RISK') && (
        <p>
          <Link data-navigation to={`/risks/${record}`}>
            Open full risk assessment and evidence graph →
          </Link>
        </p>
      )}
      {data !== null &&
        typeof data === 'object' &&
        'control_id' in data &&
        typeof data.control_id === 'string' && <CascadeGraph controlRef={data.control_id} />}
      {data !== null && <RecordFields value={data} />}
    </aside>
  )
}
