import React from 'react';
import remarkGfm from 'remark-gfm';
import ReactMarkdown from 'react-markdown';
import { WidgetCard } from '../WidgetCard';
import 'highlight.js/styles/github.css';

interface MarkdownWidgetCardProps {
    data: {
        content: string;
        title?: string;
    };
}

export function MarkdownWidget({ data }: MarkdownWidgetCardProps) {
    return (
        <WidgetCard title={data.title}>
            <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                    a: ({ node, ...props }) => (
                        <a {...props} target="_blank" rel="noreferrer" />
                    ),
                    img: ({ node, ...props }) => (
                        <img {...props} loading="lazy" style={{ maxWidth: '100%' }} />
                    ),
                }}
            >
                {data.content}
            </ReactMarkdown>
        </WidgetCard>

    );
}
