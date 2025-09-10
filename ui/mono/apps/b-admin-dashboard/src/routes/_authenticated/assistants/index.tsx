import { createFileRoute } from '@tanstack/react-router'
import {Assistants} from '@/features/assistants'

export const Route = createFileRoute('/_authenticated/assistants/')({
  component: Assistants,
})
