"use client";

import { useEffect, useState } from "react";
import { Check, ChevronsUpDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import type { LLMModelConfig } from "@/types/entity";

interface ModelSelectorProps {
  models: LLMModelConfig[];
  value?: string | null;
  onChange: (modelId: string | null) => void;
  placeholder?: string;
  disabled?: boolean;
  allowClear?: boolean;
}

export function ModelSelector({
  models,
  value,
  onChange,
  placeholder = "Select model...",
  disabled = false,
  allowClear = true,
}: ModelSelectorProps) {
  const [open, setOpen] = useState(false);
  const [selectedValue, setSelectedValue] = useState<string | null>(
    value || null
  );

  useEffect(() => {
    setSelectedValue(value || null);
  }, [value]);

  const selectedModel = models.find((m) => m.id === selectedValue);

  const handleSelect = (modelId: string) => {
    const newValue = selectedValue === modelId ? null : modelId;
    setSelectedValue(newValue);
    onChange(newValue);
    setOpen(false);
  };

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          className="w-full justify-between"
          disabled={disabled}
        >
          {selectedModel ? (
            <span className="flex items-center gap-2">
              <span className="font-medium">{selectedModel.name}</span>
              <span className="text-xs text-muted-foreground">
                ({selectedModel.provider}/{selectedModel.model})
              </span>
            </span>
          ) : (
            <span className="text-muted-foreground">{placeholder}</span>
          )}
          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-full p-0">
        <Command>
          <CommandInput placeholder="Search models..." />
          <CommandList>
            <CommandEmpty>No model found.</CommandEmpty>
            <CommandGroup>
              {allowClear && selectedValue && (
                <CommandItem
                  onSelect={() => {
                    setSelectedValue(null);
                    onChange(null);
                    setOpen(false);
                  }}
                >
                  <Check
                    className={cn(
                      "mr-2 h-4 w-4",
                      !selectedValue ? "opacity-100" : "opacity-0"
                    )}
                  />
                  <span className="text-muted-foreground italic">
                    (Use default)
                  </span>
                </CommandItem>
              )}
              {models
                .filter((m) => m.is_active)
                .map((model) => (
                  <CommandItem
                    key={model.id}
                    value={model.id}
                    onSelect={() => handleSelect(model.id)}
                  >
                    <Check
                      className={cn(
                        "mr-2 h-4 w-4",
                        selectedValue === model.id ? "opacity-100" : "opacity-0"
                      )}
                    />
                    <div className="flex flex-col">
                      <span className="font-medium">{model.name}</span>
                      <span className="text-xs text-muted-foreground">
                        {model.provider}/{model.model}
                      </span>
                    </div>
                  </CommandItem>
                ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
