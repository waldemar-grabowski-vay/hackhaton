/**
 * E2E — TS_diag entry-point dual visibility (007 US1, FR-001).
 *
 * Confirms the "Live diagnostic" button appears in both the header
 * and the picker's primary-action area when Developer mode is on,
 * and disappears from both when Developer mode is off. The toggle
 * is the source of truth (localStorage-backed `useDeveloperMode`);
 * the backend's `settings.developer_mode` is not consulted.
 *
 * Prerequisites: backend running on http://localhost:8000 (or fixture
 * mode), frontend dev server on :5173 with VAYOBD_DEV_USER set so
 * /api/* requests carry X-Vay-User.
 */
import { expect, test } from "@playwright/test";

test.describe("US1 — Live diagnostic entry points", () => {
  test.beforeEach(async ({ context }) => {
    // Start each test with developer mode OFF.
    await context.addInitScript(() => {
      window.localStorage.removeItem("vayobd.developerMode.v1");
    });
  });

  test("developer-mode OFF: neither entry point is visible", async ({ page }) => {
    await page.goto("/");
    // Wait for the picker to render so we're past any loading state.
    await expect(page.getByRole("heading", { name: /where is the host/i })).toBeVisible();

    const liveLinks = page.getByRole("link", { name: /live diagnostic/i });
    await expect(liveLinks).toHaveCount(0);
  });

  test("developer-mode ON: header entry point is visible from the picker", async ({
    page,
  }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: /where is the host/i })).toBeVisible();

    // Toggle Developer mode on via the header switch.
    await page.getByRole("switch", { name: /toggle developer mode/i }).click();

    // Header copy is now visible.
    const liveLinks = page.getByRole("link", { name: /live diagnostic/i });
    await expect(liveLinks.first()).toBeVisible();
  });

  test("developer-mode ON + picker on host step: both entry points visible", async ({
    page,
  }) => {
    await page.goto("/");

    // Toggle Developer mode on.
    await page.getByRole("switch", { name: /toggle developer mode/i }).click();

    // Walk the wizard until the host step (the only step where the main-page
    // copy renders).
    await page.locator('[data-country="de"]').click();
    // Step 2 — pick telestation or vehicle (either works; the test only needs
    // to land on the host step).
    await page.getByRole("button", { name: /^vehicle$/i }).click();
    await expect(page.getByRole("heading", { name: /pick a host/i })).toBeVisible();

    // Both copies are now in the DOM — header (sticky top) and main (next to
    // Continue button).
    const liveLinks = page.getByRole("link", { name: /live diagnostic/i });
    await expect(liveLinks).toHaveCount(2);
  });

  test("toggle off again: both entry points disappear in lockstep", async ({ page }) => {
    await page.goto("/");

    // Turn on, walk to host step, confirm 2 buttons.
    await page.getByRole("switch", { name: /toggle developer mode/i }).click();
    await page.locator('[data-country="de"]').click();
    await page.getByRole("button", { name: /^vehicle$/i }).click();
    await expect(page.getByRole("heading", { name: /pick a host/i })).toBeVisible();
    const liveLinks = page.getByRole("link", { name: /live diagnostic/i });
    await expect(liveLinks).toHaveCount(2);

    // Turn off.
    await page.getByRole("switch", { name: /toggle developer mode/i }).click();
    await expect(liveLinks).toHaveCount(0);
  });

  test("header copy stays reachable from /live itself", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("switch", { name: /toggle developer mode/i }).click();

    // Click the header button to navigate to /live.
    await page.getByRole("link", { name: /live diagnostic/i }).first().click();
    await expect(page).toHaveURL(/\/live$/);

    // The header copy is still visible from /live (FR-001 acceptance #4).
    await expect(page.getByRole("link", { name: /live diagnostic/i })).toBeVisible();
  });
});
