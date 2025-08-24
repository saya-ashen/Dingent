import type { FC } from "react";
import { Handle, Position } from "@xyflow/react";

const StartNode: FC = () => {
    return (
        <div className="px-4 py-2 rounded-full bg-emerald-500 text-white text-sm font-semibold shadow border border-emerald-600">
            Start
            <Handle type="source" position={Position.Right} />
        </div>
    );
};

export default StartNode;
