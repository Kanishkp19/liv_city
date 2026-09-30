import { useQuery } from '@tanstack/react-query'

export default function SystemHealth() {
  const { data } = useQuery({
    queryKey: ['health'],
    queryFn: () => fetch('/api/v1/system/health').then((r) => r.json()),
    refetchInterval: 5000,
  })
  return (
    <div className="rounded border border-border bg-surface p-4 text-sm">
      <h2 className="mb-3 font-semibold">System health</h2>
      <ul className="space-y-1 font-mono text-xs">
        {Object.entries((data?.providers ?? {}) as Record<string, string>).map(([k, v]) => (
          <li key={k}>
            {k}: <span className={v === 'ready' ? 'text-ok' : 'text-warn'}>{v}</span>
          </li>
        ))}
        <li>db: <span className="text-ok">{String(data?.db ?? 'unknown')}</span></li>
      </ul>
    </div>
  )
}
