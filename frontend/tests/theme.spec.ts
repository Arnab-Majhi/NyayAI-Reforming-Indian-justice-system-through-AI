import { test, expect, type Page } from "@playwright/test";

const theme = (page: Page) => page.getByRole("combobox", { name: "Color theme", exact: true });

test("native theme dropdown options have contrasting backgrounds in both themes", async ({ page }) => {
  await page.goto("/");
  for (const [mode, background, foreground] of [
    ["dark", "rgb(20, 32, 51)", "rgb(219, 229, 242)"],
    ["light", "rgb(255, 255, 255)", "rgb(30, 41, 59)"],
  ]) {
    await theme(page).selectOption(mode);
    await expect(theme(page)).toHaveCSS("background-color", background);
    for (const option of await theme(page).locator("option").all()) {
      await expect(option).toHaveCSS("background-color", background);
      await expect(option).toHaveCSS("color", foreground);
    }
  }
  await theme(page).focus();
  await page.keyboard.press("d");
  await page.keyboard.press("Enter");
  await expect(theme(page)).toHaveValue("dark");
});

test("theme follows system, persists explicit choice, and syncs between tabs", async ({ page, context }) => {
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  page.on("console", message => { if (message.type() === "error" && /hydrat/i.test(message.text())) errors.push(message.text()); });
  await page.emulateMedia({ colorScheme: "dark" });
  await page.goto("/");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await expect(theme(page)).toHaveValue("system");
  await page.emulateMedia({ colorScheme: "light" });
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await theme(page).selectOption("dark");
  await expect(page.locator("body")).toHaveCSS("background-color", "rgb(11, 18, 32)");
  await page.reload();
  await expect(theme(page)).toHaveValue("dark");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  const second = await context.newPage();
  await second.goto("/");
  await expect(theme(second)).toHaveValue("dark");
  await theme(page).selectOption("light");
  await expect(theme(second)).toHaveValue("light");
  await expect(second.locator("html")).toHaveAttribute("data-theme", "light");
  await page.emulateMedia({ colorScheme: "dark" });
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await theme(page).selectOption("system");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await second.close();
  expect(errors).toEqual([]);
});

test("saved theme applies before hydration and blocked storage is safe", async ({ browser, baseURL }) => {
  const context = await browser.newContext({ colorScheme: "light", baseURL });
  const page = await context.newPage();
  await page.goto("/");
  await theme(page).selectOption("dark");
  // Block all client bundles on a fresh page; only the head bootstrap can apply
  // the saved preference. This verifies the pre-hydration path, not an effect.
  const early = await context.newPage();
  await early.route("**/_next/static/**/*.js", route => route.abort());
  await early.goto("/");
  await expect(early.locator("html")).toHaveAttribute("data-theme", "dark");
  await context.close();

  const blocked = await browser.newContext({ colorScheme: "dark", baseURL });
  await blocked.addInitScript(() => {
    Storage.prototype.getItem = () => { throw new DOMException("Blocked", "SecurityError"); };
    Storage.prototype.setItem = () => { throw new DOMException("Blocked", "SecurityError"); };
  });
  const restricted = await blocked.newPage();
  const errors: string[] = [];
  restricted.on("pageerror", e => errors.push(e.message));
  await restricted.goto("/");
  await expect(restricted.locator("html")).toHaveAttribute("data-theme", "dark");
  await theme(restricted).selectOption("light");
  await expect(restricted.locator("html")).toHaveAttribute("data-theme", "light");
  expect(errors).toEqual([]);
  await blocked.close();
});

test("dark mode covers staff modules, chart tooltip, mobile and light printing", async ({ page }, testInfo) => {
  const errors: string[] = [];
  page.on("pageerror", e => errors.push(e.message));
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  await theme(page).selectOption("dark");
  await page.screenshot({ path: testInfo.outputPath("dark-landing.png"), fullPage: true });
  await page.goto("/workspace");
  await expect(theme(page)).toHaveValue("dark");
  await expect(page.locator(".auth-card")).toHaveCSS("background-color", "rgb(20, 32, 51)");
  await page.getByLabel("Demo account").selectOption("staff-1");
  await page.getByRole("button", { name: "Enter demo workspace" }).click();
  await expect(page.getByRole("heading", { name: "Registry snapshot" })).toBeVisible();
  await expect(page.locator(".panel").first()).toHaveCSS("background-color", "rgb(20, 32, 51)");
  await page.locator(".recharts-bar-rectangle").first().hover();
  await expect(page.locator(".recharts-default-tooltip").first()).toBeVisible();
  await expect(page.locator(".recharts-default-tooltip").first()).toHaveCSS("background-color", "rgb(20, 32, 51)");
  await page.mouse.move(0, 0);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.getByRole("button", { name: "Dismiss notification" }).click();
  await page.screenshot({ path: testInfo.outputPath("dark-dashboard.png"), fullPage: true });
  for (const [label, heading] of [
    ["Smart Case Management", "Smart Case Management"], ["Legal Research", "Legal Research"],
    ["Filing Assistant", "Filing Assistant"], ["Citizen Legal Assistant", "Citizen Legal Assistant"],
    ["Predictive Analysis", "Predictive Analysis"], ["Decision Support", "Decision Support"],
  ]) {
    await page.getByRole("link", { name: label, exact: true }).click();
    await expect(page.getByRole("heading", { name: heading, exact: true, level: 1 })).toBeVisible();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  }
  await expect(page.getByLabel("Claimant / prosecution allegations")).not.toBeEmpty();
  await expect(page.getByLabel("Claimant / prosecution allegations")).toHaveCSS("background-color", "rgb(20, 32, 51)");
  await page.emulateMedia({ media: "print" });
  await expect(page.locator("body")).toHaveCSS("background-color", "rgb(255, 255, 255)");
  await expect(page.locator(".panel").first()).toHaveCSS("color", "rgb(30, 41, 59)");
  await page.emulateMedia({ media: "screen" });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(theme(page)).toBeVisible();
  await theme(page).selectOption("light");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await theme(page).selectOption("dark");
  await page.getByRole("button", { name: "Toggle navigation" }).click();
  await page.getByRole("link", { name: "Overview", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Registry snapshot" })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)).toBe(false);
  await page.screenshot({ path: testInfo.outputPath("dark-mobile.png"), fullPage: true });
  expect(errors).toEqual([]);
});