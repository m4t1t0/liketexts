import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import Avatar from "./Avatar.vue";

describe("Avatar", () => {
  it("renders the image when an avatar URL is given", () => {
    const wrapper = mount(Avatar, {
      props: { name: "Ada Lovelace", avatarUrl: "/uploads/avatars/ada.png" },
    });
    const img = wrapper.find("img");
    expect(img.exists()).toBe(true);
    expect(img.attributes("src")).toBe("http://localhost:5000/uploads/avatars/ada.png");
    expect(img.attributes("alt")).toBe("Ada Lovelace");
  });

  it("falls back to initials when there is no avatar", () => {
    const wrapper = mount(Avatar, { props: { name: "ada lovelace" } });
    expect(wrapper.find("img").exists()).toBe(false);
    expect(wrapper.text()).toBe("A");
  });
});
