import { expect, test } from "@playwright/test";

const visitorId = "018f4d80-0000-7000-8000-000000000001";
const WORKSPACE_SLUG = "playwright-e2e";

/* ── SSE helpers ─────────────────────────────────────────── */

function sseEvent(event: Record<string, unknown>): string {
  return `data: ${JSON.stringify(event)}\n\n`;
}

function activitySnapshotEvent(messageId: string, activityType: string, content: Record<string, unknown>) {
  return { type: "ACTIVITY_SNAPSHOT", messageId, activityType, content };
}

/** Real A2UI operations from the Python backend for table display. */
const REAL_A2UI_OPS = [
  {
    version: "v0.9",
    createSurface: {
      surfaceId: "test-surface",
      catalogId: [
        { id: "root", component: "Column", children: ["tableTitle", "tableHeader", "row_0", "row_1", "paginationRow"], align: "stretch" },
        { id: "tableTitle", component: "Text", text: "Scores", variant: "h3" },
        { id: "tableHeader", component: "Row", children: ["header_0", "header_1"], justify: "spaceBetween", align: "center" },
        { id: "header_0", component: "Text", text: "name", variant: "label" },
        { id: "header_1", component: "Text", text: "score", variant: "label" },
        { id: "row_0", component: "Row", children: ["cell_0_0", "cell_0_1"], justify: "spaceBetween", align: "center" },
        { id: "cell_0_0", component: "Text", text: "" },
        { id: "cell_0_1", component: "Text", text: "" },
        { id: "row_1", component: "Row", children: ["cell_1_0", "cell_1_1"], justify: "spaceBetween", align: "center" },
        { id: "cell_1_0", component: "Text", text: "" },
        { id: "cell_1_1", component: "Text", text: "" },
        { id: "paginationRow", component: "Row", children: ["prevBtn", "pageInfo", "nextBtn"], justify: "center", align: "center" },
        { id: "prevBtn", component: "Button", child: "prevBtnText", action: { event: { name: "test_tool", context: { query_args: { page: 1 } } } } },
        { id: "prevBtnText", component: "Text", text: "Previous" },
        { id: "pageInfo", component: "Text", text: "Page 1", variant: "caption" },
        { id: "nextBtn", component: "Button", child: "nextBtnText", action: { event: { name: "test_tool", context: { query_args: { page: 2 } } } } },
        { id: "nextBtnText", component: "Text", text: "Next" },
      ],
    },
  },
  {
    op: "updateDataModel",
    updateDataModel: {
      surfaceId: "test-surface",
      path: "/",
      value: {
        title: "Scores",
        columns: ["name", "score"],
        rows: [{ name: "Alice", score: 95 }, { name: "Bob", score: 87 }],
        pageInfo: "Page 1",
        isFirstPage: true,
        isLastPage: false,
      },
    },
  },
];

/* ── Stream builders ─────────────────────────────────────────── */

function buildMarkdownStream(): string {
  return [
    { type: "RUN_STARTED", threadId: "t-md", runId: "r-md" },
    { type: "TEXT_MESSAGE_START", messageId: "msg-md", role: "assistant" },
    { type: "TEXT_MESSAGE_CONTENT", messageId: "msg-md", delta: "Let me summarize…\n\n" },
    activitySnapshotEvent("call_md:activity", "a2ui-surface", {
      type: "markdown", title: "Analysis Result", content: "**Alice** scored 95 points.\n\n**Bob** scored 87 points.",
    }),
    { type: "TEXT_MESSAGE_CONTENT", messageId: "msg-md", delta: "That's the summary." },
    { type: "TEXT_MESSAGE_END", messageId: "msg-md" },
    { type: "RUN_FINISHED", threadId: "t-md", runId: "r-md" },
  ].map(sseEvent).join("");
}

