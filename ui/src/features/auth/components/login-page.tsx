"use client";

import { UserAuthForm } from "@/components/common/user-auth-form";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card";
import { ApiClient } from "@/services";

interface LoginPageProps {
  api: ApiClient;
  onLoginSuccess: (token: string) => void;
  onLoginFail?: (error: Error) => void;
}
export function LoginPage({ api, onLoginSuccess, onLoginFail }: LoginPageProps) {
  return (
    <Card className="gap-4">
      <CardHeader>
        <CardTitle className="text-lg tracking-tight">Sign in</CardTitle>
        <CardDescription>
          Enter your email and password below to <br />
          log into your account
        </CardDescription>
      </CardHeader>
      <CardContent>
        <UserAuthForm
          api={api}
          onLoginSuccess={onLoginSuccess}
          onLoginFail={onLoginFail} />
      </CardContent>
      <CardFooter>
        <p className="text-muted-foreground px-8 text-center text-sm">
          By clicking sign in, you agree to our{" "}
          <a
            href="/terms"
            className="hover:text-primary underline underline-offset-4"
          >
            Terms of Service
          </a>{" "}
          and{" "}
          <a
            href="/privacy"
            className="hover:text-primary underline underline-offset-4"
          >
            Privacy Policy
          </a>
          .
        </p>
      </CardFooter>
    </Card>
  );
}
