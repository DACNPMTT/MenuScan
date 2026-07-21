/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL?: string
  readonly VITE_API_V1_PREFIX?: string
  readonly VITE_GOOGLE_MAPS_EMBED_KEY?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