function buildA2UIStream(): string {
  return [
    { type: "RUN_STARTED", threadId: "t-a2ui", runId: "r-a2ui" },
    { type: "TEXT_MESSAGE_START", messageId: "msg-a2ui", role: "assistant" },
    { type: "TEXT_MESSAGE_CONTENT", messageId: "msg-a2ui", delta: "Here is the data:\n\n" },
    activitySnapshotEvent("call_table:activity", "a2ui-surface", { a2ui_operations: REAL_A2UI_OPS, surfaceId: "test-surface" }),
    { type: "TEXT_MESSAGE_CONTENT", messageId: "msg-a2ui", delta: "Done." },
    { type: "TEXT_MESSAGE_END", messageId: "msg-a2ui" },
    { type: "RUN_FINISHED", threadId: "t-a2ui", runId: "r-a2ui" },
  ].map(sseEvent).join("");
}

function buildMultiItemStream(): string {
  return [
    { type: "RUN_STARTED", threadId: "t-multi", runId: "r-multi" },
    { type: "TEXT_MESSAGE_START", messageId: "msg-multi", role: "assistant" },
    { type: "TEXT_MESSAGE_CONTENT", messageId: "msg-multi", delta: "Results:\n\n" },
    activitySnapshotEvent("call_multi:activity:0", "a2ui-surface", { type: "markdown", title: "Quick Summary", content: "Found **2 records**." }),
    activitySnapshotEvent("call_multi:activity:1", "a2ui-surface", { a2ui_operations: REAL_A2UI_OPS, surfaceId: "test-surface" }),
    { type: "TEXT_MESSAGE_CONTENT", messageId: "msg-multi", delta: " All done." },
    { type: "TEXT_MESSAGE_END", messageId: "msg-multi" },
    { type: "RUN_FINISHED", threadId: "t-multi", runId: "r-multi" },
  ].map(sseEvent).join("");
}

function buildPlainStream(): string {
  return [
    { type: "RUN_STARTED", threadId: "t-plain", runId: "r-plain" },
    { type: "TEXT_MESSAGE_START", messageId: "msg-plain", role: "assistant" },
    { type: "TEXT_MESSAGE_CONTENT", messageId: "msg-plain", delta: "Plain response, no tools." },
    { type: "TEXT_MESSAGE_END", messageId: "msg-plain" },
    { type: "RUN_FINISHED", threadId: "t-plain", runId: "r-plain" },
  ].map(sseEvent).join("");
}

/* ── Shared route setup helper ──────────────────────────────── */

/**
 * Intercept CopilotKit POST requests to /chat/agent/{id}/connect and /chat/agent/{id}/runs.
 * Returns a fake SSE stream. The `runs` call is the one that streams agent events.
 */
async function interceptAgentRoute(page: any, streamBody: string) {
  // CopilotKit sends two POSTs: /connect (initial state) and /runs (streaming)
  // We need to handle the /runs call with our fake SSE stream.
  await page.route(/\/chat\/agent\/.*\/(connect|runs)/, async (route: any) => {
    if (route.request().method() !== "POST") return route.continue();

    const url = route.request().url();
    if (url.endsWith("/connect")) {
      // /connect response: just a basic state snapshot
      await route.fulfill({
        status: 200,
        headers: { "Content-Type": "text/event-stream", "Cache-Control": "no-cache", Connection: "keep-alive" },
        body: "",
      });
      return;
    }

    if (url.endsWith("/runs")) {
      // /runs response: our fake agent streaming events
      await route.fulfill({
        status: 200,
        headers: { "Content-Type": "text/event-stream", "Cache-Control": "no-cache", Connection: "keep-alive" },
        body: streamBody,
      });
      return;
    }

    return route.continue();
  });
}

/* ── Tests ──────────────────────────────────────────────────── */

