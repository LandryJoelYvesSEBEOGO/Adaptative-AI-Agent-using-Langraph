import { Bot, Copy, RotateCcw, ThumbsDown, ThumbsUp, User } from "lucide-react";

import type { Citation, FeedbackType, Message } from "@/api/types";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface MessageItemProps {
  role: Message["role"];
  content: string;
  citations?: Citation[] | null;
  /** Réponse interrompue par l'utilisateur. */
  stopped?: boolean;
  /** Réponse en cours de génération. */
  streaming?: boolean;
  feedback?: FeedbackType | null;
  canRegenerate?: boolean;
  onCopy?: () => void;
  onFeedback?: (type: FeedbackType) => void;
  onRegenerate?: () => void;
}

const MessageItem = ({
  role,
  content,
  citations,
  stopped,
  streaming,
  feedback,
  canRegenerate,
  onCopy,
  onFeedback,
  onRegenerate,
}: MessageItemProps) => {
  const isUser = role === "user";
  return (
    <div className={cn("flex gap-4", isUser ? "justify-end" : "justify-start")} data-role={role}>
      {!isUser && (
        <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
          <Bot className="w-4 h-4 text-primary" />
        </div>
      )}
      <div className={cn("chat-bubble relative", isUser ? "chat-bubble-user" : "chat-bubble-assistant")}>
        <div className="whitespace-pre-wrap" data-testid="message-content">
          {content}
          {streaming && <span className="inline-block w-2 h-4 ml-0.5 align-text-bottom bg-current animate-pulse" />}
        </div>
        {!isUser && citations && citations.length > 0 && !streaming && (
          <p className="mt-2 text-xs text-muted-foreground">
            {citations.length} source{citations.length > 1 ? "s" : ""}
          </p>
        )}
        {stopped && <p className="mt-2 text-xs italic text-muted-foreground">Réponse interrompue</p>}
        {!isUser && !streaming && content && (
          <div className="flex items-center gap-1 mt-4 pt-3 border-t border-border/50">
            <Button variant="ghost" size="sm" className="h-8 px-2 text-muted-foreground" onClick={onCopy}>
              <Copy className="w-3.5 h-3.5 mr-1.5" />
              Copier
            </Button>
            {canRegenerate && (
              <Button variant="ghost" size="sm" className="h-8 px-2 text-muted-foreground" onClick={onRegenerate}>
                <RotateCcw className="w-3.5 h-3.5 mr-1.5" />
                Régénérer
              </Button>
            )}
            <Button
              variant="ghost"
              size="sm"
              aria-label="Réponse utile"
              aria-pressed={feedback === "thumbs_up"}
              className={cn("h-8 px-2 text-muted-foreground hover:text-success", feedback === "thumbs_up" && "text-success")}
              onClick={() => onFeedback?.("thumbs_up")}
            >
              <ThumbsUp className="w-3.5 h-3.5" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              aria-label="Réponse inutile"
              aria-pressed={feedback === "thumbs_down"}
              className={cn("h-8 px-2 text-muted-foreground hover:text-destructive", feedback === "thumbs_down" && "text-destructive")}
              onClick={() => onFeedback?.("thumbs_down")}
            >
              <ThumbsDown className="w-3.5 h-3.5" />
            </Button>
          </div>
        )}
      </div>
      {isUser && (
        <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center shrink-0">
          <User className="w-4 h-4 text-primary-foreground" />
        </div>
      )}
    </div>
  );
};

export default MessageItem;
