"use client";

import { useEffect, useState } from "react";
import { z } from "zod";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  getAppSettings,
  saveAppSettings,
  type AppSettings,
} from "@repo/api-client";

// UI Components
import {
  Button,
  Input,
  Label,
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  ConfigDrawer,
  FloatingActionButtons,
  Header,
  Main,
  LoadingSkeleton,
  ProfileDropdown,
  Search,
  SearchableSelect,
  ThemeSwitch,
} from "@repo/ui/components";

// Icons
import { X, Save, Loader2 } from "lucide-react";

// Define the validation schema for the form
const schema = z.object({
  llm: z.object({
    model: z.string().optional().or(z.literal("")),
    base_url: z.string().url("Invalid URL").optional().or(z.literal("")),
    provider: z.string().optional().or(z.literal("")),
    api_key: z.string().optional().or(z.literal("")),
  }),
  current_workflow: z.string().optional().or(z.literal("")),
});

type FormValues = z.infer<typeof schema>;

// The main component for the settings page
export default function AgentSettings() {
  const queryClient = useQueryClient();

  const {
    data: settings,
    isLoading,
    error,
  } = useQuery<AppSettings>({
    queryKey: ["app-settings"],
    queryFn: async () =>
      (await getAppSettings()) ?? { llm: {}, current_workflow: "" },
    staleTime: 5_000,
  });

  const [saveDialogOpen, setSaveDialogOpen] = useState(false);
  const workflows = settings?.workflows || [];

  const {
    register,
    handleSubmit,
    setValue,
    control,
    formState: { errors, isSubmitting, isDirty },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { llm: {}, current_workflow: "" },
  });

  // Effect to populate the form once settings data is loaded
  useEffect(() => {
    if (settings) {
      setValue("llm.model", settings.llm?.model || "");
      setValue("llm.base_url", settings.llm?.base_url || "");
      setValue("llm.provider", settings.llm?.provider || "");
      setValue("llm.api_key", settings.llm?.api_key || "");
      setValue("current_workflow", settings.current_workflow || "");
    }
  }, [settings, setValue]);

  const saveMutation = useMutation({
    mutationFn: (form: FormValues) => saveAppSettings(form as AppSettings),
    onSuccess: async () => {
      toast.success("Settings saved successfully!");
      await queryClient.invalidateQueries({ queryKey: ["app-settings"] });
      setSaveDialogOpen(false);
    },
    onError: (e: any) => toast.error(e.message || "Failed to save settings."),
  });

  if (isLoading) {
    return (
      <Main>
        <h1 className="text-2xl font-bold tracking-tight">Agent Settings</h1>
        <LoadingSkeleton lines={6} />
      </Main>
    );
  }

  if (error) {
    return (
      <Main>
        <h1 className="text-2xl font-bold tracking-tight">Agent Settings</h1>
        <p className="text-muted-foreground">
          Failed to load settings. Please try again later.
        </p>
      </Main>
    );
  }

  return (
    <>
      <Header>
        <Search />
        <div className="ms-auto flex items-center gap-4">
          <ThemeSwitch />
          <ConfigDrawer />
          <ProfileDropdown />
        </div>
      </Header>

      <FloatingActionButtons>
        <Dialog open={saveDialogOpen} onOpenChange={setSaveDialogOpen}>
          <DialogTrigger asChild>
            <Button disabled={!isDirty || saveMutation.isPending}>
              <Save className="mr-2 h-4 w-4" />
              Save Changes
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Confirm Your Changes</DialogTitle>
              <DialogDescription>
                Are you sure you want to save? This will update the
                configuration for all assistants and reload them.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter className="gap-2 sm:justify-end">
              <DialogClose asChild>
                <Button type="button" variant="outline">
                  <X className="mr-2 h-4 w-4" />
                  Cancel
                </Button>
              </DialogClose>
              <Button
                type="button"
                onClick={handleSubmit((data) => saveMutation.mutate(data))}
                disabled={saveMutation.isPending}
              >
                {saveMutation.isPending ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Save className="mr-2 h-4 w-4" />
                )}
                {saveMutation.isPending ? "Saving..." : "Confirm & Save"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </FloatingActionButtons>

      <Main>
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Agent Settings</h1>
          <p className="text-muted-foreground">
            Configure LLM provider and general defaults.
          </p>
        </div>

        <form
          className="space-y-4 pt-3"
          onSubmit={(e) => {
            e.preventDefault();
            // On form submit (e.g., pressing Enter), open the confirmation dialog
            if (isDirty) {
              setSaveDialogOpen(true);
            }
          }}
        >
          <div className="space-y-3 rounded-lg border p-4">
            <h2 className="text-lg font-semibold">LLM Provider Settings</h2>
            <Field label="Model Name" error={errors.llm?.model?.message}>
              <Input {...register("llm.model")} />
            </Field>
            <Field label="API Base URL" error={errors.llm?.base_url?.message}>
              <Input
                {...register("llm.base_url")}
                placeholder="https://api.example.com/v1"
              />
            </Field>
            <Field
              label="Provider"
              hint="For example: 'openai', 'anthropic', etc."
            >
              <Input {...register("llm.provider")} />
            </Field>
            <Field
              label="API Key"
              hint="If using providers like OpenAI, enter the API key here."
            >
              <Input type="password" {...register("llm.api_key")} />
            </Field>
          </div>

          <div className="space-y-3 rounded-lg border p-4">
            <h2 className="text-lg font-semibold">General Settings</h2>
            <Field
              label="Current Workflow"
              hint="The assistant used by default when none is specified."
            >
              <Controller
                name="current_workflow"
                control={control}
                render={({ field }) => (
                  <SearchableSelect
                    options={workflows.map((wf) => ({
                      label: wf.name,
                      value: wf.id,
                    }))}
                    value={field.value}
                    onChange={field.onChange}
                    placeholder="Select a workflow"
                    className="min-w-[160px] sm:min-w-[220px]"
                  />
                )}
              />
            </Field>
          </div>
        </form>
      </Main>
    </>
  );
}

// A reusable Field component for form elements
function Field({
  label,
  hint,
  error,
  children,
}: {
  label: string;
  hint?: string;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1">
      <Label>{label}</Label>
      {children}
      {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  );
}
