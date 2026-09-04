import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await expect(page.getByTestId("dialog-101")).toBeVisible();
});

test("dialogs start near the top and paginate in their scroll area", async ({ page }) => {
  const firstDialog = page.getByTestId("dialog-101");
  const box = await firstDialog.boundingBox();
  expect(box).not.toBeNull();
  expect(box!.y).toBeLessThan(180);

  const pane = page.getByTestId("dialogs-scroll");
  await expect.poll(() => pane.evaluate((element) => element.scrollHeight > element.clientHeight)).toBe(true);
  await pane.evaluate((element) => { element.scrollTop = element.scrollHeight; });
  await expect(page.getByTestId("dialog-145")).toBeVisible();
});

test("older messages load without hiding the latest message", async ({ page }) => {
  await page.getByTestId("dialog-101").click();
  await expect(page.getByTestId("message-60")).toBeVisible();

  const pane = page.getByTestId("messages-scroll");
  await pane.evaluate((element) => { element.scrollTop = 0; });
  await expect(page.getByTestId("message-1")).toBeAttached();
  await expect(page.getByTestId("message-60")).toBeAttached();
});

test("an incoming SSE message appears in the open dialog", async ({ page }) => {
  await page.getByTestId("dialog-101").click();
  await expect(page.getByTestId("live-status")).toContainText("Автообновление включено");
  await expect(page.getByText("Realtime message arrived", { exact: true })).toBeVisible();
});
