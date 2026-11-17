"use client";

import Link from "next/link";
import { useUser, useClerk } from "@clerk/nextjs";
import {
  ArrowLeft,
  User,
  Languages,
  Shield,
  LogOut,
  CheckCircle2,
  ExternalLink,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { SUPPORTED_LANGUAGES } from "@/lib/api/chats";

export default function SettingsPage() {
  const { user } = useUser();
  const { signOut } = useClerk();

  return (
    <div className="min-h-screen bg-[#090D16] text-[#F8FAFC]">
      {/* Top Header */}
      <header className="border-b border-slate-800/80 bg-[#0A0F1D] px-6 py-4">
        <div className="mx-auto flex max-w-4xl items-center justify-between">
          <Link
            href="/chat"
            className="flex items-center gap-2 text-xs font-medium text-slate-400 hover:text-white transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            <span>Back to Chat Workspace</span>
          </Link>

          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Preferences & Account
          </span>
        </div>
      </header>

      {/* Main Settings Content */}
      <main className="mx-auto max-w-4xl px-6 py-10 space-y-8">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">
            Settings
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            Manage your account, view supported languages, and review system configurations.
          </p>
        </div>

        {/* Profile Section */}
        <section className="rounded-2xl border border-slate-800 bg-[#0F1626] p-6 shadow-sm space-y-4">
          <div className="flex items-center gap-3 border-b border-slate-800/80 pb-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              <User className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-white">User Account</h2>
              <p className="text-xs text-slate-400">Authenticated via Clerk</p>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
            <div>
              <label className="text-slate-500 block mb-1 font-medium">Name</label>
              <p className="font-semibold text-slate-200">
                {user?.fullName || "Not provided"}
              </p>
            </div>
            <div>
              <label className="text-slate-500 block mb-1 font-medium">Email Address</label>
              <p className="font-semibold text-slate-200">
                {user?.primaryEmailAddress?.emailAddress || "Not available"}
              </p>
            </div>
            <div>
              <label className="text-slate-500 block mb-1 font-medium">User ID</label>
              <p className="font-mono text-slate-400 text-[11px] truncate">
                {user?.id || "—"}
              </p>
            </div>
            <div>
              <label className="text-slate-500 block mb-1 font-medium">Session Status</label>
              <div className="flex items-center gap-1.5 text-emerald-400 font-medium">
                <CheckCircle2 className="h-3.5 w-3.5" />
                <span>Active & Verified</span>
              </div>
            </div>
          </div>
        </section>

        {/* Language Capabilities */}
        <section className="rounded-2xl border border-slate-800 bg-[#0F1626] p-6 shadow-sm space-y-4">
          <div className="flex items-center gap-3 border-b border-slate-800/80 pb-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-sky-500/10 text-sky-400 border border-sky-500/20">
              <Languages className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-white">
                Multilingual Engine
              </h2>
              <p className="text-xs text-slate-400">
                Supported output languages for responses, citations, and summaries
              </p>
            </div>
          </div>

          <p className="text-xs text-slate-300 leading-relaxed">
            The RAG pipeline retrieves multilingual embeddings via{" "}
            <code className="rounded bg-[#131B2E] px-1.5 py-0.5 text-indigo-300 font-mono text-[11px]">
              paraphrase-multilingual-MiniLM-L12-v2
            </code>{" "}
            and synthesizes responses in the chat's configured output language.
          </p>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 pt-2">
            {SUPPORTED_LANGUAGES.map((lang) => (
              <div
                key={lang}
                className="flex items-center gap-2 rounded-xl border border-slate-800/80 bg-[#131B2E] px-3 py-2 text-xs font-medium text-slate-200"
              >
                <CheckCircle2 className="h-3.5 w-3.5 text-indigo-400" />
                <span>{lang}</span>
              </div>
            ))}
          </div>
        </section>

        {/* System & Architecture */}
        <section className="rounded-2xl border border-slate-800 bg-[#0F1626] p-6 shadow-sm space-y-4">
          <div className="flex items-center gap-3 border-b border-slate-800/80 pb-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-purple-500/10 text-purple-400 border border-purple-500/20">
              <Shield className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-white">
                System Infrastructure
              </h2>
              <p className="text-xs text-slate-400">Backend components & models</p>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
            <div className="rounded-xl border border-slate-800/60 bg-[#131B2E] p-3">
              <span className="text-slate-500 font-medium block">Vector Store</span>
              <span className="text-slate-200 font-semibold mt-0.5 block">
                Qdrant Cloud (384-dim Multilingual)
              </span>
            </div>
            <div className="rounded-xl border border-slate-800/60 bg-[#131B2E] p-3">
              <span className="text-slate-500 font-medium block">Reranking Model</span>
              <span className="text-slate-200 font-semibold mt-0.5 block">
                FlashRank (ms-marco-TinyBERT-L-2-v2)
              </span>
            </div>
            <div className="rounded-xl border border-slate-800/60 bg-[#131B2E] p-3">
              <span className="text-slate-500 font-medium block">Inference Engine</span>
              <span className="text-slate-200 font-semibold mt-0.5 block">
                Groq (openai/gpt-oss-120b)
              </span>
            </div>
            <div className="rounded-xl border border-slate-800/60 bg-[#131B2E] p-3">
              <span className="text-slate-500 font-medium block">Background Summaries</span>
              <span className="text-slate-200 font-semibold mt-0.5 block">
                Celery + Redis + ReportLab PDF
              </span>
            </div>
          </div>
        </section>

        {/* Sign Out */}
        <div className="flex justify-end pt-4">
          <Button
            variant="danger"
            size="md"
            onClick={() => signOut({ redirectUrl: "/" })}
          >
            <LogOut className="h-4 w-4" />
            Sign Out of Account
          </Button>
        </div>
      </main>
    </div>
  );
}

