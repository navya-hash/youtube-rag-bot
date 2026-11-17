import { Sparkles, Youtube, MessageSquare, Lightbulb, FileText } from "lucide-react";
import { Button } from "@/components/ui/Button";

export function WelcomeState({ onSelectPrompt, onOpenAddVideo, videoCount = 0 }) {
  const suggestions = [
    {
      icon: Lightbulb,
      title: "Explain Core Concepts",
      prompt: "What are the main concepts and takeaways discussed in the video?",
    },
    {
      icon: FileText,
      title: "Detailed Summary",
      prompt: "Can you provide a step-by-step summary of the topics covered?",
    },
    {
      icon: MessageSquare,
      title: "Pros & Limitations",
      prompt: "What limitations, challenges, or trade-offs does the speaker highlight?",
    },
    {
      icon: Sparkles,
      title: "Compare Perspectives",
      prompt: "How does the speaker compare this approach with traditional methods?",
    },
  ];

  return (
    <div className="flex flex-1 flex-col items-center justify-center p-6 text-center max-w-2xl mx-auto">
      {/* Icon Badge */}
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-tr from-indigo-600 to-indigo-500 shadow-xl shadow-indigo-600/20 text-white mb-6">
        <Youtube className="h-7 w-7" />
      </div>

      <h2 className="text-2xl font-bold tracking-tight text-white sm:text-3xl">
        Chat with your YouTube Video
      </h2>

      <p className="mt-3 text-sm text-slate-400 leading-relaxed max-w-lg">
        {videoCount > 0
          ? `You have ${videoCount} video${videoCount > 1 ? "s" : ""} attached to this chat. Ask any question below or choose a starter prompt.`
          : "Get started by adding a YouTube video URL in the right panel to analyze its transcript and ask questions."}
      </p>

      {/* If no video attached, show prominent Add Video button */}
      {videoCount === 0 && (
        <div className="mt-6">
          <Button variant="primary" onClick={onOpenAddVideo}>
            <Youtube className="h-4 w-4" />
            Add YouTube Video URL
          </Button>
        </div>
      )}

      {/* Starter Prompts */}
      <div className="mt-10 grid w-full grid-cols-1 sm:grid-cols-2 gap-3 text-left">
        {suggestions.map((item, idx) => {
          const Icon = item.icon;
          return (
            <button
              key={idx}
              onClick={() => onSelectPrompt(item.prompt)}
              className="flex items-start gap-3 rounded-2xl border border-slate-800/80 bg-[#0F1626]/60 p-4 text-xs hover:border-slate-700 hover:bg-[#131B2E] transition-all group shadow-sm text-left"
            >
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 group-hover:bg-indigo-500/20 transition-colors">
                <Icon className="h-4 w-4" />
              </div>
              <div className="flex-1">
                <h3 className="font-semibold text-slate-200 group-hover:text-white transition-colors">
                  {item.title}
                </h3>
                <p className="mt-1 text-slate-400 line-clamp-2">
                  {item.prompt}
                </p>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

