import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { clearApiToken, getApiToken } from "../lib/auth";

const TOKEN_STORAGE_KEY = "lessoncanvas_workspace_token";

function guestTokenResponse(token: string) {
  return Promise.resolve({
    ok: true,
    status: 201,
    json: async () => ({ token, subject: `guest-${token}` }),
  });
}

beforeEach(() => {
  window.localStorage.clear();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("getApiToken / clearApiToken (browser workspace token)", () => {
  it("returns the stored token without touching the network", async () => {
    window.localStorage.setItem(TOKEN_STORAGE_KEY, "stored-token");
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    await expect(getApiToken()).resolves.toBe("stored-token");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("issues and stores a guest token when none is stored", async () => {
    const fetchMock = vi.fn().mockReturnValue(guestTokenResponse("minted-token"));
    vi.stubGlobal("fetch", fetchMock);

    await expect(getApiToken()).resolves.toBe("minted-token");
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/auth/guest-token"),
      expect.objectContaining({ method: "POST" }),
    );
    expect(window.localStorage.getItem(TOKEN_STORAGE_KEY)).toBe("minted-token");

    // The next call reuses the stored token; no second issuance.
    await expect(getApiToken()).resolves.toBe("minted-token");
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("shares one issuance among concurrent callers so queries stay in one workspace", async () => {
    let resolveFetch!: (value: Awaited<ReturnType<typeof guestTokenResponse>>) => void;
    const fetchMock = vi.fn().mockReturnValue(
      new Promise((resolve) => {
        resolveFetch = resolve;
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const first = getApiToken();
    const second = getApiToken();
    resolveFetch(await guestTokenResponse("shared-token"));

    await expect(first).resolves.toBe("shared-token");
    await expect(second).resolves.toBe("shared-token");
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("throws when issuance fails and leaves no token stored", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: false, status: 503, json: async () => ({}) }),
    );

    await expect(getApiToken()).rejects.toThrow();
    expect(window.localStorage.getItem(TOKEN_STORAGE_KEY)).toBeNull();
  });

  it("clearApiToken removes the stored token so the next call re-issues", async () => {
    window.localStorage.setItem(TOKEN_STORAGE_KEY, "old-token");
    vi.stubGlobal("fetch", vi.fn().mockReturnValue(guestTokenResponse("next-token")));

    clearApiToken();
    expect(window.localStorage.getItem(TOKEN_STORAGE_KEY)).toBeNull();
    await expect(getApiToken()).resolves.toBe("next-token");
  });
});
