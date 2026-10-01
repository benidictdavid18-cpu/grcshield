import { type SetStateAction } from 'react'
import { useSearchParams } from 'react-router-dom'

export function useViewState<T extends string>(key: string, initial: T, allowed?: readonly T[]) {
  const [params, setParams] = useSearchParams()
  const raw = params.get(key)
  const value = (raw !== null && (!allowed || allowed.includes(raw as T)) ? raw : initial) as T
  const setValue = (change: SetStateAction<T>) =>
    setParams(
      (old) => {
        const next = new URLSearchParams(old)
        const updated = typeof change === 'function' ? change(value) : change
        if (updated === initial) next.delete(key)
        else next.set(key, updated)
        return next
      },
      { replace: true },
    )
  return [value, setValue] as const
}

export function useViewSelection(key: string) {
  const [value, setValue] = useViewState<string>(key, '')
  return [value || null, (next: string | null) => setValue(next ?? '')] as const
}
