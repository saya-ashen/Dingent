import { createFileRoute } from '@tanstack/react-router'
import { Apps } from '@/features/market'

export const Route = createFileRoute('/_authenticated/market/')({
  component: Apps,
})
