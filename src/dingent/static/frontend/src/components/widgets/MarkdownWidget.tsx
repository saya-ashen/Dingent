import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface MarkdownWidgetCardProps {
    data: {
        content: string;
    };
}

export function MarkdownWidget({ data }: MarkdownWidgetCardProps) {
    return (
        <div className="max-w-4xl w-full bg-white/80 backdrop-blur-sm rounded-lg shadow-lg overflow-hidden">
            <article className="prose prose-indigo lg:prose-xl p-6">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {data.content}
                </ReactMarkdown>
            </article>
        </div>
    );
}
