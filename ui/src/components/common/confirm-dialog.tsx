import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger, // 引入 Trigger
} from "@/components/ui/alert-dialog";
import { Button } from "../ui/button";

// 合并两个组件的所有 Props，并设为可选
type UniversalConfirmDialogProps = {
  // --- 通用内容属性 ---
  title: ReactNode;
  description: ReactNode; // 使用一个统一的名称，例如 'description'
  children?: ReactNode; // 允许插入额外内容

  // --- 操作与按钮 ---
  onConfirm: () => void | Promise<void>;
  confirmText?: ReactNode;
  cancelText?: string;
  destructive?: boolean;

  // --- 状态控制 ---
  isLoading?: boolean;
  disabled?: boolean; // 外部传入的禁用状态

  // --- 样式 ---
  className?: string;

  // --- 兼容两种模式的关键属性 ---

  /**
   * 非受控模式：传入一个React节点（如按钮）作为触发器，组件将管理自己的打开/关闭状态。
   * @example <ConfirmDialog trigger={<Button>Delete</Button>} ... />
   */
  trigger?: ReactNode;

  /**
   * 受控模式：通过外部state控制对话框的打开状态。
   * 如果提供了`trigger`，此属性将被忽略。
   * @example <ConfirmDialog open={isOpen} onOpenChange={setIsOpen} ... />
   */
  open?: boolean;

  /**
   * 受控模式：当打开状态改变时调用的回调函数。
   * 如果提供了`trigger`，此属性将被忽略。
   */
  onOpenChange?: (open: boolean) => void;
};

export function ConfirmDialog(props: UniversalConfirmDialogProps) {
  const {
    // 通用
    title,
    description,
    children,
    onConfirm,
    confirmText = "Confirm",
    cancelText = "Cancel",
    destructive = false,
    // 状态
    isLoading = false,
    disabled = false,
    // 样式
    className,
    // 模式切换
    trigger,
    open,
    onOpenChange,
  } = props;

  // 这是对话框的核心内容，两种模式下都可以复用
  const dialogContent = (
    <AlertDialogContent className={cn(className)}>
      <AlertDialogHeader className="text-start">
        <AlertDialogTitle>{title}</AlertDialogTitle>
        <AlertDialogDescription asChild>
          <div>{description}</div>
        </AlertDialogDescription>
      </AlertDialogHeader>
      {children}
      <AlertDialogFooter>
        <AlertDialogCancel disabled={isLoading}>{cancelText}</AlertDialogCancel>
        <Button
          variant={destructive ? "destructive" : "default"}
          onClick={onConfirm}
          disabled={disabled || isLoading}
        >
          {/* 在这里统一处理加载状态 */}
          {isLoading && <span className="mr-2 h-4 w-4 animate-spin">⏳</span>}
          {confirmText}
        </Button>
      </AlertDialogFooter>
    </AlertDialogContent>
  );

  // 1. 如果 trigger 存在，使用非受控模式
  if (trigger) {
    return (
      <AlertDialog>
        <AlertDialogTrigger asChild>{trigger}</AlertDialogTrigger>
        {dialogContent}
      </AlertDialog>
    );
  }

  // 2. 否则，使用受控模式
  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      {dialogContent}
    </AlertDialog>
  );
}
