/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL?: string;
  readonly VITE_API_PROXY?: string;
  /** Absolute API origin for WebSockets when VITE_API_URL is relative (e.g. https://jobai-three.vercel.app). */
  readonly VITE_API_ORIGIN?: string;
  /** Full realtime endpoint (ws/wss or http/https), e.g. wss://jobai-three.vercel.app/api/v1/ws */
  readonly VITE_WS_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
