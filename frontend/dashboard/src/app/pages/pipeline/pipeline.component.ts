// src/app/pipeline/pipeline.component.ts

import { Component, ElementRef, ViewChild, AfterViewInit, OnDestroy } from '@angular/core';
import { CdkDragDrop, CdkDragEnd, CdkDragStart, CdkDropList } from '@angular/cdk/drag-drop';
import { PipelineService } from './pipeline.service';
import { Node ,Edge,TopologyData} from './models/pipeline-data.model';
import { Subscription } from 'rxjs'; // Import Subscription for cleanup
import { v4 as uuidv4 } from 'uuid'; // 确保导入 uuid


@Component({
  selector: 'app-pipeline',
  templateUrl: './pipeline.component.html',
  styleUrls: ['./pipeline.component.scss']
})
export class PipelineComponent implements AfterViewInit, OnDestroy {
  // Reference to the canvas drop list
  @ViewChild(CdkDropList) pipelineCanvasList!: CdkDropList;

  // Reference to the main canvas container element
  @ViewChild('pipelineCanvasList', { read: ElementRef }) canvasContainerEl!: ElementRef<HTMLElement>;

  canvasWidth = 1000; // Example size, adjust as needed
  canvasHeight = 800; // Example size, adjust as needed

  selectedNodeId: string | null = null; // Optional: for highlighting selected node

  private subscriptions = new Subscription(); // To manage subscriptions for cleanup

  constructor(public pipelineService: PipelineService) { } // Make public to access observables in template

  ngAfterViewInit() {
     // Register this drop list with the operator palette's connectedTo
     // This linking can also be done declaratively in the palette's HTML: [cdkDropListConnectedTo]="['pipelineCanvasList']"
     // However, getting the instance via ViewChild is more robust if the palette isn't a direct sibling.
     // A simpler way is to give both the palette drop list and canvas drop list the same ID
     // and use [cdkDropListConnectedTo] with that ID. Let's use that simpler approach.
     // Make sure palette's cdkDropList has id="paletteList" and canvas has id="pipelineCanvasList"
     // And palette has [cdkDropListConnectedTo]="['pipelineCanvasList']"
  }

  // 右键菜单相关属性
  contextMenuPosition: { x: number, y: number } | null = null;
  contextMenuNodeId: string = '';
  
  // 添加边的右键菜单相关属性
  edgeContextMenuPosition: { x: number, y: number } | null = null;
  contextMenuEdgeId: string = '';
  
  // 添加这个属性声明
  private hideNodeMenuBound: (() => void) | null = null;
  private hideEdgeMenuBound: (() => void) | null = null;

  ngOnDestroy() {
    this.subscriptions.unsubscribe(); // Clean up subscriptions
    // 清理事件监听器
    if (this.hideNodeMenuBound) {
      window.removeEventListener('click', this.hideNodeMenuBound);
      this.hideNodeMenuBound = null;
    }
    // 清理边菜单事件监听器
    if (this.hideEdgeMenuBound) {
      window.removeEventListener('click', this.hideEdgeMenuBound);
      this.hideEdgeMenuBound = null;
    }
  }


  // --- Handle Drag and Drop from Palette to Canvas ---

