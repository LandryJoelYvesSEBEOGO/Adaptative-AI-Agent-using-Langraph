import { type QueryClient, useQueryClient } from "@tanstack/react-query";
import { useCallback, useRef, useState } from "react";

import { errorMessage } from "@/api/errors";
import { listMessages } from "@/api/endpoints";
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
  /** Interrompu par l'utilisateur : le texte partiel reste affiché le temps que le serveur l'enregistre. */
  stopped: boolean;
}

interface UseChatOptions {
  conversationId: string | undefined;
  onConversationStart: (id: string) => void;
}

/** Relit l'historique jusqu'à ce que la dernière réponse de l'assistant soit enregistrée. */
async function waitForAssistantMessage(
  queryClient: QueryClient,
  conversationId: string,
  attempts = 10,
  delayMs = 300,
) {
  for (let attempt = 0; attempt < attempts; attempt++) {
    await new Promise((resolve) => setTimeout(resolve, delayMs));
    const messages = await queryClient
      .fetchQuery({
        queryKey: queryKeys.messages(conversationId),
        queryFn: () => listMessages(conversationId),
        staleTime: 0,
      })
      .catch(() => undefined);
    if (messages?.at(-1)?.role === "assistant") return;
  }
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
      let failed = false;
      setPending({
        question: request.regenerate ? null : request.question,
        text: "",
        citations: [],
        error: null,
        regenerating: Boolean(request.regenerate),
        stopped: false,
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
            failed = true;
            setPending((turn) => turn && { ...turn, error: event.message });
          }
        }
      } catch (error) {
        if (!isAbort(error)) {
          setPending((turn) => turn && { ...turn, error: errorMessage(error) });
          controller.current = null;
          return; // l'erreur reste affichée ; l'historique n'est pas relu
        }
        // Stop : le serveur détecte la coupure puis enregistre la réponse partielle (quelques
        // centaines de ms). On garde le texte affiché jusqu'à ce qu'il apparaisse dans l'historique.
        setPending((turn) => turn && { ...turn, stopped: true });
        if (activeConversation) await waitForAssistantMessage(queryClient, activeConversation);
      }

      controller.current = null;
      if (failed) return; // l'erreur reste affichée avec « Réessayer »
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

  const busy = pending !== null && pending.error === null;
  return {
    pending,
    /** Un échange est en cours (génération, ou attente de l'enregistrement après Stop). */
    busy,
    /** La génération est en cours : le bouton Stop est utile. */
    isStreaming: busy && !pending.stopped,
    send,
    regenerate,
    stop,
    dismissError,
  };
}
