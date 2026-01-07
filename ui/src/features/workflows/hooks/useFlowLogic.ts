import { useCallback } from "react";
import {
  addEdge,
  applyEdgeChanges,
  applyNodeChanges,
  Connection,
  EdgeChange,
  NodeChange,
  useReactFlow,
  type Edge,
} from "@xyflow/react";
import { toast } from "sonner";
import { AssistantNodeType } from "../components/nodes/AssistantNode";
import { Assistant } from "@/types/entity";
import { v4 as uuidv4 } from "uuid";

// 这里定义你的 Node 数据类型

export function useFlowLogic(
  nodes: AssistantNodeType[],
  setNodes: React.Dispatch<React.SetStateAction<AssistantNodeType[]>>,
  edges: Edge[],
  setEdges: React.Dispatch<React.SetStateAction<Edge[]>>,
) {
  const { screenToFlowPosition } = useReactFlow();

  const onNodesChange = useCallback(
    (changes: NodeChange<AssistantNodeType>[]) =>
      setNodes((nds) => applyNodeChanges(changes, nds)),
    [setNodes],
  );

  const onEdgesChange = useCallback(
    (changes: EdgeChange[]) =>
      setEdges((eds) => applyEdgeChanges(changes, eds)),
    [setEdges],
  );

  const onConnect = useCallback(
    (connection: Connection) => {
      // 可以在这里加各种校验逻辑
      if (connection.source === connection.target) return;
      setEdges((eds) => addEdge({ ...connection, type: "directional" }, eds));
    },
    [setEdges],
  );

  // 处理拖拽放置
  const onDrop = useCallback(
    (event: React.DragEvent, assistant: Assistant | null) => {
      event.preventDefault();
      if (!assistant) return;

      // 检查是否已存在
      const alreadyExists = nodes.some(
        (n) => n.data.assistantId === assistant.id,
      );
      if (alreadyExists) {
        toast.warning("This assistant is already in the workflow");
        return;
      }

      const position = screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      });

      const newNode: AssistantNodeType = {
        id: uuidv4(),
        type: "assistant", // 确保你在 nodeTypes 里注册了这个类型
        position,
        data: {
          assistantId: assistant.id,
          name: assistant.name,
          isStart: nodes.length === 0, // 如果是第一个节点，设为 Start
        },
      };

      setNodes((nds) => [...nds, newNode]);
    },
    [nodes, setNodes, screenToFlowPosition],
  );

  return { onNodesChange, onEdgesChange, onConnect, onDrop };
}
