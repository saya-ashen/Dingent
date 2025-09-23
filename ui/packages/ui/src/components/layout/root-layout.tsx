import type { ReactNode } from "react";
import { fonts } from "@repo/config/fonts";
import { GlobalProviders } from "../../providers";
import "@repo/ui/styles.css";

// Import shared styles here

// You might need to adjust paths for CopilotKit styles if it's used in both
// or keep it in the specific app's layout if it's not shared.
// For now, let's assume it could be in an app's global.css
// import "@copilotkit/react-ui/styles.css";

const geistSans = fonts.sans;
const geistMono = fonts.mono;

interface RootLayoutProps {
  children: ReactNode;
  bodyClassName?: string;
}

export function RootLayout({ children, bodyClassName = "" }: RootLayoutProps) {
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
