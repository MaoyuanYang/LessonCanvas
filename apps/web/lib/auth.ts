// ADR-0006: browser-scoped guest workspace token (no managed identity).
//
// The workspace identity is a JWT minted by POST /auth/guest-token and kept in
// localStorage under this key. Clearing browser data yields a fresh, blank
// workspace; deleting the workspace data happens through the account flow.
import { requestGuestToken } from "@/lib/api";

const TOKEN_STORAGE_KEY = "lessoncanvas_workspace_token";

let pendingToken: Promise<string> | null = null;

function readStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_STORAGE_KEY);
}

/**
 * Returns the browser workspace token, minting and storing one on first use.
 * Concurrent callers share a single mint request so simultaneous queries never
 * fan out into different workspaces. Throws when issuance fails.
 */
export async function getApiToken(): Promise<string> {
  const stored = readStoredToken();
  if (stored) return stored;

  if (!pendingToken) {
    pendingToken = requestGuestToken()
      .then(({ token }) => {
        window.localStorage.setItem(TOKEN_STORAGE_KEY, token);
        return token;
      })
      .finally(() => {
        pendingToken = null;
      });
  }
  return pendingToken;
}

/** Removes the stored workspace token (the browser then gets a fresh workspace). */
export function clearApiToken(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(TOKEN_STORAGE_KEY);
}
