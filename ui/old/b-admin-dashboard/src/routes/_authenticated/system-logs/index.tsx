import { createFileRoute } from '@tanstack/react-router'
import { Logs } from '@/features/system-logs'

export const Route = createFileRoute('/_authenticated/system-logs/')({
  component: Logs,
})
