import type { FC } from "react";
import { Handle, Position } from "@xyflow/react";

interface AssistantNodeProps {
    data: {
        isStart?: boolean;
        assistantName: string;
        description?: string;
    };
}

// Base style for the connection handles remains the same
const circleBase: React.CSSProperties = {
    width: 14,
    height: 14,
    border: '2px solid #fff',
    borderRadius: '50%',
    position: 'absolute',
    top: '50%',
    transform: 'translateY(-50%)',
    cursor: 'crosshair',
    transition: 'box-shadow .2s, transform .2s',
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
                width: 100,// Set fixed width
                height: 80,// Set fixed height to make it a square
                padding: '16px', // Adjusted padding for a square shape
                display: 'flex', // Use flexbox for easy centering
                flexDirection: 'column',
                justifyContent: 'center',
                alignItems: 'center',
                textAlign: 'center', // Center all text inside
                position: 'relative',
                borderRadius: 18, // Slightly increased border radius for a softer look
                boxShadow:
                    isStart
                        ? '0 4px 14px -4px rgba(22,163,74,0.35),0 1px 0 rgba(255,255,255,0.7) inset'
                        : '0 4px 10px -2px rgba(0,0,0,0.08),0 1px 0 rgba(255,255,255,0.6) inset',
                fontSize: 12,
                lineHeight: 1.3,
                transition: 'box-shadow .25s, border-color .25s, transform .25s',
            }}
            data-start={isStart ? 'true' : 'false'}
        >
            {/* Handles remain the same, they are positioned relative to the container */}
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
            <div>
                <div
                    style={{
                        fontWeight: 600,
                        fontSize: 10, // Slightly larger font for title
                        color: '#0f172a',
                        letterSpacing: 0.2,
                        marginBottom: 4, // Adjust space between title and description
                    }}
                >
                    {data.assistantName}
                </div>
                {data.description && (
                    <div
                        style={{
                            fontSize: 8,
                            color: '#64748b',
                            whiteSpace: 'normal', // Allow text to wrap
                            lineHeight: 1.4,
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
