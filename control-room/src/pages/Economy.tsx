import { LineChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

const demo = Array.from({ length: 30 }, (_, i) => ({ tick: i, supply: 50000 + i * 37 }))

export default function Economy() {
  return (
    <div className="rounded border border-border bg-surface p-4">
      <h2 className="mb-3 text-sm font-semibold">Money supply</h2>
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={demo}>
          <XAxis dataKey="tick" stroke="#9AA7B4" fontSize={11} />
          <YAxis stroke="#9AA7B4" fontSize={11} />
          <Tooltip contentStyle={{ background: '#161B22', border: '1px solid #2A323D' }} />
          <Line type="monotone" dataKey="supply" stroke="#58A6FF" dot={false} strokeWidth={2} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
