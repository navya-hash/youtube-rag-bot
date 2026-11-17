import { ClerkProvider } from "@clerk/nextjs";
import QueryProvider from "@/components/providers/QueryProvider";
import "./globals.css";

export const metadata = {
  title: "YouTube RAG Bot | AI Video Knowledge Base",
  description:
    "Chat with YouTube videos, extract verified citations, generate multilingual summaries, and export PDFs.",
  icons: {
    icon: "/favicon.ico",
  },
};

export default function RootLayout({ children }) {
  return (
    <ClerkProvider
      appearance={{
        variables: {
          colorPrimary: "#6366F1",
          colorBackground: "#0F1626",
          colorInputBackground: "#131B2E",
          colorInputText: "#F8FAFC",
          colorText: "#F8FAFC",
          colorTextSecondary: "#94A3B8",
        },
        elements: {
          card: "border border-slate-800 bg-[#0F1626] shadow-2xl",
          navbar: "hidden",
        },
      }}
    >
      <html lang="en" className="dark">
        <body className="min-h-screen bg-[#090D16] text-[#F8FAFC] antialiased">
          <QueryProvider>{children}</QueryProvider>
        </body>
      </html>
    </ClerkProvider>
  );
}
