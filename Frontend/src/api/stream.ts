import { apiUrl, fetchWithRefresh } from "./client";
import { ApiError, messageFromBody, toApiError } from "./errors";
import type { Citation, StreamEvent } from "./types";

export interface StreamRequest {
  question: string;
  conversationId?: string;
  regenerate?: boolean;
}

/** Analyse un flux SSE en événements `data: …`. Ignore les fragments incomplets jusqu'à leur fin. */
export async function* parseSse(body: ReadableStream<Uint8Array>): AsyncGenerator<string> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let boundary: number;
      while ((boundary = buffer.indexOf("\n\n")) !== -1) {
        const block = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);
        const data = block
          .split("\n")
          .filter((line) => line.startsWith("data:"))
          .map((line) => line.slice(5).trimStart())
          .join("\n");
        if (data) yield data;
      }
    }
  } finally {
    reader.releaseLock();
  }
}

interface RawEvent {
  chunk?: string;
  citations?: Citation[];
  message_id?: string | null;
  conversation_id?: string;
  error?: string;
}

/**
 * Interroge le RAG en streaming. Les fragments de réponse arrivent au fil de la génération ;
 * passer un `AbortSignal` permet d'interrompre (le serveur arrête alors la génération).
 */
export async function* streamChat(
  request: StreamRequest,
  signal?: AbortSignal,
): AsyncGenerator<StreamEvent> {
  const response = await fetchWithRefresh(
    new Request(apiUrl("/api/v1/chat/query/stream"), {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      body: JSON.stringify({
        question: request.question,
        conversation_id: request.conversationId ?? null,
        regenerate: request.regenerate ?? false,
      }),
      signal,
    }),
  );
  if (!response.ok || !response.body) {
    throw toApiError(response, await response.json().catch(() => undefined));
  }

  for await (const data of parseSse(response.body)) {
    if (data === "[DONE]") return;
    let event: RawEvent;
    try {
      event = JSON.parse(data) as RawEvent;
    } catch {
      continue; // fragment illisible : ignoré
    }
    if (event.conversation_id && event.citations === undefined && event.chunk === undefined && !event.error) {
      yield { type: "meta", conversationId: event.conversation_id };
    } else if (event.error) {
      yield { type: "error", message: messageFromBody({ error: event.error }) ?? event.error };
    } else if (event.chunk !== undefined) {
      yield { type: "chunk", text: event.chunk };
    } else if (event.citations) {
      yield {
        type: "done",
        citations: event.citations,
        messageId: event.message_id ?? null,
        conversationId: event.conversation_id ?? request.conversationId ?? "",
      };
    }
  }
}

export { ApiError };
