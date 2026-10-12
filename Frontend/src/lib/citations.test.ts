import { describe, expect, it } from "vitest";

import { citationNumber, linkCitations } from "./citations";

describe("linkCitations", () => {
  it("transforme [1] en lien interne", () => {
    expect(linkCitations("Capex 1 577 [1].")).toBe("Capex 1 577 [\\[1\\]](cite:1).");
  });

  it("gère les listes [1, 3]", () => {
    expect(linkCitations("vu [1, 3]")).toBe("vu [\\[1\\]](cite:1)[\\[3\\]](cite:3)");
  });

  it("ne touche ni au code ni aux liens markdown existants", () => {
    const text = "`a[1]` et ```\nx[2]\n``` et [lien](http://x.io) et [3]: ref";
    expect(linkCitations(text)).toBe(text);
  });
});

describe("citationNumber", () => {
  it("lit uniquement les liens cite:N valides", () => {
    expect(citationNumber("cite:4")).toBe(4);
    expect(citationNumber("cite:abc")).toBeNull();
    expect(citationNumber("cite:0")).toBeNull();
    expect(citationNumber("https://x.io")).toBeNull();
    expect(citationNumber(undefined)).toBeNull();
  });
});
