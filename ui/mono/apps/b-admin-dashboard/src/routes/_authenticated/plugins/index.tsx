import { createFileRoute } from '@tanstack/react-router'
import Plugins from '@/features/plugins'

export const Route = createFileRoute('/_authenticated/plugins/')({
  component: Plugins,
})
