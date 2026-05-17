import { test } from "@playwright/test";

test("capture visual qa shell", async ({ page }) => {
  await page.goto("/");
  const newMissionButton = page.getByRole("button", { name: "New Mission" });
  if (await newMissionButton.isVisible()) {
    await newMissionButton.click();
  }
  await page.getByRole("textbox").fill(
    "Visual QA mission for the cockpit shell and runtime cards."
  );
  await page.getByRole("button", { name: "Send to Hive" }).click();
  await page.locator(".bubble-agent").last().waitFor({ state: "visible", timeout: 15000 });
  await page.screenshot({ path: "test-results/visual-qa-shell.png", fullPage: true });
});
