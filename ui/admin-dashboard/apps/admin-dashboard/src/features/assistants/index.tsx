import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Loader2, PlusCircle, Save, X } from 'lucide-react'
import { toast } from 'sonner'
import {
  addPluginToAssistant,
  getAssistantsConfig,
  getAvailablePlugins,
  removePluginFromAssistant,
  updateAssistant,
  deleteAssistant,
  addAssistant,
} from '@/dingent/api-client/'
import type { Assistant } from '@/lib/types'
import { safeBool, effectiveStatusForItem } from '@/lib/utils'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/dingent/components/ui/accordion'
import { Button } from '@/dingent/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
  DialogDescription,
  DialogClose,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { ConfigDrawer } from '@/components/config-drawer'
import { ConfirmDialog } from '@/components/confirm-dialog'
import { EmptyState } from '@/components/empty-state'
import { FloatingActionButtons } from '@/components/layout/floating-action-button'
import { Header } from '@/components/layout/header'
import { Main } from '@/components/layout/main'
import { LoadingSkeleton } from '@/components/loading-skeleton'
import { ProfileDropdown } from '@/components/profile-dropdown'
import { Search } from '@/components/search'
import { StatusBadge } from '@/components/status-badge'
import { ThemeSwitch } from '@/components/theme-switch'
import { AssistantEditor } from './components/plugin-editor'

