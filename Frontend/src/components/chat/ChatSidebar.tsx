import { Bot, LogOut, MessageSquare, Plus, X } from "lucide-react";

import type { Conversation, User } from "@/api/types";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface ChatSidebarProps {
  open: boolean;
  conversations: Conversation[];
  activeId: string | undefined;
  user: User | null | undefined;
  loading: boolean;
  onClose: () => void;
  onNewChat: () => void;
  onSelect: (id: string) => void;
  onLogout: () => void;
}

const ChatSidebar = ({
  open,
  conversations,
  activeId,
  user,
  loading,
  onClose,
  onNewChat,
  onSelect,
  onLogout,
}: ChatSidebarProps) => (
  <>
    {open && (
      <div className="fixed inset-0 bg-background/80 backdrop-blur-xs z-40 lg:hidden" onClick={onClose} />
    )}
    <aside
      className={cn(
        "fixed lg:static inset-y-0 left-0 z-50 w-72 bg-sidebar border-r border-sidebar-border flex flex-col transition-transform duration-300 lg:translate-x-0",
        open ? "translate-x-0" : "-translate-x-full",
      )}
    >
      <div className="flex items-center justify-between p-4 border-b border-sidebar-border">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-foreground flex items-center justify-center">
            <Bot className="w-5 h-5 text-background" />
          </div>
          <div className="flex flex-col">
            <span className="font-oswald text-lg font-medium tracking-tight">
              RAG<span className="text-primary">SYSTEM</span>
            </span>
            <span className="text-[0.6rem] font-space uppercase tracking-widest text-muted-foreground">
              Assistant d'analyse financière
            </span>
          </div>
        </div>
        <Button variant="ghost" size="icon" className="lg:hidden" onClick={onClose} aria-label="Fermer le menu">
          <X className="w-5 h-5" />
        </Button>
      </div>

      <div className="p-4">
        <Button onClick={onNewChat} className="w-full" variant="outline">
          <Plus className="w-4 h-4 mr-2" />
          Nouvelle conversation
        </Button>
      </div>

      <nav className="flex-1 overflow-y-auto p-4 space-y-2" aria-label="Historique">
        <p className="text-xs font-space uppercase tracking-widest text-muted-foreground mb-3">Historique</p>
        {loading ? (
          <p className="text-sm text-muted-foreground">Chargement…</p>
        ) : conversations.length === 0 ? (
          <p className="text-sm text-muted-foreground">Aucune conversation</p>
        ) : (
          conversations.map((conversation) => (
            <button
              key={conversation.id}
              onClick={() => onSelect(conversation.id)}
              aria-current={activeId === conversation.id}
              className={cn(
                "w-full text-left p-3 rounded-lg hover:bg-sidebar-accent transition-colors group",
                activeId === conversation.id && "bg-sidebar-accent",
              )}
            >
              <div className="flex items-center gap-3">
                <MessageSquare className="w-4 h-4 text-muted-foreground group-hover:text-foreground" />
                <span className="text-sm truncate">{conversation.title || "Conversation"}</span>
              </div>
            </button>
          ))
        )}
      </nav>

      <div className="p-4 border-t border-sidebar-border">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center">
            <span className="text-sm font-medium text-primary">{user?.name.charAt(0).toUpperCase()}</span>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate">{user?.name}</p>
            <p className="text-xs text-muted-foreground truncate">{user?.email}</p>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={onLogout}
            aria-label="Se déconnecter"
            className="text-muted-foreground hover:text-destructive"
          >
            <LogOut className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </aside>
  </>
);

export default ChatSidebar;
