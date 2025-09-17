import { Geist_Mono, Geist } from "next/font/google";

const geistMono = Geist_Mono({
  subsets: ["latin"],
});
const geistSans = Geist({ subsets: ["latin"] });
export const fonts = {
  sans: geistSans,
  mono: geistMono,
};
export const fontOptions = ["inter", "manrope", "system"] as const;
