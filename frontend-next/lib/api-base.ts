const DEFAULT_API_BASE_URL = "http://localhost:5000/api";

export function getApiBaseUrl(): string {
  const configured =
    process.env.NEXT_API_BASE_URL ||
    process.env.NEXT_PUBLIC_API_BASE_URL ||
    DEFAULT_API_BASE_URL;
  return configured.replace(/\/+$/, "");
}
