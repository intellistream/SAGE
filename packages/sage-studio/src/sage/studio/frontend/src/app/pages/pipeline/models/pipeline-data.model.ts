// models/pipeline-data.model.ts

// 确保 Node 接口包含源节点和终结点标记
export interface Node {
  id: string;
  type: string;
  name: string;
  fullName?: string;
  description?: string;
  operatorId?: string | number; // 添加操作符ID字段，用于引用原始操作符
  x: number;
  y: number;
  isSource?: boolean; // 是否为源节点
  isSink?: boolean;   // 是否为终结点
  // Add any other node-specific properties here
}

export interface Edge {
  id: string;
  source: string;
  target: string;
  // Add any other edge-specific properties here (e.g., label, connection type)
}

export interface PipelineData {
  nodes: Node[];
  edges: Edge[];
  sourceNodeId?: string;
  sinkNodeId?: string;
}


// 定义拓扑图数据结构，用于传递给后端
export interface TopologyData {
  // 拓扑图基本信息
  id?: string;
  name?: string;
  description?: string;
  
  // 节点信息
  nodes: TopologyNode[];
  
  // 边信息
  edges: TopologyEdge[];
  
  // 源节点和终结点
  sourceNodeId: string;
  sinkNodeId: string;
}

// 简化的节点结构，只包含后端需要的信息
export interface TopologyNode {
  id: string;
  operatorId: string | number; // 原始操作符ID
  type: string;
  name: string;
  isSource: boolean;
  isSink: boolean;
  // 可以添加其他节点配置信息
  config?: any;
}

// 简化的边结构
export interface TopologyEdge {
  id: string;
  source: string; // 源节点ID
  target: string; // 目标节点ID
  // 可以添加边的配置信息
  config?: any;
}