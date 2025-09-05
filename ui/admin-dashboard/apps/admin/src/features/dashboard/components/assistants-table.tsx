import type { OverviewAssistantItem } from '@/lib/types'
import { cn } from '@/lib/utils'
import { Skeleton } from '@/components/ui/skeleton'

export function AssistantsTable({
  items,
  loading,
}: {
  items: OverviewAssistantItem[]
  loading?: boolean
}) {
  if (loading) {
    return (
      <div className='space-y-2'>
        <Skeleton className='h-6 w-full' />
        <Skeleton className='h-6 w-full' />
        <Skeleton className='h-6 w-full' />
      </div>
    )
  }
  if (!items?.length) {
    return <div className='text-muted-foreground text-sm'>No assistants.</div>
  }
  return (
    <div className='overflow-x-auto'>
      <table className='w-full text-sm'>
        <thead className='text-muted-foreground text-left'>
          <tr>
            <th className='py-1 pr-4 font-medium'>Name</th>
            <th className='py-1 pr-4 font-medium'>Status</th>
            <th className='py-1 pr-4 font-medium'>Plugins</th>
            <th className='py-1 pr-4 font-medium'>Enabled</th>
          </tr>
        </thead>
        <tbody>
          {items.map((a) => (
            <tr key={a.id} className='border-t last:border-b'>
              <td className='py-1 pr-4'>{a.name}</td>
              <td className='py-1 pr-4'>
                <span
                  className={cn(
                    'inline-flex items-center rounded px-1.5 py-0.5 text-xs font-medium',
                    a.status === 'active'
                      ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                      : 'bg-muted text-muted-foreground'
                  )}
                >
                  {a.status}
                </span>
              </td>
              <td className='py-1 pr-4'>{a.plugin_count}</td>
              <td className='py-1 pr-4'>{a.enabled_plugin_count}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
