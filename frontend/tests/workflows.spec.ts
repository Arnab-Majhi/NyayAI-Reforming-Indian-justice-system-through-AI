import { test, expect, type Page } from "@playwright/test";

async function login(page: Page, account: string) {
  await page.goto("/workspace");
  await page.getByLabel("Demo account").selectOption(account);
  await page.getByRole("button", { name: "Enter demo workspace" }).click();
  await expect(page.getByRole("navigation", { name: "Main navigation" })).toBeVisible();
}

test("citizen navigation, scoped cases, research, assistant and logout", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /Accessible justice/ })).toBeVisible();
  await login(page, "citizen-1");
  await expect(page.getByText("My sample cases").first()).toBeVisible();
  await page.getByRole("link", { name: "Smart Case Management" }).click();
  await expect(page.getByRole("heading", { name: /Sample case registry/ })).toBeVisible();
  await page.getByRole("textbox", { name: "Search cases", exact: true }).fill("nonexistent-xyz");
  await page.getByRole("button", { name: "Search", exact: true }).click();
  await expect(page.getByText("Try another search or remove filters.")).toBeVisible();
  await page.getByRole("link", { name: "Legal Research", exact: true }).click();
  await page.getByLabel("Research question").fill("How can I find case status without CNR?");
  await page.getByRole("button", { name: "Search approved sources" }).click();
  await expect(page.getByText("eCourts Services — finding case status", { exact: true })).toBeVisible();
  await page.getByRole("link", { name: "Citizen Legal Assistant", exact: true }).click();
  await page.getByLabel("Your procedural question").fill("Where can I find legal aid?");
  await page.getByRole("button", { name: "Send question" }).click();
  await expect(page.getByRole("heading", { name: "Practical next steps" }).last()).toBeVisible();
  await page.getByRole("button", { name: "Create checklist" }).click();
  await expect(page.getByRole("button", { name: "Download report" })).toBeVisible();
  await page.goto("/workspace/decision");
  await expect(page.getByText("Court staff permission is required.", { exact: false })).toBeVisible();
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(page.getByLabel("Demo account")).toBeVisible();
  expect(errors).toEqual([]);
});

test("filing upload, text review, validation and checklist", async ({ page }) => {
  await login(page, "citizen-1");
  const sample = await page.request.get("/api/demo/sample-document?kind=valid");
  expect(sample.ok()).toBeTruthy();
  await page.getByRole("link", { name: "Filing Assistant", exact: true }).click();
  await page.getByLabel("Choose documents").setInputFiles({ name: "browser-synthetic.pdf", mimeType: "application/pdf", buffer: await sample.body() });
  await page.getByRole("button", { name: "Upload & extract" }).click();
  await expect(page.getByText("browser-synthetic.pdf", { exact: true }).last()).toBeVisible();
  await page.getByRole("combobox", { name: "Classify browser-synthetic.pdf" }).last().selectOption("statement");
  await page.getByRole("button", { name: "Review text", exact: true }).last().click();
  await expect(page.getByText("page 1", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Run filing readiness check" }).click();
  await expect(page.getByRole("heading", { name: "Filing-readiness report", exact: true })).toBeVisible();
  await expect(page.getByText("Include a supporting record", { exact: true })).toBeVisible();
});

test("staff tasks, scheduling, model metrics and non-binding analysis", async ({ page }) => {
  await login(page, "staff-1");
  await page.getByRole("link", { name: "Smart Case Management" }).click();
  await page.getByRole("button", { name: "Open DEMO/2026/0001", exact: true }).click();
  await page.getByRole("tab", { name: "Tasks", exact: true }).click();
  await page.getByLabel("Task title", { exact: true }).fill("Browser synthetic document review");
  await page.getByLabel("Deadline", { exact: true }).fill("2027-01-15");
  await page.getByRole("button", { name: "Create task", exact: true }).click();
  await expect(page.getByText("Browser synthetic document review", { exact: true }).last()).toBeVisible();
  await page.getByRole("button", { name: "Mark complete", exact: true }).last().click();
  await page.getByRole("tab", { name: "Scheduling", exact: true }).click();
  await page.getByRole("button", { name: "Suggest available slots" }).click();
  await expect(page.getByRole("button", { name: "Confirm simulated slot" }).first()).toBeVisible();
  page.once("dialog", dialog => dialog.accept());
  await page.getByRole("button", { name: "Confirm simulated slot" }).first().click();
  await expect(page.getByRole("status").filter({ hasText: "Human-confirmed simulated schedule saved" })).toBeVisible();
  await page.getByRole("link", { name: "Predictive Analysis", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Model card & reproducible evaluation" })).toBeVisible();
  await expect(page.getByText("baseline_prior", { exact: true })).toBeVisible();
  await page.getByRole("link", { name: "Decision Support", exact: true }).click();
  await expect(page.getByLabel("Claimant / prosecution allegations")).not.toBeEmpty();
  await page.getByRole("checkbox", { name: /I reviewed and corrected/ }).check();
  await page.getByRole("button", { name: "Generate non-binding report" }).click();
  await expect(page.getByRole("heading", { name: "Structured decision-support report", exact: true })).toBeVisible();
  await expect(page.getByText("A responsible outcome assessment cannot be formed from the available materials.", { exact: true })).toBeVisible();
});

test("mobile navigation and native form validation", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await login(page, "citizen-2");
  await page.getByRole("button", { name: "Toggle navigation" }).click();
  await page.getByRole("link", { name: "Legal Research", exact: true }).click();
  await page.getByRole("button", { name: "Search approved sources" }).click();
  await expect(page.getByLabel("Research question")).toBeFocused();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
  expect(overflow).toBe(false);
});