// src/sage_examples/pipeline/pipeline.service.ts
import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';
// 修改导入，避免与下方自定义的 Node 接口冲突
import { Node as PipelineNode, Edge, PipelineData,TopologyNode,TopologyEdge,TopologyData } from './models/pipeline-data.model';
import { v4 as uuidv4 } from 'uuid'; // Import uuid

@Injectable({
  providedIn: 'root' // Or provide in PipelineModule if preferred
})
export class PipelineService {
  private apiUrl = `http://localhost:8080/api/pipeline`;
  // Use BehaviorSubject to hold the current state and emit changes
  private _nodes = new BehaviorSubject<PipelineNode[]>([]);
  nodes$: Observable<PipelineNode[]> = this._nodes.asObservable(); // Observable for components to subscribe to

  private _edges = new BehaviorSubject<Edge[]>([]);
  edges$: Observable<Edge[]> = this._edges.asObservable(); // Observable for components to subscribe to

  private firstNodeForEdge: string | null = null; // State for tracking edge creation

  constructor(private http: HttpClient) {
     // Optional: Load initial data here
     // this.loadPipelineData({...});
  }
  submitPipeline(topologyData: TopologyData): Observable<any> {

    // 发送到后端API
    return this.http.post<any>(`${this.apiUrl}/submit`, topologyData);
  }
  // --- Node Management ---

  // 修改 addNode 方法，添加 operatorId 参数
  addNode(type: string, name: string, fullName: string, id: string, description: string, position: { x: number; y: number }, operatorId?: string | number) {
    const newNode: PipelineNode = {
      id: id, // 使用传入的唯一ID
      type: type,
      name: name,
      fullName: fullName || name,
      description: description,
      operatorId: operatorId, // 保存原始操作符ID
      x: position.x,
      y: position.y,
      isSource: false,
      isSink: false
    };
    const currentNodes = this._nodes.getValue();
    this._nodes.next([...currentNodes, newNode]); // Emit new array to subscribers
  }

  updateNodePosition(nodeId: string, position: { x: number; y: number}) {
    // 使用requestAnimationFrame确保与浏览器渲染同步
    requestAnimationFrame(() => {
      const currentNodes = this._nodes.getValue();
      // 找到要更新的节点
      const nodeIndex = currentNodes.findIndex(node => node.id === nodeId);

      if (nodeIndex >= 0) {
        // 创建新的节点数组，避免直接修改原数组
        const updatedNodes = [...currentNodes];
        // 更新节点位置
        updatedNodes[nodeIndex] = {
          ...updatedNodes[nodeIndex],
          x: position.x,
          y: position.y
        };
        // 发送更新后的数组
        this._nodes.next(updatedNodes);
      }
    });
  }

  getNode(nodeId: string): PipelineNode | undefined {
    return this._nodes.getValue().find(node => node.id === nodeId);
  }

  removeNode(nodeId: string) {
    const currentNodes = this._nodes.getValue();
    const updatedNodes = currentNodes.filter(node => node.id !== nodeId);
    this._nodes.next(updatedNodes); // Emit updated array

    // Also remove any edges connected to this node
    const currentEdges = this._edges.getValue();
    const updatedEdges = currentEdges.filter(edge => edge.source !== nodeId && edge.target !== nodeId);
    this._edges.next(updatedEdges); // Emit updated array
  }

  // 添加更新节点源/终结点状态的方法
  updateNodeAsSource(nodeId: string, isSource: boolean) {
    const nodes = this._nodes.getValue();
    const nodeIndex = nodes.findIndex(n => n.id === nodeId);

    if (nodeIndex >= 0) {
      const updatedNodes = [...nodes];
      updatedNodes[nodeIndex] = {
        ...updatedNodes[nodeIndex],
        isSource: isSource
      };
      this._nodes.next(updatedNodes);
    }
  }

