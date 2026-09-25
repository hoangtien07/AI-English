const splitList = (value?: string) =>
  value
    ? value
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean)
    : [];

const trimTrailingSlash = (url: string) => url.replace(/\/+$/, "");
const stripApiV1 = (url: string) => trimTrailingSlash(url).replace(/\/api\/v1$/, "");
const DEFAULT_API_URL = "http://127.0.0.1:8000/api/v1";

const env = (import.meta.env.VITE_ENV as string) || "development";
const configuredBackendUrl = import.meta.env.VITE_BACKEND_URL as string | undefined;
const configuredAiUrl = import.meta.env.VITE_AI_URL as string | undefined;

if (env === "production" && (!configuredBackendUrl || !configuredAiUrl)) {
  throw new Error("Production requires explicit VITE_BACKEND_URL and VITE_AI_URL values.");
}

const assertProductionUrl = (name: string, value?: string) => {
  if (env !== "production" || !value) return;
  let parsed: URL;
  try {
    parsed = new URL(value);
  } catch {
    throw new Error(`${name} must be a valid absolute URL.`);
  }
  if (parsed.protocol !== "https:") {
    throw new Error(`${name} must use HTTPS in production.`);
  }
  if (["localhost", "127.0.0.1", "0.0.0.0", "::1"].includes(parsed.hostname)) {
    throw new Error(`${name} cannot use a loopback host in production.`);
  }
};

assertProductionUrl("VITE_BACKEND_URL", configuredBackendUrl);
assertProductionUrl("VITE_AI_URL", configuredAiUrl);

const backendUrl = trimTrailingSlash(configuredBackendUrl || DEFAULT_API_URL);
const aiUrl = trimTrailingSlash(configuredAiUrl || "http://127.0.0.1:8001/api/v1");
const useGateway = ((import.meta.env.VITE_USE_GATEWAY as string) || "false").toLowerCase() === "true";
const gatewayBase = stripApiV1(backendUrl);

export const ENV = {
  /** "development" | "production" */
  env,
  isDev:  env === "development",
  isProd: env === "production",

  /** Backend primary URL — local (dev) hoặc Render.com (prod) */
  backendUrl,
  /** Backend fallback URL — thử khi primary không reach được */
  backendUrlFallback: (import.meta.env.VITE_BACKEND_URL_FALLBACK as string) || "",

  /** AI service primary URL */
  aiUrl,
  /** AI service fallback URL */
  aiUrlFallback: (import.meta.env.VITE_AI_URL_FALLBACK as string) || "",

  /** Kong/API Gateway mode */
  useGateway,
  /** Gateway API key for protected routes */
  apiKey: (import.meta.env.VITE_API_KEY as string) || "",
  /**
   * AI-service admin operations (topics, model config) are proxied through
   * backend-service's own JWT-gated routes — the ai-service admin key is
   * injected there, server-side, and never shipped to the browser.
   */
  aiAdminUrl: `${backendUrl}/admin/ai-proxy`,

  /** Health endpoints differ between direct services and gateway */
  backendHealthUrl: useGateway ? `${gatewayBase}/backend-health` : `${stripApiV1(backendUrl)}/health`,
  aiHealthUrl: useGateway ? `${gatewayBase}/ai-health` : `${stripApiV1(aiUrl)}/health`,

  googleClientId:   (import.meta.env.VITE_GOOGLE_CLIENT_ID as string) || "",
  adminEmails:      splitList(import.meta.env.VITE_ADMIN_EMAILS as string | undefined),
  superAdminEmails: splitList(import.meta.env.VITE_SUPER_ADMIN_EMAILS as string | undefined),
};
