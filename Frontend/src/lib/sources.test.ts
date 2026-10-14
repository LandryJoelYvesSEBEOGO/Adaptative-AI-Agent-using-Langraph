import { describe, expect, it } from "vitest";

import type { Citation } from "@/api/types";

import { byNumber, citationLabel, citationMeta, documentUrl } from "./sources";

const pdf: Citation = {
  id: 1,
  source: "3M_2018_10K.pdf",
  excerpt: "PP&E (1,577)",
  metadata: {
    page: 60,
    section: "Item 7 > Liquidity",
    company: "3M",
    fiscal_year: 2018,
    doc_type: "10-K",
    document_id: "doc-1",
    is_web: false,
  },
};
const web: Citation = {
  id: 2,
  source: "https://news.example/3m",
  excerpt: "3M news",
  metadata: { is_web: true },
};

describe("sources", () => {
  it("lit les métadonnées typées", () => {
    expect(citationMeta(pdf)).toMatchObject({ page: 60, company: "3M", fiscalYear: 2018, documentId: "doc-1" });
    expect(citationMeta({ id: 3, source: "x", excerpt: "" })).toMatchObject({ page: null, isWeb: false });
  });

  it("construit un libellé lisible", () => {
    expect(citationLabel(pdf)).toBe("3M · 2018 · 10-K · p. 60");
    expect(citationLabel(web)).toBe("https://news.example/3m");
    expect(citationLabel({ id: 4, source: "autre.pdf", excerpt: "" })).toBe("autre.pdf");
  });

  it("donne l'URL du PDF via l'API, ou l'URL d'une source web", () => {
    expect(documentUrl(pdf)).toBe("/api/v1/documents/doc-1/file");
    expect(documentUrl(web)).toBe("https://news.example/3m");
    expect(documentUrl({ id: 5, source: "x.pdf", excerpt: "" })).toBeNull();
  });

  it("indexe les citations par numéro", () => {
    expect(byNumber([pdf, web]).get(2)).toBe(web);
    expect(byNumber(null).size).toBe(0);
  });
});
