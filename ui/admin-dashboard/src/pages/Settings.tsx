import { useEffect } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { z } from "zod";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import type { AppSettings } from "@/lib/types";
import { getAppSettings, saveAppSettings } from "@/lib/api";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/layout/Page";
import { LoadingSkeleton } from "@/components/LoadingSkeleton";
import { toast } from "sonner";

const schema = z.object({
    llm: z.object({
        model: z.string().min(1, "Model is required").optional().or(z.literal("")),
        base_url: z.string().url("Invalid URL").optional().or(z.literal("")),
        provider: z.string().optional().or(z.literal("")),
        api_key: z.string().optional().or(z.literal(""))
    }),
    default_assistant: z.string().optional().or(z.literal(""))
});

type FormValues = z.infer<typeof schema>;

export default function SettingsPage() {
    const qc = useQueryClient();

    const settingsQ = useQuery({
        queryKey: ["app-settings"],
        queryFn: async () => (await getAppSettings()) ?? ({ llm: {}, default_assistant: "" } as AppSettings),
        staleTime: 5_000
    });

    const { register, handleSubmit, setValue, formState: { errors, isSubmitting, isDirty } } = useForm<FormValues>({
        resolver: zodResolver(schema),
        defaultValues: { llm: {}, default_assistant: "" }
    });

    useEffect(() => {
        if (settingsQ.data) {
            setValue("llm.model", settingsQ.data.llm?.model || "");
            setValue("llm.base_url", settingsQ.data.llm?.base_url || "");
            setValue("llm.provider", settingsQ.data.llm?.provider || "");
            setValue("llm.api_key", settingsQ.data.llm?.api_key || "");
            setValue("default_assistant", settingsQ.data.default_assistant || "");
        }
    }, [settingsQ.data, setValue]);

    const saveMut = useMutation({
        mutationFn: async (form: FormValues) => saveAppSettings(form as AppSettings),
        onSuccess: async () => {
            toast.success("Settings saved");
            await qc.invalidateQueries({ queryKey: ["app-settings"] });
        },
        onError: (e: any) => toast.error(e.message || "Save failed")
    });

    if (settingsQ.isLoading) {
        return (
            <div className="space-y-4">
                <PageHeader title="App Settings" />
                <LoadingSkeleton lines={6} />
            </div>
        );
    }

    if (settingsQ.error) {
        return (
            <div className="space-y-4">
                <PageHeader title="App Settings" />
                <div className="text-red-600">Failed to load settings</div>
            </div>
        );
    }

    return (
        <div className="space-y-4">
            <PageHeader title="App Settings" description="Configure LLM provider and general defaults." />
            <form
                className="space-y-4"
                onSubmit={handleSubmit((data) => saveMut.mutate(data))}
            >
                <div className="rounded-lg border p-4 space-y-3">
                    <h2 className="text-lg font-semibold">LLM Provider Settings</h2>
                    <Field label="Model Name" error={errors.llm?.model?.message}>
                        <Input {...register("llm.model")} />
                    </Field>
                    <Field label="API Base URL" error={errors.llm?.base_url?.message}>
                        <Input {...register("llm.base_url")} placeholder="https://api.example.com/v1" />
                    </Field>
                    <Field label="Provider" hint="For example: 'openai', 'anthropic', etc.">
                        <Input {...register("llm.provider")} />
                    </Field>
                    <Field label="API Key" hint="If using providers like OpenAI, enter the API key here.">
                        <Input type="password" {...register("llm.api_key")} />
                    </Field>
                </div>

                <div className="rounded-lg border p-4 space-y-3">
                    <h2 className="text-lg font-semibold">General Settings</h2>
                    <Field label="Default Assistant Name" hint="The assistant name used by default when the user does not specify one.">
                        <Input {...register("default_assistant")} />
                    </Field>
                </div>

                <Button type="submit" disabled={isSubmitting || saveMut.isPending || !isDirty}>
                    {saveMut.isPending ? "Saving..." : "Save"}
                </Button>
            </form>
        </div>
    );
}

function Field({ label, hint, error, children }: { label: string; hint?: string; error?: string; children: React.ReactNode }) {
    return (
        <div className="space-y-1">
            <Label>{label}</Label>
            {children}
            {hint && <div className="text-xs text-muted-foreground">{hint}</div>}
            {error && <div className="text-xs text-red-600">{error}</div>}
        </div>
    );
}
