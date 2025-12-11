import type { ReactNode } from "react";
import { fonts } from "@repo/config/fonts";
import { GlobalProviders } from "../../providers";
import "@repo/ui/styles.css";
import StoreInitializer from "../common/store-initializer";

const geistSans = fonts.sans;
const geistMono = fonts.mono;

interface RootLayoutProps {
  children: ReactNode;
  bodyClassName?: string;
}

export function RootLayout({ children, bodyClassName = "" }: RootLayoutProps) {
  StoreInitializer()
  return (
    <html lang="en">
      <body
        className={`${geistSans.className} ${geistMono.className} antialiased ${bodyClassName}`}
      >
        <GlobalProviders>{children}</GlobalProviders>
      </body>
    </html>
  );
}