export function Assistants() {
  const qc = useQueryClient()

  const assistantsQ = useQuery({
    queryKey: ['assistants'],
    queryFn: async () => (await getAssistantsConfig()) ?? [],
    staleTime: 5_000,
  })

  const pluginsQ = useQuery({
    queryKey: ['available-plugins'],
    queryFn: async () => (await getAvailablePlugins()) ?? [],
    staleTime: 30_000,
  })

  const [editable, setEditable] = useState<Assistant[]>([])
  const [dirtyAssistantIds, setDirtyAssistantIds] = useState<Set<string>>(
    new Set()
  )

  useEffect(() => {
    if (assistantsQ.data) {
      setEditable(JSON.parse(JSON.stringify(assistantsQ.data)))
    }
  }, [assistantsQ.data])

  const addPluginMutation = useMutation({
    mutationFn: async (p: { assistantId: string; pluginId: string }) =>
      addPluginToAssistant(p.assistantId, p.pluginId),
    onSuccess: async () => {
      toast.success('Plugin added')
      await qc.invalidateQueries({ queryKey: ['assistants'] })
    },
    onError: (e: any) => toast.error(e.message || 'Add plugin failed'),
  })

  const removePluginMutation = useMutation({
    mutationFn: async (p: { assistantId: string; pluginId: string }) =>
      removePluginFromAssistant(p.assistantId, p.pluginId),
    onSuccess: async () => {
      toast.success('Plugin removed')
      await qc.invalidateQueries({ queryKey: ['assistants'] })
    },
    onError: (e: any) => toast.error(e.message || 'Remove plugin failed'),
  })

  const [addDialogOpen, setAddDialogOpen] = useState(false)
  const [saveDialogOpen, setSaveDialogOpen] = useState(false)
  const [newAssistant, setNewAssistant] = useState<{
    name: string
    description: string
  }>({ name: '', description: '' })

  const addAssistantMutation = useMutation({
    mutationFn: async ({
      name,
      description,
    }: {
      name: string
      description: string
    }) => addAssistant(name, description),
    onSuccess: async () => {
      toast.success('Assistant added successfully!')
      await qc.invalidateQueries({ queryKey: ['assistants'] })
      setAddDialogOpen(false) // ✨ Close dialog on success
      setNewAssistant({ name: '', description: '' }) // ✨ Reset form
    },
    onError: (e: any) => toast.error(e.message || 'Add assistant failed'),
  })

  const saveMutation = useMutation({
    mutationFn: async () => {
      const changedAssistants = editable.filter((a) =>
        dirtyAssistantIds.has(a.id)
      )

      if (changedAssistants.length === 0) {
        toast.info('No changes to save.')
        return
      }

      const updatePromises = changedAssistants.map((assistant) =>
        updateAssistant(assistant.id, assistant)
      )

      await Promise.all(updatePromises)
    },
    onSuccess: async () => {
      toast.success('All changes have been saved successfully!')
      await qc.invalidateQueries({ queryKey: ['assistants'] })
      setSaveDialogOpen(false) // Close the dialog
      // The useEffect will then clear the dirty set automatically
    },
    onError: (e: any) =>
      toast.error(e.message || 'Failed to save some changes.'),
  })

  const deleteAssistantMutation = useMutation({
    mutationFn: async (assistantId: string) => deleteAssistant(assistantId),
    onSuccess: async () => {
      toast.success('Assistant deleted')
      await qc.invalidateQueries({ queryKey: ['assistants'] })
    },
    onError: (e: any) => toast.error(e.message || 'Delete assistant failed'),
  })

  return (
    <>
      <Header>
        <Search />
        <div className='ms-auto flex items-center gap-4'>
          <ThemeSwitch />
          <ConfigDrawer />
          <ProfileDropdown />
        </div>
      </Header>
      <FloatingActionButtons>
        {/* --- Add Assistant Dialog --- */}
        <Dialog open={addDialogOpen} onOpenChange={setAddDialogOpen}>
          <DialogTrigger asChild>
            {/* ✨ Added icon and adjusted text */}
            <Button variant='outline'>
              <PlusCircle className='mr-2 h-4 w-4' />
              Add Assistant
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Add New Assistant</DialogTitle>
            </DialogHeader>
            <div className='space-y-4 py-4'>
              <div className='space-y-2'>
                <Label htmlFor='new-name'>Name (Required)</Label>
                <Input
                  id='new-name'
                  value={newAssistant.name}
                  onChange={(e) =>
                    setNewAssistant((prev) => ({
                      ...prev,
                      name: e.target.value,
                    }))
                  }
                  placeholder='Enter assistant name'
                />
              </div>
              <div className='space-y-2'>
                <Label htmlFor='new-desc'>Description</Label>
                <Textarea
                  id='new-desc'
                  value={newAssistant.description}
                  onChange={(e) =>
                    setNewAssistant((prev) => ({
                      ...prev,
                      description: e.target.value,
                    }))
                  }
                  placeholder='Enter assistant description'
                />
              </div>
            </div>
            <DialogFooter>
              <Button
                onClick={() =>
                  addAssistantMutation.mutate({
                    name: newAssistant.name,
                    description: newAssistant.description,
                  })
                }
                disabled={addAssistantMutation.isPending}
              >
                {addAssistantMutation.isPending ? (
                  <Loader2 className='mr-2 h-4 w-4 animate-spin' />
                ) : (
                  // ✨ Added icon here as well for consistency
                  <PlusCircle className='mr-2 h-4 w-4' />
                )}
                {addAssistantMutation.isPending ? 'Adding...' : 'Add'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* --- Save Configuration Dialog --- */}
        <Dialog open={saveDialogOpen} onOpenChange={setSaveDialogOpen}>
          <DialogTrigger asChild>
            <Button disabled={dirtyAssistantIds.size === 0}>
              <Save className='mr-2 h-4 w-4' />
              Save Changes
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Confirm Your Changes</DialogTitle>
              <DialogDescription>
                Are you sure you want to save all changes? This will update the
                configuration for all assistants and reload them.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter className='gap-2 sm:justify-end'>
              <DialogClose asChild>
                <Button type='button' variant='outline'>
                  <X className='mr-2 h-4 w-4' />
                  Cancel
                </Button>
              </DialogClose>
              <Button
                type='button'
                onClick={() => saveMutation.mutate()}
                disabled={saveMutation.isPending}
              >
                {saveMutation.isPending ? (
                  <Loader2 className='mr-2 h-4 w-4 animate-spin' />
                ) : (
                  <Save className='mr-2 h-4 w-4' />
                )}
                {saveMutation.isPending ? 'Saving...' : 'Confirm & Save'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </FloatingActionButtons>
      <Main>
        <div>
          <h1 className='text-2xl font-bold tracking-tight'>
            Assistant Configuration
          </h1>
          <p className='text-muted-foreground'>
            Manage assistants, enable/disable plugins, and edit plugin settings
            and tools.
          </p>
        </div>
        <div>
          {assistantsQ.isLoading && <LoadingSkeleton lines={5} />}
          {assistantsQ.error && (
            <div className='text-red-600'>Failed to load assistants.</div>
          )}
          {!assistantsQ.isLoading &&
            !assistantsQ.error &&
            editable.length === 0 && (
              <EmptyState
                title='No assistants'
                description='There are currently no assistants to configure.'
              />
            )}
          <Accordion
            type='single'
            collapsible
            className='w-full space-y-4 pt-3'
          >
            {editable.map((assistant, i) => {
              const enabled = safeBool(assistant.enabled, false)
              const { level, label } = effectiveStatusForItem(
                assistant.status,
                enabled
              )

              return (
                <AccordionItem
                  value={assistant.id || `item-${i}`}
                  key={assistant.id || i}
                  className='rounded-lg border'
                >
                  <AccordionTrigger className='px-4 py-3 text-lg font-semibold hover:no-underline'>
                    <div className='flex w-full items-center justify-between gap-4 pr-4'>
                      {' '}
                      {/* Added pr-4 for spacing before delete */}
                      <span className='truncate'>
                        {assistant.name || 'Unnamed'}
                      </span>
                      <div className='flex-shrink-0'>
                        <StatusBadge
                          level={level}
                          label={label}
                          title={assistant.status}
                        />
                      </div>
                    </div>
                  </AccordionTrigger>
                  <AccordionContent className='p-4 pt-0'>
                    <div className='mb-4 flex justify-end'>
                      {' '}
                      {/* Delete button inside content for better layout */}
                      <ConfirmDialog
                        title='Confirm Delete Assistant'
                        description={`Are you sure you want to delete assistant '${assistant.name || 'Unnamed'}'?`}
                        confirmText='Confirm Delete'
                        onConfirm={() =>
                          deleteAssistantMutation.mutate(assistant.id)
                        }
                        trigger={
                          <Button
                            variant='destructive'
                            size='sm'
                            disabled={
                              deleteAssistantMutation.isPending &&
                              deleteAssistantMutation.variables === assistant.id
                            }
                          >
                            {deleteAssistantMutation.isPending &&
                              deleteAssistantMutation.variables ===
                                assistant.id && (
                                <Loader2 className='mr-2 h-4 w-4 animate-spin' />
                              )}
                            Delete Assistant
                          </Button>
                        }
                      />
                    </div>
                    <AssistantEditor
                      assistant={assistant}
                      onChange={(updatedAssistant) => {
                        const nextState = [...editable]
                        nextState[i] = updatedAssistant
                        setEditable(nextState)
                        setDirtyAssistantIds((prev) =>
                          new Set(prev).add(updatedAssistant.id)
                        )
                      }}
                      availablePlugins={pluginsQ.data || []}
                      onAddPlugin={(pluginId) =>
                        addPluginMutation.mutate({
                          assistantId: assistant.id,
                          pluginId: pluginId,
                        })
                      }
                      isAddingPlugin={addPluginMutation.isPending}
                      addingPluginDetails={addPluginMutation.variables!}
                      onRemovePlugin={(pluginId) =>
                        removePluginMutation.mutate({
                          assistantId: assistant.id,
                          pluginId,
                        })
                      }
                      isRemovingPlugin={removePluginMutation.isPending}
                      removingPluginDetails={
                        removePluginMutation.variables || null
                      }
                    />
                  </AccordionContent>
                </AccordionItem>
              )
            })}
          </Accordion>
        </div>
      </Main>
    </>
  )
}
