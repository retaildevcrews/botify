/// <reference types="vite/client" />

interface ImportMetaEnv {
    readonly VITE_BACKEND_API_ENDPOINT_PREFIX: string
    readonly VITE_TOKEN_SERVICE_PREFIX: string
    readonly VITE_SPEECH_VOICE_NAME: string
    // more env variables...
  }

  interface ImportMeta {
    readonly env: ImportMetaEnv
  }
