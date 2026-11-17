import Link from "next/link";
import Image from "next/image";
import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import {
  Sparkles,
  Youtube,
  FileText,
  Languages,
  ShieldCheck,
  ArrowRight,
  Clock,
  Layers,
} from "lucide-react";

export default async function HomePage() {
  const { userId } = await auth();

  // If already authenticated, jump straight to the chat workspace
  if (userId) {
    redirect("/chat");
  }

  return (
    <div className="relative min-h-screen bg-[#090D16] text-[#F8FAFC]">
      {/* Background ambient glow */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -top-40 left-1/2 h-[500px] w-[800px] -translate-x-1/2 rounded-full bg-indigo-600/10 blur-[140px]" />
        <div className="absolute top-96 right-10 h-[400px] w-[500px] rounded-full bg-cyan-600/5 blur-[120px]" />
      </div>

      {/* Navigation Header */}
      <header className="relative z-10 mx-auto flex max-w-6xl items-center justify-between px-6 py-6 border-b border-slate-800/60">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-tr from-indigo-600 to-indigo-500 shadow-lg shadow-indigo-500/20">
            <Youtube className="h-5 w-5 text-white" />
          </div>
          <div>
            <span className="text-lg font-semibold tracking-tight text-white">
              YouTube RAG Bot
            </span>
            <span className="ml-2 rounded-full border border-indigo-500/30 bg-indigo-500/10 px-2 py-0.5 text-[10px] font-medium text-indigo-300">
              AI Workspace
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href="/sign-in"
            className="rounded-lg px-4 py-2 text-sm font-medium text-slate-300 hover:text-white transition-colors"
          >
            Sign In
          </Link>
          <Link
            href="/sign-up"
            className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-md shadow-indigo-600/20 hover:bg-indigo-500 transition-all active:scale-[0.98]"
          >
            Get Started
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </header>

      {/* Hero Section */}
      <main className="relative z-10 mx-auto max-w-6xl px-6 pt-20 pb-28">
        <div className="mx-auto max-w-3xl text-center">
          <div className="inline-flex items-center gap-2 rounded-full border border-slate-800 bg-[#0F1626] px-3.5 py-1.5 text-xs font-medium text-slate-300 shadow-inner">
            <Sparkles className="h-3.5 w-3.5 text-indigo-400" />
            <span>Multilingual RAG • Guardrails • Async Summaries</span>
          </div>

          <h1 className="mt-8 text-4xl font-extrabold tracking-tight sm:text-6xl text-white">
            Turn YouTube videos into your{" "}
            <span className="bg-gradient-to-r from-indigo-400 via-sky-300 to-indigo-200 bg-clip-text text-transparent">
              interactive knowledge base
            </span>
            .
          </h1>

          <p className="mt-6 text-lg text-slate-400 leading-relaxed">
            Attach any YouTube video or playlist to your chats. Ask complex
            questions, receive grounded answers with exact timestamp citations,
            generate multilingual summaries, and download executive PDF reports.
          </p>

          <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
            <Link
              href="/sign-up"
              className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-6 py-3.5 text-base font-semibold text-white shadow-xl shadow-indigo-600/25 hover:bg-indigo-500 hover:shadow-indigo-500/35 transition-all"
            >
              Start Chatting for Free
              <ArrowRight className="h-4 w-4" />
            </Link>
            <Link
              href="/sign-in"
              className="inline-flex items-center gap-2 rounded-xl border border-slate-800 bg-[#0F1626] px-6 py-3.5 text-base font-medium text-slate-200 hover:bg-slate-800/80 transition-colors"
            >
              Sign In to Account
            </Link>
          </div>
        </div>

        {/* Feature Grid */}
        <div className="mt-24 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
          <div className="rounded-2xl border border-slate-800/80 bg-[#0F1626]/80 p-6 shadow-xl backdrop-blur-sm">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              <Clock className="h-5 w-5" />
            </div>
            <h3 className="mt-4 text-base font-semibold text-white">
              Verified Timestamp Citations
            </h3>
            <p className="mt-2 text-sm text-slate-400 leading-relaxed">
              Every answer is grounded in extracted transcript chunks. Click any citation to jump directly to that exact second in the YouTube video.
            </p>
          </div>

          <div className="rounded-2xl border border-slate-800/80 bg-[#0F1626]/80 p-6 shadow-xl backdrop-blur-sm">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-sky-500/10 text-sky-400 border border-sky-500/20">
              <Languages className="h-5 w-5" />
            </div>
            <h3 className="mt-4 text-base font-semibold text-white">
              Multilingual RAG & Output
            </h3>
            <p className="mt-2 text-sm text-slate-400 leading-relaxed">
              Ask questions and generate responses in 7 supported languages including English, Hindi, Punjabi, Spanish, French, German, and Japanese.
            </p>
          </div>

          <div className="rounded-2xl border border-slate-800/80 bg-[#0F1626]/80 p-6 shadow-xl backdrop-blur-sm">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-purple-500/10 text-purple-400 border border-purple-500/20">
              <FileText className="h-5 w-5" />
            </div>
            <h3 className="mt-4 text-base font-semibold text-white">
              Async Summaries & PDF Export
            </h3>
            <p className="mt-2 text-sm text-slate-400 leading-relaxed">
              Celery-powered asynchronous video summarization with bulleted key takeaways, core topics, and one-click downloadable PDF reports.
            </p>
          </div>

          <div className="rounded-2xl border border-slate-800/80 bg-[#0F1626]/80 p-6 shadow-xl backdrop-blur-sm">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <ShieldCheck className="h-5 w-5" />
            </div>
            <h3 className="mt-4 text-base font-semibold text-white">
              Enterprise Guardrails
            </h3>
            <p className="mt-2 text-sm text-slate-400 leading-relaxed">
              Equipped with intent classification, prompt injection detection, relevance checking, and hallucination reduction.
            </p>
          </div>

          <div className="rounded-2xl border border-slate-800/80 bg-[#0F1626]/80 p-6 shadow-xl backdrop-blur-sm">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/20">
              <Layers className="h-5 w-5" />
            </div>
            <h3 className="mt-4 text-base font-semibold text-white">
              Multi-Video Chat Workspaces
            </h3>
            <p className="mt-2 text-sm text-slate-400 leading-relaxed">
              Attach multiple videos to a single conversation. Inquire across videos or compare viewpoints with automatic candidate re-ranking.
            </p>
          </div>

          <div className="rounded-2xl border border-slate-800/80 bg-[#0F1626]/80 p-6 shadow-xl backdrop-blur-sm">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-rose-500/10 text-rose-400 border border-rose-500/20">
              <Sparkles className="h-5 w-5" />
            </div>
            <h3 className="mt-4 text-base font-semibold text-white">
              High Performance Architecture
            </h3>
            <p className="mt-2 text-sm text-slate-400 leading-relaxed">
              Powered by Qdrant vector database, Groq LLM, FlashRank reranking, and Redis-cached conversation memory.
            </p>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/60 py-8 text-center text-xs text-slate-500">
        <p>© 2026 YouTube RAG Bot. Built with Next.js, FastAPI, Qdrant & Groq.</p>
      </footer>
    </div>
  );
}

