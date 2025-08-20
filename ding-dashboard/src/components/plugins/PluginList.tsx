import * as React from "react";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
// import { ScrollArea } from "@/components/ui/scroll-area";

export type Plugin = {
    id: string;
    name: string;
    version?: string;
    description?: string;
    author?: string;
    enabled?: boolean;
    tags?: string[];
    // ...更多字段：配置项、权限、说明等
};

type Props = {
    plugins: Plugin[];
    onToggle?: (plugin: Plugin, nextEnabled: boolean) => void;
    onConfigure?: (plugin: Plugin) => void;
};

export function PluginList({ plugins, onToggle, onConfigure }: Props) {
    return (
        // 单列显示：使用 max-w 容器 + 宽度 100%
        <div className="w-full max-w-3xl mx-auto">
            <Accordion type="multiple" collapsible className="w-full space-y-3">
                {plugins.map((p) => (
                    <AccordionItem
                        key={p.id}
                        value={p.id}
                        className="rounded-lg border bg-card text-card-foreground overflow-hidden"
                    >
                        <AccordionTrigger className="px-4 py-3 hover:no-underline">
                            <div className="w-full flex items-center justify-between gap-4 min-w-0">
                                <div className="min-w-0">
                                    <div className="text-sm font-medium truncate">{p.name}</div>
                                    <div className="text-xs text-muted-foreground truncate">
                                        {p.description || "No description"}
                                    </div>
                                </div>

                                <div className="shrink-0 flex items-center gap-2">
                                    {p.version ? (
                                        <Badge variant="secondary" className="whitespace-nowrap">
                                            v{p.version}
                                        </Badge>
                                    ) : null}
                                    <Badge
                                        variant={p.enabled ? "default" : "outline"}
                                        className="whitespace-nowrap"
                                    >
                                        {p.enabled ? "Enabled" : "Disabled"}
                                    </Badge>
                                </div>
                            </div>
                        </AccordionTrigger>

                        <AccordionContent className="px-4 pb-4">
                            {/* <ScrollArea className="h-64 pr-3"> */}
                            <div className="space-y-4">
                                <section className="space-y-2">
                                    <h4 className="text-sm font-medium">Details</h4>
                                    <div className="text-sm text-muted-foreground">
                                        {p.description || "No description provided."}
                                    </div>
                                    {p.author ? (
                                        <div className="text-xs text-muted-foreground">
                                            Author: {p.author}
                                        </div>
                                    ) : null}
                                    {p.tags?.length ? (
                                        <div className="flex flex-wrap gap-2">
                                            {p.tags.map((t) => (
                                                <Badge key={t} variant="outline">{t}</Badge>
                                            ))}
                                        </div>
                                    ) : null}
                                </section>

                                <div className="flex items-center gap-2 pt-2">
                                    {onToggle ? (
                                        <Button
                                            size="sm"
                                            variant={p.enabled ? "secondary" : "default"}
                                            onClick={() => onToggle(p, !p.enabled)}
                                        >
                                            {p.enabled ? "Disable" : "Enable"}
                                        </Button>
                                    ) : null}
                                    {onConfigure ? (
                                        <Button size="sm" variant="outline" onClick={() => onConfigure(p)}>
                                            Configure
                                        </Button>
                                    ) : null}
                                </div>
                            </div>
                            {/* </ScrollArea> */}
                        </AccordionContent>
                    </AccordionItem>
                ))}
            </Accordion>
        </div>
    );
}
