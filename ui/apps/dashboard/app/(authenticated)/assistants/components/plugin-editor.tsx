"use client";
import { useMemo, useState } from "react";
import { Loader2 } from "lucide-react";
import type {
  Assistant,
  AssistantPlugin,
  PluginManifest,
} from "@repo/api-client";
import { safeBool, effectiveStatusForItem, toStr } from "@repo/lib/utils";
import {
  Button,
  ConfirmDialog,
  Input,
  Label,
  StatusBadge,
  Textarea,
  Separator,
  Switch,
  SearchableSelect,
} from "@repo/ui/components";

function PluginEditor({
  plugin,
  onChange,
  onRemove,
  isRemoving,
}: {
  plugin: AssistantPlugin;
  onChange: (p: AssistantPlugin) => void;
  onRemove: () => void;
  isRemoving?: boolean;
}) {
  const enabled = safeBool(plugin.enabled, false);
  const { level, label } = effectiveStatusForItem(plugin.status, enabled);

  return (
    <div className="rounded-md border p-4">
      {" "}
      {/* Increased padding for better readability */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="font-mono">Plugin: {toStr(plugin.display_name)}</div>

          <StatusBadge level={level} label={label} title={plugin.status} />
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground text-sm">Enable</span>

            <Switch
              checked={enabled}
              onCheckedChange={(v) => onChange({ ...plugin, enabled: v })}
            />
          </div>

          <ConfirmDialog
            title="Confirm Remove Plugin"
            description={`Are you sure you want to remove plugin '${plugin.display_name}'?`}
            confirmText="Confirm Remove"
            onConfirm={onRemove}
            trigger={
              <Button
                variant="destructive"
                size="icon"
                disabled={isRemoving} // Disable the button while loading
              >
                {isRemoving ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  "🗑️"
                )}
              </Button>
            }
          />
        </div>
      </div>
      {plugin.config && plugin.config.length > 0 && (
        <div className="mt-4 space-y-3">
          <div className="text-sm font-medium">User Configuration</div>

          {plugin.config.map((item, idx) => {
            const id = `cfg_${plugin.plugin_id}_${idx}`;
            const label = `${item.name}${item.required ? " (Required)" : ""}`;
            const desc = item.description || `Set ${item.name}`;
            const rawValue = item.value ?? item.default ?? "";

            const updateValue = (nextValue: string | number | boolean | null) => {
              const next = structuredClone(plugin);
              const config = next.config;
              if (!config || config.length <= idx) return;

              config[idx]!.value = nextValue;
              onChange(next);
            };

            // integer
            if (item.type === "integer") {
              const display = rawValue === null ? "" : String(rawValue);

              return (
                <div
                  key={id}
                  className="grid grid-cols-1 gap-2 md:grid-cols-[240px_1fr]"
                >
                  <Label htmlFor={id}>{label}</Label>

                  <Input
                    id={id}
                    type="number"
                    value={display}
                    onChange={(e) => {
                      const v = e.target.value;
                      if (v === "") {
                        // 允许为空，交给后端判断 required
                        updateValue(null);
                      } else {
                        const n = Number(v);
                        updateValue(Number.isFinite(n) ? n : null);
                      }
                    }}
                    placeholder={desc}
                  />
                </div>
              );
            }

            // float
            if (item.type === "float") {
              const display = rawValue === null ? "" : String(rawValue);

              return (
                <div
                  key={id}
                  className="grid grid-cols-1 gap-2 md:grid-cols-[240px_1fr]"
                >
                  <Label htmlFor={id}>{label}</Label>

                  <Input
                    id={id}
                    type="number"
                    step="any"
                    value={display}
                    onChange={(e) => {
                      const v = e.target.value;
                      if (v === "") {
                        updateValue(null);
                      } else {
                        const n = Number(v);
                        updateValue(Number.isFinite(n) ? n : null);
                      }
                    }}
                    placeholder={desc}
                  />
                </div>
              );
            }

            // bool
            if (item.type === "bool") {
              const checked =
                typeof rawValue === "boolean"
                  ? rawValue
                  : Boolean(rawValue ?? false);

              return (
                <div
                  key={id}
                  className="grid grid-cols-1 gap-2 md:grid-cols-[240px_1fr]"
                >
                  <Label htmlFor={id}>{label}</Label>

                  <div className="flex items-center gap-2">
                    <input
                      id={id}
                      type="checkbox"
                      checked={checked}
                      onChange={(e) => updateValue(e.target.checked)}
                    />
                    <span className="text-sm text-muted-foreground">{desc}</span>
                  </div>
                </div>
              );
            }

            // string 默认分支
            const display = rawValue === null || rawValue === undefined
              ? ""
              : String(rawValue);

            return (
              <div
                key={id}
                className="grid grid-cols-1 gap-2 md:grid-cols-[240px_1fr]"
              >
                <Label htmlFor={id}>{label}</Label>

                <Input
                  id={id}
                  type={item.secret ? "password" : "text"}
                  value={display}
                  onChange={(e) => {
                    updateValue(e.target.value);
                  }}
                  placeholder={desc}
                />
              </div>
            );
          })}
        </div>
      )}
      {!!plugin.tools?.length && (
        <div className="mt-4">
          <div className="text-sm font-medium">Tools</div>

          <div className="mt-2 space-y-2">
            {" "}
            {/* Increased space-y for tools */}
            {plugin.tools!.map((tool, k) => (
              <div
                key={k}
                className="flex items-center justify-between rounded border p-3"
              >
                {" "}
                {/* Increased padding */}
                <div>
                  <div className="font-mono">{tool.name}</div>

                  {tool.description && (
                    <div className="text-muted-foreground text-xs">
                      {tool.description}
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-muted-foreground text-sm">Enable</span>

                  <Switch
                    checked={safeBool(tool.enabled, false)}
                    onCheckedChange={(v) => {
                      const next = structuredClone(plugin);
                      const tools = next.tools;
                      if (tools && tools.length > k) {
                        tools[k]!.enabled = v;
                      }
                      onChange(next);
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export function AssistantEditor({
  assistant,
  onChange,
  availablePlugins,
  onAddPlugin,
  isAddingPlugin,
  addingPluginDetails,
  onRemovePlugin,
  isRemovingPlugin,
  removingPluginDetails,
}: {
  assistant: Assistant;
  onChange: (a: Assistant) => void;
  availablePlugins: PluginManifest[];
  onAddPlugin: (pluginId: string) => void;
  isAddingPlugin: boolean;
  addingPluginDetails: { assistantId: string; pluginId: string } | null;
  onRemovePlugin: (pluginId: string) => void;
  isRemovingPlugin: boolean;
  removingPluginDetails: { assistantId: string; pluginId: string } | null;
}) {
  const enabled = safeBool(assistant.enabled, false);

  // 1. Track currently used plugins by their ID for robustness
  const currentIds = new Set((assistant.plugins || []).map((p) => p.plugin_id));

  // 2. Filter available plugins by ID and map them for the select component
  //    value = id (for logic), label = name (for display)
  const addable = useMemo(
    () =>
      availablePlugins
        .filter((p) => !currentIds.has(p.registry_id))
        .map((p) => ({ value: p.registry_id, label: p.display_name })),
    [availablePlugins, currentIds],
  );

  // 3. State now holds the ID of the plugin to be added
  const [selectedPluginIdToAdd, setSelectedPluginIdToAdd] =
    useState<string>("");

  const isCurrentlyAdding =
    isAddingPlugin && addingPluginDetails?.assistantId === assistant.id;

  return (
    <div className="space-y-6">
      {" "}
      {/* Increased space-y for better section separation */}
      <h3 className="text-base font-semibold"> Basic Settings</h3>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <div className="space-y-2">
          <Label>Name</Label>
          <Input
            value={assistant.name || ""}
            onChange={(e) => onChange({ ...assistant, name: e.target.value })}
          />
        </div>
        <div className="space-y-2">
          <Label>Enable assistant</Label>
          <div className="flex h-10 items-center">
            <Switch
              checked={enabled}
              onCheckedChange={(v) => onChange({ ...assistant, enabled: v })}
            />
          </div>
        </div>
      </div>
      <div className="space-y-2">
        <Label>Description</Label>
        <Textarea
          value={assistant.description || ""}
          onChange={(e) =>
            onChange({ ...assistant, description: e.target.value })
          }
        />
      </div>
      <Separator />
      <div className="flex items-center justify-start gap-4">
        <h3 className="text-base font-semibold">Plugins</h3>
        <div className="flex gap-2">
          <SearchableSelect
            options={addable}
            value={selectedPluginIdToAdd}
            onChange={setSelectedPluginIdToAdd}
            placeholder="Select plugin to add"
            className="min-w-[160px] sm:min-w-[220px]"
          />
          <Button
            disabled={!selectedPluginIdToAdd || isCurrentlyAdding}
            onClick={() =>
              selectedPluginIdToAdd && onAddPlugin(selectedPluginIdToAdd)
            }
          >
            {isCurrentlyAdding && (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            )}
            {isCurrentlyAdding ? "Adding..." : "Add"}
          </Button>
        </div>
      </div>
      {!assistant.plugins?.length && (
        <div className="text-muted-foreground mt-2 text-sm">
          No plugins configured.
        </div>
      )}
      <div className="space-y-4">
        {(assistant.plugins || []).map((p, j) => {
          // --- Logic to check if THIS plugin is the one being removed ---
          const isCurrentlyRemoving =
            isRemovingPlugin &&
            removingPluginDetails?.assistantId === assistant.id &&
            removingPluginDetails?.pluginId === p.plugin_id;

          return (
            <PluginEditor
              key={p.plugin_id}
              plugin={p}
              onChange={(np) => {
                const next = structuredClone(assistant) as Assistant;
                next.plugins = next.plugins || [];
                next.plugins[j] = np;
                onChange(next);
              }}
              onRemove={() => onRemovePlugin(p.plugin_id)}
              // --- Pass the calculated boolean down ---
              isRemoving={isCurrentlyRemoving}
            />
          );
        })}
      </div>
    </div>
  );
}
