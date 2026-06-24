import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";

import { CopilotChatActivityList } from "./CopilotChatActivityMessage";
// We use the REAL renderer, not a mock
import { createA2UIMessageRenderer } from "./MyA2UIMessageRenderer";

/* ── Mock CopilotKit v2 hooks used internally ────────────────── */

// Real activity messages use a2ui-surface type
vi.mock("@copilotkit/react-core/v2", () => ({
  useRenderActivityMessage: () => {
    const renderer = createA2UIMessageRenderer({});
    // The CopilotKit SDK dispatches to the renderer by activityType.
    // The renderer receives { content: message.content } as props.
    return {
      renderActivityMessage: (message: { id: string; activityType: string; content: any }) => {
        if (message.activityType === "a2ui-surface") {
          // Call the render function directly with the content prop
          return renderer.render({ content: message.content });
        }
        return <div>Unknown activity type: {message.activityType}</div>;
      },
    };
  },
}));

// The A2UI renderer imports from these — mock minimally
vi.mock("@copilotkit/a2ui-renderer", () => ({
  A2UIProvider: ({ children }: { children: React.ReactNode }) => <div data-testid="a2ui-provider">{children}</div>,
  A2UIRenderer: ({ surfaceId }: { surfaceId: string }) => <div data-testid={`a2ui-surface-${surfaceId}`}>{surfaceId}</div>,
  useA2UIActions: () => ({
    processMessages: vi.fn(),
  }),
}));

// Mock DataTable from the A2UI components to simplify rendering
vi.mock("@/components/A2UI/data-table", () => ({
  DataTable: ({ columns, data }: { columns: any[]; data: any[] }) => (
    <div data-testid="datatable">
      <div data-testid="table-columns">{columns.map((c: any) => c.accessorKey || c).join(",")}</div>
      <div data-testid="table-rows">{JSON.stringify(data)}</div>
    </div>
  ),
}));

// Mock shadcn UI table components
vi.mock("@/components/ui/table", () => ({
  Table: ({ children }: any) => <table>{children}</table>,
  TableBody: ({ children }: any) => <tbody>{children}</tbody>,
  TableCell: ({ children }: any) => <td>{children}</td>,
  TableHead: ({ children }: any) => <th>{children}</th>,
  TableHeader: ({ children }: any) => <thead>{children}</thead>,
  TableRow: ({ children }: any) => <tr>{children}</tr>,
}));

vi.mock("@/components/ui/button", () => ({
  Button: ({ children, ...props }: any) => <button {...props}>{children}</button>,
}));

/* ── Tests ───────────────────────────────────────────────────── */

