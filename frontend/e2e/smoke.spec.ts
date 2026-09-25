import { expect, test } from "@playwright/test";

/**
 * Smoke suite — hermetic by design. All API traffic is stubbed with
 * page.route so these run with only `npm run dev`, no backend needed.
 */
test("home loads the Substack-style hero and cookie banner", async ({ page }) => {
  await page.route("**/api/v1/**", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: "{}" }),
  );
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /get paid for the work/i })).toBeVisible();
  await expect(page.getByText("Explore writers")).toBeVisible();
  await expect(page.getByText("Cookie policy")).toBeVisible();
});

test("logged-out /reader redirects to login with ?next=", async ({ page }) => {
  await page.goto("/reader");
  await expect(page).toHaveURL(/\/login\?next=\/reader/);
  await expect(page.getByRole("heading", { name: "Login" })).toBeVisible();
  await expect(page.getByPlaceholder("Email")).toBeVisible();
});

test("failed login surfaces the API error", async ({ page }) => {
  await page.route("**/api/v1/auth/login", (route) =>
    route.fulfill({
      status: 401,
      contentType: "application/json",
      body: JSON.stringify({ message: "Invalid credentials" }),
    }),
  );
  await page.goto("/login");
  await page.getByPlaceholder("Email").fill("nope@example.com");
  await page.getByPlaceholder("Password").fill("wrong");
  await page.getByRole("button", { name: "Login" }).click();
  await expect(page.getByText("Invalid credentials")).toBeVisible();
});

test("paywalled post shows the subscriber banner", async ({ page }) => {
  await page.route("**/api/v1/posts/abc*", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "abc",
        writer_id: "w1",
        title: "A paywalled essay",
        preview_content: "Free intro…",
        status: "published",
        published_at: new Date().toISOString(),
        created_at: new Date().toISOString(),
        subscriber_content: null,
        has_full_access: false,
        writer_name: "Ada",
        writer_avatar_url: null,
      }),
    }),
  );
  await page.goto("/posts/abc");
  await expect(page.getByRole("heading", { name: "A paywalled essay" })).toBeVisible();
  await expect(page.getByText("This post continues for subscribers.")).toBeVisible();
  await expect(page.getByRole("link", { name: /reader dashboard/i })).toBeVisible();
});
