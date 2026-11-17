"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { UserButton } from "@clerk/nextjs";
import {
  Youtube,
  Plus,
  Search,
  MessageSquare,
  Edit2,
  Trash2,
  Check,
  X,
  Settings,
  ChevronLeft,
  ChevronRight,
  Loader2,
} from "lucide-react";
import { useChats } from "@/hooks/useChats";
import { Modal } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { formatDate } from "@/lib/utils/formatters";
import { cn } from "@/lib/utils/cn";

export function Sidebar({ isCollapsed, onToggleCollapse, isMobileOpen, onCloseMobile }) {
  const params = useParams();
  const router = useRouter();
  const currentChatId = params?.chatId;

  const {
    chats,
    isLoading,
    createChat,
    isCreating,
    updateTitle,
    deleteChat,
    isDeleting,
  } = useChats();

  const [searchQuery, setSearchQuery] = useState("");
  const [editingChatId, setEditingChatId] = useState(null);
  const [editTitleValue, setEditTitleValue] = useState("");
  const [deletingChat, setDeletingChat] = useState(null);

  // Filter chats by title
  const filteredChats = chats.filter((c) =>
    (c.title || "New chat").toLowerCase().includes(searchQuery.toLowerCase())
  );

  async function handleCreateNewChat() {
    try {
      const newChat = await createChat({ title: "New chat" });
      if (onCloseMobile) onCloseMobile();
      router.push(`/chat/${newChat.id}`);
    } catch (err) {
      console.error("Failed to create chat:", err);
    }
  }

  function startEditing(chat, event) {
    event.preventDefault();
    event.stopPropagation();
    setEditingChatId(chat.id);
    setEditTitleValue(chat.title || "New chat");
  }

  async function saveEditing(chatId, event) {
    if (event) {
      event.preventDefault();
      event.stopPropagation();
    }
    const trimmed = editTitleValue.trim();
    if (trimmed) {
      try {
        await updateTitle({ chatId, title: trimmed });
      } catch (err) {
        console.error("Failed to update title:", err);
      }
    }
    setEditingChatId(null);
  }

  function cancelEditing(event) {
    if (event) {
      event.preventDefault();
      event.stopPropagation();
    }
    setEditingChatId(null);
  }

  function confirmDelete(chat, event) {
    event.preventDefault();
    event.stopPropagation();
    setDeletingChat(chat);
  }

  async function handleDeleteChat() {
    if (!deletingChat) return;
    try {
      await deleteChat(deletingChat.id);
      if (currentChatId === deletingChat.id) {
        router.push("/chat");
      }
      setDeletingChat(null);
    } catch (err) {
      console.error("Failed to delete chat:", err);
    }
  }

  return (
    <>
      {/* Mobile Backdrop */}
      {isMobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/70 backdrop-blur-sm lg:hidden"
          onClick={onCloseMobile}
        />
      )}

      {/* Sidebar Container */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex flex-col border-r border-slate-800 bg-[#0A0F1D] transition-all duration-300 ease-in-out lg:static",
          isCollapsed ? "w-20" : "w-72",
          isMobileOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        )}
      >
        {/* Top Header: Logo & Name */}
        <div className="flex h-16 items-center justify-between px-4 border-b border-slate-800/80">
          <Link
            href="/chat"
            className="flex items-center gap-3 overflow-hidden group"
          >
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-tr from-indigo-600 to-indigo-500 shadow-md shadow-indigo-600/20 group-hover:shadow-indigo-500/30 transition-shadow">
              <Youtube className="h-5 w-5 text-white" />
            </div>
            {!isCollapsed && (
              <div className="flex flex-col overflow-hidden">
                <span className="truncate text-sm font-semibold tracking-tight text-white">
                  YouTube RAG Bot
                </span>
                <span className="truncate text-[10px] text-slate-500 font-medium">
                  Knowledge Workspace
                </span>
              </div>
            )}
          </Link>

          {/* Desktop Collapse Toggle */}
          <button
            onClick={onToggleCollapse}
            className="hidden lg:flex h-7 w-7 items-center justify-center rounded-lg text-slate-400 hover:bg-[#131B2E] hover:text-white transition-colors"
            title={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {isCollapsed ? (
              <ChevronRight className="h-4 w-4" />
            ) : (
              <ChevronLeft className="h-4 w-4" />
            )}
          </button>

          {/* Mobile Close Button */}
          <button
            onClick={onCloseMobile}
            className="flex lg:hidden h-8 w-8 items-center justify-center rounded-lg text-slate-400 hover:bg-[#131B2E] hover:text-white"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Action: New Chat Button */}
        <div className="p-3">
          <button
            onClick={handleCreateNewChat}
            disabled={isCreating}
            className={cn(
              "flex w-full items-center justify-center gap-2 rounded-xl bg-indigo-600 py-2.5 font-medium text-white shadow-md shadow-indigo-600/20 hover:bg-indigo-500 hover:shadow-indigo-500/30 transition-all active:scale-[0.98] disabled:opacity-50",
              isCollapsed ? "px-0" : "px-4 text-sm"
            )}
            title="Start a new chat"
          >
            {isCreating ? (
              <Loader2 className="h-4 w-4 animate-spin shrink-0" />
            ) : (
              <Plus className="h-4 w-4 shrink-0" />
            )}
            {!isCollapsed && <span>New Chat</span>}
          </button>
        </div>

        {/* Search Bar (When expanded) */}
        {!isCollapsed && (
          <div className="px-3 pb-2">
            <div className="relative">
              <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-500" />
              <input
                type="text"
                placeholder="Search conversations..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full rounded-lg border border-slate-800/80 bg-[#0F1626] py-1.5 pl-8 pr-3 text-xs text-slate-200 placeholder-slate-500 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 transition-colors"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery("")}
                  className="absolute right-2.5 top-2.5 text-slate-500 hover:text-slate-300"
                >
                  <X className="h-3 w-3" />
                </button>
              )}
            </div>
          </div>
        )}

        {/* Chat List */}
        <div className="flex-1 overflow-y-auto px-2 py-1 space-y-1">
          {isLoading ? (
            <div className="flex flex-col items-center justify-center py-10 text-slate-500">
              <Loader2 className="h-5 w-5 animate-spin" />
              {!isCollapsed && (
                <span className="mt-2 text-xs">Loading chats...</span>
              )}
            </div>
          ) : filteredChats.length === 0 ? (
            <div className="py-8 text-center text-xs text-slate-500">
              {!isCollapsed && (
                <p>
                  {searchQuery ? "No matching chats" : "No chats yet"}
                </p>
              )}
            </div>
          ) : (
            filteredChats.map((chat) => {
              const isActive = currentChatId === chat.id;
              const isEditing = editingChatId === chat.id;

              return (
                <div
                  key={chat.id}
                  className="relative group rounded-xl transition-colors"
                >
                  {isEditing ? (
                    <div className="flex items-center gap-1.5 p-1 bg-[#131B2E] rounded-xl border border-indigo-500/50">
                      <input
                        type="text"
                        value={editTitleValue}
                        onChange={(e) => setEditTitleValue(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") saveEditing(chat.id, e);
                          if (e.key === "Escape") cancelEditing(e);
                        }}
                        autoFocus
                        className="w-full bg-transparent px-2 py-1 text-xs text-white focus:outline-none"
                      />
                      <button
                        onClick={(e) => saveEditing(chat.id, e)}
                        className="p-1 text-emerald-400 hover:bg-emerald-500/20 rounded"
                        title="Save"
                      >
                        <Check className="h-3.5 w-3.5" />
                      </button>
                      <button
                        onClick={cancelEditing}
                        className="p-1 text-slate-400 hover:bg-slate-700/50 rounded"
                        title="Cancel"
                      >
                        <X className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  ) : (
                    <Link
                      href={`/chat/${chat.id}`}
                      onClick={() => {
                        if (onCloseMobile) onCloseMobile();
                      }}
                      className={cn(
                        "flex items-center gap-2.5 rounded-xl px-3 py-2 text-xs font-medium transition-all",
                        isActive
                          ? "bg-[#131B2E] text-white border border-slate-700/60 shadow-sm"
                          : "text-slate-400 hover:bg-[#0F1626] hover:text-slate-200"
                      )}
                      title={chat.title || "New chat"}
                    >
                      <MessageSquare
                        className={cn(
                          "h-4 w-4 shrink-0",
                          isActive ? "text-indigo-400" : "text-slate-500"
                        )}
                      />

                      {!isCollapsed && (
                        <div className="flex-1 overflow-hidden">
                          <p className="truncate">{chat.title || "New chat"}</p>
                          <span className="text-[10px] text-slate-500">
                            {formatDate(chat.updated_at || chat.created_at)}
                          </span>
                        </div>
                      )}

                      {/* Hover action buttons (Rename, Delete) */}
                      {!isCollapsed && (
                        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                          <button
                            onClick={(e) => startEditing(chat, e)}
                            className="rounded p-1 text-slate-400 hover:bg-slate-800 hover:text-white"
                            title="Rename chat"
                          >
                            <Edit2 className="h-3 w-3" />
                          </button>
                          <button
                            onClick={(e) => confirmDelete(chat, e)}
                            className="rounded p-1 text-slate-400 hover:bg-rose-500/20 hover:text-rose-400"
                            title="Delete chat"
                          >
                            <Trash2 className="h-3 w-3" />
                          </button>
                        </div>
                      )}
                    </Link>
                  )}
                </div>
              );
            })
          )}
        </div>

        {/* Bottom User Profile & Settings */}
        <div className="border-t border-slate-800/80 p-3 space-y-2">
          <Link
            href="/settings"
            className={cn(
              "flex items-center gap-3 rounded-xl px-3 py-2 text-xs font-medium text-slate-400 hover:bg-[#131B2E] hover:text-white transition-colors",
              isCollapsed ? "justify-center px-0" : ""
            )}
            title="Settings"
          >
            <Settings className="h-4 w-4 shrink-0 text-slate-400" />
            {!isCollapsed && <span>Settings & Languages</span>}
          </Link>

          <div
            className={cn(
              "flex items-center rounded-xl bg-[#0F1626] p-2 border border-slate-800/60",
              isCollapsed ? "justify-center" : "gap-3"
            )}
          >
            <UserButton
              afterSignOutUrl="/"
              appearance={{
                elements: {
                  avatarBox: "h-7 w-7",
                },
              }}
            />
            {!isCollapsed && (
              <div className="flex flex-col overflow-hidden text-xs">
                <span className="font-medium text-slate-200 truncate">
                  My Account
                </span>
                <span className="text-[10px] text-slate-500">Active</span>
              </div>
            )}
          </div>
        </div>
      </aside>

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={Boolean(deletingChat)}
        onClose={() => setDeletingChat(null)}
        title="Delete Chat"
        description="Are you sure you want to delete this conversation? This will permanently remove all messages and video associations from this chat."
      >
        <div className="flex justify-end gap-3 mt-6">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setDeletingChat(null)}
            disabled={isDeleting}
          >
            Cancel
          </Button>
          <Button
            variant="danger"
            size="sm"
            isLoading={isDeleting}
            onClick={handleDeleteChat}
          >
            Delete Conversation
          </Button>
        </div>
      </Modal>
    </>
  );
}

