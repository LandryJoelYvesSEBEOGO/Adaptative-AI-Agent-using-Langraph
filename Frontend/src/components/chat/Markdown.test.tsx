import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import Markdown from "./Markdown";

describe("Markdown", () => {
  it("rend titres, gras et tableaux GFM au lieu du texte brut", () => {
    const { container } = render(
      <Markdown content={"## Capex\n\n**1 577** M$\n\n| Année | Capex |\n|---|---|\n| 2018 | 1 577 |"} />,
    );
    expect(screen.getByRole("heading", { level: 2, name: "Capex" })).toBeInTheDocument();
    expect(container.querySelector("strong")).toHaveTextContent("1 577");
    const table = screen.getByRole("table");
    expect(within(table).getAllByRole("columnheader").map((c) => c.textContent)).toEqual(["Année", "Capex"]);
    expect(within(table).getByRole("cell", { name: "1 577" })).toBeInTheDocument();
    expect(container).not.toHaveTextContent("**");
    expect(container).not.toHaveTextContent("|---|");
  });

  it("rend le code", () => {
    const { container } = render(<Markdown content={"```sql\nSELECT 1;\n```"} />);
    expect(container.querySelector("pre code")).toHaveTextContent("SELECT 1;");
  });

  it("neutralise le HTML actif et les liens javascript:", () => {
    const { container } = render(
      <Markdown
        content={
          'Voir <script>alert(1)</script><img src=x onerror="alert(2)"> et [clic](javascript:alert(3)) ' +
          'et <a href="javascript:alert(4)">piège</a> et [ok](https://example.com)'
        }
      />,
    );
    expect(container.querySelector("script")).toBeNull();
    expect(container.querySelector("img")).toBeNull();
    expect(container.innerHTML).not.toContain("onerror");
    expect(container.innerHTML).not.toContain("javascript:");
    const link = screen.getByRole("link", { name: "ok" });
    expect(link).toHaveAttribute("href", "https://example.com");
    expect(link).toHaveAttribute("rel", expect.stringContaining("noopener"));
    expect(link).toHaveAttribute("target", "_blank");
  });

  it("rend les renvois [n] en badges, sans lien cliquable parasite", () => {
    render(<Markdown content={"Capex de 1 577 [1] et [2, 3]."} />);
    expect(screen.getAllByText(/^\[\d\]$/).map((n) => n.textContent)).toEqual(["[1]", "[2]", "[3]"]);
    expect(screen.queryByRole("link")).toBeNull();
  });

  it("délègue le rendu des renvois quand renderCitation est fourni", () => {
    render(<Markdown content="Voir [2]." renderCitation={(n) => <button>source {n}</button>} />);
    expect(screen.getByRole("button", { name: "source 2" })).toBeInTheDocument();
  });
});