  drop(event: CdkDragDrop<any, any>) {
    // 检查是否从不同容器（操作符面板）拖放
    if (event.previousContainer !== event.container) {
      const paletteOperator = event.item.data as Partial<Node>; // 获取操作符数据
    
      // 计算相对于画布容器左上角的放置位置
      const containerRect = this.canvasContainerEl.nativeElement.getBoundingClientRect();
      const svgElement = this.canvasContainerEl.nativeElement.querySelector('svg');
      
      // 添加null检查
      if (!svgElement) {
        console.error('SVG element not found');
        return;
      }
      
      // 考虑SVG的缩放和位置
      const svgRect = svgElement.getBoundingClientRect();
      const scaleX = svgElement.clientWidth / svgRect.width;
      const scaleY = svgElement.clientHeight / svgRect.height;
      
      // 计算在SVG坐标系中的位置
      const dropPointX = (event.dropPoint.x - containerRect.left) * scaleX;
      const dropPointY = (event.dropPoint.y - containerRect.top) * scaleY;
      
      // 添加节点到服务
      const position = {
        x: dropPointX,
        y: dropPointY
      };
  
      // 为新节点生成唯一ID
      const uniqueNodeId = uuidv4();
  
      // 检查必要属性并为可选属性提供默认值
      if (paletteOperator.type && paletteOperator.name) {
        // 使用requestAnimationFrame确保与浏览器渲染同步
        requestAnimationFrame(() => {
          this.pipelineService.addNode(
            paletteOperator.type!, // 添加非空断言操作符
            paletteOperator.name!,
            paletteOperator.fullName || paletteOperator.name!,
            uniqueNodeId,
            paletteOperator.description || '暂无描述',
            position,
            paletteOperator.operatorId
          );
        });
      } else {
        console.error("拖放项没有有效的操作符数据:", paletteOperator);
      }
    }
  }


  // --- Handle Dragging Nodes on the Canvas ---

  // Optional: Store initial drag position if needed for complex position calculations
  nodeDragStarted(nodeId: string) {
    console.log(`Started dragging node: ${nodeId}`);
    // You might store the initial node position here if needed
  }

  nodeDragEnded(event: CdkDragEnd, nodeId: string) {
    // 获取被拖动的元素（节点的SVG组）
    const draggedElement = event.source.element.nativeElement;
    
    // 获取CDK应用的最终变换
    const transform = draggedElement.getAttribute('transform');
    let x = 0;
    let y = 0;
    
    if (transform) {
      // 使用正则表达式提取translate值
      const translateMatch = transform.match(/translate\(([^,]+),([^)]+)\)/);
      if (translateMatch && translateMatch[1] && translateMatch[2]) {
        x = parseFloat(translateMatch[1]);
        y = parseFloat(translateMatch[2]);
        
        // 立即更新节点的位置，避免异步更新导致的跳跃
        requestAnimationFrame(() => {
          // 更新服务中节点的位置
          this.pipelineService.updateNodePosition(nodeId, { x, y });
        });
      }
    }
    