test.describe("Tool call activity rendering E2E", () => {
  test("renders markdown activity message in the middle section", async ({ page }) => {
    await page.addInitScript((id) => {
      window.localStorage.setItem("dingent_visitor_id", id);
      window.localStorage.setItem("currentChatThreadId", "");
    }, visitorId);

    await interceptAgentRoute(page, buildMarkdownStream());

    await page.goto(`/dingent/web/guest/${WORKSPACE_SLUG}/chat`);
    await expect(page.getByText("New Chat").first()).toBeVisible({ timeout: 10_000 });

    const input = page.getByRole("textbox").last();
    await input.fill("Show analysis");
    await input.press("Enter");

    // Wait for the assistant text to appear (proof SSE was processed)
    await expect(page.getByText("That's the summary.")).toBeVisible({ timeout: 15_000 });

    // Verify markdown activity rendered in the middle section
    await expect(page.getByText("Analysis Result")).toBeVisible({ timeout: 5_000 });
    await expect(page.getByText(/Alice/)).toBeVisible({ timeout: 5_000 });
    await expect(page.getByText(/scored 95 points/)).toBeVisible({ timeout: 5_000 });
    await expect(page.getByText(/Bob/)).toBeVisible({ timeout: 5_000 });
    await expect(page.getByText(/scored 87 points/)).toBeVisible({ timeout: 5_000 });
  });

  test("renders A2UI table activity message in the middle section", async ({ page }) => {
    await page.addInitScript((id) => {
      window.localStorage.setItem("dingent_visitor_id", id);
      window.localStorage.setItem("currentChatThreadId", "");
    }, visitorId);

    await interceptAgentRoute(page, buildA2UIStream());

    await page.goto(`/dingent/web/guest/${WORKSPACE_SLUG}/chat`);
    await expect(page.getByText("New Chat").first()).toBeVisible({ timeout: 10_000 });

    const input = page.getByRole("textbox").last();
    await input.fill("Show table");
    await input.press("Enter");

    await expect(page.getByText("Done.")).toBeVisible({ timeout: 15_000 });

    // Verify A2UI table rendered: title, data cells, pagination
    await expect(page.getByText("Scores")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("Alice")).toBeVisible({ timeout: 5_000 });
    await expect(page.getByText("95")).toBeVisible({ timeout: 5_000 });
    await expect(page.getByText("Bob")).toBeVisible({ timeout: 5_000 });
    await expect(page.getByText("87")).toBeVisible({ timeout: 5_000 });
    await expect(page.getByText("Page 1")).toBeVisible({ timeout: 5_000 });
    await expect(page.getByText("Previous")).toBeVisible({ timeout: 5_000 });
    await expect(page.getByText("Next")).toBeVisible({ timeout: 5_000 });
  });

  test("renders both markdown and A2UI table when tool returns multi-item display", async ({ page }) => {
    await page.addInitScript((id) => {
      window.localStorage.setItem("dingent_visitor_id", id);
      window.localStorage.setItem("currentChatThreadId", "");
    }, visitorId);

    await interceptAgentRoute(page, buildMultiItemStream());

    await page.goto(`/dingent/web/guest/${WORKSPACE_SLUG}/chat`);
    await expect(page.getByText("New Chat").first()).toBeVisible({ timeout: 10_000 });

    const input = page.getByRole("textbox").last();
    await input.fill("Show everything");
    await input.press("Enter");

    await expect(page.getByText("All done.")).toBeVisible({ timeout: 15_000 });

    await expect(page.getByText("Quick Summary")).toBeVisible({ timeout: 5_000 });
    await expect(page.getByText(/2 records/)).toBeVisible({ timeout: 5_000 });
    await expect(page.getByText("Scores")).toBeVisible({ timeout: 5_000 });
    await expect(page.getByText("Alice")).toBeVisible({ timeout: 5_000 });
    await expect(page.getByText("Bob")).toBeVisible({ timeout: 5_000 });
  });

  test("no activity messages shown when SSE stream has no activity events", async ({ page }) => {
    await page.addInitScript((id) => {
      window.localStorage.setItem("dingent_visitor_id", id);
      window.localStorage.setItem("currentChatThreadId", "");
    }, visitorId);

    await interceptAgentRoute(page, buildPlainStream());

    await page.goto(`/dingent/web/guest/${WORKSPACE_SLUG}/chat`);
    await expect(page.getByText("New Chat").first()).toBeVisible({ timeout: 10_000 });

    const input = page.getByRole("textbox").last();
    await input.fill("Hello");
    await input.press("Enter");

    await expect(page.getByText("Plain response, no tools.")).toBeVisible({ timeout: 15_000 });

    // No activity-related content should appear
    await expect(page.getByText("Scores")).not.toBeVisible({ timeout: 3_000 });
    await expect(page.getByText("Analysis Result")).not.toBeVisible({ timeout: 3_000 });
  });
});
