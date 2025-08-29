import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { downloadMarketItem, getMarketItems, getMarketMetadata } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/layout/AppLayout";
import { EmptyState } from "@/components/EmptyState";
import { LoadingSkeleton } from "@/components/LoadingSkeleton";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Download, Star, Calendar, User, Tag } from "lucide-react";
import type { MarketItem } from "@/lib/types";

export default function MarketPage() {
    const [selectedCategory, setSelectedCategory] = useState<"all" | "plugin" | "assistant" | "workflow">("all");
    const qc = useQueryClient();

    const metadataQuery = useQuery({
        queryKey: ["market-metadata"],
        queryFn: getMarketMetadata,
        staleTime: 300_000 // 5 minutes
    });

    const itemsQuery = useQuery({
        queryKey: ["market-items", selectedCategory],
        queryFn: () => getMarketItems(selectedCategory),
        staleTime: 60_000 // 1 minute
    });

    const downloadMutation = useMutation({
        mutationFn: downloadMarketItem,
        onSuccess: (_, variables) => {
            toast.success(`Successfully downloaded ${variables.category}: ${variables.item_id}`);
            // Invalidate relevant queries to refresh installed status
            qc.invalidateQueries({ queryKey: ["available-plugins"] });
            qc.invalidateQueries({ queryKey: ["assistants"] });
            qc.invalidateQueries({ queryKey: ["workflows"] });
        },
        onError: (error: any) => {
            toast.error(error.message || "Download failed");
        }
    });

    const handleDownload = (item: MarketItem) => {
        downloadMutation.mutate({
            item_id: item.id,
            category: item.category
        });
    };

    const formatCategory = (category: string) => {
        if (typeof category !== 'string' || category.length === 0) {
            return 'Uncategorized'; // Return a default value
        }
        return category.charAt(0).toUpperCase() + category.slice(1);
    };

    const getCategoryColor = (category: string) => {
        switch (category) {
            case "plugin": return "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300";
            case "assistant": return "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300";
            case "workflow": return "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300";
            default: return "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-300";
        }
    };

    return (
        <div className="space-y-6">
            <PageHeader
                title="Market"
                description="Browse and download plugins, assistants, and workflows from the community marketplace."
            />

            {/* Market Statistics */}
            {metadataQuery.data && (
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <Card>
                        <CardHeader className="pb-2">
                            <CardTitle className="text-sm font-medium">Total Items</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="text-2xl font-bold">
                                {metadataQuery.data.categories.plugins +
                                    metadataQuery.data.categories.assistants +
                                    metadataQuery.data.categories.workflows}
                            </div>
                        </CardContent>
                    </Card>
                    <Card>
                        <CardHeader className="pb-2">
                            <CardTitle className="text-sm font-medium">Plugins</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="text-2xl font-bold">{metadataQuery.data.categories.plugins}</div>
                        </CardContent>
                    </Card>
                    <Card>
                        <CardHeader className="pb-2">
                            <CardTitle className="text-sm font-medium">Assistants</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="text-2xl font-bold">{metadataQuery.data.categories.assistants}</div>
                        </CardContent>
                    </Card>
                    <Card>
                        <CardHeader className="pb-2">
                            <CardTitle className="text-sm font-medium">Workflows</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="text-2xl font-bold">{metadataQuery.data.categories.workflows}</div>
                        </CardContent>
                    </Card>
                </div>
            )}

            {/* Category Tabs */}
            <Tabs value={selectedCategory} onValueChange={(value) => setSelectedCategory(value as any)}>
                <TabsList className="grid w-full grid-cols-4">
                    <TabsTrigger value="all">All</TabsTrigger>
                    <TabsTrigger value="plugin">Plugins</TabsTrigger>
                    <TabsTrigger value="assistant">Assistants</TabsTrigger>
                    <TabsTrigger value="workflow">Workflows</TabsTrigger>
                </TabsList>

                <TabsContent value={selectedCategory} className="mt-6">
                    {/* Loading State */}
                    {itemsQuery.isLoading && <LoadingSkeleton lines={5} />}

                    {/* Error State */}
                    {itemsQuery.error && (
                        <div className="text-red-600">
                            Unable to fetch market items from the backend.
                        </div>
                    )}

                    {/* Empty State */}
                    {itemsQuery.data && itemsQuery.data.length === 0 && (
                        <EmptyState title="No items found" />
                    )}

                    {/* Items Grid */}
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {itemsQuery.data?.map((item) => (
                            <Card key={item.id} className="flex flex-col">
                                <CardHeader>
                                    <div className="flex items-start justify-between">
                                        <div className="flex-1">
                                            <CardTitle className="text-lg">{item.name}</CardTitle>
                                            {item.version && (
                                                <Badge variant="outline" className="mt-1">
                                                    v{item.version}
                                                </Badge>
                                            )}
                                        </div>
                                        <Badge className={getCategoryColor(item)}>
                                            {formatCategory(item.category)}
                                        </Badge>
                                    </div>
                                    <CardDescription className="mt-2">
                                        {item.description}
                                    </CardDescription>
                                </CardHeader>

                                <CardContent className="flex-1">
                                    {/* Tags */}
                                    {item.tags && item.tags.length > 0 && (
                                        <div className="flex flex-wrap gap-1 mb-3">
                                            {item.tags.slice(0, 3).map((tag) => (
                                                <Badge key={tag} variant="secondary" className="text-xs">
                                                    <Tag className="w-3 h-3 mr-1" />
                                                    {tag}
                                                </Badge>
                                            ))}
                                            {item.tags.length > 3 && (
                                                <Badge variant="secondary" className="text-xs">
                                                    +{item.tags.length - 3}
                                                </Badge>
                                            )}
                                        </div>
                                    )}

                                    {/* Metadata */}
                                    <div className="space-y-2 text-sm text-muted-foreground">
                                        {item.author && (
                                            <div className="flex items-center gap-2">
                                                <User className="w-4 h-4" />
                                                <span>{item.author}</span>
                                            </div>
                                        )}
                                        {
                                            //item.downloads !== undefined && (
                                            //     <div className="flex items-center gap-2">
                                            //         <Download className="w-4 h-4" />
                                            //         <span>{item.downloads.toLocaleString()} downloads</span>
                                            //     </div>
                                            // )
                                        }
                                        {item.rating && (
                                            <div className="flex items-center gap-2">
                                                <Star className="w-4 h-4 fill-yellow-400 text-yellow-400" />
                                                <span>{item.rating}/5</span>
                                            </div>
                                        )}
                                        {item.updated_at && (
                                            <div className="flex items-center gap-2">
                                                <Calendar className="w-4 h-4" />
                                                <span>Updated {new Date(item.updated_at).toLocaleDateString()}</span>
                                            </div>
                                        )}
                                    </div>
                                </CardContent>

                                <CardFooter>
                                    <Button
                                        onClick={() => handleDownload(item)}
                                        disabled={downloadMutation.isPending || item.is_installed}
                                        className="w-full"
                                    >
                                        <Download className="w-4 h-4 mr-2" />
                                        {
                                            item.is_installed
                                                ? "Installed"
                                                : downloadMutation.isPending
                                                    ? "Downloading..."
                                                    : "Download"
                                        }
                                    </Button>
                                </CardFooter>
                            </Card>
                        ))}
                    </div>
                </TabsContent>
            </Tabs>
        </div >
    );
}
