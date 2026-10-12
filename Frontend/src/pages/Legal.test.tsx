import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { LegalNotice, PrivacyPolicy } from "./Legal";

describe("pages légales", () => {
  it("affichent les mentions légales avec les champs à compléter signalés", () => {
    render(<MemoryRouter><LegalNotice /></MemoryRouter>);
    expect(screen.getByRole("heading", { level: 1, name: "Mentions légales" })).toBeTruthy();
    expect(screen.getAllByText(/À COMPLÉTER/).length).toBeGreaterThan(0);
  });

  it("décrivent les données, les sous-traitants et les droits", () => {
    render(<MemoryRouter><PrivacyPolicy /></MemoryRouter>);
    expect(screen.getByRole("heading", { name: "Données collectées et finalités" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Destinataires et sous-traitants" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Vos droits" })).toBeTruthy();
  });
});
