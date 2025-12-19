import {
  Tag,
  Download,
  Star,
  Calendar,
  User,
  ArrowUpCircle,
  CheckCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { MarketItem } from "@/types/entity";

interface MarketCardProps {
  item: MarketItem;
  onDownload: (item: MarketItem) => void;
  isProcessing: boolean;
}

export function MarketCard({ item, onDownload, isProcessing }: MarketCardProps) {
  const getCategoryColor = (cat: string) => {
    switch (cat) {
      case "plugin": return "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300";
      case "assistant": return "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300";
      case "workflow": return "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300";
      default: return "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-300";
    }
  };

  return (
    <Card className="flex flex-col h-full">
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <CardTitle className="text-lg">{item.name}</CardTitle>
            {item.version && (
              <Badge
                variant="outline"
                className={cn("mt-1", {
                  "border-yellow-500 text-yellow-600": item.update_available,
                })}
              >
                {item.update_available
                  ? `v${item.installed_version} → v${item.version}`
                  : `v${item.version}`}
              </Badge>
            )}
          </div>
          <Badge className={getCategoryColor(item.category)}>
            {item.category ? item.category.charAt(0).toUpperCase() + item.category.slice(1) : "Uncategorized"}
          </Badge>
        </div>
        <CardDescription className="mt-2 line-clamp-2" title={item.description}>
          {item.description}
        </CardDescription>
      </CardHeader>

      <CardContent className="flex-1">
        {item.tags && item.tags.length > 0 && (
          <div className="mb-3 flex flex-wrap gap-1">
            {item.tags.slice(0, 3).map((tag) => (
              <Badge key={tag} variant="secondary" className="text-xs">
                <Tag className="mr-1 h-3 w-3" />
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
        <div className="text-muted-foreground space-y-2 text-sm">
          {item.author && (
            <div className="flex items-center gap-2">
              <User className="h-4 w-4" />
              <span>{item.author}</span>
            </div>
          )}
          {item.rating && (
            <div className="flex items-center gap-2">
              <Star className="h-4 w-4 fill-yellow-400 text-yellow-400" />
              <span>{item.rating}/5</span>
            </div>
          )}
          {item.updated_at && (
            <div className="flex items-center gap-2">
              <Calendar className="h-4 w-4" />
              <span>
                Updated {new Date(item.updated_at).toLocaleDateString()}
              </span>
            </div>
          )}
        </div>
      </CardContent>

      <CardFooter>
        <ActionButton item={item} isProcessing={isProcessing} onClick={() => onDownload(item)} />
      </CardFooter>
    </Card>
  );
}

// 内部小组件
function ActionButton({
  item,
  isProcessing,
  onClick
}: {
  item: MarketItem;
  isProcessing: boolean;
  onClick: () => void
}) {
  if (item.update_available) {
    return (
      <Button
        onClick={onClick}
        disabled={isProcessing}
        className="w-full bg-yellow-500 text-black hover:bg-yellow-600"
      >
        <ArrowUpCircle className="mr-2 h-4 w-4" />
        {isProcessing ? "Updating..." : "Update"}
      </Button>
    );
  }
  if (item.is_installed) {
    return (
      <Button disabled className="w-full" variant="secondary">
        <CheckCircle className="mr-2 h-4 w-4" />
        Installed
      </Button>
    );
  }
  return (
    <Button onClick={onClick} disabled={isProcessing} className="w-full">
      <Download className="mr-2 h-4 w-4" />
      {isProcessing ? "Downloading..." : "Download"}
    </Button>
  );
}
