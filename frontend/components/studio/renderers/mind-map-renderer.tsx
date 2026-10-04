"use client";

import { useMemo } from "react";
import ReactFlow, {
  Background,
  Controls,
  Handle,
  Position,
  type Edge,
  type Node,
} from "reactflow";
import "reactflow/dist/style.css";
import type { MindMapContent, MindNode } from "@/types";

/**
 * Renders a mind map as an interactive radial graph. The recursive MindNode
 * tree is flattened into reactflow nodes/edges with a simple angular layout:
 * the root sits centre, level-1 branches fan out on a ring, and deeper nodes
 * extend outward along their parent's angle.
 */

const LEVEL_COLORS = [
  { bg: "#7c3aed", ring: "#a78bfa" }, // root — violet
  { bg: "#2563eb", ring: "#93c5fd" }, // l1 — blue
  { bg: "#0d9488", ring: "#5eead4" }, // l2 — teal
  { bg: "#d97706", ring: "#fcd34d" }, // l3 — amber
];

function colorFor(level: number) {
  return LEVEL_COLORS[Math.min(level, LEVEL_COLORS.length - 1)] as {
    bg: string;
    ring: string;
  };
}

function MindNodeCard({ data }: { data: { label: string; level: number } }) {
  const c = colorFor(data.level);
  const isRoot = data.level === 0;
  return (
    <div
      style={{
        background: isRoot ? c.bg : "var(--rf-node-bg, #fff)",
        borderColor: c.bg,
        color: isRoot ? "#fff" : "inherit",
      }}
      className="max-w-[190px] rounded-xl border-2 px-3 py-2 text-center text-sm font-medium shadow-sm"
    >
      <Handle type="target" position={Position.Left} className="!bg-transparent !border-0" />
      {data.label}
      <Handle type="source" position={Position.Right} className="!bg-transparent !border-0" />
    </div>
  );
}

const nodeTypes = { mind: MindNodeCard };

function layout(root: MindNode): { nodes: Node[]; edges: Edge[] } {
  const nodes: Node[] = [];
  const edges: Edge[] = [];
  let id = 0;

  // Count leaves to allocate vertical space per branch.
  function countLeaves(n: MindNode): number {
    if (!n.children || n.children.length === 0) return 1;
    return n.children.reduce((s, c) => s + countLeaves(c), 0);
  }

  const X_GAP = 260;
  const Y_GAP = 70;
  let cursorY = 0;

  function walk(n: MindNode, level: number, parentId: string | null): void {
    const myId = String(id++);
    const leaves = countLeaves(n);
    const isLeaf = !n.children || n.children.length === 0;

    let y: number;
    if (isLeaf) {
      y = cursorY * Y_GAP;
      cursorY += 1;
    } else {
      const startY = cursorY;
      n.children!.forEach((c) => walk(c, level + 1, myId));
      const endY = cursorY - 1;
      y = ((startY + endY) / 2) * Y_GAP;
    }

    nodes.push({
      id: myId,
      type: "mind",
      position: { x: level * X_GAP, y },
      data: { label: n.label || "…", level },
    });
    if (parentId !== null) {
      edges.push({
        id: `e${parentId}-${myId}`,
        source: parentId,
        target: myId,
        type: "smoothstep",
        style: { stroke: colorFor(level).ring, strokeWidth: 2 },
      });
    }
  }

  walk(root, 0, null);
  return { nodes, edges };
}

export function MindMapRenderer({ content }: { content: MindMapContent }) {
  const { nodes, edges } = useMemo(
    () => layout(content.root ?? { label: content.title, children: [] }),
    [content],
  );

  return (
    <div className="pb-6">
      <h1 className="mb-3 text-xl font-bold">{content.title}</h1>
      <div className="h-[520px] w-full overflow-hidden rounded-xl border">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.2 }}
          proOptions={{ hideAttribution: true }}
          nodesDraggable
          minZoom={0.2}
        >
          <Background color="#94a3b8" gap={20} size={1} />
          <Controls showInteractive={false} />
        </ReactFlow>
      </div>
      <p className="mt-2 text-center text-xs text-muted-foreground">
        Drag nodes to rearrange · scroll to zoom
      </p>
    </div>
  );
}
