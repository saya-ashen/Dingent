import localFont from "next/font/local";

const geistSans = localFont({
  src: [
    {
      path: "./fonts/Geist-Regular.woff2",
      weight: "400",
      style: "normal",
    },
    {
      path: "./fonts/Geist-Bold.woff2",
      weight: "700",
      style: "normal",
    },
  ],
  variable: "--font-geist-sans",
});

const geistMono = localFont({
  src: [
    {
      path: "./fonts/GeistMono-Regular.woff2",
      weight: "400",
      style: "normal",
    },
  ],
  variable: "--font-geist-mono",
});

export const fonts = {
  sans: geistSans,
  mono: geistMono,
};

export const fontOptions = ["inter", "manrope", "system"] as const;
