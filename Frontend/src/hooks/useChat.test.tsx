import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { StreamEvent } from "@/api/types";

import { useChat } from "./useChat";

const streamChat = vi.hoisted(() => vi.fn());
const listMessages = vi.hoisted(() => vi.fn());
vi.mock("@/api/stream", () => ({ streamChat }));
vi.mock("@/api/endpoints", () => ({ listMessages }));

const wrapper = ({ children }: { children: ReactNode }) => (
  <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
    {children}
  </QueryClientProvider>
);

async function* events(...items: StreamEvent[]) {
  for (const item of items) yield item;
}

const DONE: StreamEvent = { type: "done", citations: [], messageId: "m1", conversationId: "c1" };

beforeEach(() => {
  streamChat.mockReset();
  listMessages.mockReset();
});

describe("useChat", () => {
  it("accumule les tokens, annonce la conversation puis libère l'état", async () => {
    streamChat.mockReturnValue(
      events(
        { type: "meta", conversationId: "c1" },
        { type: "chunk", text: "Capex " },
        { type: "chunk", text: "1 577" },
        DONE,
      ),
    );
    const onConversationStart = vi.fn();
    const { result } = renderHook(() => useChat({ conversationId: undefined, onConversationStart }), { wrapper });

    await act(async () => {
      await result.current.send("capex ?");
    });

    expect(onConversationStart).toHaveBeenCalledWith("c1");
    expect(streamChat).toHaveBeenCalledWith(
      { question: "capex ?", conversationId: undefined, regenerate: undefined },
      expect.any(AbortSignal),
    );
    expect(result.current.pending).toBeNull(); // l'historique serveur prend le relais
    expect(result.current.busy).toBe(false);
  });

  it("montre le texte au fil du flux et refuse un second échange simultané", async () => {
    let release: () => void = () => {};
    const gate = new Promise<void>((resolve) => (release = resolve));
    streamChat.mockImplementation(async function* () {
      yield { type: "chunk", text: "début" } satisfies StreamEvent;
      await gate;
      yield DONE;
    });
    const { result } = renderHook(() => useChat({ conversationId: "c1", onConversationStart: vi.fn() }), { wrapper });

    let first: Promise<void> = Promise.resolve();
    act(() => {
      first = result.current.send("q1");
    });
    await waitFor(() => expect(result.current.pending?.text).toBe("début"));
    expect(result.current.isStreaming).toBe(true);
    expect(result.current.pending?.question).toBe("q1");

    await act(async () => {
      await result.current.send("q2"); // ignoré : un échange est déjà en cours
    });
    expect(streamChat).toHaveBeenCalledTimes(1);

    await act(async () => {
      release();
      await first;
    });
    expect(result.current.pending).toBeNull();
  });

  it("Stop : garde le texte partiel jusqu'à ce que le serveur l'ait enregistré", async () => {
    streamChat.mockImplementation(async function* (_request, signal: AbortSignal) {
      yield { type: "meta", conversationId: "c1" } satisfies StreamEvent;
      yield { type: "chunk", text: "partiel" } satisfies StreamEvent;
      await new Promise((_resolve, reject) =>
        signal.addEventListener("abort", () => reject(new DOMException("aborted", "AbortError"))),
      );
    });
    // le serveur n'a pas encore enregistré la réponse au 1er sondage, puis oui
    listMessages
      .mockResolvedValueOnce([{ id: "u", role: "user" }])
      .mockResolvedValue([{ id: "u", role: "user" }, { id: "a", role: "assistant" }]);

    const { result } = renderHook(() => useChat({ conversationId: undefined, onConversationStart: vi.fn() }), { wrapper });
    let run: Promise<void> = Promise.resolve();
    act(() => {
      run = result.current.send("q");
    });
    await waitFor(() => expect(result.current.pending?.text).toBe("partiel"));

    act(() => result.current.stop());
    await waitFor(() => expect(result.current.pending?.stopped).toBe(true));
    expect(result.current.pending?.text).toBe("partiel"); // toujours affiché
    expect(result.current.isStreaming).toBe(false);
    expect(result.current.busy).toBe(true); // pas de nouvel échange tant que ce n'est pas enregistré

    await act(async () => {
      await run;
    });
    expect(listMessages.mock.calls.length).toBeGreaterThanOrEqual(2);
    expect(result.current.pending).toBeNull();
  });

  it("garde l'erreur affichée, sans relire l'historique, et autorise un nouvel essai", async () => {
    streamChat.mockImplementationOnce(async function* () {
      yield { type: "error", message: "Erreur lors du traitement" } satisfies StreamEvent;
    });
    const { result } = renderHook(() => useChat({ conversationId: "c1", onConversationStart: vi.fn() }), { wrapper });

    await act(async () => {
      await result.current.send("q");
    });
    expect(result.current.pending?.error).toBe("Erreur lors du traitement");
    expect(result.current.busy).toBe(false);

    streamChat.mockReturnValueOnce(events(DONE));
    await act(async () => {
      await result.current.send("q bis");
    });
    expect(streamChat).toHaveBeenCalledTimes(2);
    expect(result.current.pending).toBeNull();
  });

  it("transforme une panne réseau en message lisible", async () => {
    streamChat.mockImplementationOnce(() => ({
      [Symbol.asyncIterator]() {
        return { next: () => Promise.reject(new TypeError("Failed to fetch")) };
      },
    }));
    const { result } = renderHook(() => useChat({ conversationId: "c1", onConversationStart: vi.fn() }), { wrapper });
    await act(async () => {
      await result.current.send("q");
    });
    expect(result.current.pending?.error).toMatch(/joindre le serveur/);
  });

  it("régénérer : n'affiche pas de nouvelle question", async () => {
    streamChat.mockReturnValue(events(DONE));
    const { result } = renderHook(() => useChat({ conversationId: "c1", onConversationStart: vi.fn() }), { wrapper });
    await act(async () => {
      await result.current.regenerate();
    });
    expect(streamChat).toHaveBeenCalledWith(
      { question: "", conversationId: "c1", regenerate: true },
      expect.any(AbortSignal),
    );
  });
});
