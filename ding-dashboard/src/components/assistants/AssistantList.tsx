import * as React from "react";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
// 可选：如果内容很多，使用 ScrollArea 限高，避免撑满页面
// import { ScrollArea } from "@/components/ui/scroll-area";

export type Assistant = {
    id: string;
    name: string;
    description?: string;
    model?: string;
    tags?: string[];
    updatedAt?: string;
    // ...其他字段
};

type Props = {
    assistants: Assistant[];
    // 单选/多选展开，默认单选（一次只展开一个，避免页面过长）
    allowMultipleOpen?: boolean;
    onEdit?: (assistant: Assistant) => void;
    onDelete?: (assistant: Assistant) => void;
};

export function AssistantList({
    assistants,
    allowMultipleOpen = false,
    onEdit,
    onDelete,
}: Props) {
    return (
        <div className="w-full max-w-5xl mx-auto">
            <Accordion
                type={allowMultipleOpen ? "multiple" : "single"}
                collapsible
                className="w-full space-y-3"
            >
                {assistants.map((a) => (
                    <AccordionItem
                        key={a.id}
                        value={a.id}
                        // rounded + border + bg 让每个卡片明确分隔；overflow-hidden 防止内层绝对定位元素溢出
                        className="rounded-lg border bg-card text-card-foreground overflow-hidden"
                    >
                        <AccordionTrigger
                            // 使用 flex + min-w-0 + truncate，避免长标题把布局挤炸导致“重叠”
                            className="px-4 py-3 hover:no-underline"
                        >
                            <div className="w-full flex items-center justify-between gap-4 min-w-0">
                                <div className="flex items-center gap-3 min-w-0">
                                    {/* 左侧主信息 */}
                                    <div className="min-w-0">
                                        <div className="text-sm font-medium truncate">
                                            {a.name}
                                        </div>
                                        <div className="text-xs text-muted-foreground truncate">
                                            {a.description || "No description"}
                                        </div>
                                    </div>

                                    {/* 标签区：使用换行/折行避免拥挤 */}
                                    {a.tags?.length ? (
                                        <div className="hidden md:flex flex-wrap gap-1">
                                            {a.tags.map((t) => (
                                                <Badge key={t} variant="secondary" className="whitespace-nowrap">
                                                    {t}
                                                </Badge>
                                            ))}
                                        </div>
                                    ) : null}
                                </div>

                                {/* 右侧次要信息 */}
                                <div className="shrink-0 text-xs text-muted-foreground text-right">
                                    {a.model ? <div className="truncate">Model: {a.model}</div> : null}
                                    {a.updatedAt ? <div className="truncate">Updated: {a.updatedAt}</div> : null}
                                </div>
                            </div>
                        </AccordionTrigger>

                        <AccordionContent className="px-4 pb-4">
                            {/* 可选：ScrollArea 限高，防止大量内容撑开页面 */}
                            {/* <ScrollArea className="h-64 pr-3"> */}
                            <div className="space-y-4">
                                {/* 详情内容块，按需替换为你的实际字段 */}
                                <section className="space-y-2">
                                    <h4 className="text-sm font-medium">Overview</h4>
                                    <p className="text-sm text-muted-foreground">
                                        {a.description || "No description provided."}
                                    </p>
                                </section>

                                {a.tags?.length ? (
                                    <section className="space-y-2">
                                        <h4 className="text-sm font-medium">Tags</h4>
                                        <div className="flex flex-wrap gap-2">
                                            {a.tags.map((t) => (
                                                <Badge key={t} variant="outline">{t}</Badge>
                                            ))}
                                        </div>
                                    </section>
                                ) : null}

                                {a.model ? (
                                    <section className="space-y-2">
                                        <h4 className="text-sm font-medium">Model</h4>
                                        <div className="text-sm">{a.model}</div>
                                    </section>
                                ) : null}

                                {/* 操作按钮 */}
                                <div className="flex items-center gap-2 pt-2">
                                    {onEdit ? (
                                        <Button variant="secondary" size="sm" onClick={() => onEdit(a)}>
                                            Edit
                                        </Button>
                                    ) : null}
                                    {onDelete ? (
                                        <Button variant="destructive" size="sm" onClick={() => onDelete(a)}>
                                            Delete
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
