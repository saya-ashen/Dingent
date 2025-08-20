import * as React from "react";
import { Check, ChevronsUpDown } from "lucide-react";
import { twMerge } from 'tailwind-merge'
import { Button } from "@/components/ui/button";
import {
    Popover,
    PopoverContent,
    PopoverTrigger
} from "@/components/ui/popover";
import {
    Command,
    CommandEmpty,
    CommandGroup,
    CommandInput,
    CommandItem
} from "@/components/ui/command";

export function SearchableSelect({
    options,
    value,
    onChange,
    placeholder = "Select...",
    emptyText = "No results.",
    className
}: {
    options: string[];
    value?: string;
    onChange: (v: string) => void;
    placeholder?: string;
    emptyText?: string;
    className?: string;
}) {
    const [open, setOpen] = React.useState(false);

    return (
        <Popover open={open} onOpenChange={setOpen}>
            <PopoverTrigger asChild>
                <Button
                    variant="outline"
                    role="combobox"
                    aria-expanded={open}
                    className={twMerge("w-full justify-between", className)}
                >
                    {value || placeholder}
                    <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                </Button>
            </PopoverTrigger>
            <PopoverContent className="w-[var(--radix-popover-trigger-width)] p-0">
                <Command>
                    <CommandInput placeholder="Search..." />
                    <CommandEmpty>{emptyText}</CommandEmpty>
                    <CommandGroup>
                        {options.map((opt) => (
                            <CommandItem
                                key={opt}
                                value={opt}
                                onSelect={(val) => {
                                    onChange(val);
                                    setOpen(false);
                                }}
                            >
                                <Check className={twMerge("mr-2 h-4 w-4", value === opt ? "opacity-100" : "opacity-0")} />
                                {opt}
                            </CommandItem>
                        ))}
                    </CommandGroup>
                </Command>
            </PopoverContent>
        </Popover>
    );
}
