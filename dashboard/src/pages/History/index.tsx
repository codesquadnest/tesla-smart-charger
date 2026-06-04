import { useState } from 'react'
import { useHistory } from '@/hooks/useHistory'
import { useVehicles } from '@/hooks/useVehicles'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Spinner } from '@/components/ui/Spinner'
import { Alert } from '@/components/ui/Alert'
import { Input, Select } from '@/components/ui/Input'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { formatDuration, formatDateTime } from '@/lib/utils'
import type { OverloadEvent } from '@/lib/types'

export default function HistoryPage() {
  const [vehicleFilter, setVehicleFilter] = useState('')
  const [fromDate, setFromDate] = useState('')
  const [toDate, setToDate] = useState('')
  const [limit, setLimit] = useState(50)

  const { data: vehicles = [] } = useVehicles()
  const { data, isLoading, error, refetch } = useHistory({
    limit,
    vehicle_id: vehicleFilter,
    from_date: fromDate,
    to_date: toDate,
  })

  const events: OverloadEvent[] = data?.data ?? []

  // Chart data: duration in seconds per event (most recent first → reverse for chart)
  const chartData = [...events]
    .reverse()
    .map((e, i) => ({
      index: i + 1,
      duration: typeof e.duration === 'number' ? e.duration : parseFloat(String(e.duration)) || 0,
      start: e.start,
    }))

  const vehicleOptions = [
    { value: '', label: 'All vehicles' },
    ...vehicles.map((v) => ({ value: v.id, label: v.name || v.id })),
  ]

  return (
    <div className="p-8 space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Overload History</h1>
        <p className="text-slate-500 text-sm mt-1">
          Log of all past overload events and their durations.
        </p>
      </div>

      {/* Filters */}
      <Card>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Select
            label="Vehicle"
            value={vehicleFilter}
            onChange={(e) => setVehicleFilter(e.target.value)}
            options={vehicleOptions}
          />
          <Input
            label="From date"
            type="date"
            value={fromDate}
            onChange={(e) => setFromDate(e.target.value ? `${e.target.value} 00:00:00` : '')}
          />
          <Input
            label="To date"
            type="date"
            value={toDate}
            onChange={(e) => setToDate(e.target.value ? `${e.target.value} 23:59:59` : '')}
          />
          <Input
            label="Limit"
            type="number"
            min={1}
            max={500}
            value={limit}
            onChange={(e) => setLimit(Number(e.target.value))}
          />
        </div>
        <div className="flex gap-3 mt-4">
          <Button onClick={() => refetch()}>Apply filters</Button>
          <Button
            variant="secondary"
            onClick={() => {
              setVehicleFilter('')
              setFromDate('')
              setToDate('')
              setLimit(50)
            }}
          >
            Reset
          </Button>
        </div>
      </Card>

      {error && <Alert type="error">{(error as Error).message}</Alert>}

      {isLoading ? (
        <div className="flex justify-center py-12">
          <Spinner size={32} />
        </div>
      ) : (
        <>
          {/* Chart */}
          {chartData.length > 0 && (
            <Card>
              <p className="text-sm font-semibold text-slate-900 mb-4">
                Event Duration (seconds)
              </p>
              <ResponsiveContainer width="100%" height={220}>
                <AreaChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                  <defs>
                    <linearGradient id="dur" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#6366f1" stopOpacity={0.2} />
                      <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="index" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip
                    formatter={(val) => [formatDuration(Number(val ?? 0)), 'Duration']}
                    labelFormatter={(i) => `Event #${i}`}
                  />
                  <Area
                    type="monotone"
                    dataKey="duration"
                    stroke="#6366f1"
                    fill="url(#dur)"
                    strokeWidth={2}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </Card>
          )}

          {/* Table */}
          <Card>
            <div className="flex items-center justify-between mb-4">
              <p className="text-sm font-semibold text-slate-900">
                {data?.count ?? 0} events
              </p>
            </div>

            {events.length === 0 ? (
              <p className="text-center text-slate-500 py-8">No events found.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-100 text-left">
                      <th className="pb-3 font-medium text-slate-500 pr-6">#</th>
                      <th className="pb-3 font-medium text-slate-500 pr-6">Start</th>
                      <th className="pb-3 font-medium text-slate-500 pr-6">End</th>
                      <th className="pb-3 font-medium text-slate-500 pr-6">Duration</th>
                      <th className="pb-3 font-medium text-slate-500">Vehicle</th>
                    </tr>
                  </thead>
                  <tbody>
                    {events.map((e) => (
                      <EventRow key={e.id} event={e} vehicles={vehicles} />
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </>
      )}
    </div>
  )
}

function EventRow({
  event: e,
  vehicles,
}: {
  event: OverloadEvent
  vehicles: { id: string; name: string }[]
}) {
  const duration =
    typeof e.duration === 'number' ? e.duration : parseFloat(String(e.duration)) || 0
  const vehicleName =
    vehicles.find((v) => v.id === e.vehicle_id)?.name ?? e.vehicle_id ?? '—'

  return (
    <tr className="border-b border-slate-50 hover:bg-slate-50/50">
      <td className="py-3 pr-6 text-slate-400 font-mono text-xs">{e.id}</td>
      <td className="py-3 pr-6 text-slate-900">{formatDateTime(e.start)}</td>
      <td className="py-3 pr-6 text-slate-900">{formatDateTime(e.end)}</td>
      <td className="py-3 pr-6">
        <span
          className={`font-medium ${
            duration > 300 ? 'text-red-600' : duration > 60 ? 'text-yellow-600' : 'text-green-600'
          }`}
        >
          {formatDuration(duration)}
        </span>
      </td>
      <td className="py-3 text-slate-500">{vehicleName}</td>
    </tr>
  )
}
