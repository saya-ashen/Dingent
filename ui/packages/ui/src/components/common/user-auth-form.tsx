import { useState } from "react";
import { z } from "zod";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { Loader2, LogIn } from "lucide-react";
import { toast } from "sonner";
import { useAuthStore } from "@repo/store";
import { cn } from "@repo/lib/utils";
import {
  Button,
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
  Input,
  PasswordInput,
} from "@repo/ui/components";
import type { ApiClient } from "@repo/api-client";
import { useWorkspaceStore } from "@repo/store";

const formSchema = z.object({
  email: z.email({
    error: (iss) => (iss.input === "" ? "Please enter your email" : undefined),
  }),
  password: z
    .string()
    .min(1, "Please enter your password")
    .min(7, "Password must be at least 7 characters long"),
});

interface UserAuthFormProps extends React.HTMLAttributes<HTMLFormElement> {
  api: ApiClient;
  onLoginSuccess: (user: any, token: string) => void;
  onLoginFail?: (error: Error) => void;
}

export function UserAuthForm({
  api,
  className,
  onLoginSuccess,
  onLoginFail,
  ...props
}: UserAuthFormProps) {
  const [isLoading, setIsLoading] = useState(false);
  const { setAuth } = useAuthStore();
  const { setWorkspaces } = useWorkspaceStore();

  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      email: "",
      password: "",
    },
  });

  function onSubmit(data: z.infer<typeof formSchema>) {
    setIsLoading(true);

    const handleLoginFlow = async () => {


      // 第一步：登录
      // 注意：这里的 api.auth 对应我们在 @repo/api 中定义的 AuthApi 类
      const { access_token, user } = await api.auth.login({
        email: data.email,
        password: data.password,
      });

      // 第二步：更新状态 (这一步至关重要)
      // 我们需要先将 Token 写入 Store/Cookie，后续的 API 请求才能带上 Token
      // 假设 setAuth = (token, user) => { Cookie.set(...); set({ token, user }) }
      setAuth(access_token, user);

      // 第三步：获取工作空间
      // getClientApi 内部会读取刚才 setAuth 更新后的 Store/Cookie
      const workspaces = await api.workspaces.list(); // 假设 API 方法名为 list

      // 第四步：存入 Workspace Store
      setWorkspaces(workspaces);

      return { user, access_token };
    };

    toast.promise(handleLoginFlow(), {
      loading: "正在登录并加载数据...",
      success: ({ user, access_token }) => {
        setIsLoading(false);
        // 执行跳转或其他逻辑
        onLoginSuccess(user, access_token);
        return `欢迎回来, ${user.full_name || user.email}!`;
      },
      error: (err) => {
        setIsLoading(false);
        if (onLoginFail) {
          onLoginFail(err);
        }
        // 这里既捕获登录错误，也捕获获取 Workspace 失败的错误
        return err.message || "登录过程中发生错误";
      },
    });
  }

  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit(onSubmit)}
        className={cn("grid gap-3", className)}
        {...props}
      >
        <FormField
          control={form.control}
          name="email"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Email</FormLabel>
              <FormControl>
                <Input placeholder="name@example.com" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="password"
          render={({ field }) => (
            <FormItem className="relative">
              <FormLabel>Password</FormLabel>
              <FormControl>
                <PasswordInput placeholder="********" {...field} />
              </FormControl>
              <FormMessage />
              <Link
                href="/forgot-password"
                className="text-muted-foreground absolute end-0 -top-0.5 text-sm font-medium hover:opacity-75"
              >
                Forgot password?
              </Link>
            </FormItem>
          )}
        />
        <Button className="mt-2" disabled={isLoading}>
          {isLoading ? <Loader2 className="animate-spin" /> : <LogIn />}
          Sign in
        </Button>

        <div className="relative my-2">
          <div className="absolute inset-0 flex items-center">
            <span className="w-full border-t" />
          </div>
          <div className="relative flex justify-center text-xs uppercase">
            <span className="bg-background text-muted-foreground px-2">
              Or
            </span>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-2">
          <Link href="/auth/sign-up">
            <Button
              variant="outline"
              type="button"
              disabled={isLoading}
              className="w-full" // 确保按钮填满 Link 容器的宽度
            >
              Sign up
            </Button>
          </Link>
          <Button variant="outline" type="button" disabled={isLoading}>
            SSO
          </Button>
        </div>
      </form>
    </Form>
  );
}
