import { expect, Page, test } from "@playwright/test";

test.describe.configure({ mode: "serial" });

function uniqueMission(label: string) {
  return `${label} ${Date.now()}-${Math.random().toString(16).slice(2, 8)}`;
}

async function openApp(page: Page) {
  const consoleErrors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") {
      consoleErrors.push(message.text());
    }
  });

  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Hive Circle Console" })).toBeVisible();

  return consoleErrors;
}

async function sendPrompt(page: Page, prompt: string) {
  await page.getByRole("textbox").fill(prompt);
  await page.getByRole("button", { name: "Send to Hive" }).click();
  await expect(page.locator(".bubble-agent").last()).toContainText(/logged a turn/i, {
    timeout: 15_000,
  });
}

test("loads the shell without hydration errors", async ({ page }) => {
  const consoleErrors = await openApp(page);

  await expect(page.getByText("Mission Control")).toBeVisible();
  await expect(page.locator(".status-pill-live")).toContainText("Backend live");
  expect(consoleErrors.filter((entry) => /hydration/i.test(entry))).toHaveLength(0);
});

test("starter prompt seeds the composer", async ({ page }) => {
  await openApp(page);

  await page.locator(".starter-card").first().click();
  await expect(page.getByRole("textbox")).toHaveValue(/Design an adaptable multi-agent traffic circle/i);
});

test("first send creates a mission and agent turn summary", async ({ page }) => {
  await openApp(page);

  const prompt = uniqueMission("First mission");
  await sendPrompt(page, prompt);

  await expect(page.locator(".bubble-user").last()).toContainText(prompt);
  await expect(page.locator(".goal-title")).toContainText("First mission");
  await expect(page.locator(".bubble-agent").last()).toContainText("Next up:");
});

test("runtime card surfaces API and contract versions", async ({ page }) => {
  await openApp(page);

  await expect(page.getByText("run-start.v2")).toBeVisible();
  await expect(page.getByText("0.3.0")).toBeVisible();
});

test("auto mode shows recommended role strategy", async ({ page }) => {
  await openApp(page);

  const prompt = uniqueMission("Auto strategy");
  await sendPrompt(page, prompt);

  await expect(page.getByText("recommended_roles")).toBeVisible();
  await expect(page.locator(".recommendation-item")).toHaveCount(3);
});

test("manual mode shows manual rotation strategy", async ({ page }) => {
  await openApp(page);

  await page.getByRole("button", { name: "Manual Circle" }).click();
  await sendPrompt(page, uniqueMission("Manual strategy"));

  await expect(page.getByText("manual_active_roles")).toBeVisible();
});

test("pass turn updates the ledger and report", async ({ page }) => {
  await openApp(page);

  await sendPrompt(page, uniqueMission("Pass turn"));
  await page.getByRole("button", { name: "Pass Turn" }).click();

  await expect(page.locator(".bubble-agent").last()).toContainText(/passed due to low confidence/i);
  await expect(page.locator(".ledger-item").first()).toContainText(/fallback|confidence|role activation/i);
});

test("ring radar shows why-now reasoning and the current role", async ({ page }) => {
  await openApp(page);

  await sendPrompt(page, uniqueMission("Radar"));
  await expect(page.getByText("Why now:")).toBeVisible();
  await expect(page.locator(".ring-core")).not.toContainText("None");
});

test("goal selector lists multiple missions", async ({ page }) => {
  await openApp(page);

  await page.request.post("http://127.0.0.1:8010/goals", {
    data: {
      title: uniqueMission("Seeded mission A"),
      success_criteria: ["Expose selector options"],
      constraints: [],
      priority: "medium",
    },
  });

  await page.request.post("http://127.0.0.1:8010/goals", {
    data: {
      title: uniqueMission("Seeded mission B"),
      success_criteria: ["Expose selector options"],
      constraints: [],
      priority: "medium",
    },
  });

  await page.reload();
  const optionCount = await page.locator(".goal-select option").count();
  expect(optionCount).toBeGreaterThanOrEqual(3);
});

test("agent artwork is visible in radar and conversation", async ({ page }) => {
  await openApp(page);

  await sendPrompt(page, uniqueMission("Artwork"));
  await expect(page.locator(".role-avatar")).toHaveCount(3);
  await expect(page.locator(".bubble-agent-id img").first()).toBeVisible();
});

test("successful runs do not surface the raw error banner", async ({ page }) => {
  await openApp(page);

  await sendPrompt(page, uniqueMission("Clean run"));
  await expect(page.locator(".error-banner")).toHaveCount(0);
});
