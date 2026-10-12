import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import AlertsBanner from "./AlertsBanner";

describe("AlertsBanner", () => {
  it("n'affiche rien sans alerte", () => {
    const { container } = render(<AlertsBanner alerts={[]} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("liste les alertes actives", () => {
    render(
      <AlertsBanner
        alerts={[
          { kind: "error_rate", message: "Taux d'erreur de 50 % sur 15 min" },
          { kind: "latency", message: "Latence p95 de 61,0 s sur 15 min" },
        ]}
      />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("2 alertes actives");
    expect(screen.getByText(/Taux d'erreur de 50 %/)).toBeInTheDocument();
    expect(screen.getByText(/Latence p95/)).toBeInTheDocument();
  });
});
