"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { createPortal } from "react-dom";
import {
  Menu,
  Languages,
  Video,
  Edit2,
  Check,
  X,
  ChevronDown,
} from "lucide-react";
import { SUPPORTED_LANGUAGES } from "@/lib/api/chats";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/utils/cn";

export function Header({
  chat,
  videoCount = 0,
  isVideoPanelOpen,
  onToggleVideoPanel,
  onOpenMobileSidebar,
  onUpdateTitle,
  onUpdateLanguage,
}) {
  const [isEditingTitle, setIsEditingTitle] = useState(false);
  const [titleValue, setTitleValue] = useState(chat?.title || "New chat");
  const [isLanguageOpen, setIsLanguageOpen] = useState(false);
  const [dropdownPos, setDropdownPos] = useState({ top: 0, right: 0 });
  const [mounted, setMounted] = useState(false);

  const languageButtonRef = useRef(null);
  const dropdownRef = useRef(null);

  const currentLanguage = chat?.output_language || "English";

  useEffect(() => {
    setMounted(true);
  }, []);

  const updateDropdownPosition = useCallback(() => {
    if (languageButtonRef.current) {
      const rect = languageButtonRef.current.getBoundingClientRect();
      setDropdownPos({
        top: rect.bottom + 8,
        right: Math.max(16, window.innerWidth - rect.right),
      });
    }
  }, []);

  useEffect(() => {
    if (!isLanguageOpen) return;

    updateDropdownPosition();

    function handleKeyDown(e) {
      if (e.key === "Escape") {
        setIsLanguageOpen(false);
      }
    }

    function handleResize() {
      updateDropdownPosition();
    }

    function handleScroll() {
      updateDropdownPosition();
    }

    window.addEventListener("keydown", handleKeyDown);
    window.addEventListener("resize", handleResize);
    window.addEventListener("scroll", handleScroll, true);

    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("resize", handleResize);
      window.removeEventListener("scroll", handleScroll, true);
    };
  }, [isLanguageOpen, updateDropdownPosition]);

  async function handleSaveTitle() {
    const trimmed = titleValue.trim();
    if (trimmed && trimmed !== chat?.title && onUpdateTitle) {
      await onUpdateTitle(trimmed);
    }
    setIsEditingTitle(false);
  }

  return (
    <header className="relative z-20 flex h-16 shrink-0 items-center justify-between border-b border-slate-800/80 bg-[#0A0F1D]/80 px-4 backdrop-blur-md">
      {/* Left: Mobile Toggle & Title */}
      <div className="flex items-center gap-3 overflow-hidden">
        <button
          onClick={onOpenMobileSidebar}
          className="flex lg:hidden h-9 w-9 items-center justify-center rounded-lg text-slate-400 hover:bg-[#131B2E] hover:text-white"
        >
          <Menu className="h-5 w-5" />
        </button>

        {isEditingTitle ? (
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={titleValue}
              onChange={(e) => setTitleValue(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleSaveTitle();
                if (e.key === "Escape") setIsEditingTitle(false);
              }}
              autoFocus
              className="rounded-lg border border-indigo-500 bg-[#0F1626] px-2.5 py-1 text-sm font-semibold text-white focus:outline-none"
            />
            <button
              onClick={handleSaveTitle}
              className="p-1 text-emerald-400 hover:bg-emerald-500/20 rounded"
              title="Save title"
            >
              <Check className="h-4 w-4" />
            </button>
            <button
              onClick={() => setIsEditingTitle(false)}
              className="p-1 text-slate-400 hover:bg-slate-800 rounded"
              title="Cancel"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-2 overflow-hidden group">
            <h1 className="truncate text-base font-semibold text-white tracking-tight">
              {chat?.title || "New Conversation"}
            </h1>
            {chat && (
              <button
                onClick={() => {
                  setTitleValue(chat.title || "New chat");
                  setIsEditingTitle(true);
                }}
                className="opacity-0 group-hover:opacity-100 p-1 text-slate-400 hover:text-white rounded hover:bg-[#131B2E] transition-all"
                title="Edit title"
              >
                <Edit2 className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
        )}
      </div>

      {/* Right: Language Selector & Video Panel Toggle */}
      <div className="flex items-center gap-2.5">
        {/* Language Selector Dropdown */}
        {chat && (
          <div className="relative">
            <button
              ref={languageButtonRef}
              onClick={() => {
                if (!isLanguageOpen) {
                  updateDropdownPosition();
                }
                setIsLanguageOpen(!isLanguageOpen);
              }}
              aria-expanded={isLanguageOpen}
              aria-haspopup="listbox"
              className={cn(
                "flex items-center gap-1.5 rounded-xl border border-slate-800 bg-[#0F1626] px-3 py-1.5 text-xs font-medium text-slate-300 hover:border-slate-700 hover:text-white transition-colors",
                isLanguageOpen && "border-indigo-500/50 text-white ring-1 ring-indigo-500/30"
              )}
              title="Output Language"
            >
              <Languages className="h-3.5 w-3.5 text-indigo-400" />
              <span className="hidden sm:inline">{currentLanguage}</span>
              <ChevronDown
                className={cn(
                  "h-3 w-3 text-slate-500 transition-transform duration-200",
                  isLanguageOpen && "rotate-180 text-indigo-400"
                )}
              />
            </button>

            {/* Portal Dropdown to document.body to escape any parent overflow or stacking context */}
            {mounted && isLanguageOpen && createPortal(
              <>
                <div
                  className="fixed inset-0 z-40 bg-transparent"
                  onClick={() => setIsLanguageOpen(false)}
                  aria-hidden="true"
                />
                <div
                  ref={dropdownRef}
                  style={{
                    position: "fixed",
                    top: `${dropdownPos.top}px`,
                    right: `${dropdownPos.right}px`,
                  }}
                  className="z-50 w-48 rounded-xl border border-slate-800 bg-[#0F1626] p-1.5 shadow-2xl backdrop-blur-xl animate-in fade-in zoom-in-95 duration-100"
                  role="listbox"
                  aria-label="Output Language"
                >
                  <div className="px-2 py-1.5 text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
                    Output Language
                  </div>
                  {SUPPORTED_LANGUAGES.map((lang) => (
                    <button
                      key={lang}
                      role="option"
                      aria-selected={lang === currentLanguage}
                      onClick={() => {
                        if (onUpdateLanguage) onUpdateLanguage(lang);
                        setIsLanguageOpen(false);
                      }}
                      className={cn(
                        "flex w-full items-center justify-between rounded-lg px-2.5 py-1.5 text-xs transition-colors",
                        lang === currentLanguage
                          ? "bg-indigo-600/20 text-indigo-300 font-medium"
                          : "text-slate-300 hover:bg-[#131B2E] hover:text-white"
                      )}
                    >
                      <span>{lang}</span>
                      {lang === currentLanguage && (
                        <Check className="h-3.5 w-3.5 text-indigo-400" />
                      )}
                    </button>
                  ))}
                </div>
              </>,
              document.body
            )}
          </div>
        )}

        {/* Video Context Panel Toggle Button */}
        <Button
          variant={isVideoPanelOpen ? "primary" : "secondary"}
          size="sm"
          onClick={onToggleVideoPanel}
          className="relative"
          title={isVideoPanelOpen ? "Hide video panel" : "Show attached videos"}
        >
          <Video className="h-4 w-4" />
          <span className="hidden sm:inline">Videos</span>
          {videoCount > 0 && (
            <span
              className={cn(
                "flex h-4 min-w-4 items-center justify-center rounded-full px-1 text-[10px] font-bold",
                isVideoPanelOpen
                  ? "bg-white text-indigo-600"
                  : "bg-indigo-500 text-white"
              )}
            >
              {videoCount}
            </span>
          )}
        </Button>
      </div>
    </header>
  );
}

