"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { Youtube, Loader2, AlertCircle } from "lucide-react";
import { Modal } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { isValidYouTubeUrl } from "@/lib/utils/youtube";

const schema = z.object({
  url: z
    .string()
    .min(1, "YouTube URL is required")
    .refine((val) => isValidYouTubeUrl(val), {
      message:
        "Please enter a valid YouTube video URL (standard, youtu.be, or Shorts)",
    }),
  language: z.string().default("en"),
});

export function AddVideoModal({ isOpen, onClose, onIngest }) {
  const [serverError, setServerError] = useState("");

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: zodResolver(schema),
    defaultValues: {
      url: "",
      language: "en",
    },
  });

  async function onSubmit(data) {
    setServerError("");
    try {
      await onIngest({
        url: data.url.trim(),
        language: data.language,
      });
      reset();
      onClose();
    } catch (err) {
      setServerError(
        err.message ||
          "Could not ingest video transcript. Please verify the URL and try again."
      );
    }
  }

  function handleClose() {
    reset();
    setServerError("");
    onClose();
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="Add YouTube Video"
      description="Enter any YouTube URL to extract its transcript, generate multilingual embeddings, and enable contextual Q&A."
    >
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        {serverError && (
          <div className="flex items-start gap-2.5 rounded-xl border border-rose-500/20 bg-rose-500/10 p-3 text-xs text-rose-400">
            <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
            <span>{serverError}</span>
          </div>
        )}

        <div>
          <label className="block text-xs font-semibold text-slate-300 mb-1.5">
            YouTube Video URL
          </label>
          <Input
            placeholder="https://www.youtube.com/watch?v=... or https://youtu.be/..."
            {...register("url")}
            error={errors.url?.message}
            disabled={isSubmitting}
            autoFocus
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-300 mb-1.5">
            Transcript Language
          </label>
          <select
            {...register("language")}
            disabled={isSubmitting}
            className="w-full rounded-xl border border-slate-800 bg-[#0F1626] px-3.5 py-2 text-sm text-[#F8FAFC] focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 transition-colors"
          >
            <option value="en">English (default)</option>
            <option value="hi">Hindi (हिन्दी)</option>
            <option value="pa">Punjabi (ਪੰਜਾਬੀ)</option>
            <option value="es">Spanish (Español)</option>
            <option value="fr">French (Français)</option>
            <option value="de">German (Deutsch)</option>
            <option value="ja">Japanese (日本語)</option>
          </select>
        </div>

        <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800/80">
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={handleClose}
            disabled={isSubmitting}
          >
            Cancel
          </Button>
          <Button
            type="submit"
            variant="primary"
            size="sm"
            isLoading={isSubmitting}
          >
            <Youtube className="h-4 w-4" />
            Ingest & Attach Video
          </Button>
        </div>
      </form>
    </Modal>
  );
}

