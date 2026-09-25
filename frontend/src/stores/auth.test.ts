import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { useAuthStore } from "./auth";
import { setToken } from "../api/client";

vi.mock("../api/client", async (importOriginal) => {
  const mod = await importOriginal<typeof import("../api/client")>();
  return {
    ...mod,
    api: {
      login: vi.fn(),
      register: vi.fn(),
      me: vi.fn(),
      updateProfile: vi.fn(),
      uploadAvatar: vi.fn(),
    },
    getToken: vi.fn(() => null),
    setToken: vi.fn(),
  };
});

const TOKEN = {
  access_token: "abc",
  refresh_token: "ref",
  expires_in: 900,
  token_type: "Bearer",
};

const PROFILE = {
  id: "u1",
  email: "a@example.com",
  display_name: "A",
  first_name: null,
  last_name: null,
  avatar_url: null,
  created_at: new Date().toISOString(),
  is_writer: false,
  is_reader: false,
};
const loginMock = vi.mocked((await import("../api/client")).api.login);
const meMock = vi.mocked((await import("../api/client")).api.me);

beforeEach(() => {
  setActivePinia(createPinia());
  vi.clearAllMocks();
  localStorage.clear();
});

describe("useAuthStore", () => {
  it("login stores the token and loads the profile", async () => {
    loginMock.mockResolvedValue(TOKEN);
    meMock.mockResolvedValue(PROFILE);

    const auth = useAuthStore();
    expect(auth.isLoggedIn).toBe(false);
    await auth.login("a@example.com", "secret");

    expect(loginMock).toHaveBeenCalledWith("a@example.com", "secret");
    expect(setToken).toHaveBeenCalledWith("abc");
    expect(auth.token).toBe("abc");
    expect(auth.profile?.email).toBe("a@example.com");
    expect(auth.isLoggedIn).toBe(true);
  });

  it("logout clears token and profile", async () => {
    loginMock.mockResolvedValue(TOKEN);
    meMock.mockResolvedValue(PROFILE);

    const auth = useAuthStore();
    await auth.login("a@example.com", "secret");
    auth.logout();

    expect(setToken).toHaveBeenCalledWith(null);
    expect(auth.token).toBeNull();
    expect(auth.profile).toBeNull();
    expect(auth.isLoggedIn).toBe(false);
  });
});
