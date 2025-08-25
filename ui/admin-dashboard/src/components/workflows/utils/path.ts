/**
 * 生成带圆角的正交折线路径
 * 思路：
 *  1. 仍使用 “先水平后垂直” 或 “先垂直后水平” 的三段式
 *  2. 在两个拐角处用二次贝塞尔 Q 做圆角
 * @param sx 起点 x
 * @param sy 起点 y
 * @param tx 终点 x
 * @param ty 终点 y
 * @param radius 圆角半径 (默认 14)
 */
export function buildRoundedOrthPath(
    sx: number,
    sy: number,
    tx: number,
    ty: number,
    radius = 14
): string {
    const dx = tx - sx;
    const dy = ty - sy;
    const horizontalFirst = Math.abs(dx) >= Math.abs(dy);

    // 避免过短导致半径大于段长
    const safeR = Math.min(
        radius,
        Math.abs(dx) / 2 - 2 || radius,
        Math.abs(dy) / 2 - 2 || radius
    );

    if (horizontalFirst) {
        // M -> H 到拐角前 safeR -> Q -> V -> Q -> H
        const midX = sx + dx / 2;
        const p1x = midX - safeR;
        const p2x = midX + safeR;

        return [
            `M ${sx} ${sy}`,
            `L ${p1x} ${sy}`,
            // 第一拐角 (向下 / 上)
            `Q ${midX} ${sy} ${midX} ${sy + (dy > 0 ? safeR : -safeR)}`,
            `L ${midX} ${ty - (dy > 0 ? safeR : -safeR)}`,
            // 第二拐角
            `Q ${midX} ${ty} ${p2x} ${ty}`,
            `L ${tx} ${ty}`,
        ].join(' ');
    } else {
        const midY = sy + dy / 2;
        const p1y = midY - safeR;
        const p2y = midY + safeR;

        return [
            `M ${sx} ${sy}`,
            `L ${sx} ${p1y}`,
            `Q ${sx} ${midY} ${sx + (dx > 0 ? safeR : -safeR)} ${midY}`,
            `L ${tx - (dx > 0 ? safeR : -safeR)} ${midY}`,
            `Q ${tx} ${midY} ${tx} ${p2y}`,
            `L ${tx} ${ty}`,
        ].join(' ');
    }
}
