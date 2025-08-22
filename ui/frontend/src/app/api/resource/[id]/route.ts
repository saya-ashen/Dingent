import { NextResponse } from 'next/server';

/**
 * Reverse proxy for a backend resource
 */
export async function GET(request: Request, context: unknown) {
    const contextTyped = context as { params?: { id?: string | string[] } };
    const raw = contextTyped.params?.id;
    const resourceId = Array.isArray(raw) ? raw[0] : raw;

    if (!resourceId) {
        return NextResponse.json({ message: 'Missing resource id' }, { status: 400 });
    }

    const backendApiUrl = process.env.BACKEND_API_URL ?? 'http://127.0.0.1:2024';
    const targetUrl = `${backendApiUrl}/api/resource/${resourceId}`;

    console.log(`Forwarding request for resource [${resourceId}] to [${targetUrl}]`);

    try {
        const response = await fetch(targetUrl, {
            method: 'GET',
            headers: request.headers, // forward original request headers
        });

        // Stream back the response using the standard Response
        return new Response(response.body, {
            status: response.status,
            statusText: response.statusText,
            headers: response.headers,
        });
    } catch (error) {
        console.error(`Error proxying request to ${targetUrl}:`, error);
        return NextResponse.json(
            { message: 'Error connecting to the backend service.' },
            { status: 500 }
        );
    }
}
