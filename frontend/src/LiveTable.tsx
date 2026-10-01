import { Children, cloneElement, isValidElement, type ReactElement, type ReactNode } from 'react'
import { useSearchParams } from 'react-router-dom'

type Element = ReactElement<{ children?: ReactNode; className?: string }>
function elements(node: ReactNode): Element[] {
  return Children.toArray(node).filter(isValidElement) as Element[]
}
function text(node: ReactNode): string {
  return Children.toArray(node)
    .map((child) =>
      isValidElement<{ children?: ReactNode; value?: string }>(child)
        ? text(child.props.children ?? child.props.value)
        : String(child),
    )
    .join(' ')
}

/** Retains the register's authored cells and links; view state belongs in the URL. */
export function LiveTable({
  id,
  children,
  className = 'register',
}: {
  id: string
  children: ReactNode
  className?: string
}) {
  const [params, setParams] = useSearchParams()
  const query = params.get(`${id}.q`) ?? ''
  const sort = Number(params.get(`${id}.sort`) ?? -1)
  const descending = params.get(`${id}.dir`) === 'desc'
  const hidden = new Set((params.get(`${id}.hide`) ?? '').split(',').filter(Boolean))
  const sections = elements(children)
  const head = sections.find((section) => section.type === 'thead')
  const body = sections.find((section) => section.type === 'tbody')
  const headers = elements(elements(head?.props.children)[0]?.props.children)
  const rows = elements(body?.props.children)
  const update = (key: string, value: string) =>
    setParams(
      (previous) => {
        const next = new URLSearchParams(previous)
        if (value) next.set(`${id}.${key}`, value)
        else next.delete(`${id}.${key}`)
        return next
      },
      { replace: true },
    )
  const shown = rows.filter((row) =>
    text(row.props.children).toLocaleLowerCase().includes(query.toLocaleLowerCase()),
  )
  if (sort >= 0 && sort < headers.length)
    shown.sort((a, b) => {
      const left = text(elements(a.props.children)[sort]?.props.children).trim()
      const right = text(elements(b.props.children)[sort]?.props.children).trim()
      return left.localeCompare(right, undefined, { numeric: true }) * (descending ? -1 : 1)
    })
  return (
    <section className="live-table" aria-label={`${id.replace(/-/g, ' ')} register`}>
      <div className="table-tools">
        <label className="table-search">
          Search this view
          <input
            type="search"
            value={query}
            placeholder="Reference, owner, status…"
            onChange={(e) => update('q', e.target.value)}
          />
        </label>
        <details className="column-picker">
          <summary>Columns</summary>
          <div>
            {headers.map((header, index) => (
              <label key={index}>
                <input
                  type="checkbox"
                  checked={!hidden.has(String(index))}
                  disabled={!hidden.has(String(index)) && headers.length - hidden.size <= 1}
                  onChange={(e) => {
                    if (e.target.checked) hidden.delete(String(index))
                    else hidden.add(String(index))
                    update('hide', [...hidden].join(','))
                  }}
                />
                {text(header.props.children)}
              </label>
            ))}
          </div>
        </details>
        <span className="muted" role="status">
          {shown.length} of {rows.length} records
        </span>
        <button
          type="button"
          onClick={() =>
            setParams(
              (previous) => {
                const next = new URLSearchParams(previous)
                for (const key of [...next.keys()]) if (key.startsWith(`${id}.`)) next.delete(key)
                return next
              },
              { replace: true },
            )
          }
        >
          Reset view
        </button>
      </div>
      <table className={className} aria-label={id.replace(/-/g, ' ')}>
        <thead>
          <tr>
            {headers.map(
              (header, index) =>
                !hidden.has(String(index)) && (
                  <th
                    key={index}
                    scope="col"
                    aria-sort={sort === index ? (descending ? 'descending' : 'ascending') : 'none'}
                  >
                    <button
                      type="button"
                      onClick={() =>
                        setParams(
                          (previous) => {
                            const next = new URLSearchParams(previous)
                            next.set(`${id}.sort`, String(index))
                            next.set(`${id}.dir`, sort === index && !descending ? 'desc' : 'asc')
                            return next
                          },
                          { replace: true },
                        )
                      }
                    >
                      {header.props.children}{' '}
                      <span aria-hidden="true">
                        {sort === index ? (descending ? '↓' : '↑') : '↕'}
                      </span>
                    </button>
                  </th>
                ),
            )}
          </tr>
        </thead>
        <tbody>
          {shown.map((row, index) => (
            <tr
              key={row.key ?? index}
              className={row.props.className}
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.target !== e.currentTarget) return
                const siblings = Array.from(
                  e.currentTarget.parentElement?.children ?? [],
                ) as HTMLElement[]
                const position = siblings.indexOf(e.currentTarget)
                const target =
                  e.key === 'ArrowDown'
                    ? siblings[position + 1]
                    : e.key === 'ArrowUp'
                      ? siblings[position - 1]
                      : e.key === 'Home'
                        ? siblings[0]
                        : e.key === 'End'
                          ? siblings.at(-1)
                          : null
                if (target) {
                  e.preventDefault()
                  target.focus()
                }
                if (e.key === 'Enter')
                  e.currentTarget.querySelector<HTMLElement>('a,button')?.click()
              }}
            >
              {elements(row.props.children).map(
                (cell, col) =>
                  !hidden.has(String(col)) &&
                  cloneElement(cell, {
                    key: col,
                    ...{ 'data-label': text(headers[col]?.props.children) },
                  }),
              )}
            </tr>
          ))}
        </tbody>
      </table>
      {!shown.length && (
        <p className="empty">No records match this view. Clear the search or reset the filters.</p>
      )}
    </section>
  )
}
