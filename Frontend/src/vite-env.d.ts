/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Origine de l'API ; vide = même origine. */
  readonly VITE_API_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
