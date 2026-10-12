import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { Citation } from "@/api/types";

import CitationBadge from "./CitationBadge";
import Markdown from "./Markdown";
import SourcesPanel from "./SourcesPanel";

// pdf.js ne s'exécute pas sous jsdom : l'aperçu est simulé
vi.mock("./PdfPreview", () => ({
  default: ({ url, page }: { url: string; page: number }) => <div data-testid="pdf">{`${url}#${page}`}</div>,
}));

const citations: Citation[] = [
  {
    id: 1,
    source: "3M_2018_10K.pdf",
    excerpt: "Purchases of PP&E (1,577)",
    metadata: { page: 60, section: "Item 7 > Liquidity", company: "3M", fiscal_year: 2018, doc_type: "10-K", document_id: "doc-1" },
  },
  {
    id: 2,
    source: "https://news.example/3m",
    excerpt: "3M news",
    metadata: { is_web: true },
  },
];

describe("CitationBadge", () => {
  it("ouvre la source au clic", async () => {
    const onOpen = vi.fn();
    render(<CitationBadge number={1} citation={citations[0]} onOpen={onOpen} />);
    await userEvent.click(screen.getByRole("button", { name: /Source 1 : 3M · 2018 · 10-K · p\. 60/ }));
    expect(onOpen).toHaveBeenCalledWith(1);
  });

  it("n'est pas interactif quand la source est inconnue", () => {
    render(<CitationBadge number={9} citation={undefined} onOpen={vi.fn()} />);
    expect(screen.getByText("[9]")).toBeInTheDocument();
    expect(screen.queryByRole("button")).toBeNull();
  });

  it("s'intègre au rendu Markdown des réponses", async () => {
    const onOpen = vi.fn();
    render(
      <Markdown
        content="Capex de 1 577 [1] mais [7]."
        renderCitation={(n) => <CitationBadge number={n} citation={citations.find((c) => c.id === n)} onOpen={onOpen} />}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: /Source 1/ }));
    expect(onOpen).toHaveBeenCalledWith(1);
    expect(screen.getAllByRole("button")).toHaveLength(1); // [7] n'a pas de source
  });
});

describe("SourcesPanel", () => {
  const renderPanel = (selected: number | null, handlers = { onSelect: vi.fn(), onClose: vi.fn() }) =>
    render(<SourcesPanel citations={citations} selected={selected} {...handlers} />);

  it("reste fermé sans sélection", () => {
    renderPanel(null);
    expect(screen.queryByText("Sources")).toBeNull();
  });

  it("affiche l'extrait, l'aperçu de la bonne page et le lien vers le PDF", async () => {
    renderPanel(1);
    expect(await screen.findByText("Purchases of PP&E (1,577)")).toBeInTheDocument();
    expect(await screen.findByTestId("pdf")).toHaveTextContent("/api/v1/documents/doc-1/file#60");
    expect(screen.getByRole("link", { name: /Ouvrir le PDF à la page 60/ })).toHaveAttribute(
      "href",
      "/api/v1/documents/doc-1/file#page=60",
    );
  });

  it("propose les sources web sans aperçu PDF", async () => {
    renderPanel(2);
    expect(await screen.findByRole("link", { name: /Ouvrir la page web/ })).toHaveAttribute("href", "https://news.example/3m");
    expect(screen.queryByTestId("pdf")).toBeNull();
  });

  it("permet de changer de source depuis la liste", async () => {
    const handlers = { onSelect: vi.fn(), onClose: vi.fn() };
    renderPanel(1, handlers);
    await userEvent.click(await screen.findByRole("button", { name: /\[2\]/ }));
    expect(handlers.onSelect).toHaveBeenCalledWith(2);
  });
});