describe("CopilotChatActivityList integration with real renderer", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders markdown content correctly", () => {
    const messages = [
      {
        id: "call_md:activity",
        role: "activity" as const,
        activityType: "a2ui-surface",
        content: {
          type: "markdown",
          title: "Analysis Result",
          content: "**Alice** scored 95 points.\n\n**Bob** scored 87 points.",
        },
      },
    ];

    render(<CopilotChatActivityList messages={messages} />);

    // Title should be rendered
    expect(screen.getByText("Analysis Result")).toBeInTheDocument();

    // Markdown should be rendered (ReactMarkdown converts **text** to <strong>)
    // Note: ReactMarkdown renders as HTML, so we query for the text content
    expect(screen.getByText(/Alice/)).toBeInTheDocument();
    expect(screen.getByText(/scored 95 points/)).toBeInTheDocument();
    expect(screen.getByText(/Bob/)).toBeInTheDocument();
    expect(screen.getByText(/scored 87 points/)).toBeInTheDocument();
  });

  it("renders A2UI table content correctly", () => {
    const messages = [
      {
        id: "call_table:activity",
        role: "activity" as const,
        activityType: "a2ui-surface",
        content: {
          a2ui_operations: [{ version: "v0.9", createSurface: { surfaceId: "call_table-0", catalogId: [] } }],
          surfaceId: "call_table-0",
        },
      },
    ];

    render(<CopilotChatActivityList messages={messages} />);

    // A2UI provider should be rendered
    expect(screen.getByTestId("a2ui-provider")).toBeInTheDocument();
    // A2UI surface should render with the surfaceId
    expect(screen.getByTestId("a2ui-surface-call_table-0")).toBeInTheDocument();
  });

  it("renders legacy table content (without a2ui_operations)", () => {
    const messages = [
      {
        id: "call_legacy:activity",
        role: "activity" as const,
        activityType: "a2ui-surface",
        content: {
          type: "table",
          title: "Scores",
          columns: ["name", "score"],
          rows: [["Alice", "95"], ["Bob", "87"]],
        },
      },
    ];

    render(<CopilotChatActivityList messages={messages} />);

    // Title should be rendered (h3 element)
    expect(screen.getByText("Scores")).toBeInTheDocument();

    // DataTable should be rendered with the data
    expect(screen.getByTestId("datatable")).toBeInTheDocument();
    expect(screen.getByTestId("table-columns")).toHaveTextContent("name,score");
    expect(screen.getByTestId("table-rows")).toHaveTextContent("Alice");
    expect(screen.getByTestId("table-rows")).toHaveTextContent("Bob");
  });

  it("renders multiple activity messages (markdown + A2UI) simultaneously", () => {
    const messages = [
      {
        id: "call_multi:activity:0",
        role: "activity" as const,
        activityType: "a2ui-surface",
        content: { type: "markdown", title: "Summary", content: "Found **2 records**." },
      },
      {
        id: "call_multi:activity:1",
        role: "activity" as const,
        activityType: "a2ui-surface",
        content: {
          a2ui_operations: [{ version: "v0.9", createSurface: { surfaceId: "call_table-0", catalogId: [] } }],
          surfaceId: "call_table-0",
        },
      },
    ];

    render(<CopilotChatActivityList messages={messages} />);

    // Both markdown and A2UI should render
    expect(screen.getByText("Summary")).toBeInTheDocument();
    expect(screen.getByText(/2 records/)).toBeInTheDocument();
    expect(screen.getByTestId("a2ui-surface-call_table-0")).toBeInTheDocument();
  });

  it("renders nothing when messages array is empty", () => {
    const { container } = render(<CopilotChatActivityList messages={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it("handles todo_list messages by showing only the last one", () => {
    const messages = [
      { id: "todo-1", role: "activity" as const, activityType: "a2ui-surface", content: { type: "todo_list", label: "First todo" } },
      { id: "table-1", role: "activity" as const, activityType: "a2ui-surface", content: { type: "table", title: "Data", columns: ["x"], rows: [["1"]] } },
      { id: "todo-2", role: "activity" as const, activityType: "a2ui-surface", content: { type: "todo_list", label: "Last todo" } },
    ];

    render(<CopilotChatActivityList messages={messages} />);
    // "First todo" should NOT be visible (it's not the last todo_list)
    expect(screen.queryByText("First todo")).not.toBeInTheDocument();
    // "Last todo" appears inside the Unknown content type pre block
    // The renderer doesn't have a todo_list branch, so it shows the JSON
    expect(screen.getByText(/Last todo/)).toBeInTheDocument();
    // The table should still be visible
    expect(screen.getByText("Data")).toBeInTheDocument();
    // todo_list renders as "Unknown content type" fallback
    expect(screen.getByText(/Unknown content type/)).toBeInTheDocument();
    // Actually todo_list doesn't have a matching branch in the renderer, so it shows "Unknown content type"
  });

  it("handles content with a2ui_operations as non-array gracefully", () => {
    const messages = [
      {
        id: "bad-a2ui",
        role: "activity" as const,
        activityType: "a2ui-surface",
        content: { a2ui_operations: "not-an-array", surfaceId: "bad-surface" },
      },
    ];

    render(<CopilotChatActivityList messages={messages} />);

    // Should not crash; should fall through to unknown type handler
    // (The renderer checks Array.isArray(content.a2ui_operations) → false, then switch on type → default)
    expect(screen.getByText(/Unknown content type/)).toBeInTheDocument();
  });

  it("handles null/undefined content gracefully", () => {
    const messages = [
      { id: "null-content", role: "activity" as const, activityType: "a2ui-surface", content: null as any },
    ];

    render(<CopilotChatActivityList messages={messages} />);

    // Should render error fallback
    expect(screen.getByText(/Data format error/)).toBeInTheDocument();
  });
});
