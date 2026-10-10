import type { Metadata } from "next";
import { ThemeProvider } from "@/components/theme";
import { themeInitializationScript } from "@/lib/theme";
import "./globals.css";
export const metadata: Metadata = { title: "NyayaAI | Accessible Justice", description: "Accessible Justice. Smarter Workflows. Responsible AI. A clearly labeled judicial assistance prototype." };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en" suppressHydrationWarning><head><script dangerouslySetInnerHTML={{ __html: themeInitializationScript }} /></head><body><ThemeProvider><a className="skip-link" href="#main-content">Skip to main content</a>{children}</ThemeProvider></body></html>;
}