    console.log(`节点 ${nodeId} 拖动到位置: (${x}, ${y})`);
  }

  // --- Handle Node Clicks for Edge Creation ---

  // 添加源节点和终结点的标识
  sourceNodeId: string | null = null;
  sinkNodeId: string | null = null;

  // 添加错误提示属性
  edgeError: string | null = null;
  
  // 获取节点名称的辅助方法
  getNodeName(nodeId: string): string {
    const node = this.pipelineService.getNode(nodeId);
    return node ? node.name : '未知节点';
  }
  
  // 修改节点点击方法
  nodeClicked(nodeId: string) {
    // 设置选中节点
    this.selectedNodeId = nodeId;
    
    // 获取当前是否有边的起点
    const firstNodeId = this.pipelineService['firstNodeForEdge'];
    
    if (firstNodeId === null) {
      // 第一次点击：开始创建边
      this.pipelineService.startEdge(nodeId);
      
      // 添加视觉反馈
      setTimeout(() => {
        const nodeElements = document.querySelectorAll('.node');
        nodeElements.forEach(el => {
          if (el.getAttribute('data-node-id') === nodeId) {
            el.classList.add('edge-source');
          }
        });
      });
      
    } else {
      // 第二次点击：尝试完成边的创建
      
      // 检查是否点击了同一个节点
      if (firstNodeId === nodeId) {
        this.showEdgeError('不能连接到同一个节点');
        return;
      }
      
      // 检查是否已经存在从源节点到目标节点的边
      const edges = this.pipelineService.getPipelineData().edges;
      const existingEdge = edges.find(e => e.source === firstNodeId && e.target === nodeId);
      
      if (existingEdge) {
        this.showEdgeError('这两个节点之间已经存在连接');
        return;
      }
      
      // 检查是否已经存在从目标节点到源节点的边（反向边）
      const reverseEdge = edges.find(e => e.source === nodeId && e.target === firstNodeId);
      
      if (reverseEdge) {
        this.showEdgeError('不允许创建双向连接');
        return;
      }
      
      // 通过所有验证，创建边
      this.pipelineService.endEdge(nodeId);
      
      // 移除视觉反馈
      setTimeout(() => {
        const nodeElements = document.querySelectorAll('.node');
        nodeElements.forEach(el => {
          el.classList.remove('edge-source');
          el.classList.remove('invalid-target');
        });
      });
    }
  }

  // 显示边错误的方法
  showEdgeError(message: string) {
    this.edgeError = message;
    
    // 取消当前的边创建
    this.cancelEdgeCreation();
    
    // 3秒后清除错误消息
    setTimeout(() => {
      this.edgeError = null;
    }, 3000);
  }

  // 取消边创建的方法
  cancelEdgeCreation() {
    this.pipelineService.cancelEdge();
    
    // 移除视觉反馈
    setTimeout(() => {
      const nodeElements = document.querySelectorAll('.node');
      nodeElements.forEach(el => {
        el.classList.remove('edge-source');
        el.classList.remove('invalid-target');
      });
    });
  }

  // --- Helper for Edge Drawing ---
  getNodePosition(nodeId: string): { x: number; y: number } | undefined {
    const node = this.pipelineService.getNode(nodeId);
    // Return the node's stored position. This position is used as the center for line drawing.
    return node ? { x: node.x, y: node.y } : undefined;
  }

  // 修改边路径生成方法，添加箭头指示方向
  // 计算边的路径
  getEdgePath(edge: Edge): string {
    const nodes = this.pipelineService.getPipelineData().nodes;
    const sourceNode = nodes.find(node => node.id === edge.source);
    const targetNode = nodes.find(node => node.id === edge.target);
    
    if (!sourceNode || !targetNode) {
      return '';
    }
    
    // 节点半径
    const nodeRadius = 32;
    
    // 计算源节点和目标节点之间的距离和角度
    const dx = targetNode.x - sourceNode.x;
    const dy = targetNode.y - sourceNode.y;
    const distance = Math.sqrt(dx * dx + dy * dy);
    const angle = Math.atan2(dy, dx);
    
    // 计算边的起点和终点（考虑节点半径）
    const startX = sourceNode.x + nodeRadius * Math.cos(angle);
    const startY = sourceNode.y + nodeRadius * Math.sin(angle);
    // 增加终点与节点的距离，确保箭头不被节点覆盖
    const endX = targetNode.x - (nodeRadius + 10) * Math.cos(angle);
    const endY = targetNode.y - (nodeRadius + 10) * Math.sin(angle);
    
    // 计算控制点（使曲线更自然）
    // 调整控制点距离，使曲线更明显
    const controlPointDistance = distance / 2.5;
    
    // 添加一些垂直偏移，使曲线更明显
    const perpX = -dy / distance * 30; // 垂直于连线方向的偏移
    const perpY = dx / distance * 30;
    
    const controlX1 = startX + controlPointDistance * Math.cos(angle) + perpX;
    const controlY1 = startY + controlPointDistance * Math.sin(angle) + perpY;
    const controlX2 = endX - controlPointDistance * Math.cos(angle) + perpX;
    const controlY2 = endY - controlPointDistance * Math.sin(angle) + perpY;
    
    // 返回贝塞尔曲线路径
    return `M ${startX} ${startY} C ${controlX1} ${controlY1}, ${controlX2} ${controlY2}, ${endX} ${endY}`;
  }
  
  // 计算边缘标签位置
  getEdgeLabelPosition(edge: Edge): {x: number, y: number} {
    const source = this.getNodePosition(edge.source);
    const target = this.getNodePosition(edge.target);
    
    if (!source || !target) return {x: 0, y: 0};
    
    // 标签位置在边缘中点
    return {
      x: (source.x + target.x) / 2,
      y: (source.y + target.y) / 2 - 10 // 稍微上移，避免与线重叠
    };
  }
  
  // 显示节点右键菜单
  showNodeMenu(event: MouseEvent, nodeId: string) {
    event.preventDefault();
    this.contextMenuPosition = { x: event.clientX, y: event.clientY };
    this.contextMenuNodeId = nodeId;
    
    // 点击页面其他地方时隐藏菜单
    setTimeout(() => {
      this.hideNodeMenuBound = this.hideNodeMenu.bind(this);
      window.addEventListener('click', this.hideNodeMenuBound, { once: true });
    });
  }
  
  // 隐藏节点右键菜单
  hideNodeMenu() {
    this.contextMenuPosition = null;
    if (this.hideNodeMenuBound) {
      window.removeEventListener('click', this.hideNodeMenuBound);
      this.hideNodeMenuBound = null;
    }
  }

  // 设置节点为源节点
  setAsSourceNode(nodeId: string) {
    // 如果已经是源节点，则取消设置
    if (this.sourceNodeId === nodeId) {
      this.sourceNodeId = null;
      // 更新节点的源节点标记
      this.pipelineService.updateNodeAsSource(nodeId, false);
      return;
    }
    
    // 如果之前有其他源节点，先取消之前的设置
    if (this.sourceNodeId) {
      this.pipelineService.updateNodeAsSource(this.sourceNodeId, false);
    }
    
    // 设置新的源节点
    this.sourceNodeId = nodeId;
    this.pipelineService.updateNodeAsSource(nodeId, true);
    
    // 如果该节点已经是终结点，则取消终结点设置
    if (this.sinkNodeId === nodeId) {
      this.sinkNodeId = null;
      this.pipelineService.updateNodeAsSink(nodeId, false);
    }
  }
  
  // 设置节点为终结点
  setAsSinkNode(nodeId: string) {
    // 如果已经是终结点，则取消设置
    if (this.sinkNodeId === nodeId) {
      this.sinkNodeId = null;
      // 更新节点的终结点标记
      this.pipelineService.updateNodeAsSink(nodeId, false);
      return;
    }
    
    // 如果之前有其他终结点，先取消之前的设置
    if (this.sinkNodeId) {
      this.pipelineService.updateNodeAsSink(this.sinkNodeId, false);
    }
    
    // 设置新的终结点
    this.sinkNodeId = nodeId;
    this.pipelineService.updateNodeAsSink(nodeId, true);
    
    // 如果该节点已经是源节点，则取消源节点设置
    if (this.sourceNodeId === nodeId) {
      this.sourceNodeId = null;
      this.pipelineService.updateNodeAsSource(nodeId, false);
    }
  }

  // 添加属性用于存储用户输入的名称和描述
  pipelineName: string = '我的拓扑图';
  pipelineDescription: string = '';
  
  // 改进保存方法，添加源节点和终结点的验证
  savePipeline() {
    // 验证是否设置了源节点和终结点
    if (!this.sourceNodeId) {
      alert("请设置一个源节点（起点）");
      return;
    }
    
    if (!this.sinkNodeId) {
      alert("请设置一个终结点（终点）");
      return;
    }
    
    // 验证图的连通性
    if (!this.validateTopology()) {
      alert("拓扑图不完整，请确保从源节点到终结点有一条完整的路径");
      return;
    }
  
    // 验证名称是否为空
    if (!this.pipelineName.trim()) {
      alert("请输入拓扑图名称");
      return;
    }
    
    // 转换为拓扑图数据结构
    const topologyData = this.pipelineService.convertToTopology(
      this.sourceNodeId, 
      this.sinkNodeId,
      this.pipelineName, // 使用用户输入的名称
      this.pipelineDescription // 使用用户输入的描述
    );
    
    console.log("拓扑图数据:", topologyData);
    
    // 调用后端API保存拓扑图
    this.savePipelineToBackend(topologyData);
  }

  // 验证拓扑图的连通性
  validateTopology(): boolean {
    if (!this.sourceNodeId || !this.sinkNodeId) {
      return false;
    }
    
    const edges = this.pipelineService.getPipelineData().edges;
    const nodes = this.pipelineService.getPipelineData().nodes;
    
    // 使用BFS算法检查从源节点到终结点是否有路径
    const visited = new Set<string>();
    const queue: string[] = [this.sourceNodeId];
    
    while (queue.length > 0) {
      const currentNodeId = queue.shift()!;
      
      if (currentNodeId === this.sinkNodeId) {
        return true; // 找到路径
      }
      
      if (!visited.has(currentNodeId)) {
        visited.add(currentNodeId);
        
        // 找出所有从当前节点出发的边
        const outgoingEdges = edges.filter(edge => edge.source === currentNodeId);
        
        // 将这些边的目标节点加入队列
        for (const edge of outgoingEdges) {
          if (!visited.has(edge.target)) {
            queue.push(edge.target);
          }
        }
      }
    }
    
    return false; // 没有找到从源节点到终结点的路径
  }

  // 保存拓扑图到后端
  savePipelineToBackend(topologyData: TopologyData) {
    // 这里使用HttpClient调用后端API
    // 示例代码，需要替换为实际的API调用
    /*
    this.http.post<any>('/api/topology', topologyData).subscribe({
      next: (response) => {
        console.log('拓扑图保存成功', response);
        alert('拓扑图保存成功');
      },
      error: (error) => {
        console.error('保存拓扑图失败', error);
        alert('保存拓扑图失败: ' + error.message);
      }
    });
    */
    this.pipelineService.submitPipeline(topologyData).subscribe({
      next: (response) => {
        console.log('拓扑图保存成功', response);
        alert('拓扑图保存成功');
      },
      error: (error) => {
        console.error('保存拓扑图失败', error);
        alert('保存拓扑图失败:'+ error.message);
      }
    })
    
    // 临时提示，实际项目中替换为上面的API调用
    alert("拓扑图数据已准备好发送到后端，请查看控制台输出");
  }

  // --- Load StreamingExecutionEnvironment Data (Optional) ---
  // loadPipeline() {
  //    // TODO: Fetch data from backend using HttpClient
  //    // Example:
  //    // this.backendService.loadPipeline().subscribe({
  //    //   next: (data) => this.pipelineService.loadPipelineData(data),
  //    //   error: (error) => console.error('Failed to load pipeline', error)
  //    // });
  // }
  showEdgeMenu(event: MouseEvent, edgeId: string) {
    event.preventDefault();
    event.stopPropagation();
    
    this.edgeContextMenuPosition = { x: event.clientX, y: event.clientY };
    this.contextMenuEdgeId = edgeId;
    
    // 添加点击其他地方关闭菜单的事件
    this.hideEdgeMenuBound = this.hideEdgeMenu.bind(this);
    setTimeout(() => {
      window.addEventListener('click', this.hideEdgeMenuBound as EventListener);
    });
  }
  
  hideEdgeMenu() {
    this.edgeContextMenuPosition = null;
    
    if (this.hideEdgeMenuBound) {
      window.removeEventListener('click', this.hideEdgeMenuBound as EventListener);
      this.hideEdgeMenuBound = null;
    }
  }
  
  deleteNode(nodeId: string) {
    if (confirm('确定要删除此节点吗？相关的所有连接也将被删除。')) {
      this.pipelineService.removeNode(nodeId);
      
      // 如果删除的是源节点或终结点，更新相应的标识
      if (this.sourceNodeId === nodeId) {
        this.sourceNodeId = null;
      }
      if (this.sinkNodeId === nodeId) {
        this.sinkNodeId = null;
      }
    }
  }
  
  // Add this function to your PipelineComponent class
  // 添加trackBy函数提高渲染性能
  trackByNodeId(index: number, node: Node): string {
    return node.id;
  }

  deleteEdge(edgeId: string) {
    if (confirm('确定要删除此连接吗？')) {
      this.pipelineService.removeEdge(edgeId);
    }
  }
}

// 添加对画布元素的引用
// @ViewChild('pipelineCanvasList', { static: true }) canvasElement: ElementRef;
