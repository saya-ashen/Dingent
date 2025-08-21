// app/api/resource/[id]/route.ts

import { NextRequest, NextResponse } from 'next/server';

/**
 * This route handler acts as a reverse proxy.
 * It takes a resource ID from the URL, fetches the corresponding data
 * from a backend service, and streams the response back to the client.
 */
export const GET = async (
    req: NextRequest,
    // highlight-start
    { params }: { params: { id: string } }
    // highlight-end
) => {
    const { id: resourceId } = await params
    const backendApiUrl = process.env.BACKEND_API_URL || 'http://127.0.0.1:2024';
    const targetUrl = `${backendApiUrl}/api/resource/${resourceId}`;

    console.log(`Forwarding request for resource [${resourceId}] to [${targetUrl}]`);

    try {
        const response = await fetch(targetUrl, {
            method: 'GET',
            headers: req.headers, // Forwarding original request headers
        });

        if (!response.ok) {
            // If the backend returned an error, create a corresponding error response.
            // The response body from the backend is piped through.
            return new NextResponse(response.body, {
                status: response.status,
                statusText: response.statusText,
                headers: response.headers,
            });
        }

        // Stream the response from the backend directly to the client.
        // This is memory-efficient as your Next.js server doesn't need to
        // load the entire response into memory before sending it.
        return new NextResponse(response.body, {
            status: response.status,
            statusText: response.statusText,
            headers: response.headers, // Forwarding backend response headers
        });

    } catch (error) {
        console.error(`Error proxying request to ${targetUrl}:`, error);
        // If the fetch itself fails (e.g., network error, backend is down),
        // return a 500 Internal Server Error.
        return NextResponse.json(
            { message: 'Error connecting to the backend service.' },
            { status: 500 }
        );
    }
};
