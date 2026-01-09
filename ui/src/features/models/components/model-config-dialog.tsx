"use client";
import { useState, useEffect } from "react";
import { Loader2, PlusCircle, Save, AlertCircle, CheckCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Alert, AlertDescription } from "@/components/ui/alert";
import type {
  LLMModelConfig,
  LLMModelConfigCreate,
  LLMModelConfigUpdate,
  TestConnectionRequest,
  TestConnectionResponse,
} from "@/types/entity";

interface ModelConfigDialogProps {
  model?: LLMModelConfig;
  isPending: boolean;
  onSave: (data: LLMModelConfigCreate | LLMModelConfigUpdate) => void;
  onTestConnection?: (data: TestConnectionRequest) => Promise<TestConnectionResponse>;
  trigger?: React.ReactNode;
}

const PROVIDERS = [
  { value: "openai", label: "OpenAI" },
  { value: "azure", label: "Azure OpenAI" },
  { value: "anthropic", label: "Anthropic" },
  { value: "ollama", label: "Ollama" },
  { value: "gemini", label: "Google Gemini" },
];

export function ModelConfigDialog({
  model,
  isPending,
  onSave,
  onTestConnection,
  trigger,
}: ModelConfigDialogProps) {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState<LLMModelConfigCreate>({
    name: "",
    provider: "openai",
    model: "",
    api_base: "",
    api_version: "",
    api_key: "",
    is_active: true,
  });
  const [testResult, setTestResult] = useState<{
    status: "idle" | "testing" | "success" | "error";
    message: string;
    latency?: number;
  }>({ status: "idle", message: "" });

  useEffect(() => {
    if (model) {
      setData({
        name: model.name,
        provider: model.provider,
        model: model.model,
        api_base: model.api_base || "",
        api_version: model.api_version || "",
        api_key: "",
        is_active: model.is_active,
      });
    } else {
      setData({
        name: "",
        provider: "openai",
        model: "",
        api_base: "",
        api_version: "",
        api_key: "",
        is_active: true,
      });
    }
    setTestResult({ status: "idle", message: "" });
  }, [model, open]);

  const handleSubmit = () => {
    onSave(data);
    setOpen(false);
  };

  const handleTest = async () => {
    if (!onTestConnection) return;
    
    setTestResult({ status: "testing", message: "Testing connection..." });
    try {
      const result = await onTestConnection(data);
      setTestResult({
        status: result.success ? "success" : "error",
        message: result.message,
        latency: result.latency_ms,
      });
    } catch (error: any) {
      setTestResult({
        status: "error",
        message: error.message || "Connection test failed",
      });
    }
  };

  const isValid = data.name && data.provider && data.model;

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {trigger || (
          <Button variant="outline">
            <PlusCircle className="mr-2 h-4 w-4" /> Add Model
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {model ? "Edit Model Configuration" : "Add New Model Configuration"}
          </DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Configuration Name *</Label>
              <Input
                value={data.name}
                onChange={(e) => setData({ ...data, name: e.target.value })}
                placeholder="e.g., My GPT-4"
              />
            </div>
            <div className="space-y-2">
              <Label>Provider *</Label>
              <Select
                value={data.provider}
                onValueChange={(value) => setData({ ...data, provider: value })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {PROVIDERS.map((p) => (
                    <SelectItem key={p.value} value={p.value}>
                      {p.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-2">
            <Label>Model Name *</Label>
            <Input
              value={data.model}
              onChange={(e) => setData({ ...data, model: e.target.value })}
              placeholder="e.g., gpt-4, claude-3-opus, llama3"
            />
          </div>

          <div className="space-y-2">
            <Label>API Key {model ? "(leave empty to keep existing)" : ""}</Label>
            <Input
              type="password"
              value={data.api_key || ""}
              onChange={(e) => setData({ ...data, api_key: e.target.value })}
              placeholder={model ? "••••••••" : "Enter API key"}
            />
          </div>

          <div className="space-y-2">
            <Label>API Base URL (Optional)</Label>
            <Input
              value={data.api_base || ""}
              onChange={(e) => setData({ ...data, api_base: e.target.value })}
              placeholder="e.g., http://localhost:11434 for Ollama"
            />
          </div>

          {data.provider === "azure" && (
            <div className="space-y-2">
              <Label>API Version (Azure)</Label>
              <Input
                value={data.api_version || ""}
                onChange={(e) =>
                  setData({ ...data, api_version: e.target.value })
                }
                placeholder="e.g., 2024-02-15-preview"
              />
            </div>
          )}

          {testResult.status !== "idle" && (
            <Alert
              variant={
                testResult.status === "success"
                  ? "default"
                  : testResult.status === "error"
                    ? "destructive"
                    : "default"
              }
            >
              {testResult.status === "success" && (
                <CheckCircle className="h-4 w-4" />
              )}
              {testResult.status === "error" && (
                <AlertCircle className="h-4 w-4" />
              )}
              {testResult.status === "testing" && (
                <Loader2 className="h-4 w-4 animate-spin" />
              )}
              <AlertDescription>
                {testResult.message}
                {testResult.latency && ` (${testResult.latency}ms)`}
              </AlertDescription>
            </Alert>
          )}
        </div>
        <DialogFooter className="gap-2">
          {onTestConnection && (
            <Button
              onClick={handleTest}
              variant="outline"
              disabled={!isValid || testResult.status === "testing"}
            >
              {testResult.status === "testing" ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <AlertCircle className="mr-2 h-4 w-4" />
              )}
              Test Connection
            </Button>
          )}
          <Button onClick={handleSubmit} disabled={isPending || !isValid}>
            {isPending ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : model ? (
              <Save className="mr-2 h-4 w-4" />
            ) : (
              <PlusCircle className="mr-2 h-4 w-4" />
            )}
            {isPending ? "Saving..." : model ? "Update" : "Add"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
