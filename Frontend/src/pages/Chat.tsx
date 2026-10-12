import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  Send,
  Bot,
  User,
  Loader2,
  ThumbsUp,
  ThumbsDown,
  Copy,
  RotateCcw,
  Menu,
  LogOut,
  Settings,
  MessageSquare,
  Plus,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card } from "@/components/ui/card";
import { useAuthStore } from "@/stores/authStore";
import { useToast } from "@/hooks/use-toast";
import ThemeToggle from "@/components/ThemeToggle";
import { cn } from "@/lib/utils";
import { apiClient, ApiError, Conversation, MessageDTO } from "@/services/api";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  citations?: { id: number; source: string; excerpt: string; metadata?: Record<string, any> }[];
  messageId?: string; // Pour le feedback
}

interface SuggestedQuestion {
  text: string;
}

const suggestedQuestions: SuggestedQuestion[] = [
  { text: "Comment configurer l'authentification ?" },
  { text: "Quelles sont les limites de l'API ?" },
  { text: "Comment optimiser les performances ?" },
];

const Chat = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [conversationId, setConversationId] = useState<string | undefined>(undefined);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | undefined>(undefined);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const { toast } = useToast();

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    const loadConversations = async () => {
      try {
        const data = await apiClient.listConversations();
        setConversations(data);
      } catch (error) {
        const apiError = error instanceof ApiError
          ? error
          : new ApiError(error instanceof Error ? error.message : "Impossible de charger l'historique");
        toast({
          title: "Erreur",
          description: apiError.getUserMessage(),
          variant: "destructive",
        });
      }
    };
    loadConversations();
  }, [toast]);

  const loadConversation = async (id: string) => {
    try {
      const msgs = await apiClient.listMessages(id);
      setActiveConversationId(id);
      setConversationId(id);
      setMessages(
        msgs.map((m: MessageDTO) => ({
          id: m.id,
          role: m.role === "user" ? "user" : "assistant",
          content: m.content,
          timestamp: new Date(m.created_at),
          citations: m.citations,
          messageId: m.id,
        }))
      );
    } catch (error) {
      const apiError = error instanceof ApiError
        ? error
        : new ApiError(error instanceof Error ? error.message : "Impossible de charger la conversation");
      toast({
        title: "Erreur",
        description: apiError.getUserMessage(),
        variant: "destructive",
      });
    }
  };

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    const question = input.trim();
    setInput("");
    setIsLoading(true);

    // Créer un message assistant vide pour le streaming
    const assistantMessageId = (Date.now() + 1).toString();
    const assistantMessage: Message = {
      id: assistantMessageId,
      role: "assistant",
      content: "",
      timestamp: new Date(),
      messageId: assistantMessageId,
    };

    setMessages((prev) => [...prev, assistantMessage]);

    try {
      let currentConversationId = conversationId;
      if (!currentConversationId) {
        const conv = await apiClient.createConversation(question.slice(0, 60));
        currentConversationId = conv.id;
        setConversationId(currentConversationId);
        setActiveConversationId(currentConversationId);
        setConversations((prev) => [conv, ...prev]);
      }

      // Utiliser le streaming pour une meilleure UX
      let fullResponse = "";
      let citations: Message["citations"] = [];

      await apiClient.queryRAGStream(
        question,
        currentConversationId,
        (chunk: string) => {
          fullResponse += chunk;
          // Mettre à jour le message en temps réel
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId
                ? { ...msg, content: fullResponse }
                : msg
            )
          );
          scrollToBottom();
        },
        {
          onCitations: (items) => {
            citations = items;
          }
        }
      );

      // Mettre à jour le message final avec les citations
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMessageId
            ? { ...msg, citations }
            : msg
        )
      );

      const updatedConversations = await apiClient.listConversations();
      setConversations(updatedConversations);
    } catch (error) {
      // Utiliser le système d'erreurs expressif
      const apiError = error instanceof ApiError 
        ? error 
        : new ApiError(
            error instanceof Error ? error.message : "Une erreur s'est produite",
            error instanceof ApiError ? error.status : undefined
          );
      
      const errorMessage = apiError.getUserMessage();
      
      // Afficher l'erreur dans le message
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMessageId
            ? { ...msg, content: `❌ ${errorMessage}` }
            : msg
        )
      );
      
      // Afficher un toast expressif
      toast({
        title: "Erreur lors de la requête",
        description: errorMessage,
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSuggestionClick = (question: string) => {
    setInput(question);
    textareaRef.current?.focus();
  };

  const handleCopy = (content: string) => {
    navigator.clipboard.writeText(content);
    toast({
      title: "Copié",
      description: "Le texte a été copié dans le presse-papiers",
    });
  };

  const handleFeedback = async (messageId: string, feedbackType: 'thumbs_up' | 'thumbs_down') => {
    try {
      await apiClient.submitFeedback(messageId, feedbackType);
      toast({
        title: "Merci !",
        description: "Votre avis a été enregistré",
      });
    } catch (error) {
      const errorMessage = error instanceof ApiError 
        ? error.getUserMessage() 
        : error instanceof Error 
        ? error.message 
        : "Impossible d'enregistrer votre avis";
      
      toast({
        title: "Erreur lors de l'enregistrement",
        description: errorMessage,
        variant: "destructive",
      });
    }
  };

  const handleLogout = () => {
    logout();
    navigate("/");
  };

  const handleNewChat = async () => {
    try {
      const conv = await apiClient.createConversation("Nouvelle conversation");
      setMessages([]);
      setConversationId(conv.id);
      setActiveConversationId(conv.id);
      setConversations((prev) => [conv, ...prev]);
    } catch (error) {
      const apiError = error instanceof ApiError
        ? error
        : new ApiError(error instanceof Error ? error.message : "Impossible de créer la conversation");
      toast({
        title: "Erreur",
        description: apiError.getUserMessage(),
        variant: "destructive",
      });
    }
  };

  const renderCitation = (text: string, citations?: Message["citations"]) => {
    if (!citations) return text;

    const parts = text.split(/(\[\d+\])/g);
    return parts.map((part, index) => {
      const match = part.match(/\[(\d+)\]/);
      if (match) {
        const citationId = parseInt(match[1]);
        const citation = citations.find((c) => c.id === citationId);
        if (citation) {
          const pageInfo = citation.metadata?.page ? ` (page ${citation.metadata.page})` : "";
          return (
            <button
              key={index}
              className="text-primary hover:underline font-medium mx-0.5"
              onClick={() =>
                toast({
                  title: `${citation.source}${pageInfo}`,
                  description: citation.excerpt,
                })
              }
            >
              [{citationId}]
            </button>
          );
        }
      }
      return <span key={index}>{part}</span>;
    });
  };

  return (
    <div className="min-h-screen bg-background flex relative">
      {/* Background effects inspired by template */}
      <div className="absolute inset-0 pointer-events-none opacity-40 dark:opacity-20">
        <div 
          className="absolute inset-0 mix-blend-overlay"
          style={{
            backgroundImage: "url('https://grainy-gradients.vercel.app/noise.svg')",
          }}
        />
      </div>
      <div className="absolute top-0 right-0 w-[40rem] h-[40rem] bg-gradient-to-b from-primary/10 to-transparent opacity-50 dark:opacity-30 blur-3xl pointer-events-none rounded-full translate-x-1/4 -translate-y-1/4" />
      
      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-background/80 backdrop-blur-sm z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          "fixed lg:static inset-y-0 left-0 z-50 w-72 bg-sidebar border-r border-sidebar-border flex flex-col transition-transform duration-300 lg:translate-x-0",
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        {/* Sidebar Header */}
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
                RAG Assistant
              </span>
            </div>
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="lg:hidden"
            onClick={() => setSidebarOpen(false)}
          >
            <X className="w-5 h-5" />
          </Button>
        </div>

        {/* New Chat Button */}
        <div className="p-4">
          <Button onClick={handleNewChat} className="w-full" variant="outline">
            <Plus className="w-4 h-4 mr-2" />
            Nouvelle conversation
          </Button>
        </div>

        {/* Chat History */}
        <div className="flex-1 overflow-y-auto p-4 space-y-2">
          <p className="text-xs font-space uppercase tracking-widest text-muted-foreground mb-3">
            Historique
          </p>
          {conversations.length === 0 ? (
            <p className="text-sm text-muted-foreground">Aucune conversation</p>
          ) : (
            conversations.map((conversation) => (
              <button
                key={conversation.id}
                onClick={() => loadConversation(conversation.id)}
                className={cn(
                  "w-full text-left p-3 rounded-lg hover:bg-sidebar-accent transition-colors group",
                  activeConversationId === conversation.id && "bg-sidebar-accent"
                )}
              >
                <div className="flex items-center gap-3">
                  <MessageSquare className="w-4 h-4 text-muted-foreground group-hover:text-foreground" />
                  <span className="text-sm truncate">
                    {conversation.title || "Conversation"}
                  </span>
                </div>
              </button>
            ))
          )}
        </div>

        {/* User section */}
        <div className="p-4 border-t border-sidebar-border">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center">
              <span className="text-sm font-medium text-primary">
                {user?.name.charAt(0).toUpperCase()}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">{user?.name}</p>
              <p className="text-xs text-muted-foreground truncate">{user?.email}</p>
            </div>
          </div>
          <div className="flex gap-2">
            <Button variant="ghost" size="sm" className="flex-1">
              <Settings className="w-4 h-4 mr-2" />
              Paramètres
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleLogout}
              className="text-muted-foreground hover:text-destructive"
            >
              <LogOut className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </aside>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col min-h-screen">
        {/* Mobile Header */}
        <header className="lg:hidden flex items-center justify-between gap-4 p-4 border-b border-border bg-background/80 backdrop-blur-xl sticky top-0 z-10">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="icon" onClick={() => setSidebarOpen(true)}>
              <Menu className="w-5 h-5" />
            </Button>
            <div className="flex items-center gap-2">
              <Bot className="w-5 h-5 text-primary" />
              <span className="font-oswald font-medium">RAG Chat</span>
            </div>
          </div>
          <ThemeToggle variant="compact" />
        </header>
        
        {/* Desktop Header */}
        <header className="hidden lg:flex items-center justify-between px-6 py-4 border-b border-border bg-background/80 backdrop-blur-xl sticky top-0 z-10">
          <div className="flex items-center gap-2">
            <Bot className="w-5 h-5 text-primary" />
            <span className="font-oswald font-medium">RAG Chat</span>
          </div>
          <ThemeToggle variant="compact" />
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto relative">
          {/* Background effects for messages area */}
          <div className="absolute inset-0 pointer-events-none opacity-30 dark:opacity-10">
            <div 
              className="absolute inset-0"
              style={{
                backgroundImage: "url('https://grainy-gradients.vercel.app/noise.svg')",
              }}
            />
          </div>
          <div className="max-w-3xl mx-auto p-4 lg:p-8 space-y-6 relative z-10">
            {messages.length === 0 ? (
              <div className="text-center py-16">
                <div className="relative inline-block mb-6">
                  <div className="absolute inset-0 bg-primary/20 rounded-2xl blur-xl" />
                  <div className="relative w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center">
                    <Bot className="w-8 h-8 text-primary" />
                  </div>
                </div>
                <h2 className="text-3xl font-oswald font-medium mb-3">
                  Comment puis-je vous aider ?
                </h2>
                <p className="text-muted-foreground mb-8 text-lg">
                  Posez une question sur notre documentation ou nos produits
                </p>
                <div className="flex flex-wrap justify-center gap-3">
                  {suggestedQuestions.map((q, i) => (
                    <Button
                      key={i}
                      variant="outline"
                      onClick={() => handleSuggestionClick(q.text)}
                      className="text-sm hover:border-primary/50 hover:bg-primary/5 transition-all"
                    >
                      {q.text}
                    </Button>
                  ))}
                </div>
              </div>
            ) : (
              messages.map((message) => (
                <div
                  key={message.id}
                  className={cn(
                    "flex gap-4",
                    message.role === "user" ? "justify-end" : "justify-start"
                  )}
                >
                  {message.role === "assistant" && (
                    <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                      <Bot className="w-4 h-4 text-primary" />
                    </div>
                  )}
                  <div
                    className={cn(
                      "chat-bubble relative group",
                      message.role === "user"
                        ? "chat-bubble-user"
                        : "chat-bubble-assistant"
                    )}
                  >
                    {/* Subtle gradient effect for assistant messages */}
                    {message.role === "assistant" && (
                      <div className="absolute inset-0 bg-gradient-to-br from-primary/5 to-transparent rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none" />
                    )}
                    <div className="whitespace-pre-wrap">
                      {message.role === "assistant"
                        ? renderCitation(message.content, message.citations)
                        : message.content}
                    </div>
                    {message.role === "assistant" && (
                      <div className="flex items-center gap-2 mt-4 pt-3 border-t border-border/50">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-8 px-2 text-muted-foreground hover:text-foreground"
                          onClick={() => handleCopy(message.content)}
                        >
                          <Copy className="w-3.5 h-3.5 mr-1.5" />
                          Copier
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-8 px-2 text-muted-foreground hover:text-success"
                          onClick={() => message.messageId && handleFeedback(message.messageId, 'thumbs_up')}
                        >
                          <ThumbsUp className="w-3.5 h-3.5" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-8 px-2 text-muted-foreground hover:text-destructive"
                          onClick={() => message.messageId && handleFeedback(message.messageId, 'thumbs_down')}
                        >
                          <ThumbsDown className="w-3.5 h-3.5" />
                        </Button>
                      </div>
                    )}
                  </div>
                  {message.role === "user" && (
                    <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center shrink-0">
                      <User className="w-4 h-4 text-primary-foreground" />
                    </div>
                  )}
                </div>
              ))
            )}
            {isLoading && (
              <div className="flex gap-4">
                <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                  <Bot className="w-4 h-4 text-primary" />
                </div>
                <Card className="p-4">
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span className="text-sm">L'assistant écrit...</span>
                  </div>
                </Card>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Input Area with enhanced styling */}
        <div className="border-t border-border bg-background/80 backdrop-blur-xl sticky bottom-0 z-10">
          <div className="max-w-3xl mx-auto p-4">
            <div className="relative">
              <div className="absolute inset-0 bg-gradient-to-t from-background to-transparent pointer-events-none" />
              <Textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Posez votre question..."
                className="min-h-[60px] max-h-[200px] pr-14 resize-none bg-card border-border/50 focus:border-primary/50 transition-colors"
                rows={2}
              />
              <Button
                onClick={handleSend}
                disabled={!input.trim() || isLoading}
                size="icon"
                className="absolute right-2 bottom-2 shadow-lg hover:shadow-xl transition-shadow"
              >
                {isLoading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Send className="w-4 h-4" />
                )}
              </Button>
            </div>
            <p className="text-xs text-muted-foreground text-center mt-3">
              RAG System peut faire des erreurs. Vérifiez les informations importantes.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Chat;