import { useQuery } from '@tanstack/react-query'

/** Live City placeholder: PixiJS canvas lands with the WS stream (T6.4). */
export default function LiveCity() {
  const { data, isLoading } = useQuery({
    queryKey: ['worlds'],
    queryFn: () => fetch('/api/v1/worlds').then((r) => r.json()),
    refetchInterval: 5000,
  })
  if (isLoading) return <p className="text-dim">loading worlds…</p>
  const items = (data?.items ?? []) as { id: string; tick: number; status: string }[]
  if (items.length === 0) {
    return (
      <div className="rounded border border-border bg-surface p-8 text-center text-dim">
        No world yet. Create one: <code className="font-mono text-info">POST /api/v1/worlds</code>
      </div>
    )
  }
  return (
    <div className="grid gap-3 md:grid-cols-3">
      {items.map((w) => (
        <div key={w.id} className="rounded border border-border bg-surface p-4">
          <p className="font-mono text-xs text-dim">{w.id}</p>
          <p className="text-lg">tick {w.tick}</p>
          <span className="rounded bg-info/20 px-2 py-0.5 text-xs text-info">{w.status}</span>
        </div>
      ))}
    </div>
  )
}
