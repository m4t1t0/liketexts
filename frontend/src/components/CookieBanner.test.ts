import { beforeEach, describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import CookieBanner from "./CookieBanner.vue";

const KEY = "paperlet_cookie_consent";

function mountBanner() {
  return mount(CookieBanner, {
    global: {
      stubs: { RouterLink: { template: "<a><slot /></a>" } },
    },
  });
}

beforeEach(() => {
  localStorage.clear();
});

describe("CookieBanner", () => {
  it("shows the banner when no consent is stored", () => {
    const wrapper = mountBanner();
    expect(wrapper.text()).toContain("Cookie policy");
  });

  it("hides after Accept and persists the choice", async () => {
    const wrapper = mountBanner();
    await wrapper.findAll("button")[2].trigger("click");
    expect(JSON.parse(localStorage.getItem(KEY) ?? "")).toEqual({
      choice: "accepted",
      analytics: true,
    });
    expect(wrapper.html()).not.toContain("Cookie policy");
  });

  it("opens preferences via Manage and saves a custom choice", async () => {
    const wrapper = mountBanner();
    await wrapper.findAll("button")[0].trigger("click");
    expect(wrapper.text()).toContain("Cookie preferences");
    await wrapper.find("button").trigger("click");
    expect(JSON.parse(localStorage.getItem(KEY) ?? "").choice).toBe("custom");
  });
});
