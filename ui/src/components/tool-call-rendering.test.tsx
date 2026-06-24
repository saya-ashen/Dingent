import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { createA2UIMessageRenderer } from "./MyA2UIMessageRenderer";

// Mock dependencies
vi.mock("@copilotkit/a2ui-renderer", () => ({
  A2UIProvider: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="a2ui-provider">{children}</div>
  ),
  A2UIRenderer: ({ surfaceId }: { surfaceId: string }) => (
    <div data-testid="a2ui-renderer">{surfaceId}</div>
  ),
  useA2UIActions: () => ({ processMessages: vi.fn() }),
}));

vi.mock("react-photo-view", () => ({
  PhotoProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  PhotoView: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));
vi.mock("react-photo-view/dist/react-photo-view.css", () => ({}));

vi.mock("./A2UI/data-table", () => ({
  DataTable: ({ columns, data }: { columns: Array<{ accessorKey: string }>; data: Array<Record<string, unknown>> }) => (
    <div data-testid="legacy-table">
      <div data-testid="table-columns">{columns.map((c) => c.accessorKey).join(",")}</div>
      <div data-testid="table-rows">{JSON.stringify(data)}</div>
    </div>
  ),
}));

const renderer = createA2UIMessageRenderer({});
const RenderComponent = renderer.render;

describe("createA2UIMessageRenderer - tool call rendering", () => {
  // ======== REALISTIC BACKEND OUTPUT SHAPES ========

  it("renders a2ui_operations content from tool artifact display (table via A2UI surface)", () => {
    // This is the shape produced by mcp_artifact_to_agui_display for tables
    render(
      <RenderComponent
        activityType="a2ui-surface"
        content={{
          a2ui_operations: [
            { createSurface: { surfaceId: "call_table_test-0" } },
            { updateComponents: { surfaceId: "call_table_test-0", components: [] } },
            { updateDataModel: { surfaceId: "call_table_test-0", value: {} } },
          ],
          surfaceId: "call_table_test-0",
        }}
        message={{}}
        agent={{}}
      />,
    );

    expect(screen.getByTestId("a2ui-provider")).toBeInTheDocument();
    expect(screen.getByTestId("a2ui-renderer")).toHaveTextContent("call_table_test-0");
  });

  it("renders markdown content from tool artifact display (non-A2UI path)", () => {
    // This is the shape produced by mcp_artifact_to_agui_display for markdown content
    render(
      <RenderComponent
        activityType="a2ui-surface"
        content={{ type: "markdown", title: "Analysis", content: "# Results\n\nAlice: 42" }}
        message={{}}
        agent={{}}
      />,
    );

    expect(screen.getByText("Analysis")).toBeInTheDocument();
    expect(screen.getByText("Alice: 42")).toBeInTheDocument();
  });

  it("renders legacy table content", () => {
    // Legacy table format (non-A2UI wrapped)
    render(
      <RenderComponent
        activityType="a2ui-surface"
        content={{ type: "table", title: "Users", columns: ["name", "age"], rows: [{ name: "Alice", age: 30 }] }}
        message={{}}
        agent={{}}
      />,
    );

    expect(screen.getByText("Users")).toBeInTheDocument();
    expect(screen.getByTestId("legacy-table")).toBeInTheDocument();
    expect(screen.getByTestId("table-columns")).toHaveTextContent("name,age");
  });

  it("renders legacy table with array rows", () => {
    // Legacy table with rows as arrays (before normalization)
    render(
      <RenderComponent
        activityType="a2ui-surface"
        content={{ type: "table", title: "Users", columns: ["name", "age"], rows: [["Alice", 30]] }}
        message={{}}
        agent={{}}
      />,
    );

    expect(screen.getByTestId("legacy-table")).toBeInTheDocument();
    // After normalization, [["Alice", 30]] should become [{ name: "Alice", age: 30 }]
    expect(screen.getByTestId("table-rows")).toHaveTextContent("Alice")
  });

  it("renders table when content has rows/columns but no explicit type", () => {
    // Fallback: rows and columns detection even without type field
    render(
      <RenderComponent
        activityType="a2ui-surface"
        content={{ title: "Results", columns: ["x"], rows: [{ x: 1 }] }}
        message={{}}
        agent={{}}
      />,
    );

    expect(screen.getByTestId("legacy-table")).toBeInTheDocument();
  });

  // ======== CONTENT THAT COMES VIA ACTIVITY_SNAPSHOT EVENTS ========

  it("renders content array (multiple display items from a single tool call)", () => {
    // When a tool produces both table and markdown displays
    render(
      <RenderComponent
        activityType="a2ui-surface"
        content={[
          {
            a2ui_operations: [
              { createSurface: { surfaceId: "call_multi-0" } },
              { updateDataModel: { surfaceId: "call_multi-0", value: {} } },
            ],
            surfaceId: "call_multi-0",
          },
          { type: "markdown", title: "Summary", content: "Final analysis" },
        ]}
        message={{}}
        agent={{}}
      />,
    );

    expect(screen.getByTestId("a2ui-provider")).toBeInTheDocument();
    expect(screen.getByText("Final analysis")).toBeInTheDocument();
  });

  it("shows error for null content", () => {
    render(
      <RenderComponent
        activityType="a2ui-surface"
        content={null}
        message={{}}
        agent={{}}
      />,
    );

    expect(screen.getByText(/Content is missing or invalid/i)).toBeInTheDocument();
  });

  it("shows error for undefined content", () => {
    render(
      <RenderComponent
        activityType="a2ui-surface"
        content={undefined}
        message={{}}
        agent={{}}
      />,
    );

    expect(screen.getByText(/Content is missing or invalid/i)).toBeInTheDocument();
  });

  it("shows error for string content (invalid shape)", () => {
    render(
      <RenderComponent
        activityType="a2ui-surface"
        content="just a string"
        message={{}}
        agent={{}}
      />,
    );

    expect(screen.getByText(/Data format error/i)).toBeInTheDocument();
  });

  it("shows fallback for unknown content type", () => {
    render(
      <RenderComponent
        activityType="a2ui-surface"
        content={{ type: "unknown_format", someField: "test" }}
        message={{}}
        agent={{}}
      />,
    );
    expect(screen.getByText(/Unknown content type/i)).toBeInTheDocument()
    expect(screen.getByText(/unknown_format/i, { selector: "p" })).toBeInTheDocument()
  });

  // ======== COPIED FROM EXISTING TESTS ========

  it("routes official A2UI operations through the official provider and renderer", () => {
    // Copied from existing test to ensure compatibility
    const operations = [
      { createSurface: { surfaceId: "surface-1" } },
      { updateDataModel: { surfaceId: "surface-1", value: { title: "Result" } } },
    ];

    render(
      <RenderComponent
        activityType="a2ui-surface"
        content={{ a2ui_operations: operations }}
        message={{}}
        agent={{}}
      />,
    );

    expect(screen.getByTestId("a2ui-provider")).toBeInTheDocument();
    expect(screen.getByTestId("a2ui-renderer")).toHaveTextContent("surface-1");
  });

  it("renders legacy table content wrapped in an activity content array", () => {
    render(
      <RenderComponent
        activityType="a2ui-surface"
        content={[{ type: "table", columns: ["name"], rows: [{ name: "Alice" }] }]}
        message={{}}
        agent={{}}
      />,
    );

    expect(screen.getByTestId("legacy-table")).toBeInTheDocument()
    expect(screen.getByTestId("table-columns")).toHaveTextContent("name");
    expect(screen.getByTestId("table-rows")).toHaveTextContent("Alice");
  });
});
