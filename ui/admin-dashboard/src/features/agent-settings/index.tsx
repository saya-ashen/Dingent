import { useEffect } from 'react'
import { z } from 'zod'
import { useForm, Controller } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { getAppSettings, saveAppSettings } from '@/lib/api'
import type { AppSettings } from '@/lib/types'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { ConfigDrawer } from '@/components/config-drawer'
import { FloatingActionButtons } from '@/components/layout/floating-action-button'
import { Header } from '@/components/layout/header'
import { Main } from '@/components/layout/main'
import { LoadingSkeleton } from '@/components/loading-skeleton'
import { ProfileDropdown } from '@/components/profile-dropdown'
import { Search } from '@/components/search'
import { SearchableSelect } from '@/components/searchable-select'
import { ThemeSwitch } from '@/components/theme-switch'

const schema = z.object({
  llm: z.object({
    model: z.string().min(1, 'Model is required').optional().or(z.literal('')),
    base_url: z.string().url('Invalid URL').optional().or(z.literal('')),
    provider: z.string().optional().or(z.literal('')),
    api_key: z.string().optional().or(z.literal('')),
  }),
  current_workflow: z.string().optional().or(z.literal('')),
})

type FormValues = z.infer<typeof schema>

export function AgentSettings() {
  const qc = useQueryClient()

  const settingsQ = useQuery({
    queryKey: ['app-settings'],
    queryFn: async () =>
      (await getAppSettings()) ??
      ({ llm: {}, default_assistant: '' } as AppSettings),
    staleTime: 5_000,
  })

  const workflows = settingsQ.data?.workflows || []
  const {
    register,
    handleSubmit,
    setValue,
    control,
    formState: { errors, isSubmitting, isDirty },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { llm: {}, current_workflow: '' },
  })

  useEffect(() => {
    if (settingsQ.data) {
      setValue('llm.model', settingsQ.data.llm?.model || '')
      setValue('llm.base_url', settingsQ.data.llm?.base_url || '')
      setValue('llm.provider', settingsQ.data.llm?.provider || '')
      setValue('llm.api_key', settingsQ.data.llm?.api_key || '')
      setValue('current_workflow', settingsQ.data.current_workflow || '')
    }
  }, [settingsQ.data, setValue])

  const saveMut = useMutation({
    mutationFn: async (form: FormValues) =>
      saveAppSettings(form as AppSettings),
    onSuccess: async () => {
      toast.success('Settings saved')
      await qc.invalidateQueries({ queryKey: ['app-settings'] })
    },
    onError: (e: any) => toast.error(e.message || 'Save failed'),
  })

  if (settingsQ.isLoading) {
    return (
      <div>
        <h1 className='text-2xl font-bold tracking-tight'>Agent Settings</h1>
        <LoadingSkeleton lines={6} />
      </div>
    )
  }

  if (settingsQ.error) {
    return (
      <div>
        <h1 className='text-2xl font-bold tracking-tight'>Agent Settings</h1>
        <p className='text-muted-foreground'>Failed to load settings</p>
      </div>
    )
  }

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
        <Button
          type='submit'
          disabled={isSubmitting || saveMut.isPending || !isDirty}
        >
          {saveMut.isPending ? 'Saving...' : 'Save Changes'}
        </Button>
      </FloatingActionButtons>
      <Main>
        <div>
          <h1 className='text-2xl font-bold tracking-tight'>Agent Settings</h1>
          <p className='text-muted-foreground'>
            Configure LLM provider and general defaults.
          </p>
        </div>
        <form
          className='space-y-4 pt-3'
          onSubmit={handleSubmit((data) => saveMut.mutate(data))}
        >
          <div className='space-y-3 rounded-lg border p-4'>
            <h2 className='text-lg font-semibold'>LLM Provider Settings</h2>
            <Field label='Model Name' error={errors.llm?.model?.message}>
              <Input {...register('llm.model')} />
            </Field>
            <Field label='API Base URL' error={errors.llm?.base_url?.message}>
              <Input
                {...register('llm.base_url')}
                placeholder='https://api.example.com/v1'
              />
            </Field>
            <Field
              label='Provider'
              hint="For example: 'openai', 'anthropic', etc."
            >
              <Input {...register('llm.provider')} />
            </Field>
            <Field
              label='API Key'
              hint='If using providers like OpenAI, enter the API key here.'
            >
              <Input type='password' {...register('llm.api_key')} />
            </Field>
          </div>

          <div className='space-y-3 rounded-lg border p-4'>
            <h2 className='text-lg font-semibold'>General Settings</h2>
            <Field
              label='Current Workflow'
              hint='The assistant name used by default when the user does not specify one.'
            >
              <Controller
                name='current_workflow'
                control={control}
                render={({ field }) => (
                  <SearchableSelect
                    options={workflows.map((wf) => ({
                      label: wf.name,
                      value: wf.id,
                    }))}
                    value={field.value}
                    onChange={field.onChange} // Use onChange from the controller
                    placeholder='Select a workflow'
                    className='min-w-[160px] sm:min-w-[220px]'
                  />
                )}
              />
            </Field>
          </div>
        </form>
      </Main>
    </>
  )
}

function Field({
  label,
  hint,
  error,
  children,
}: {
  label: string
  hint?: string
  error?: string
  children: React.ReactNode
}) {
  return (
    <div className='space-y-1'>
      <Label>{label}</Label>
      {children}
      {hint && <div className='text-muted-foreground text-xs'>{hint}</div>}
      {error && <div className='text-xs text-red-600'>{error}</div>}
    </div>
  )
}
