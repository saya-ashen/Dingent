import React, { useState, useMemo, useCallback, useDeferredValue } from "react";
import ReactMarkdown from "react-markdown";
import type { Pluggable } from "unified";
import { WidgetCard } from '../WidgetCard';
import {
    ColumnDef,
    ColumnFiltersState,
    SortingState,
    ExpandedState,
    flexRender,
    getCoreRowModel,
    getFilteredRowModel,
    getPaginationRowModel,
    getSortedRowModel,
    getExpandedRowModel,
    useReactTable,
    Row,
    Table as TanstackTable,
} from "@tanstack/react-table";

import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import type { TablePayload } from "@/types";

// ------------------------------------
// Configurable Constants / Utilities
// ------------------------------------
const DEFAULT_PAGE_SIZE = 12;

function SortIndicator({ sorted }: { sorted: false | "asc" | "desc" }) {
    if (!sorted) return <span className="ml-1 text-muted-foreground opacity-40">↕</span>;
    return (
        <span className="ml-1">
            {sorted === "asc" ? (
                <span aria-label="Ascending" className="text-primary">▲</span>
            ) : (
                <span aria-label="Descending" className="text-primary">▼</span>
            )}
        </span>
    );
}

interface ExpandedRowContentProps<TData> {
    row: Row<TData>;
    markdown?: boolean;
    renderers?: {
        _extend?: string;
    };
}

