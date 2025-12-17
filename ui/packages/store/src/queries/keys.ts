export const workflowKeys = {
  all: ['workflows'] as const,
  lists: (workspaceId: string | undefined) => [...workflowKeys.all, 'list', workspaceId] as const,
  details: () => [...workflowKeys.all, 'detail'] as const,
  detail: (id: string) => [...workflowKeys.details(), id] as const,
  assistants: (workspaceId: string | undefined) => [...workflowKeys.all, 'assistants', workspaceId] as const,
};
