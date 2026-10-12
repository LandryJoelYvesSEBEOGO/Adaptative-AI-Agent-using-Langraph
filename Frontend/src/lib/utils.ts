import { clsx, type ClassValue } from "clsx";
import { extendTailwindMerge } from "tailwind-merge";

// Les ombres personnalisées (voir index.css, --shadow-*) doivent être reconnues comme des
// utilitaires `shadow` pour que `cn("shadow-xs", "shadow-soft-lg")` garde la dernière.
const twMerge = extendTailwindMerge({
  extend: {
    classGroups: {
      shadow: [{ shadow: ["soft", "soft-lg", "glow", "glow-lg"] }],
    },
  },
});

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