function ExpandedRowContent<TData>({ row }: ExpandedRowContentProps<TData>) {
    return (
        <div className="p-4 bg-muted/40 rounded-md animate-in fade-in">
            <h4 className="text-sm font-semibold mb-3 text-muted-foreground">Details</h4>
            <div className="grid gap-3 md:grid-cols-2">
                {row.getVisibleCells().map((cell) => {
                    const headerDef = cell.column.columnDef.header;

                    const headerText =
                        typeof headerDef === "function"
                            ? cell.column.id
                            : String(headerDef ?? "");

                    return (
                        <div
                            key={`${cell.id}-expanded`}
                            className="flex flex-col rounded border bg-background/60 p-2"
                        >
                            <span className="text-xs font-medium text-muted-foreground truncate mb-1">
                                {headerText}
                            </span>
                            <div className="text-sm break-all">
                                {flexRender(cell.column.columnDef.cell, cell.getContext())}
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

interface DataTableWidgetProps<TData> {
    columns: ColumnDef<TData, unknown>[];
    data: TData[];
    isLoading?: boolean;
    title?: string;
    filterColumnId?: string;
    pageSize?: number;
    enableExpand?: boolean;
    enableZebra?: boolean;
    tableContainerClassName?: string;
}

function DataTablePagination<TData>({ table }: { table: TanstackTable<TData> }) {
    const pageIndex = table.getState().pagination.pageIndex;
    const pageCount = table.getPageCount() || 1;
    return (
        <div className="flex flex-wrap items-center justify-end gap-3 py-4">
            <div className="flex-1 text-xs sm:text-sm text-muted-foreground">
                Page {pageIndex + 1} of {pageCount} ({table.getFilteredRowModel().rows.length} rows total)
            </div>
            <div className="flex gap-2">
                <Button
                    variant="outline"
                    size="sm"
                    onClick={() => table.setPageIndex(0)}
                    disabled={!table.getCanPreviousPage()}
                >
                    First
                </Button>
                <Button
                    variant="outline"
                    size="sm"
                    onClick={() => table.previousPage()}
                    disabled={!table.getCanPreviousPage()}
                >
                    Previous
                </Button>
                <Button
                    variant="outline"
                    size="sm"
                    onClick={() => table.nextPage()}
                    disabled={!table.getCanNextPage()}
                >
                    Next
                </Button>
                <Button
                    variant="outline"
                    size="sm"
                    onClick={() => table.setPageIndex(pageCount - 1)}
                    disabled={!table.getCanNextPage()}
                >
                    Last
                </Button>
            </div>
        </div>
    );
}

function DataTableWidget<TData>({
    columns,
    data,
    isLoading = false,
    filterColumnId,
    title,
    pageSize = DEFAULT_PAGE_SIZE,
    enableExpand = true,
    enableZebra = true,
    tableContainerClassName = "",
}: DataTableWidgetProps<TData>) {
    const [sorting, setSorting] = useState<SortingState>([]);
    const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);
    const [expanded, setExpanded] = useState<ExpandedState>({});

    // Single column filter value (only if filterColumnId exists)
    const rawFilterValue =
        (filterColumnId &&
            (columnFilters.find((f) => f.id === filterColumnId)?.value as string)) ||
        "";
    const deferredFilterValue = useDeferredValue(rawFilterValue);

    // Update table state with the deferred value (to avoid excessive re-renders)
    React.useEffect(() => {
        if (!filterColumnId) return;
        setColumnFilters((prev) => {
            const existing = prev.filter((f) => f.id !== filterColumnId);
            if (!deferredFilterValue) return existing;
            return [...existing, { id: filterColumnId, value: deferredFilterValue }];
        });
    }, [deferredFilterValue, filterColumnId]);

    const table = useReactTable({
        data,
        columns,
        getRowId: (_row, index) => `row_${index}`,
        getCoreRowModel: getCoreRowModel(),
        getPaginationRowModel: getPaginationRowModel(),
        getSortedRowModel: getSortedRowModel(),
        getFilteredRowModel: getFilteredRowModel(),
        getExpandedRowModel: getExpandedRowModel(),
        onSortingChange: setSorting,
        onColumnFiltersChange: setColumnFilters,
        onExpandedChange: setExpanded,
        initialState: { pagination: { pageSize } },
        state: { sorting, columnFilters, expanded },
        // Optional: Manual mode support (server-side pagination, etc.) can be extended here
    });

    const onFilterInputChange = useCallback(
        (e: React.ChangeEvent<HTMLInputElement>) => {
            const val = e.target.value;
            if (!filterColumnId) return;
            setColumnFilters((prev) => {
                const others = prev.filter((f) => f.id !== filterColumnId);
                if (!val) return others;
                return [...others, { id: filterColumnId, value: val }];
            });
        },
        [filterColumnId]
    );

    const loadingRowsCount = table.getState().pagination.pageSize || pageSize;

    const renderSkeletonBody = () =>
        Array.from({ length: loadingRowsCount }).map((_, i) => (
            <TableRow key={`skeleton-row-${i}`}>
                {columns.map((_, j) => (
                    <TableCell key={`skeleton-cell-${i}-${j}`}>
                        <Skeleton className="h-5 w-full" />
                    </TableCell>
                ))}
            </TableRow>
        ));

    const renderEmpty = () => (
        <TableRow>
            <TableCell
                colSpan={columns.length}
                className="h-28 text-center text-sm text-muted-foreground"
            >
                No results found.
            </TableCell>
        </TableRow>
    );

    const handleRowToggle = (row: Row<TData>) => {
        if (!enableExpand) return;
        const isAlreadyExpanded = (expanded as Record<string, boolean>)[row.id];

        setExpanded(isAlreadyExpanded ? {} : { [row.id]: true });
    };

    const onRowKeyDown = (e: React.KeyboardEvent, row: Row<TData>) => {
        if (!enableExpand) return;
        if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            handleRowToggle(row);
        }
    };

    const rows = table.getRowModel().rows;
    const { pageSize: tablePageSize } = table.getState().pagination;
    const pageRows = table.getRowModel().rows;

    const emptyRowsCount = pageRows.length < tablePageSize ? tablePageSize - pageRows.length : 0;

    return (
        <div className="space-y-4">
            {title && (
                <div className="flex items-center justify-between flex-wrap gap-2">
                    <h3 className="text-xl font-semibold tracking-tight">{title}</h3>
                </div>
            )}

            {filterColumnId && (
                <div className="max-w-xs">
                    <Input
                        placeholder={`Filter ${filterColumnId}...`}
                        value={rawFilterValue}
                        onChange={onFilterInputChange}
                        className="h-9"
                    />
                </div>
            )}

            <div
                className={
                    "overflow-hidden rounded-lg border bg-white/80 backdrop-blur-sm shadow-sm " +
                    tableContainerClassName
                }
            >
                <Table className="w-full table-fixed">
                    <TableHeader className="bg-muted/40">
                        {table.getHeaderGroups().map((hg) => (
                            <TableRow key={hg.id}>
                                {hg.headers.map((header) => {
                                    if (header.isPlaceholder) return <TableHead key={header.id} />;
                                    const sorted = header.column.getIsSorted();
                                    const canSort = header.column.getCanSort();

                                    return (
                                        <TableHead
                                            key={header.id}
                                            className="whitespace-nowrap"
                                        >
                                            {canSort ? (
                                                <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    className="-ml-2 px-2 hover:bg-transparent data-[state=open]:bg-transparent"
                                                    onClick={() =>
                                                        header.column.toggleSorting(
                                                            header.column.getIsSorted() === "asc"
                                                        )
                                                    }
                                                >
                                                    {flexRender(
                                                        header.column.columnDef.header,
                                                        header.getContext()
                                                    )}
                                                    <SortIndicator sorted={sorted} />
                                                </Button>
                                            ) : (
                                                flexRender(
                                                    header.column.columnDef.header,
                                                    header.getContext()
                                                )
                                            )}
                                        </TableHead>
                                    );
                                })}
                            </TableRow>
                        ))}
                    </TableHeader>

                    <TableBody>
                        {isLoading
                            ? renderSkeletonBody()
                            : rows.length === 0
                                ? renderEmpty()
                                : rows.map((row, idx) => {
                                    const zebra =
                                        enableZebra && idx % 2 === 1
                                            ? "bg-muted/20 dark:bg-muted/30"
                                            : "";
                                    return (
                                        <React.Fragment key={row.id}>
                                            <TableRow
                                                data-state={row.getIsSelected() && "selected"}
                                                tabIndex={enableExpand ? 0 : -1}
                                                aria-expanded={enableExpand ? row.getIsExpanded() : undefined}
                                                onClick={() => handleRowToggle(row)}
                                                onKeyDown={(e) => onRowKeyDown(e, row)}
                                                className={`cursor-pointer select-none transition-colors hover:bg-accent/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50 ${zebra}`}
                                            >
                                                {row.getVisibleCells().map((cell) => (
                                                    <TableCell
                                                        key={cell.id}
                                                        className="max-w-[280px] truncate align-middle"
                                                        title={String(cell.getValue() ?? "")}
                                                    >
                                                        {flexRender(
                                                            cell.column.columnDef.cell,
                                                            cell.getContext()
                                                        )}
                                                    </TableCell>
                                                ))}
                                            </TableRow>
                                            {enableExpand && row.getIsExpanded() && (
                                                <TableRow className="bg-background/70">
                                                    <TableCell colSpan={columns.length} className="p-4">
                                                        <ExpandedRowContent row={row} />
                                                    </TableCell>
                                                </TableRow>
                                            )}
                                        </React.Fragment>
                                    );
                                })}
                        {!isLoading && emptyRowsCount > 0 && (
                            Array.from({ length: emptyRowsCount }).map((_, index) => (
                                <TableRow key={`empty-${index}`} className="hover:bg-transparent pointer-events-none">
                                    <TableCell colSpan={columns.length} style={{ padding: 0, border: 'none' }}>
                                        <div style={{ height: '36px' }}>&nbsp;</div>
                                    </TableCell>
                                </TableRow>
                            ))
                        )}
                    </TableBody>
                </Table>
            </div>

            <DataTablePagination table={table} />
        </div>
    );
}


// -----------------------------
// Public Component: TableWidget
// -----------------------------
interface TableWidgetProps {
    data: TablePayload;
    pageSize?: number;
    enableExpand?: boolean;
    enableZebra?: boolean;
    enableMarkdown?: boolean;
    filterColumnId?: string;
    className?: string;
    tableContainerClassName?: string;
    remarkPlugins?: Pluggable[];
    rehypePlugins?: Pluggable[];
}

export function TableWidget({
    data,
    pageSize = DEFAULT_PAGE_SIZE,
    enableExpand = true,
    enableZebra = true,
    enableMarkdown = true,
    filterColumnId,
    tableContainerClassName = "",
    remarkPlugins,
    rehypePlugins,
}: TableWidgetProps) {
    const isDataValid =
        data && Array.isArray(data.columns) && Array.isArray(data.rows);
    const title = data?.title || "";

    // Generate columns: memoize to avoid re-generation on every render (depends on data.columns)
    const columns: ColumnDef<Record<string, unknown>>[] = useMemo(() => {
        if (!isDataValid) return [];
        return data.columns.map((header) => {
            return {
                accessorKey: header,
                header,
                enableSorting: true,
                cell: ({ getValue }) => {
                    const raw = getValue();
                    const text = raw == null ? "" : String(raw);
                    if (!enableMarkdown) {
                        return <span className="block truncate">{text}</span>;
                    }
                    return (
                        <ReactMarkdown
                            remarkPlugins={remarkPlugins}
                            rehypePlugins={rehypePlugins}
                            // Add components to simplify tags
                            components={{
                                p: (props) => <p {...props} className="m-0 leading-snug" />,
                                a: (props) => (
                                    <a
                                        {...props}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="text-blue-600 hover:underline"
                                    />
                                ),
                            }}
                        >
                            {text}
                        </ReactMarkdown>
                    );
                },
            };
        });
    }, [data, enableMarkdown, isDataValid, remarkPlugins, rehypePlugins]);

    const tableData = useMemo(
        () => (isDataValid ? (data.rows as Record<string, unknown>[]) : []),
        [data, isDataValid]
    );

    const isLoading = !isDataValid;

    return (
        <WidgetCard>
            <DataTableWidget
                columns={columns}
                data={tableData}
                isLoading={isLoading}
                title={title}
                filterColumnId={filterColumnId}
                pageSize={pageSize}
                enableExpand={enableExpand}
                enableZebra={enableZebra}
                tableContainerClassName={tableContainerClassName}
            />
        </WidgetCard>
    );
}
