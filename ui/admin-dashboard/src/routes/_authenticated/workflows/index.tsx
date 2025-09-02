import { createFileRoute } from '@tanstack/react-router'
import { Workflows } from '@/features/workflows'

export const Route = createFileRoute('/_authenticated/workflows/')({
  component: Workflows,
})
