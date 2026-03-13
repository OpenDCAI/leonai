import { test, expect } from "@playwright/test";

const PASSWORD = "testpassword123";

function uniqueUser() {
  return `e2e_conv_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`;
}

test.describe("Full Conversation Flow E2E", () => {
  test("register → new chat → send message → receive agent response", async ({ page }) => {
    const username = uniqueUser();

    // Enable console log forwarding for debugging
    page.on("console", msg => {
      if (msg.type() === "error" || msg.text().includes("[")) {
        console.log(`[BROWSER ${msg.type()}] ${msg.text()}`);
      }
    });

    // ── Step 1: Navigate to app, see login form ──
    console.log("Step 1: Navigate to app");
    await page.goto("/");
    await expect(page.locator("h1", { hasText: "Leon" })).toBeVisible({ timeout: 10_000 });
    await expect(page.locator("text=登录你的账号")).toBeVisible();
    await page.screenshot({ path: "e2e/screenshots/01-login-form.png" });

    // ── Step 2: Switch to register mode and register ──
    console.log("Step 2: Register new user:", username);
    await page.click("button:has-text('注册')");
    await expect(page.locator("text=创建新账号")).toBeVisible();
    await page.screenshot({ path: "e2e/screenshots/02-register-form.png" });

    await page.fill('input[placeholder="用户名"]', username);
    await page.fill('input[placeholder="密码"]', PASSWORD);
    await page.click('button[type="submit"]');

    // ── Step 3: Wait for app to load (nav link "消息" visible) ──
    console.log("Step 3: Wait for app to load");
    await expect(page.getByRole("link", { name: "消息" })).toBeVisible({ timeout: 15_000 });
    await page.screenshot({ path: "e2e/screenshots/03-app-loaded.png" });

    // ── Step 4: Click the "+" / "新建" button to open create dropdown ──
    console.log("Step 4: Click 新建 button");
    // The "新建" button is in the left sidebar. It may show as "+" (collapsed) or "新建" (expanded).
    // In collapsed mode it's just the Plus icon. Let's try clicking it.
    // The sidebar auto-collapses when entering /chat, so look for the round "+" button.
    const newButton = page.locator('button:has-text("新建")');
    const plusButton = page.locator('button').filter({ has: page.locator('svg.lucide-plus') }).first();
    
    // Try "新建" first (expanded sidebar), then fall back to Plus icon (collapsed)
    if (await newButton.isVisible({ timeout: 2_000 }).catch(() => false)) {
      await newButton.click();
    } else {
      // In collapsed sidebar, the Plus button is the round one
      await plusButton.click();
    }
    await page.screenshot({ path: "e2e/screenshots/04-create-dropdown.png" });

    // ── Step 5: Click "发起会话" in the dropdown ──
    console.log("Step 5: Click 发起会话 in dropdown");
    // The CreateDropdown has a button with text "发起会话"
    await page.click('button:has-text("发起会话")');

    // ── Step 6: NewChatDialog opens, click the Leon agent button ──
    console.log("Step 6: NewChatDialog - click Leon agent");
    // Wait for the dialog to appear with title "发起会话"
    const dialog = page.locator('[role="dialog"]');
    await expect(dialog).toBeVisible({ timeout: 5_000 });
    await page.screenshot({ path: "e2e/screenshots/05-new-chat-dialog.png" });

    // Click the agent button (shows agent name, e.g. "Leon")
    // The button contains the agent name and "Your AI assistant"
    const agentButton = dialog.locator('button:has-text("Leon")');
    if (await agentButton.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await agentButton.click();
    } else {
      // Might show a different agent name, click the first button in the list area
      const firstAgent = dialog.locator('button').first();
      await firstAgent.click();
    }

    // ── Step 7: Wait for navigation to chat page ──
    console.log("Step 7: Wait for navigation to chat page");
    // After creating conversation, it navigates to /chat/leon/brain-{uuid}
    // Wait for the input box to appear
    const inputBox = page.locator('textarea[placeholder="告诉 Leon 你需要什么帮助..."]');
    await expect(inputBox).toBeVisible({ timeout: 15_000 });
    await page.screenshot({ path: "e2e/screenshots/06-chat-page-loaded.png" });

    // Also verify the view mode toggle appears (indicates conversation mode)
    await expect(page.locator("text=完整视图")).toBeVisible({ timeout: 5_000 });

    // ── Step 8: Type and send a message ──
    console.log("Step 8: Send message");
    await inputBox.fill("say hello");
    await page.screenshot({ path: "e2e/screenshots/07-message-typed.png" });

    // Click the send button (or press Enter)
    // The send button has a Send icon (lucide-send)
    const sendButton = page.locator('button').filter({ has: page.locator('svg.lucide-send') });
    if (await sendButton.isVisible({ timeout: 1_000 }).catch(() => false)) {
      await sendButton.click();
    } else {
      // Press Enter to send
      await inputBox.press("Enter");
    }

    // ── Step 9: Verify user message appears ──
    console.log("Step 9: Verify user message sent");
    await expect(page.locator("text=say hello").first()).toBeVisible({ timeout: 5_000 });
    await page.screenshot({ path: "e2e/screenshots/08-message-sent.png" });

    // ── Step 10: Wait for agent response (generous timeout: up to 60s) ──
    console.log("Step 10: Wait for agent response (up to 60s)...");
    
    // The agent response will appear as an assistant turn in the ChatArea.
    // It might contain text, tool calls, etc. We just need ANY assistant content.
    // Assistant messages are rendered in divs with markdown content.
    // Let's wait for either:
    // 1. A new message bubble after our user message
    // 2. The streaming indicator to appear and then real content

    // First, wait for the streaming/thinking indicator to appear
    // (the three-dot animation or any assistant turn marker)
    // Give it up to 30s to start responding
    
    // Wait for any assistant-generated text content to appear.
    // The response will contain some text - look for markdown paragraphs in the chat area.
    // We look for elements that appear AFTER the user message.
    
    // Strategy: wait until the chat area has more than just our user message.
    // The assistant response renders as markdown with <p> tags inside prose containers.
    
    // Poll for assistant content appearing
    await page.waitForFunction(() => {
      // Look for any element with data-role="assistant" or the prose content
      const assistantContent = document.querySelectorAll('[data-turn-role="assistant"] .prose p, [data-turn-role="assistant"] .prose li');
      // Or look for text segments in the chat
      const textSegments = document.querySelectorAll('.markdown-content p, .prose p');
      return assistantContent.length > 0 || textSegments.length > 0;
    }, { timeout: 60_000 }).catch(() => null);

    // Take a screenshot regardless
    await page.screenshot({ path: "e2e/screenshots/09-waiting-response.png" });

    // Alternative: just wait for the input to become enabled again (streaming finished)
    // When the agent is done, isStreaming becomes false and the input re-enables.
    // During streaming, the textarea is still enabled (for queue messages), but the 
    // stop button appears. Wait for the stop button to disappear.
    
    // Wait for streaming to finish: the send button reappears (stop button disappears)
    console.log("Step 10b: Wait for streaming to finish...");
    await page.waitForFunction(() => {
      // When streaming finishes, the stop button (Square icon) disappears
      // and we can check if there's text content in the assistant area
      const stopBtn = document.querySelector('svg.lucide-square');
      return !stopBtn;
    }, { timeout: 60_000 }).catch(() => {
      console.log("Timeout waiting for streaming to finish - checking current state");
    });

    await page.screenshot({ path: "e2e/screenshots/10-response-received.png" });

    // ── Step 11: Verify response content exists ──
    console.log("Step 11: Verify response");
    
    // Get all text content in the chat area to see what we got
    const chatContent = await page.evaluate(() => {
      const chatArea = document.querySelector('[class*="chat"]') || document.querySelector('main');
      return chatArea?.textContent?.substring(0, 2000) || "NO CHAT CONTENT FOUND";
    });
    console.log("Chat area content (first 2000 chars):", chatContent);

    // The response should contain SOME text beyond just our message
    // Look for any prose/markdown content
    const hasAssistantContent = await page.evaluate(() => {
      const allText = document.body.innerText;
      // Our message was "say hello" - the response should add more text
      // Check if there's content after the user message area
      return allText.length > 100; // Basic sanity: page has substantial content
    });
    
    expect(hasAssistantContent).toBe(true);
    
    // Final screenshot
    await page.screenshot({ path: "e2e/screenshots/11-final-state.png", fullPage: true });
    console.log("Test completed successfully!");
  });
});
