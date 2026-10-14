import type { User } from "@/api/types";

/** Page d'accueil selon le rôle. */
export const homeFor = (user: User) => (user.role === "admin" ? "/admin/dashboard" : "/chat");
