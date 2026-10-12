import { expect, test, type Page } from "@playwright/test";

const ADMIN = { email: "admin@example.com", password: "admin-password-123" };

async function login(page: Page, { email, password } = ADMIN) {
  await page.goto("/login");
  await page.getByLabel("Email", { exact: true }).fill(email);
  await page.getByLabel("Mot de passe", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Se connecter" }).click();
}

/** Connexion puis ouverture du chat (le compte de test est administrateur : il atterrit sur le dashboard). */
async function openChat(page: Page) {
  await login(page);
  await expect(page).toHaveURL(/\/admin\/dashboard$/);
  await page.goto("/chat");
  await expect(page.getByLabel("Votre question")).toBeVisible();
}

async function ask(page: Page, question: string) {
  await page.getByLabel("Votre question").fill(question);
  await page.getByLabel("Votre question").press("Enter");
}

test.describe("authentification", () => {
  test("une route protégée renvoie vers la connexion, puis revient après connexion", async ({ page }) => {
    await page.goto("/chat");
    await expect(page).toHaveURL(/\/login$/);
    await login(page);
    await expect(page).toHaveURL(/\/chat$/); // retour à la page demandée
    await expect(page.getByLabel("Votre question")).toBeVisible();
  });

  test("identifiants invalides : message d'erreur, pas de session", async ({ page }) => {
    await login(page, { email: ADMIN.email, password: "mauvais" });
    await expect(page.getByRole("alert")).toContainText("Email ou mot de passe incorrect");
    await expect(page).toHaveURL(/\/login$/);
  });

  test("inscription : compte créé avec le rôle utilisateur, sans accès à l'administration", async ({ page }) => {
    const email = `new-${Date.now()}@example.com`;
    await page.goto("/login?mode=register");
    await page.getByLabel("Nom", { exact: true }).fill("Nouvel Utilisateur");
    await page.getByLabel("Email", { exact: true }).fill(email);
    await page.getByLabel("Mot de passe", { exact: true }).fill("MotDePasse123");
    await page.getByRole("button", { name: "Créer mon compte" }).click();
    await expect(page).toHaveURL(/\/chat$/);
    await expect(page.getByRole("button", { name: "Administration" })).toHaveCount(0);
    await page.goto("/admin/dashboard");
    await expect(page).toHaveURL(/\/chat$/); // redirigé : pas admin
  });

  test("la session survit au rechargement et la déconnexion la termine", async ({ page }) => {
    await openChat(page);
    await page.reload();
    await expect(page.getByLabel("Votre question")).toBeVisible();
    await page.getByRole("button", { name: "Se déconnecter" }).click();
    await page.goto("/chat");
    await expect(page).toHaveURL(/\/login$/);
  });

  test("aucun jeton n'est stocké côté navigateur (cookies httpOnly)", async ({ page, context }) => {
    await openChat(page);
    const storage = await page.evaluate(() => JSON.stringify({ ...localStorage }) + JSON.stringify({ ...sessionStorage }));
    expect(storage).not.toMatch(/token|eyJ/i);
    expect(await page.evaluate(() => document.cookie)).not.toMatch(/access_token|refresh_token/);
    const cookies = await context.cookies();
    expect(cookies.filter((c) => c.name.endsWith("_token")).every((c) => c.httpOnly)).toBe(true);
  });
});

test.describe("chat", () => {
  test.beforeEach(async ({ page }) => {
    await openChat(page);
  });

  test("réponse en streaming rendue en Markdown, avec sources cliquables et aperçu du PDF", async ({ page }) => {
    await ask(page, "What was 3M's capex in 2018?");

    const answer = page.locator("[data-role=assistant] [data-testid=message-content]").last();
    await expect(answer.getByRole("heading", { name: "Capital expenditure" })).toBeVisible();
    await expect(answer.locator("strong")).toHaveText("capital expenditure");
    await expect(answer.getByRole("table")).toBeVisible();
    await expect(answer).not.toContainText("**"); // pas de Markdown brut

    const citation = answer.getByRole("button", { name: /^Source 1 : 3M · 2018 · 10-K · p\. 1/ });
    await citation.hover();
    await expect(page.getByText("PP&E purchases were 1,577 million (chunk 1)").first()).toBeVisible();

    await citation.click();
    const panel = page.getByTestId("source-detail");
    await expect(panel).toContainText("3M_2018_10K.pdf");
    await expect(panel.locator("canvas")).toBeVisible({ timeout: 20_000 }); // page PDF rendue
    await expect(panel.getByRole("link", { name: /Ouvrir le PDF à la page 1/ })).toHaveAttribute("href", /\/file#page=1$/);
  });

  test("Stop interrompt la génération, la réponse partielle est conservée après rechargement", async ({ page }) => {
    await ask(page, "Question à interrompre");
    await expect(page.locator("[data-role=assistant] [data-testid=message-content]")).toBeVisible();
    await page.getByRole("button", { name: "Arrêter la génération" }).click();
    await expect(page.getByText("Réponse interrompue")).toBeVisible();

    await page.reload();
    await page.getByRole("navigation", { name: "Historique" }).getByRole("button").first().click();
    await expect(page.getByText("Réponse interrompue")).toBeVisible();
  });

  test("Régénérer remplace la réponse sans dupliquer la question ; l'avis est conservé", async ({ page }) => {
    await ask(page, "Question à régénérer");
    await expect(page.getByRole("button", { name: "Régénérer", exact: true })).toBeVisible();
    await expect(page.locator("[data-role=assistant]")).toHaveCount(1);

    await page.getByRole("button", { name: "Régénérer", exact: true }).click();
    await expect(page.getByRole("button", { name: "Régénérer", exact: true })).toBeVisible();
    await expect(page.locator("[data-role=assistant]")).toHaveCount(1);
    await expect(page.locator("[data-role=user]")).toHaveCount(1);

    await page.getByRole("button", { name: "Réponse utile" }).click();
    await expect(page.getByRole("button", { name: "Réponse utile" })).toHaveAttribute("aria-pressed", "true");
    await page.reload();
    await page.getByRole("navigation", { name: "Historique" }).getByRole("button").first().click();
    await expect(page.getByRole("button", { name: "Réponse utile" })).toHaveAttribute("aria-pressed", "true");
  });

  test("copier la réponse", async ({ page, context }) => {
    await context.grantPermissions(["clipboard-read", "clipboard-write"]);
    await ask(page, "Question à copier");
    await page.getByRole("button", { name: "Copier", exact: true }).click();
    await expect(page.getByText("Copié")).toBeVisible();
    expect(await page.evaluate(() => navigator.clipboard.readText())).toContain("capital expenditure");
  });
});

test.describe("administration", () => {
  test("l'administrateur voit le dashboard, le corpus et les utilisateurs", async ({ page }) => {
    await login(page);
    await expect(page).toHaveURL(/\/admin\/dashboard$/);
    await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();

    await page.getByRole("link", { name: "Documents" }).click();
    await expect(page.getByRole("cell", { name: "3M_2018_10K.pdf", exact: true })).toBeVisible();
    await expect(page.getByText("Prêt", { exact: true })).toBeVisible();

    await page.getByRole("link", { name: "Utilisateurs" }).click();
    await expect(page.getByText("(vous)")).toBeVisible();
    await expect(page.getByRole("combobox", { name: `Rôle de ${ADMIN.email}` })).toBeDisabled();
  });
});
