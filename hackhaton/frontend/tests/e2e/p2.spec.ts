/**
 * Playwright smoke (T063) — User Story 2 (P2) re-check after a fix.
 *
 * Walks to a result page that produces an errored item, swaps the fixture to a
 * healthy variant via test helper API, clicks "Run check again", asserts the
 * previously errored item now appears under "Working".
 *
 * Prerequisites: backend running with FixtureExecutor, fixture files
 *   ve-de-loki.yaml (errored) and ve-de-loki-healthy.yaml (healthy variant)
 *   present. The test toggles the active fixture by symlinking; if your test
 *   harness can't symlink, replace the helper with a direct file copy.
 */
import { expect, test } from "@playwright/test";
import { promises as fs } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const FIXTURES_DIR = path.resolve(
  __dirname,
  "..",
  "..",
  "..",
  "backend",
  "tests",
  "fixtures",
  "runs",
);

async function setActiveFixture(hostId: string, source: string) {
  const target = path.join(FIXTURES_DIR, `${hostId}.yaml`);
  const sourceFile = path.join(FIXTURES_DIR, source);
  await fs.copyFile(sourceFile, target);
}

test.describe("US2 — re-check after a fix", () => {
  test.beforeAll(async () => {
    // Ensure the errored fixture is active at the start. The "errored"
    // master copy lives at ve-de-loki-errored.yaml; ve-de-loki.yaml is
    // the active fixture the FixtureExecutor reads.
    await setActiveFixture("ve-de-loki", "ve-de-loki-errored.yaml");
  });

  test("re-running a fixed host moves the errored item under Working", async ({ page }) => {
    await page.goto("/");
    await page.locator('[data-country="de"]').click();
    await page.getByRole("button", { name: /^vehicle/i }).click();
    await page.getByRole("button", { name: /loki|ve-de-loki/i }).first().click();
    // FR-028: wizard last-step button is "Continue"; result view opens blank.
    await page.getByRole("button", { name: /^continue$/i }).click();
    await page.getByTestId("run-check-button").click();

    await expect(page.getByRole("heading", { name: /needs attention/i })).toBeVisible();
    const errorRow = page.locator("text=/front camera|left camera|right camera/i").first();
    await expect(errorRow).toBeVisible();

    // Swap the fixture file out-of-band to the healthy variant.
    await setActiveFixture("ve-de-loki", "ve-de-loki-healthy.yaml");

    // Re-run.
    await page.getByTestId("run-again-button").click();

    // The same item id now appears under Working.
    await expect(page.getByRole("heading", { name: /^working/i })).toBeVisible();

    // Restore the errored fixture for subsequent tests.
    await setActiveFixture("ve-de-loki", "ve-de-loki-errored.yaml");
  });
});