  updateNodeAsSink(nodeId: string, isSink: boolean) {
    const nodes = this._nodes.getValue();
    const nodeIndex = nodes.findIndex(n => n.id === nodeId);

    if (nodeIndex >= 0) {
      const updatedNodes = [...nodes];
      updatedNodes[nodeIndex] = {
        ...updatedNodes[nodeIndex],
        isSink: isSink
      };
      this._nodes.next(updatedNodes);
    }
  }

  // --- Edge Management ---

  startEdge(sourceNodeId: string) {
    this.firstNodeForEdge = sourceNodeId;
    console.log(`Edge creation started from: ${sourceNodeId}`);
    // Optional: Add visual feedback to the source node
  }

  endEdge(targetNodeId: string) {
    if (this.firstNodeForEdge === null) {
      console.warn("Edge creation not started.");
      return;
    }

    const sourceId = this.firstNodeForEdge;
    const targetId = targetNodeId;

    // Reset state immediately
    this.firstNodeForEdge = null;
    // Optional: Remove visual feedback from the source node

    if (sourceId === targetId) {
      console.log("Cannot connect node to itself.");
      return;
    }

    // Optional: Prevent duplicate edges
    const currentEdges = this._edges.getValue();
    const edgeExists = currentEdges.some(edge =>
      (edge.source === sourceId && edge.target === targetId) /*|| (edge.source === targetId && edge.target === sourceId) // Uncomment for undirected */
    );
    if (edgeExists) {
      console.log(`Edge already exists between ${sourceId} and ${targetId}.`);
      return;
    }


    const newEdge: Edge = {
      id: uuidv4(), // Unique ID for the edge (optional)
      source: sourceId,
      target: targetId,
    };

    this._edges.next([...currentEdges, newEdge]); // Emit new edge array
    console.log(`Edge created: ${sourceId} -> ${targetId}`);
  }

  cancelEdge() {
     if (this.firstNodeForEdge !== null) {
        console.log("Edge creation cancelled.");
        // Optional: Remove visual feedback from the source node
        this.firstNodeForEdge = null;
     }
  }

  removeEdge(edgeId: string) {
    const currentEdges = this._edges.getValue();
    const updatedEdges = currentEdges.filter(edge => edge.id !== edgeId);
    this._edges.next(updatedEdges);
  }


  // --- Data Management ---

  getPipelineData(): PipelineData {
    return {
      nodes: this._nodes.getValue(),
      edges: this._edges.getValue(),
    };
  }

  loadPipelineData(data: PipelineData) {
     // Optional: Clear existing state before loading
     this._nodes.next(data.nodes || []);
     this._edges.next(data.edges || []);
  }

  // --- Backend Communication (Placeholder) ---
  // You would inject HttpClient here and add methods like savePipeline, loadPipeline etc.
  // Example:
  // constructor(private http: HttpClient) {}
  // savePipelineToBackend(data: PipelineData) {
  //   return this.http.post('/api/pipeline', data);
  // }


// 添加转换为拓扑图数据的方法
convertToTopology(sourceNodeId: string, sinkNodeId: string, name?: string, description?: string): TopologyData {
  const nodes = this._nodes.getValue();
  const edges = this._edges.getValue();

  // 转换节点数据
  const topologyNodes: TopologyNode[] = nodes.map(node => ({
    id: node.id,
    operatorId: node.operatorId || '',
    type: node.type,
    name: node.fullName || node.name,
    isSource: node.id === sourceNodeId,
    isSink: node.id === sinkNodeId,
    config: {} // 可以添加节点配置
  }));

  // 转换边数据
  const topologyEdges: TopologyEdge[] = edges.map(edge => ({
    id: edge.id,
    source: edge.source,
    target: edge.target,
    config: {} // 可以添加边配置
  }));

  // 构建拓扑图数据
  return {
    id: uuidv4(), // 生成唯一ID
    name: name || '新拓扑图',
    description: description || '',
    nodes: topologyNodes,
    edges: topologyEdges,
    sourceNodeId,
    sinkNodeId
  };
}
}
