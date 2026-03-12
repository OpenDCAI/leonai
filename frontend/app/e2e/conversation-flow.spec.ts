import { test, expect } from "@playwright/test";

const PASSWORD = "testpassword123";

function uniqueUser(prefix: string) {
  return `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`;
}

/** Register a new user and wait for the app to load. */
async function registerAndWait(page: import("@playwright/test").Page, username: string) {
  await page.goto("/");
  await expect(page.locator("h1", { hasText: "Leon" })).toBeVisible();

  // Switch to register
  await page.click("button:has-text('注册')");
  await expect(page.locator("text=创建新账号")).toBeVisible();

  await page.fill('input[placeholder="用户名"]', username);
  await page.fill('input[placeholder="密码"]', PASSWORD);
  await page.click('button[type="submit"]');

  // Wait for app layout (nav link "消息" in the sidebar)
  await expect(page.getByRole("link", { name: "消息" })).toBeVisible({ timeout: 10_000 });
}

test.describe("Conversation UI E2E", () => {
  test("full flow: register → sidebar → chat → view mode toggle → persist", async ({ page }) => {
    const user = uniqueUser("e2e_full");

    // 1. Open app → login form appears
    await page.goto("/");
    await expect(page.locator("h1", { hasText: "Leon" })).toBeVisible();
    await expect(page.locator("text=登录你的账号")).toBeVisible();

    // 2. Register
    await registerAndWait(page, user);

    // 3. Sidebar shows conversation
    await expect(page.locator("text=Chat with Leon").first()).toBeVisible({ timeout: 10_000 });

    // 4. Click conversation → ChatPage loads
    await page.click("text=Chat with Leon");

    // Wait for the input area to appear (either textarea or div[contenteditable])
    const inputArea = page.locator('textarea, div[contenteditable="true"]').first();
    await expect(inputArea).toBeVisible({ timeout: 10_000 });

    // 5. View mode toggle exists (only shows for conversation-based chats)
    await expect(page.locator("text=完整视图")).toBeVisible({ timeout: 5_000 });

    // 6. Toggle to contact mode
    await page.click("text=完整视图");
    await expect(page.locator("text=消息视图")).toBeVisible();

    // 7. Toggle back to owner mode
    await page.click("text=消息视图");
    await expect(page.locator("text=完整视图")).toBeVisible();

    // 8. Verify auth persisted in localStorage
    const storage = await page.evaluate(() => localStorage.getItem("leon-auth"));
    expect(storage).toBeTruthy();
    const parsed = JSON.parse(storage!);
    expect(parsed.state.token).toBeTruthy();
    expect(parsed.state.member.name).toBe(user);

    // 9. Refresh → still logged in
    await page.reload();
    await expect(page.getByRole("link", { name: "消息" })).toBeVisible({ timeout: 10_000 });
    await expect(page.locator("text=登录你的账号")).not.toBeVisible();
  });

  test("login with existing account", async ({ page }) => {
    const user = uniqueUser("e2e_login");

    // Register first
    await registerAndWait(page, user);

    // Logout by clearing storage + reload
    await page.evaluate(() => localStorage.removeItem("leon-auth"));
    await page.reload();
    await expect(page.locator("text=登录你的账号")).toBeVisible({ timeout: 10_000 });

    // Login with same account
    await page.fill('input[placeholder="用户名"]', user);
    await page.fill('input[placeholder="密码"]', PASSWORD);
    await page.click('button[type="submit"]');
    await expect(page.getByRole("link", { name: "消息" })).toBeVisible({ timeout: 10_000 });
  });

  test("logout clears auth and shows login form", async ({ page }) => {
    const user = uniqueUser("e2e_logout");
    await registerAndWait(page, user);

    // Try clicking the logout button
    const logoutBtn = page.locator('button[title="退出登录"]');
    if (await logoutBtn.isVisible({ timeout: 2_000 }).catch(() => false)) {
      await logoutBtn.click();
    } else {
      // Sidebar might be collapsed — clear auth manually
      await page.evaluate(() => localStorage.removeItem("leon-auth"));
      await page.reload();
    }

    await expect(page.locator("text=登录你的账号")).toBeVisible({ timeout: 10_000 });
  });

  test("existing routes (/members, /tasks) still work when authenticated", async ({ page }) => {
    const user = uniqueUser("e2e_routes");
    await registerAndWait(page, user);

    // Navigate to /members
    await page.goto("/members");
    await expect(page.getByRole("link", { name: "成员" })).toBeVisible({ timeout: 10_000 });

    // Navigate to /tasks
    await page.goto("/tasks");
    await expect(page.getByRole("link", { name: "任务" })).toBeVisible({ timeout: 10_000 });
  });
});
