import { Card } from '@/shared/components/Card'

type StatCardProps = {
  label: string
  value: string
}

export function StatCard({ label, value }: StatCardProps) {
  return (
    <Card className="stat-card">
      <strong>{value}</strong>
      <span>{label}</span>
    </Card>
  )
}
