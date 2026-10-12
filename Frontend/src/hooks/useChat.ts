import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useRef, useState } from "react";

import { errorMessage } from "@/api/errors";
import { queryKeys } from "@/api/hooks";
import { streamChat } from "@/api/stream";
import type { Citation } from "@/api/types";

/** Échange en cours de génération (pas encore relu depuis le serveur). */
export interface PendingTurn {
  /** Question affichée ; `null` en régénération (la question existe déjà dans l'historique). */
  question: string | null;
  text: string;
  citations: Citation[];
  error: string | null;
  regenerating: boolean;
}

interface UseChatOptions {
  conversationId: string | undefined;
  onConversationStart: (id: string) => void;
}

const isAbort = (error: unknown) => error instanceof DOMException && error.name === "AbortError";

/**
 * Pilote un échange avec le RAG : flux de tokens en direct, arrêt (le serveur interrompt la
 * génération et garde la réponse partielle), régénération. À la fin, l'historique est relu
 * depuis le serveur, qui reste la source de vérité.
 */
export function useChat({ conversationId, onConversationStart }: UseChatOptions) {
  const queryClient = useQueryClient();
  const [pending, setPending] = useState<PendingTurn | null>(null);
  const controller = useRef<AbortController | null>(null);

  const run = useCallback(
    async (request: { question: string; regenerate?: boolean }) => {
      if (controller.current) return; // un seul échange à la fois
      const abort = new AbortController();
      controller.current = abort;
      let activeConversation = conversationId;
      setPending({
        question: request.regenerate ? null : request.question,
        text: "",
        citations: [],
        error: null,
        regenerating: Boolean(request.regenerate),
      });

      try {
        for await (const event of streamChat(
          { question: request.question, conversationId, regenerate: request.regenerate },
          abort.signal,
        )) {
          if (event.type === "meta") {
            activeConversation = event.conversationId;
            if (event.conversationId !== conversationId) onConversationStart(event.conversationId);
          } else if (event.type === "chunk") {
            setPending((turn) => turn && { ...turn, text: turn.text + event.text });
          } else if (event.type === "done") {
            setPending((turn) => turn && { ...turn, citations: event.citations });
          } else {
            setPending((turn) => turn && { ...turn, error: event.message });
          }
        }
      } catch (error) {
        if (!isAbort(error)) {
          setPending((turn) => turn && { ...turn, error: errorMessage(error) });
          controller.current = null;
          return; // l'erreur reste affichée ; l'historique n'est pas relu
        }
      }

      controller.current = null;
      const refresh = [queryClient.invalidateQueries({ queryKey: queryKeys.conversations })];
      if (activeConversation) {
        refresh.push(
          queryClient.invalidateQueries({ queryKey: queryKeys.messages(activeConversation) }),
        );
      }
      await Promise.all(refresh);
      setPending(null);
    },
    [conversationId, onConversationStart, queryClient],
  );

  const send = useCallback((question: string) => run({ question }), [run]);
  const regenerate = useCallback(() => run({ question: "", regenerate: true }), [run]);
  const stop = useCallback(() => controller.current?.abort(), []);
  const dismissError = useCallback(() => setPending(null), []);

  return { pending, isStreaming: pending !== null && pending.error === null, send, regenerate, stop, dismissError };
}
