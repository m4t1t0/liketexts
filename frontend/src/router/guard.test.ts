import { beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import router from "./index";

beforeEach(async () => {
  localStorage.clear();
  setActivePinia(createPinia());
  await router.replace("/");
});

describe("auth guard", () => {
  it("marks reader/writer/profile routes as requiring auth", () => {
    for (const name of ["reader", "writer", "profile"]) {
      expect(router.resolve({ name }).meta.requiresAuth).toBe(true);
    }
    expect(router.resolve({ name: "home" }).meta.requiresAuth).toBeFalsy();
  });

  it("redirects logged-out users to login with ?next=", async () => {
    await router.push("/reader");
    expect(router.currentRoute.value.name).toBe("login");
    expect(router.currentRoute.value.query.next).toBe("/reader");
  });

  it("lets logged-in users through", async () => {
    localStorage.setItem("paperlet_token", "tok");
    await router.push("/reader");
    expect(router.currentRoute.value.name).toBe("reader");
  });
});
