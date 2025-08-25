import { BaseEdge, EdgeLabelRenderer, type EdgeProps } from '@xyflow/react';
import { useMemo, type ReactNode } from 'react';
import { buildRoundedOrthPath } from '../utils/path';

const SINGLE_COLOR = '#2563eb';
const BIDIR_COLOR = '#a855f7';

let globalDefsInjected = false;

/**
 * 自定义 Edge：
 * - 单向：蓝色，末端箭头
 * - 双向：紫色，两端箭头 + 轻微流动动画（可通过 data.animate 禁用）
 * - 圆角正交路径
 * - Hover 发光（CSS + filter）
 */
export default function DirectionalEdge(props: EdgeProps) {
    const {
        id,
        sourceX,
        sourceY,
        targetX,
        targetY,
        data,
        style,
        selected,
    } = props;

    const mode: 'single' | 'bidirectional' =
        data?.mode === 'bidirectional' ? 'bidirectional' : 'single';

    const stroke = mode === 'bidirectional' ? BIDIR_COLOR : SINGLE_COLOR;

    const animate = mode === 'bidirectional' && data?.animate !== false;

    const path = useMemo(
        () => buildRoundedOrthPath(sourceX, sourceY, targetX, targetY, 14),
        [sourceX, sourceY, targetX, targetY]
    );

    // marker ids
    const markerEndId = `m-end-${id}`;
    const markerStartId = `m-start-${id}`;

    // 全局 defs 只注入一次
    if (!globalDefsInjected && typeof document !== 'undefined') {
        const svgRoot = document.getElementById('__global_edge_defs__');
        if (!svgRoot) {
            const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
            svg.setAttribute('width', '0');
            svg.setAttribute('height', '0');
            svg.style.position = 'absolute';
            svg.style.opacity = '0';
            svg.id = '__global_edge_defs__';
            svg.innerHTML = `
        <defs>
          <filter id="edge-glow" x="-50%" y="-50%" width="200%" height="200%">
            <feDropShadow dx="0" dy="0" stdDeviation="3" flood-color="${BIDIR_COLOR}" flood-opacity="0.45"/>
          </filter>
          <filter id="edge-glow-blue" x="-50%" y="-50%" width="200%" height="200%">
            <feDropShadow dx="0" dy="0" stdDeviation="3" flood-color="${SINGLE_COLOR}" flood-opacity="0.4"/>
          </filter>
        </defs>
      `;
            document.body.appendChild(svg);
        }
        globalDefsInjected = true;
    }

    return (
        <g
            className={`custom-directional-edge ${mode} ${selected ? 'selected' : ''}`}
            data-edgeid={id}
        >
            <defs>
                <marker
                    id={markerEndId}
                    viewBox="0 0 10 10"
                    refX="9"
                    refY="5"
                    markerWidth="5"
                    markerHeight="5"
                    orient="auto-start-reverse"
                >
                    <path d="M 0 0 L 10 5 L 0 10 z" fill={stroke} />
                </marker>
                {mode === 'bidirectional' && (
                    <marker
                        id={markerStartId}
                        viewBox="0 0 10 10"
                        refX="1"
                        refY="5"
                        markerWidth="5"
                        markerHeight="5"
                        orient="auto"
                    >
                        <path d="M 10 0 L 0 5 L 10 10 z" fill={stroke} />
                    </marker>
                )}
            </defs>
            <BaseEdge
                path={path}
                style={{
                    stroke,
                    strokeWidth: 2.8,
                    fill: 'none',
                    filter: selected
                        ? `url(#${mode === 'bidirectional' ? 'edge-glow' : 'edge-glow-blue'})`
                        : 'none',
                    ...(style || {}),
                }}
                markerEnd={`url(#${markerEndId})`}
                markerStart={
                    mode === 'bidirectional' ? `url(#${markerStartId})` : undefined
                }
                interactionWidth={24}
                className={animate ? 'edge-animatable' : undefined}
            />
            {data?.showLabel as ReactNode && (
                <EdgeLabelRenderer>
                    <div
                        style={{
                            position: 'absolute',
                            transform: `translate(-50%, -50%)`,
                            left: (sourceX + targetX) / 2,
                            top: (sourceY + targetY) / 2,
                            pointerEvents: 'all',
                            background: 'rgba(17,24,39,0.75)',
                            color: '#fff',
                            padding: '2px 6px',
                            fontSize: 10,
                            borderRadius: 4,
                            backdropFilter: 'blur(4px)',
                            boxShadow: '0 0 4px rgba(0,0,0,0.4)',
                        }}
                    >
                        {mode === 'bidirectional' ? 'bidirectional' : 'single'}
                    </div>
                </EdgeLabelRenderer>
            )}
        </g>
    );
}
