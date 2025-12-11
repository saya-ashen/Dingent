"use client";

import { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";

import { useWorkspaceStore } from "@repo/store";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Button,
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
  Input,
} from "@repo/ui/components";
import { ApiClient } from "@repo/api-client";

const formSchema = z.object({
  name: z.string().min(1, "工作空间名称不能为空").max(50, "名称太长了"),
  slug: z
    .string()
    .min(3, "标识符至少需要3个字符")
    .max(30, "标识符太长了")
    .regex(/^[a-z0-9-]+$/, "只能包含小写字母、数字和连字符 (例如: my-team)"),
});

// 2. 定义 API 请求的数据类型 (通常可以从 zod schema 推导)
type CreateWorkspaceValues = z.infer<typeof formSchema>;

interface CreateWorkspaceDialogProps {
  api: ApiClient;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CreateWorkspaceDialog({
  api,
  open,
  onOpenChange,
}: CreateWorkspaceDialogProps) {
  const [isLoading, setIsLoading] = useState(false);

  // 从 Store 获取 action
  const { addWorkspace } = useWorkspaceStore();

  // 3. 初始化表单
  const form = useForm<CreateWorkspaceValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      name: "",
      slug: "",
    },
  });

  // UX 优化：当弹窗关闭时，重置表单
  useEffect(() => {
    if (!open) {
      form.reset();
    }
  }, [open, form]);

  // 4. 提交处理
  async function onSubmit(data: CreateWorkspaceValues) {
    setIsLoading(true);

    // 构造 Promise 用于 toast.promise
    const createPromise = async () => {
      // 调用 API (假设这是你的 API 签名)
      const newWorkspace = await api.workspaces.create({
        name: data.name,
        slug: data.slug,
      });

      // 更新本地 Store (不需要重新 fetch list)
      addWorkspace(newWorkspace);

      return newWorkspace;
    };

    toast.promise(createPromise(), {
      loading: "正在创建工作空间...",
      success: (data) => {
        setIsLoading(false);
        onOpenChange(false); // 关闭弹窗
        return `工作空间 "${data.name}" 创建成功!`;
      },
      error: (err) => {
        setIsLoading(false);
        // 如果后端返回了具体的 slug 重复错误，可以在这里 setError
        if (err.message?.includes("slug")) {
          form.setError("slug", { message: "该标识符已被占用" });
        }
        return err.message || "创建失败，请重试";
      },
    });
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>创建工作空间</DialogTitle>
          <DialogDescription>
            创建一个新的工作空间来组织你的项目和团队成员。
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="grid gap-4 py-4">

            {/* Name 字段 */}
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>名称</FormLabel>
                  <FormControl>
                    <Input
                      placeholder="例如：Acme Corp"
                      {...field}
                      // UX 优化：输入名称时自动填充 slug (如果在 slug 为空的情况下)
                      onChange={(e) => {
                        field.onChange(e);
                        // 简单的自动转换逻辑：空格转连字符，大写转小写
                        const currentSlug = form.getValues("slug");
                        if (!currentSlug || currentSlug === "") {
                          const autoSlug = e.target.value
                            .toLowerCase()
                            .replace(/\s+/g, "-")
                            .replace(/[^a-z0-9-]/g, "");
                          form.setValue("slug", autoSlug);
                        }
                      }}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Slug 字段 */}
            <FormField
              control={form.control}
              name="slug"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>标识符 (Slug)</FormLabel>
                  <FormControl>
                    <div className="flex items-center">
                      <span className="text-muted-foreground mr-2 text-sm">
                        app.com/
                      </span>
                      <Input placeholder="acme-corp" {...field} />
                    </div>
                  </FormControl>
                  <FormDescription>
                    这是你的工作空间的唯一 URL 标识。
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
                disabled={isLoading}
              >
                取消
              </Button>
              <Button type="submit" disabled={isLoading}>
                {isLoading && <Loader2 className="mr-2 size-4 animate-spin" />}
                创建
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
