import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { AdminUser, DocumentInfo, User } from "@/api/types";

import AdminDocuments from "./AdminDocuments";
import AdminUsers from "./AdminUsers";

const endpoints = vi.hoisted(() => ({
  listDocuments: vi.fn(),
  uploadDocument: vi.fn(),
  reindexDocument: vi.fn(),
  deleteDocument: vi.fn(),
  listUsers: vi.fn(),
  updateUserRole: vi.fn(),
  deleteUser: vi.fn(),
  fetchSession: vi.fn(),
  login: vi.fn(),
  register: vi.fn(),
  logout: vi.fn(),
}));
vi.mock("@/api/endpoints", () => endpoints);

const wrap = (ui: ReactNode) =>
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      {ui}
    </QueryClientProvider>,
  );

const doc = (over: Partial<DocumentInfo>): DocumentInfo => ({
  id: "d1",
  filename: "3M_2018_10K.pdf",
  company: "3M",
  fiscal_year: 2018,
  doc_type: "10-K",
  status: "ready",
  pages: 120,
  chunk_count: 340,
  error: null,
  created_at: "2026-10-12T10:00:00Z",
  updated_at: "2026-10-12T10:00:00Z",
  ...over,
});

beforeEach(() => {
  for (const mock of Object.values(endpoints)) mock.mockReset();
});

describe("AdminDocuments", () => {
  it("liste le corpus avec statuts, totaux et erreur d'indexation", async () => {
    endpoints.listDocuments.mockResolvedValue([
      doc({}),
      doc({ id: "d2", filename: "scan.pdf", company: null, status: "failed", error: "aucun texte extractible", pages: null, chunk_count: null }),
    ]);
    wrap(<AdminDocuments />);
    expect(await screen.findByText("3M_2018_10K.pdf")).toBeInTheDocument();
    expect(screen.getByText("Prêt")).toBeInTheDocument();
    expect(screen.getByText("Échec")).toBeInTheDocument();
    expect(screen.getByText("aucun texte extractible")).toBeInTheDocument();
    expect(screen.getByText("340 passages indexés")).toBeInTheDocument();
  });

  it("téléverse les PDF choisis puis relit la liste", async () => {
    endpoints.listDocuments.mockResolvedValue([]);
    endpoints.uploadDocument.mockResolvedValue(doc({ status: "pending" }));
    wrap(<AdminDocuments />);
    await screen.findByText(/Aucun document/);

    const file = new File(["%PDF-1.4"], "ADOBE_2022_10K.pdf", { type: "application/pdf" });
    await userEvent.upload(screen.getByLabelText("Fichiers PDF"), file);

    await waitFor(() => expect(endpoints.uploadDocument).toHaveBeenCalledWith(file, undefined));
    await waitFor(() => expect(endpoints.listDocuments.mock.calls.length).toBeGreaterThanOrEqual(2));
  });

  it("demande confirmation avant de supprimer", async () => {
    endpoints.listDocuments.mockResolvedValue([doc({})]);
    endpoints.deleteDocument.mockResolvedValue(undefined);
    wrap(<AdminDocuments />);

    await userEvent.click(await screen.findByRole("button", { name: "Supprimer 3M_2018_10K.pdf" }));
    expect(endpoints.deleteDocument).not.toHaveBeenCalled();
    const dialog = await screen.findByRole("alertdialog");
    await userEvent.click(within(dialog).getByRole("button", { name: "Supprimer" }));
    await waitFor(() => expect(endpoints.deleteDocument).toHaveBeenCalledWith("d1"));
  });

  it("réindexe un document", async () => {
    endpoints.listDocuments.mockResolvedValue([doc({})]);
    endpoints.reindexDocument.mockResolvedValue(doc({ status: "pending" }));
    wrap(<AdminDocuments />);
    await userEvent.click(await screen.findByRole("button", { name: "Réindexer 3M_2018_10K.pdf" }));
    await waitFor(() => expect(endpoints.reindexDocument).toHaveBeenCalledWith("d1"));
  });
});

const me: User = { id: "u1", email: "boss@example.com", name: "Boss", role: "admin" };
const user = (over: Partial<AdminUser>): AdminUser => ({
  id: "u2",
  email: "alice@example.com",
  name: "Alice",
  role: "user",
  created_at: "2026-10-01T09:00:00Z",
  conversations: 3,
  requests: 12,
  last_activity: "2026-10-12T08:00:00Z",
  ...over,
});

describe("AdminUsers", () => {
  beforeEach(() => {
    endpoints.fetchSession.mockResolvedValue(me);
    endpoints.listUsers.mockResolvedValue([user({ id: "u1", email: me.email, name: "Boss", role: "admin" }), user({})]);
  });

  it("affiche l'activité et empêche d'agir sur son propre compte", async () => {
    wrap(<AdminUsers />);
    expect(await screen.findByText("alice@example.com")).toBeInTheDocument();
    expect(screen.getByText("(vous)")).toBeInTheDocument();
    const rows = screen.getAllByRole("row");
    const aliceRow = rows.find((row) => within(row).queryByText("alice@example.com"))!;
    expect(within(aliceRow).getAllByRole("cell").map((cell) => cell.textContent)).toEqual(
      expect.arrayContaining(["3", "12"]),
    );
    const selfRow = rows.find((row) => within(row).queryByText("(vous)"))!;
    expect(within(selfRow).getByRole("button", { name: "Supprimer" })).toBeDisabled();
    expect(within(selfRow).getByRole("combobox")).toBeDisabled();
  });

  it("supprime un compte après confirmation", async () => {
    endpoints.deleteUser.mockResolvedValue(undefined);
    wrap(<AdminUsers />);
    const aliceRow = (await screen.findByText("alice@example.com")).closest("tr")!;
    await userEvent.click(within(aliceRow).getByRole("button", { name: "Supprimer" }));
    const dialog = await screen.findByRole("alertdialog");
    expect(dialog).toHaveTextContent("alice@example.com");
    await userEvent.click(within(dialog).getByRole("button", { name: "Supprimer" }));
    await waitFor(() => expect(endpoints.deleteUser).toHaveBeenCalledWith("u2"));
  });

  it("montre l'erreur de chargement avec relance", async () => {
    endpoints.listUsers.mockReset();
    endpoints.listUsers.mockRejectedValueOnce(new Error("boom")).mockResolvedValue([user({})]);
    wrap(<AdminUsers />);
    expect(await screen.findByRole("alert")).toHaveTextContent("boom");
    await userEvent.click(screen.getByRole("button", { name: "Réessayer" }));
    expect(await screen.findByText("alice@example.com")).toBeInTheDocument();
  });
});
