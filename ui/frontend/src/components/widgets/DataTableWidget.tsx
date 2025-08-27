"use client"

import * as React from "react"
import { useMemo } from "react"
import ReactMarkdown from 'react-markdown' // 1. Import ReactMarkdown
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
    Table as TanstackTable,
    HeaderContext,
} from "@tanstack/react-table"
import { TablePayload } from "@/types";

import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"


interface DataTableWidgetProps<TData> {
    columns: ColumnDef<TData, unknown>[]
    data: TData[]
    isLoading?: boolean
    title?: string
    filterColumnId?: string
}

function DataTablePagination<TData>({ table }: { table: TanstackTable<TData> }) {
    return (
        <div className="flex items-center justify-end space-x-2 py-4">
            <div className="flex-1 text-sm text-muted-foreground">
                Page {table.getState().pagination.pageIndex + 1} of{" "}
                {table.getPageCount() || 1}
            </div>
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
        </div>
    )
}

function DataTableWidget<TData>({
    columns,
    data,
    isLoading = false,
    filterColumnId,
    title,
}: DataTableWidgetProps<TData>) {
    const [sorting, setSorting] = React.useState<SortingState>([])
    const [columnFilters, setColumnFilters] = React.useState<ColumnFiltersState>([])
    const [expanded, setExpanded] = React.useState<ExpandedState>({})

    const table = useReactTable({
        data,
        columns,
        getRowId: (row, index) => `row_${index}`,
        getCoreRowModel: getCoreRowModel(),
        getPaginationRowModel: getPaginationRowModel(),
        getSortedRowModel: getSortedRowModel(),
        getFilteredRowModel: getFilteredRowModel(),
        getExpandedRowModel: getExpandedRowModel(),
        onSortingChange: setSorting,
        onColumnFiltersChange: setColumnFilters,
        onExpandedChange: setExpanded,
        initialState: {
            pagination: { pageSize: 6 },
        },
        state: {
            sorting,
            columnFilters,
            expanded,
        },
    })

    const renderTableBody = () => {
        if (isLoading) {
            return Array.from({ length: 5 }).map((_, i) => (
                <TableRow key={`skeleton-row-${i}`}>
                    {columns.map((_, j) => (
                        <TableCell key={`skeleton-cell-${i}-${j}`}>
                            <Skeleton className="h-6 w-full" />
                        </TableCell>
                    ))}
                </TableRow>
            ));
        }

        if (table.getRowModel().rows.length === 0) {
            return (
                <TableRow>
                    <TableCell colSpan={columns.length} className="h-24 text-center">
                        No results.
                    </TableCell>
                </TableRow>
            );
        }

        return table.getRowModel().rows.map(row => (
            <React.Fragment key={row.id}>
                <TableRow
                    data-state={row.getIsSelected() && "selected"}
                    onClick={() => row.toggleExpanded()}
                    className="cursor-pointer"
                >
                    {row.getVisibleCells().map(cell => (
                        <TableCell key={cell.id} className="max-w-[250px] truncate" title={String(cell.getValue())}>
                            {flexRender(cell.column.columnDef.cell, cell.getContext())}
                        </TableCell>
                    ))}
                </TableRow>
                {row.getIsExpanded() && (
                    <TableRow>
                        <TableCell colSpan={columns.length} className="p-4 bg-muted/50">
                            <h4 className="text-md font-bold mb-2">Full Details</h4>
                            <ul className="space-y-2">
                                {row.getVisibleCells().map(cell => (
                                    <li key={`${cell.id}-expanded`} className="flex flex-col">
                                        <span className="text-sm font-semibold text-muted-foreground">
                                            {flexRender(
                                                cell.column.columnDef.header,
                                                // We manually create a context object that looks like HeaderContext.
                                                // We can cast the cell as a "mock" header for type-safety.
                                                {
                                                    table: table,
                                                    column: cell.column,
                                                    header: {
                                                        id: `${cell.column.id}_header`,
                                                        column: cell.column,
                                                        depth: 0, // Mock depth
                                                        index: 0, // Mock index
                                                        isPlaceholder: false,
                                                        colSpan: 1,
                                                        rowSpan: 1,
                                                        subHeaders: [],
                                                        getContext: () => ({ /* Recursion avoided */ } as HeaderContext<TData, unknown>),
                                                        getLeafHeaders: () => [],
                                                        getResizeHandler: () => (() => { }),
                                                        getStart: () => 0,
                                                        getSize: () => 0,
                                                    } as unknown as HeaderContext<TData, unknown>['header'],
                                                }
                                            )}
                                        </span>
                                        <span className="text-sm break-words whitespace-normal">
                                            {flexRender(cell.column.columnDef.cell, cell.getContext())}
                                        </span>
                                    </li>
                                ))}
                            </ul>
                        </TableCell>
                    </TableRow>
                )}
            </React.Fragment>
        ));
    }


    return (
        <div className="space-y-4">
            {title && <h3 className="text-2xl font-semibold tracking-tight">{title}</h3>}

            {filterColumnId && (
                <Input
                    placeholder={`Filter by ${filterColumnId}...`}
                    value={(table.getColumn(filterColumnId)?.getFilterValue() as string) ?? ""}
                    onChange={(event) => table.getColumn(filterColumnId)?.setFilterValue(event.target.value)}
                    className="max-w-sm"
                />
            )}

            <div className="overflow-hidden rounded-md border">
                <Table>
                    <TableHeader>
                        {table.getHeaderGroups().map(headerGroup => (
                            <TableRow key={headerGroup.id}>
                                {headerGroup.headers.map(header => (
                                    <TableHead key={header.id}>
                                        {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
                                    </TableHead>
                                ))}
                            </TableRow>
                        ))}
                    </TableHeader>
                    <TableBody>{renderTableBody()}</TableBody>
                </Table>
            </div>
            <DataTablePagination table={table} />
        </div>
    )
}


export function TableWidget({ data }: { data: TablePayload }) {
    const { tableColumns, tableData, title } = useMemo(() => {
        if (!data || !data.columns || !data.rows) {
            return { tableColumns: [], tableData: [], title: "" };
        }

        const columns: ColumnDef<Record<string, unknown>>[] = data.columns.map(header => ({
            accessorKey: header,
            header: header,
            cell: ({ getValue }) => (
                <ReactMarkdown
                // Add basic styling to prevent large margins from paragraphs
                // className="prose prose-sm prose-p:my-0"
                >
                    {String(getValue() ?? '')}
                </ReactMarkdown>
            ),
        }));

        return { tableColumns: columns, tableData: data.rows, title: data.title };
    }, [data]);

    const isLoading = !data;

    return (
        <div className="max-w-4xl w-full p-4 bg-white/80 backdrop-blur-sm rounded-lg shadow-lg">
            <DataTableWidget
                columns={tableColumns}
                data={tableData as Record<string, unknown>[]}
                isLoading={isLoading}
                title={title as string | undefined}
            />
        </div>
    );
}
