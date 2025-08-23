import React from 'react';
import remarkGfm from 'remark-gfm';
import ReactMarkdown from 'react-markdown';
import 'highlight.js/styles/github.css';
import './MarkdownWidget.css';

interface MarkdownWidgetCardProps {
    data: {
        content: string;
    };
}

export function MarkdownWidget({ data }: MarkdownWidgetCardProps) {
    return (
        <ReactMarkdown
            // className="markdown-body"
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
    );
}
