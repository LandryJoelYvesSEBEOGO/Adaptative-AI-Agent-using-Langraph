import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "./errors";
import { parseSse, streamChat } from "./stream";

const encoder = new TextEncoder();

function bodyFrom(chunks: string[]): ReadableStream<Uint8Array> {
  return new ReadableStream({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(encoder.encode(chunk));
      controller.close();
    },
  });
}

async function collect<T>(iterable: AsyncIterable<T>): Promise<T[]> {
  const items: T[] = [];
  for await (const item of iterable) items.push(item);
  return items;
}

afterEach(() => vi.unstubAllGlobals());

describe("parseSse", () => {
  it("recompose les événements coupés entre deux paquets réseau", async () => {
    const body = bodyFrom(['data: {"chunk":"Bon', 'jour"}\n\ndata: [DO', "NE]\n\n"]);
    expect(await collect(parseSse(body))).toEqual(['{"chunk":"Bonjour"}', "[DONE]"]);
  });

  it("ignore les commentaires et les lignes sans données", async () => {
    const body = bodyFrom([": keep-alive\n\n", "event: x\n\n", 'data: {"a":1}\n\n']);
    expect(await collect(parseSse(body))).toEqual(['{"a":1}']);
  });
});

describe("streamChat", () => {
  const sse = (events: unknown[]) =>
    bodyFrom([...events.map((e) => `data: ${typeof e === "string" ? e : JSON.stringify(e)}\n\n`)]);

  it("traduit le flux du serveur en événements typés", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        sse([
          { conversation_id: "c1" },
          { chunk: "Capex " },
          { chunk: "1 577 [1]" },
          { citations: [{ id: 1, source: "a.pdf", excerpt: "x" }], message_id: "m1", conversation_id: "c1" },
          "[DONE]",
        ]),
        { status: 200 },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const events = await collect(streamChat({ question: "capex ?" }));
    expect(events).toEqual([
      { type: "meta", conversationId: "c1" },
      { type: "chunk", text: "Capex " },
      { type: "chunk", text: "1 577 [1]" },
      {
        type: "done",
        citations: [{ id: 1, source: "a.pdf", excerpt: "x" }],
        messageId: "m1",
        conversationId: "c1",
      },
    ]);

    const request = fetchMock.mock.calls[0][0] as Request;
    expect(request.method).toBe("POST");
    expect(request.credentials).toBe("include");
    expect(await request.json()).toEqual({ question: "capex ?", conversation_id: null, regenerate: false });
  });

  it("signale les erreurs du pipeline sans exposer de détail technique", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(sse([{ error: "Erreur lors du traitement" }, "[DONE]"]))));
    expect(await collect(streamChat({ question: "q" }))).toEqual([
      { type: "error", message: "Erreur lors du traitement" },
    ]);
  });

  it("lève une ApiError lisible quand la requête est refusée", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: "Conversation introuvable" }), { status: 404 })),
    );
    await expect(collect(streamChat({ question: "q", conversationId: "x" }))).rejects.toMatchObject({
      name: "ApiError",
      message: "Conversation introuvable",
      status: 404,
    });
    expect(ApiError).toBeDefined();
  });

  it("ignore les fragments illisibles", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(sse(["pas du json", { chunk: "ok" }]))));
    expect(await collect(streamChat({ question: "q" }))).toEqual([{ type: "chunk", text: "ok" }]);
  });
});
