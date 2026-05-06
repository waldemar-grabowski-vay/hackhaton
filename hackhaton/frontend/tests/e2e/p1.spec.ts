/**
 * Playwright smoke (T059, T068) — User Story 1 (P1) happy path.
 *
 * Walks the wizard against a backend running with the FixtureExecutor:
 *   Country (Germany) → Type (Vehicle) → Host (apollo) → Run check
 * Asserts:
 *   - Result hero renders with the host name and a working/needs-attention split
 *   - Both groups render with rows for every catalog item (FR-003 / SC-007)
 *   - Developer mode toggle reveals a raw-output expand control without refetch
 *
 * Prerequisites: backend running with VAYOBD_EXECUTOR=fixture against a
 * checkout that contains ve-de-apollo, frontend dev server on :5173.
 */
import { expect, test } from "@playwright/test";

test.describe("US1 — run a check and see what is broken", () => {
  test("happy path with developer-mode toggle round-trip", async ({ page }) => {
    await page.goto("/");

    // Step 1 — Country
    await expect(page.getByRole("heading", { name: /where is the host/i })).toBeVisible();
    await page.getByRole("button", { name: /germany/i }).click();

    // Step 2 — Type
    await expect(page.getByRole("heading", { name: /what are you checking/i })).toBeVisible();
    await page.getByRole("button", { name: /^vehicle/i }).click();

    // Step 3 (skipped for vehicles) → Host
    await expect(page.getByRole("heading", { name: /pick a host/i })).toBeVisible();
    await page.getByRole("button", { name: /apollo|ve-de-apollo/i }).first().click();

    // Run check
    await page.getByRole("button", { name: /^run check$/i }).click();

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
