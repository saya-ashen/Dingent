import { createFileRoute } from '@tanstack/react-router'
import { AgentSettings } from '@/features/agent-settings'

export const Route = createFileRoute('/_authenticated/agent-settings/')({
  component: AgentSettings,
})
