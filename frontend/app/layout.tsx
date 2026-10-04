import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "CortexFlow — AI Research Platform",
  description:
    "Upload knowledge, chat with your documents with grounded citations, build knowledge graphs, and run multi-agent research.",
  applicationName: "CortexFlow",
  authors: [{ name: "CortexFlow" }],
  keywords: ["AI", "RAG", "research", "knowledge graph", "NotebookLM"],
  openGraph: {
    title: "CortexFlow — AI Research Platform",
    description: "Enterprise AI research platform with grounded citations.",
    type: "website",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen bg-background font-sans">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
