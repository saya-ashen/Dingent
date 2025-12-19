import { Workflow, WorkflowNode, WorkflowEdge } from "@/types/entity";


export function normalizeWorkflow(wf: Workflow | null) {
  const nodes: WorkflowNode[] = [];
  const edges: WorkflowEdge[] = [];
  if (!wf) return { nodes, edges };


  const rawNodes = structuredClone(wf.nodes ?? []);
  let hasStart = false;


  for (const n of rawNodes) {
    const isStart = (n)?.type === "start" || (n)?.data?.isStart;
    if (isStart) hasStart = true;
    nodes.push({
      ...n,
      type: "assistant",
      data: { ...(n).data, isStart },
    } as WorkflowNode);
  }


  if (!hasStart && nodes.length > 0) {
    (nodes[0]!.data).isStart = true;
  }


  edges.push(...structuredClone(wf.edges ?? []));
  return { nodes, edges };
}
