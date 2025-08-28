import { NextResponse } from 'next/server';

export async function GET(
    request: Request,
    { params }: { params: Promise<{ id: string }> } // 注意这里声明为 Promise
) {
    const { id } = await params; // 必须 await

    if (!id) {
        return NextResponse.json({ message: 'Missing resource id' }, { status: 400 });
    }

    const backendApiUrl = process.env.BACKEND_API_URL ?? 'http://localhost:8000';
    const targetUrl = `${backendApiUrl}/api/resource/${id}`;


    try {
        // 如果不想把 Host 等前端请求头原样转发，可以手动挑选需要的头
        const forwardHeaders = new Headers(request.headers);
        forwardHeaders.delete('host');

        const response = await fetch(targetUrl, {
            method: 'GET',
            headers: forwardHeaders,
        });

        // 直接返回下游响应（克隆 headers，避免某些只读/不可复用问题）
        const headers = new Headers(response.headers);
        return new Response(response.body, {
            status: response.status,
            statusText: response.statusText,
            headers,
        });
    } catch (error) {
        console.error(`Error proxying request to ${targetUrl}:`, error);
        return NextResponse.json(
            { message: 'Error connecting to the backend service.' },
            { status: 500 }
        );
    }
}
