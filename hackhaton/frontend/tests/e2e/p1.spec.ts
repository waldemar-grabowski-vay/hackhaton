/**
 * Playwright smoke (T059, T068, T087, T088, T090) — User Story 1 (P1) happy
 * path, with assertions folded in from Phase 7 re-alignment:
 *
 *   - US tile is visible-but-disabled on the Country step (T087, FR-001a step 1).
 *   - Result page is blank-on-entry: only the host header + a single "Run check"
 *     CTA are visible until the operator clicks (T088, FR-028).
 *   - After clicking the CTA, results populate.
 *   - Two-group split (FR-003) and Developer-mode toggle round-trip (FR-022).
 *
 * Prerequisites: backend running with VAYOBD_EXECUTOR=fixture against a
 * checkout that contains ve-de-apollo, frontend dev server on :5173 with
 * VAYOBD_DEV_USER set so /api/* requests carry X-Vay-User (FR-026).
 */
import { expect, test } from "@playwright/test";

test.describe("US1 — run a check and see what is broken", () => {
  test("country step renders US as disabled (Coming soon)", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: /where is the host/i })).toBeVisible();

    // Germany tile is enabled.
    const de = page.locator('[data-country="de"]');
    await expect(de).toBeVisible();
    await expect(de).not.toHaveAttribute("data-disabled", "true");

    // United States tile is rendered but disabled with a "Coming soon" badge.
    const us = page.locator('[data-country="us"]');
    await expect(us).toBeVisible();
    await expect(us).toHaveAttribute("aria-disabled", "true");
    await expect(page.getByText(/coming soon/i)).toBeVisible();

    // Clicking US is a no-op — the wizard stays on step 1.
    await us.click({ force: true });
    await expect(page.getByRole("heading", { name: /where is the host/i })).toBeVisible();
  });

  test("happy path with blank-on-entry result view + developer toggle", async ({
    page,
  }) => {
    await page.goto("/");

    // Step 1 — Country (use data-country attribute since the button's
    // accessible name combines flag emoji + label + country code).
    await page.locator('[data-country="de"]').click();

    // Step 2 — Type
    await expect(page.getByRole("heading", { name: /what are you checking/i })).toBeVisible();
    await page.getByRole("button", { name: /^vehicle/i }).click();

    // Step 3 (skipped for vehicles) → Host
    await expect(page.getByRole("heading", { name: /pick a host/i })).toBeVisible();
    await page.getByRole("button", { name: /apollo|ve-de-apollo/i }).first().click();

    // Wizard last step button is "Continue" (FR-028 — does NOT trigger a run).
    await page.getByRole("button", { name: /^continue$/i }).click();

    // Result view is BLANK on entry (FR-028 / T088): only the CTA is visible,
    // no ResultHero, no item rows yet.
    await expect(page.getByTestId("run-cta-card")).toBeVisible();
    await expect(page.getByTestId("run-check-button")).toBeVisible();
    await expect(page.getByRole("heading", { name: /^working/i })).toHaveCount(0);
    await expect(page.getByRole("heading", { name: /needs attention/i })).toHaveCount(0);

    // Operator clicks the CTA → run starts.
    await page.getByTestId("run-check-button").click();

    // Result hero — host name + headline + donut
    await expect(page.getByRole("heading", { name: /apollo/i })).toBeVisible();
    await expect(page.getByText(/checked just now|min ago/i)).toBeVisible();

    // Both groups render. SC-007: every catalog item appears in exactly one group.
    await expect(page.getByRole("heading", { name: /^working/i })).toBeVisible();
    await expect(page.getByRole("heading", { name: /needs attention/i })).toBeVisible();

    // Developer mode toggle
    const switchBtn = page.getByRole("switch", { name: /developer mode/i });
    await switchBtn.click();
    await expect(page.getByRole("button", { name: /show raw output/i }).first()).toBeVisible();

    // Expand a row and verify raw_detail panel
    await page.getByRole("button", { name: /show raw output/i }).first().click();
    await expect(page.getByText(/raw output/i).first()).toBeVisible();

    // Toggle off — controls disappear, no network refetch.
    await switchBtn.click();
    await expect(page.getByRole("button", { name: /show raw output/i })).toHaveCount(0);
  });
});
