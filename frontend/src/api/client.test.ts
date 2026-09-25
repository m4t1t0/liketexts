import { beforeEach, describe, expect, it } from "vitest";
import { ApiError, getToken, resolveAvatarUrl, setToken } from "./client";

beforeEach(() => {
  localStorage.clear();
});

describe("resolveAvatarUrl", () => {
  it("returns null for empty values", () => {
    expect(resolveAvatarUrl(null)).toBeNull();
    expect(resolveAvatarUrl(undefined)).toBeNull();
    expect(resolveAvatarUrl("")).toBeNull();
  });

  it("passes absolute and preview URLs through", () => {
    expect(resolveAvatarUrl("https://cdn.example/a.png")).toBe("https://cdn.example/a.png");
    expect(resolveAvatarUrl("http://cdn.example/a.png")).toBe("http://cdn.example/a.png");
    expect(resolveAvatarUrl("blob:abc")).toBe("blob:abc");
    expect(resolveAvatarUrl("data:image/png;base64,xx")).toBe("data:image/png;base64,xx");
  });

  it("resolves backend-relative paths against the API origin", () => {
    expect(resolveAvatarUrl("/uploads/avatars/x.png")).toBe(
      "http://localhost:5000/uploads/avatars/x.png",
    );
    expect(resolveAvatarUrl("uploads/avatars/x.png")).toBe(
      "http://localhost:5000/uploads/avatars/x.png",
    );
  });
});

describe("token storage", () => {
  it("round-trips set/get and clears on null", () => {
    expect(getToken()).toBeNull();
    setToken("tok123");
    expect(getToken()).toBe("tok123");
    setToken(null);
    expect(getToken()).toBeNull();
  });
});

describe("ApiError", () => {
  it("carries status, message and code", () => {
    const err = new ApiError(401, "bad credentials", "UNAUTHORIZED");
    expect(err).toBeInstanceOf(Error);
    expect(err.status).toBe(401);
    expect(err.message).toBe("bad credentials");
    expect(err.code).toBe("UNAUTHORIZED");
  });
});
