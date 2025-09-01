import React, { FC } from 'react';
import { Handle, Position } from '@xyflow/react';

interface AssistantNodeProps {
    data: {
        isStart?: boolean;
        assistantName: string;
        description?: string;
    };
}

// (If it's declared elsewhere, keep using that one)
const circleBase: React.CSSProperties = {
    width: 10,
    height: 10,
    borderRadius: '50%',
    position: 'absolute',
    top: '50%',
    transform: 'translateY(-50%)',
    border: '2px solid #fff',
    boxShadow: '0 0 0 1px rgba(0,0,0,0.05)',
    cursor: 'crosshair',
};

const AssistantNode: FC<AssistantNodeProps> = ({ data }) => {
    const isStart = !!data.isStart;

    const borderColor = isStart ? '#16a34a' : '#cbd5e1';
    const bgGradient = isStart
        ? 'linear-gradient(145deg,#dcfce7,#f0fdf4)'
        : 'linear-gradient(145deg,#ffffff,#f1f5f9)';

    return (
        <div
            className="workflow-assistant-node group"
            style={{
                border: `2px solid ${borderColor}`,
                background: bgGradient,
                width: 100,
                height: 80,
                padding: '16px',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'center',
                alignItems: 'center',
                textAlign: 'center',
                position: 'relative',
                borderRadius: 18,
                boxShadow: isStart
                    ? '0 4px 14px -4px rgba(22,163,74,0.35),0 1px 0 rgba(255,255,255,0.7) inset'
                    : '0 4px 10px -2px rgba(0,0,0,0.08),0 1px 0 rgba(255,255,255,0.6) inset',
                fontSize: 12,
                lineHeight: 1.3,
                transition: 'box-shadow .25s, border-color .25s, transform .25s',
                overflow: 'hidden', // Ensures internal overflow doesn't visually escape
            }}
            data-start={isStart ? 'true' : 'false'}
        >
            {/* Connection Handles */}
            <Handle
                type="target"
                position={Position.Left}
                id="left-in"
                style={{ ...circleBase, left: -8, background: '#64748b' }}
            />
            <Handle
                type="source"
                position={Position.Left}
                id="left-out"
                style={{ ...circleBase, left: -8, background: '#10b981' }}
            />
            <Handle
                type="target"
                position={Position.Right}
                id="right-in"
                style={{ ...circleBase, right: -8, background: '#64748b' }}
            />
            <Handle
                type="source"
                position={Position.Right}
                id="right-out"
                style={{ ...circleBase, right: -8, background: '#10b981' }}
            />

            {/* Text Content */}
            <div
                style={{
                    width: '100%',
                    display: 'flex',
                    flexDirection: 'column',
                    // Reserve vertical space so ellipsis can work predictably
                    overflow: 'hidden',
                }}
            >
                <div
                    title={data.assistantName} // Tooltip to show full content
                    style={{
                        fontWeight: 600,
                        fontSize: 8,
                        color: '#0f172a',
                        letterSpacing: 0.2,
                        marginBottom: 4,
                        maxWidth: '100%',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap', // Single-line ellipsis
                    }}
                >
                    {data.assistantName}
                </div>

                {data.description && (
                    <div
                        title={data.description}
                        style={{
                            fontSize: 6,
                            color: '#64748b',
                            lineHeight: 1.4,
                            maxWidth: '100%',
                            overflow: 'hidden',
                            display: '-webkit-box',
                            WebkitBoxOrient: 'vertical',
                            WebkitLineClamp: 3, // Clamp to 3 lines
                            // Fallback for non-WebKit (will just crop)
                        }}
                    >
                        {data.description}
                    </div>
                )}
            </div>
        </div>
    );
};

export default AssistantNode;
