import { useQuery } from '@tanstack/react-query'
import { Loader2 } from 'lucide-react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Pie,
  PieChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { adminAnalytics } from '@/services/adminService'

const PIE_COLORS = ['#4f46e5', '#0ea5e9', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6']

export default function AdminAnalyticsPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['admin-analytics'],
    queryFn: () => adminAnalytics(),
  })

  if (isLoading) {
    return (
      <div className="flex justify-center py-16">
        <Loader2 className="h-6 w-6 animate-spin text-brand-600" />
      </div>
    )
  }

  if (isError || !data) {
    return (
      <p className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-300">
        Could not load analytics.
      </p>
    )
  }

  const usersByRole = Object.entries(data.users_by_role).map(([name, count]) => ({
    name,
    count,
  }))
  const lawyersByStatus = Object.entries(data.lawyers_by_status).map(([name, count]) => ({
    name,
    count,
  }))
  const complaintsByStatus = Object.entries(data.complaints_by_status).map(([name, count]) => ({
    name,
    count,
  }))
  const revenueBySource = Object.entries(data.revenue_by_source).map(([source, amount]) => ({
    name: `${source} · ₹${Number(amount).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`,
    count: amount,
  }))

  return (
    <div>
      <h1 className="text-2xl font-bold">Analytics</h1>
      <p className="mt-1 text-sm text-surface-600 dark:text-surface-300">
        Platform usage and revenue breakdown.
      </p>

      <div className="mt-6 grid gap-4 md:grid-cols-2">
        <ChartCard title="Users by role">
          <PieChartWrap data={usersByRole} />
        </ChartCard>
        <ChartCard title="Lawyers by verification status">
          <PieChartWrap data={lawyersByStatus} />
        </ChartCard>
        <ChartCard title="Complaints by status">
          <BarChartWrap data={complaintsByStatus} color="#f59e0b" />
        </ChartCard>
        <ChartCard title="Revenue by source (INR)">
          <BarChartWrap data={revenueBySource} color="#10b981" />
        </ChartCard>
        <ChartCard title="Appointments by month">
          <BarChartWrap data={data.appointments_by_month.map((m) => ({ name: m.month, count: m.count }))} color="#4f46e5" />
        </ChartCard>
        <ChartCard title="Top practice areas">
          <BarChartWrap data={data.top_categories.map((c) => ({ name: c.category, count: c.count }))} color="#8b5cf6" />
        </ChartCard>
        <ChartCard title="Top lawyers by rating">
          <TopLawyers lawyers={data.top_lawyers} />
        </ChartCard>
      </div>
    </div>
  )
}

function ChartCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-surface-200 bg-white p-5 dark:border-surface-800 dark:bg-surface-800">
      <h2 className="text-lg font-semibold">{title}</h2>
      <div className="mt-3 h-60">{children}</div>
    </div>
  )
}

function PieChartWrap({ data }: { data: Array<{ name: string; count: number }> }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <PieChart>
        <Pie data={data} dataKey="count" nameKey="name" outerRadius="70%">
          {data.map((_, i) => (
            <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
          ))}
        </Pie>
        <Tooltip />
      </PieChart>
    </ResponsiveContainer>
  )
}

function shortenLabel(value: string) {
  return value.length > 14 ? `${value.slice(0, 13)}…` : value
}

function BarChartWrap({
  data,
  color,
}: {
  data: Array<{ name: string; count: number }>
  color: string
}) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#d4d4d8" />
        <XAxis dataKey="name" fontSize={11} tickFormatter={shortenLabel} />
        <YAxis fontSize={11} />
        <Tooltip />
        <Bar dataKey="count" fill={color} radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}

function TopLawyers({
  lawyers,
}: {
  lawyers: Array<{
    name: string
    avg_rating: number
    rating_count: number
    categories: string[]
  }>
}) {
  if (lawyers.length === 0) {
    return <p className="text-sm text-surface-500 dark:text-surface-400">No ratings yet.</p>
  }
  return (
    <ul className="space-y-3">
      {lawyers.map((l) => (
        <li key={l.name} className="flex items-center justify-between gap-3 rounded-lg bg-surface-50 px-3 py-2 dark:bg-surface-900">
          <div className="min-w-0">
            <p className="truncate text-sm font-medium">{l.name}</p>
            <p className="truncate text-xs text-surface-500 dark:text-surface-400">
              {l.categories.map((c) => c.replace('_', ' ')).join(', ')}
            </p>
          </div>
          <span className="shrink-0 whitespace-nowrap text-sm font-medium">
            {l.avg_rating.toFixed(1)} ★ ({l.rating_count})
          </span>
        </li>
      ))}
    </ul>
  )
}
