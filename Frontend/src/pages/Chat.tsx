import { Bot, Loader2, Menu, Send, Square } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { useConversations, useFeedback, useMessages } from "@/api/hooks";
import { useLogout, useSession } from "@/auth/session";
import ChatSidebar from "@/components/chat/ChatSidebar";
import MessageItem from "@/components/chat/MessageItem";
import SourcesPanel from "@/components/chat/SourcesPanel";
import QueryError from "@/components/QueryError";
import ThemeToggle from "@/components/ThemeToggle";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useChat } from "@/hooks/useChat";
import { useToast } from "@/hooks/use-toast";
import { errorMessage } from "@/api/errors";
import type { Citation, FeedbackType } from "@/api/types";

const SUGGESTED_QUESTIONS = [
  "What was 3M's capital expenditure in fiscal 2018?",
  "Did Adobe generate positive operating cash flow in FY2022?",
  "Quelles sont les principales sources de risque d'Amcor ?",
];

const Chat = () => {
  const [input, setInput] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [conversationId, setConversationId] = useState<string | undefined>(undefined);
  const [sources, setSources] = useState<{ citations: Citation[]; selected: number | null }>({
    citations: [],
    selected: null,
  });
  const endRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const navigate = useNavigate();
  const { toast } = useToast();
  const { data: user } = useSession();
  const logout = useLogout();

  const conversations = useConversations();
  const messagesQuery = useMessages(conversationId);
  const feedback = useFeedback(conversationId);
  const { pending, isStreaming, send, regenerate, stop, dismissError } = useChat({
    conversationId,
    onConversationStart: setConversationId,
  });

  const messages = useMemo(() => {
    const all = messagesQuery.data ?? [];
    // En régénération, l'ancienne réponse disparaît dès que le serveur la remplace
    const hideLast = pending?.regenerating && all.at(-1)?.role === "assistant";
    return hideLast ? all.slice(0, -1) : all;
  }, [messagesQuery.data, pending?.regenerating]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, pending?.text]);

  const submit = useCallback(
    (question: string) => {
      const trimmed = question.trim();
      if (!trimmed || isStreaming) return;
      setInput("");
      void send(trimmed);
    },
    [isStreaming, send],
  );

  const handleKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submit(input);
    }
  };

  const handleCopy = (content: string) => {
    navigator.clipboard
      .writeText(content)
      .then(() => toast({ title: "Copié", description: "La réponse est dans le presse-papiers." }))
      .catch(() => toast({ title: "Copie impossible", variant: "destructive" }));
  };

  const handleFeedback = (messageId: string, type: FeedbackType) => {
    feedback.mutate(
      { messageId, type },
      {
        onError: (error) =>
          toast({ title: "Avis non enregistré", description: errorMessage(error), variant: "destructive" }),
      },
    );
  };

  const handleNewChat = () => {
    if (isStreaming) return;
    setConversationId(undefined);
    setSidebarOpen(false);
    textareaRef.current?.focus();
  };

  const openSources = (citations: Citation[] | null | undefined, selected: number) =>
    citations?.length && setSources({ citations, selected });

  const lastAssistantId = messages.findLast((m) => m.role === "assistant")?.id;
  const showEmpty = messages.length === 0 && !pending;

  return (
    <div className="min-h-screen bg-background flex relative">
      <div className="absolute inset-0 pointer-events-none noise-overlay" />
      <div className="absolute top-0 right-0 w-[40rem] h-[40rem] bg-linear-to-b from-primary/10 to-transparent opacity-50 dark:opacity-30 blur-3xl pointer-events-none rounded-full translate-x-1/4 -translate-y-1/4" />

      <ChatSidebar
        open={sidebarOpen}
        conversations={conversations.data ?? []}
        activeId={conversationId}
        user={user}
        loading={conversations.isLoading}
        onClose={() => setSidebarOpen(false)}
        onNewChat={handleNewChat}
        onSelect={(id) => {
          if (isStreaming) return;
          setConversationId(id);
          setSidebarOpen(false);
        }}
        onLogout={() => logout.mutate(undefined, { onSettled: () => navigate("/") })}
      />

      <SourcesPanel
        citations={sources.citations}
        selected={sources.selected}
        onSelect={(selected) => setSources((state) => ({ ...state, selected }))}
        onClose={() => setSources((state) => ({ ...state, selected: null }))}
      />

      <div className="flex-1 flex flex-col min-h-screen min-w-0">
        <header className="flex items-center justify-between gap-4 px-4 lg:px-6 py-4 border-b border-border bg-background/80 backdrop-blur-xl sticky top-0 z-10">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="icon" className="lg:hidden" onClick={() => setSidebarOpen(true)} aria-label="Ouvrir le menu">
              <Menu className="w-5 h-5" />
            </Button>
            <Bot className="w-5 h-5 text-primary" />
            <span className="font-oswald font-medium">RAG Chat</span>
          </div>
          <div className="flex items-center gap-2">
            {user?.role === "admin" && (
              <Button variant="outline" size="sm" onClick={() => navigate("/admin/dashboard")}>
                Administration
              </Button>
            )}
            <ThemeToggle variant="compact" />
          </div>
        </header>

        <div className="flex-1 overflow-y-auto relative">
          <div className="max-w-3xl mx-auto p-4 lg:p-8 space-y-6 relative z-10">
            {messagesQuery.isError && (
              <QueryError error={messagesQuery.error} onRetry={() => void messagesQuery.refetch()} />
            )}

            {showEmpty && (
              <div className="text-center py-16">
                <div className="relative inline-block mb-6">
                  <div className="absolute inset-0 bg-primary/20 rounded-2xl blur-xl" />
                  <div className="relative w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center">
                    <Bot className="w-8 h-8 text-primary" />
                  </div>
                </div>
                <h2 className="text-3xl font-oswald font-medium mb-3">Comment puis-je vous aider ?</h2>
                <p className="text-muted-foreground mb-8 text-lg">
                  Posez une question sur les rapports 10-K et 10-Q indexés
                </p>
                <div className="flex flex-wrap justify-center gap-3">
                  {SUGGESTED_QUESTIONS.map((question) => (
                    <Button
                      key={question}
                      variant="outline"
                      onClick={() => {
                        setInput(question);
                        textareaRef.current?.focus();
                      }}
                      className="text-sm hover:border-primary/50 hover:bg-primary/5 transition-all"
                    >
                      {question}
                    </Button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((message) => (
              <MessageItem
                key={message.id}
                role={message.role}
                content={message.content}
                citations={message.citations}
                stopped={message.stopped}
                feedback={message.feedback}
                canRegenerate={message.id === lastAssistantId && !pending}
                onOpenSource={(n) => openSources(message.citations, n)}
                onCopy={() => handleCopy(message.content)}
                onFeedback={(type) => handleFeedback(message.id, type)}
                onRegenerate={() => void regenerate()}
              />
            ))}

            {pending && (
              <>
                {pending.question && <MessageItem role="user" content={pending.question} />}
                {pending.error ? (
                  <QueryError
                    error={new Error(pending.error)}
                    onRetry={
                      pending.question
                        ? () => {
                            const question = pending.question as string;
                            dismissError();
                            void send(question);
                          }
                        : () => {
                            dismissError();
                            void regenerate();
                          }
                    }
                  />
                ) : pending.text ? (
                  <MessageItem
                    role="assistant"
                    content={pending.text}
                    citations={pending.citations}
                    streaming
                  />
                ) : (
                  <div className="flex gap-4" role="status" aria-label="L'assistant réfléchit">
                    <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                      <Bot className="w-4 h-4 text-primary" />
                    </div>
                    <div className="chat-bubble chat-bubble-assistant flex items-center gap-2 text-muted-foreground">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span className="text-sm">Recherche dans les documents…</span>
                    </div>
                  </div>
                )}
              </>
            )}
            <div ref={endRef} />
          </div>
        </div>

        <div className="border-t border-border bg-background/80 backdrop-blur-xl sticky bottom-0 z-10">
          <div className="max-w-3xl mx-auto p-4">
            <div className="relative">
              <Textarea
                ref={textareaRef}
                value={input}
                onChange={(event) => setInput(event.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Posez votre question…"
                aria-label="Votre question"
                maxLength={2000}
                className="min-h-[60px] max-h-[200px] pr-14 resize-none bg-card border-border/50 focus:border-primary/50 transition-colors"
                rows={2}
              />
              {isStreaming ? (
                <Button
                  onClick={stop}
                  size="icon"
                  variant="secondary"
                  aria-label="Arrêter la génération"
                  className="absolute right-2 bottom-2"
                >
                  <Square className="w-4 h-4" />
                </Button>
              ) : (
                <Button
                  onClick={() => submit(input)}
                  disabled={!input.trim()}
                  size="icon"
                  aria-label="Envoyer"
                  className="absolute right-2 bottom-2 shadow-lg hover:shadow-xl transition-shadow"
                >
                  <Send className="w-4 h-4" />
                </Button>
              )}
            </div>
            <p className="text-xs text-muted-foreground text-center mt-3">
              Les réponses peuvent contenir des erreurs : vérifiez les chiffres importants dans les sources.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Chat;
