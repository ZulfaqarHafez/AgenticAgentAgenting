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
  const previousAgentCount = await page.locator(".bubble-agent").count();
  await page.getByRole("textbox").fill(prompt);
  await page.getByRole("button", { name: "Send to Hive" }).click();
  await expect(page.locator(".bubble-agent")).toHaveCount(previousAgentCount + 1, {
    timeout: 15_000,
  });
  await expect(page.locator(".bubble-agent").last()).toContainText(
    /Mission frame|Signals|Proof check|Implementation move|Contrarian read/i
  );
}

async function resetToFreshMission(page: Page) {
  const newMissionButton = page.getByRole("button", { name: "New Mission" });
  if ((await newMissionButton.count()) > 0) {
    await newMissionButton.click();
    await expect(page.getByRole("heading", { name: "No mission active yet" })).toBeVisible();
    return;
  }

  const selector = page.locator(".goal-select");
  if ((await selector.count()) > 0 && (await selector.isEnabled())) {
    await selector.selectOption("");
  }
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

test("new mission action clears the console for a fresh run", async ({ page }) => {
  await openApp(page);

  await sendPrompt(page, uniqueMission("Reset mission"));
  await page.getByRole("button", { name: "New Mission" }).click();

  await expect(page.getByRole("heading", { name: "No mission active yet" })).toBeVisible();
  await expect(page.locator(".bubble-agent")).toHaveCount(0);
  await expect(page.locator(".bubble-system")).toHaveCount(1);
});

test("first send creates a mission and differentiated specialist output", async ({ page }) => {
  await openApp(page);
  await resetToFreshMission(page);

  const prompt = uniqueMission("First mission");
  await sendPrompt(page, prompt);

  await expect(page.locator(".bubble-user").last()).toContainText(prompt);
  await expect(page.locator(".goal-title")).toContainText("First mission");
  await expect(page.locator(".bubble-agent").last()).toContainText(
    /Routing decision:|Open gap:|Decision: baton should move to|Delivery handoff:|Counter-move:/i
  );
});

test("runtime card surfaces API and contract versions", async ({ page }) => {
  await openApp(page);

  await expect(page.getByText("run-start.v2")).toBeVisible();
  await expect(page.getByText("0.3.0")).toBeVisible();
});

test("auto mode shows recommended role strategy", async ({ page }) => {
  await openApp(page);
  await resetToFreshMission(page);

  const prompt = uniqueMission("Auto strategy");
  await sendPrompt(page, prompt);

  await expect(page.locator("strong").filter({ hasText: "recommended_roles" }).first()).toBeVisible();
  await expect(page.locator(".recommendation-item")).toHaveCount(3);
});

test("manual mode shows manual rotation strategy", async ({ page }) => {
  await openApp(page);
  await resetToFreshMission(page);

  await page.getByRole("button", { name: "Manual Circle" }).click();
  await sendPrompt(page, uniqueMission("Manual strategy"));

  await expect(page.locator("strong").filter({ hasText: "manual_active_roles" }).first()).toBeVisible();
});

test("pass turn updates the ledger and report", async ({ page }) => {
  await openApp(page);
  await resetToFreshMission(page);

  await sendPrompt(page, uniqueMission("Pass turn"));
  await page.getByRole("button", { name: "Pass Turn" }).click();

  await expect(page.locator(".bubble-agent").last()).toContainText(/passed due to low confidence/i);
  await expect(page.locator(".ledger-item").first()).toContainText(/fallback|confidence|role activation/i);
});

test("ring radar shows why-now reasoning and the current role", async ({ page }) => {
  await openApp(page);
  await resetToFreshMission(page);

  await sendPrompt(page, uniqueMission("Radar"));
  await expect(page.getByText("Why now:")).toBeVisible();
  await expect(page.locator(".ring-core")).not.toContainText("None");
});

test("goal selector lists multiple missions", async ({ page }) => {
  await openApp(page);
  const missionA = uniqueMission("Seeded mission A");
  const missionB = uniqueMission("Seeded mission B");

  await page.request.post("http://127.0.0.1:8010/goals", {
    data: {
      title: missionA,
      success_criteria: ["Expose selector options"],
      constraints: [],
      priority: "medium",
    },
  });

  await page.request.post("http://127.0.0.1:8010/goals", {
    data: {
      title: missionB,
      success_criteria: ["Expose selector options"],
      constraints: [],
      priority: "medium",
    },
  });

  await page.reload();
  await expect(page.locator(".goal-select option").filter({ hasText: missionA })).toHaveCount(1);
  await expect(page.locator(".goal-select option").filter({ hasText: missionB })).toHaveCount(1);
});

test("agent artwork is visible in radar and conversation", async ({ page }) => {
  await openApp(page);
  await resetToFreshMission(page);

  await sendPrompt(page, uniqueMission("Artwork"));
  await expect(page.locator(".role-avatar")).toHaveCount(3);
  await expect(page.locator(".bubble-agent-id img").first()).toBeVisible();
});

test("successful runs do not surface the raw error banner", async ({ page }) => {
  await openApp(page);
  await resetToFreshMission(page);

  await sendPrompt(page, uniqueMission("Clean run"));
  await expect(page.locator(".error-banner")).toHaveCount(0);
});

test("component runtime card shows subsystem states", async ({ page }) => {
  await openApp(page);

  await expect(page.getByText("Component Runtime")).toBeVisible();
  await expect(page.locator(".runtime-part")).toHaveCount(5);
  await expect(
    page.locator(".runtime-part strong").filter({ hasText: "Goal Engine" }).first()
  ).toBeVisible();
  await expect(
    page.locator(".runtime-part strong").filter({ hasText: "Proof Gate" }).first()
  ).toBeVisible();
});

test("proof gate starts blocked and then unlocks completion", async ({ page }) => {
  await openApp(page);
  await resetToFreshMission(page);

  await sendPrompt(page, uniqueMission("Proof planner"));
  await expect(page.getByText("blocked").first()).toBeVisible();

  await sendPrompt(page, uniqueMission("Proof research"));
  await sendPrompt(page, uniqueMission("Proof verifier"));

  await expect(page.locator(".mini-badge-good").filter({ hasText: "ready" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Complete Run" })).toBeEnabled();
});

test("run completion updates status after proof gate clears", async ({ page }) => {
  await openApp(page);
  await resetToFreshMission(page);

  await sendPrompt(page, uniqueMission("Complete planner"));
  await sendPrompt(page, uniqueMission("Complete research"));
  await sendPrompt(page, uniqueMission("Complete verifier"));
  await page.getByRole("button", { name: "Complete Run" }).click();

  await expect(page.locator(".composer-status strong")).toContainText("Run completed");
  await expect(
    page.locator(".mission-facts .fact-pill strong").filter({ hasText: "completed" }).first()
  ).toBeVisible();
});

test("run history and replay timeline show persisted turns", async ({ page }) => {
  await openApp(page);
  await resetToFreshMission(page);

  await sendPrompt(page, uniqueMission("History planner"));
  await sendPrompt(page, uniqueMission("History research"));

  await expect(page.getByText("Run History")).toBeVisible();
  const historyButtons = page.locator(".history-button");
  await expect(historyButtons.first()).toBeVisible();
  await expect(page.getByText("Replay Timeline")).toBeVisible();
  await expect(page.locator(".replay-item")).toHaveCount(2);
});
