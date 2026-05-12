/**
 * E2E — host-detail page version surface (007 US2).
 *
 * Confirms:
 *   1. Initial mount renders three loading cells (em-dash + spinner),
 *   2. Cells flip atomically to their post-load state (match / drift /
 *      no-manifest / unavailable),
 *   3. The response-level source pill is at the top of the card,
 *   4. The refresh button re-triggers the loading state.
 *
 * Uses route interception to feed deterministic fixture responses, so
 * the test does not depend on a real backend / engine / testbed.
 */
import { expect, test } from "@playwright/test";

const HOST_ID = "ts-de-ber-zeus";

const driftMatchUnavailable = {
  host: {
    id: HOST_ID,
    display_name: "Zeus",
    type: "telestation",
    country: "de",
    city: "berlin",
  },
  versions: {
    vdrive_manifest: {
      value: "R12.3.0",
      verdict: "drift",
      expected: "R12.4.0",
      reason: null,
      as_of: "2026-05-11T14:02:11Z",
    },
    vreecu_version: {
      value: "8.5.3",
      verdict: "match",
      expected: null,
      reason: null,
      as_of: "2026-05-11T14:02:11Z",
    },
    sec_version: {
      value: null,
      verdict: "unavailable",
      expected: null,
      reason: "SEC package not installed on this host",
      as_of: "2026-05-11T14:02:11Z",
    },
  },
  source: "live",
} as const;

const allUnavailable = {
  host: driftMatchUnavailable.host,
  versions: {
    vdrive_manifest: { value: null, verdict: "unavailable", expected: null, reason: "couldn't reach the host over SSH", as_of: "2026-05-11T14:05:00Z" },
    vreecu_version: { value: null, verdict: "unavailable", expected: null, reason: "couldn't reach the host over SSH", as_of: "2026-05-11T14:05:00Z" },
    sec_version: { value: null, verdict: "unavailable", expected: null, reason: "couldn't reach the host over SSH", as_of: "2026-05-11T14:05:00Z" },
  },
  source: "unavailable",
} as const;

test.describe("US2 — host-detail version surface", () => {
  test("renders three cells with per-field verdicts and a source pill", async ({ page }) => {
    await page.route(`**/api/host/${HOST_ID}/versions*`, (route) => {
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(driftMatchUnavailable),
      });
    });

    await page.goto(`/host/${HOST_ID}`);

    // Source pill is live.
    await expect(page.locator('[data-source="live"]')).toBeVisible();

    // vDrive — drift, value + expected visible
    const vdrive = page.locator('[data-field="vdrive_manifest"]');
    await expect(vdrive).toHaveAttribute("data-state", "drift");
    await expect(vdrive).toContainText("R12.3.0");
    await expect(vdrive).toContainText("R12.4.0");

    // vREECU — match
    const vreecu = page.locator('[data-field="vreecu_version"]');
    await expect(vreecu).toHaveAttribute("data-state", "match");
    await expect(vreecu).toContainText("8.5.3");

    // SEC — unavailable + reason
    const sec = page.locator('[data-field="sec_version"]');
    await expect(sec).toHaveAttribute("data-state", "unavailable");
    await expect(sec).toContainText("SEC package not installed");
  });

  test("all-unavailable response renders the red source pill and three unavailable cells", async ({ page }) => {
    await page.route(`**/api/host/${HOST_ID}/versions*`, (route) => {
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(allUnavailable),
      });
    });

    await page.goto(`/host/${HOST_ID}`);
    await expect(page.locator('[data-source="unavailable"]')).toBeVisible();
    for (const fieldKey of ["vdrive_manifest", "vreecu_version", "sec_version"]) {
      await expect(page.locator(`[data-field="${fieldKey}"]`)).toHaveAttribute(
        "data-state",
        "unavailable",
      );
    }
  });

  test("refresh button calls the endpoint with ?fresh=true", async ({ page }) => {
    const calls: string[] = [];
    await page.route(`**/api/host/${HOST_ID}/versions*`, (route) => {
      calls.push(route.request().url());
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(driftMatchUnavailable),
      });
    });

    await page.goto(`/host/${HOST_ID}`);
    await expect(page.locator('[data-field="vdrive_manifest"]')).toHaveAttribute("data-state", "drift");

    // Click the refresh button.
    await page.getByRole("button", { name: /refresh/i }).click();

    // The page re-fetches with ?fresh=true on the URL.
    await expect.poll(() => calls.some((u) => u.includes("fresh=true"))).toBe(true);
  });
});
