import {Component, OnInit, OnDestroy} from '@angular/core';
import {OverviewService} from "./overview.service";
import {FormBuilder, FormGroup} from "@angular/forms";
import {Job} from "../../model/Job";
import { NzGraphData, NzGraphDataDef, NzGraphComponent } from 'ng-zorro-antd/graph';

@Component({
  selector: 'app-home',
  templateUrl: './overview.component.html',
  styleUrls: ['./overview.component.less']
})
export class OverviewComponent implements OnInit, OnDestroy {
  filterForm: FormGroup;
  jobs: Job[] = [];
  filteredJobs: Job[] = [];
  tableIsLoading = false;   // Whether the table is loading
  currentPageIndex = 1;     // Current page index
  pageSize = 10;            // Number of jobs per page
  currentPageJob: Job[] = [];
  private graphDataCache: Map<string, NzGraphData> = new Map();
  
  operatorGraphDataMap: Map<string, NzGraphDataDef> = new Map();
  nzOperatorGraphDataMap: Map<string, NzGraphData> = new Map();
  
  // 添加默认的图表数据属性
  nzOperatorGraphData: NzGraphData = new NzGraphData({ nodes: [], edges: [] });

  constructor(private overviewService: OverviewService, private formBuilder: FormBuilder) {}

  ngOnInit() {
    this.tableIsLoading = true;

    this.overviewService.getAllJobs().subscribe({
      next: (res) => {
        this.jobs = res;
        this.filteredJobs = this.jobs;
        this.preprocessJobGraphData();
        this.filterJob();
      },
      error: (error) => {
        console.error('Error loading jobs:', error);
        this.tableIsLoading = false;
      }
    });

    this.filterForm = this.formBuilder.group({
      name: [null, null],
      status: [null, null]
    });
  }

  /**
   * Change the page index
   * @param index The new page index
   */
  onPageIndexChange(index: number) {
    this.currentPageIndex = index;
    this.filterJob();
  }

  /**
   * Change the page size
   * @param size The new page size
   */
  onPageSizeChange(size: number) {
    this.pageSize = size;
    this.filterJob()
  }

  onFilterJob() {
    this.tableIsLoading = true;
    this.currentPageIndex = 1;
    this.filterJob();
  }

  /**
   * Filter jobs based on name and status
   */
  filterJob() {
    const filterName = this.filterForm.value.name;
    const filterStatus = this.filterForm.value.status;
    this.filteredJobs = this.jobs;

    if (filterName != null) {
      this.filteredJobs = this.filteredJobs.filter(job =>
        job.name.includes(`${filterName}`)
      );
    }
    if (filterStatus != null) {
      this.filteredJobs = this.filteredJobs.filter(job =>
        job.isRunning == filterStatus
      );
    }

    // Update the table
    const startIndex = (this.currentPageIndex-1) * this.pageSize;
    const endIndex = startIndex + this.pageSize;
    this.currentPageJob = this.filteredJobs.slice(startIndex, endIndex);
    this.tableIsLoading = false;
  }

  /**
   * 预处理所有作业的图表数据
   */
  preprocessJobGraphData() {
    this.jobs.forEach(job => {
      if (job && job.jobId) {
        const operatorGraphData: NzGraphDataDef = { nodes: [], edges: [] };
        
        if (job.operators && job.operators.length > 0) {
          // 添加操作符节点
          for (let i = 0; i < job.operators.length; i++) {
            operatorGraphData.nodes.push({
              id: job.operators[i].id,
              label: job.operators[i].name,
              instance: job.operators[i].numOfInstances
            });
            
            // 添加边（连接相邻操作符）
            if (i > 0) {
              operatorGraphData.edges.push({
                v: job.operators[i - 1].id,
                w: job.operators[i].id
              });
            }
          }
        } else {
          // 如果没有操作符，创建默认节点
          operatorGraphData.nodes.push({
            id: `job-${job.jobId}`,
            label: job.name || 'Unknown Job',
            instance: 1
          });
        }
        
        // 存储图表数据
        this.operatorGraphDataMap.set(job.jobId, operatorGraphData);
        this.nzOperatorGraphDataMap.set(job.jobId, new NzGraphData(operatorGraphData));
      }
    });
  }

  /**
   * 获取操作符图表数据
   */
  getOperatorGraphData(job: Job): NzGraphData {
    if (!job || !job.jobId) {
      return this.createDefaultGraphData('No Job Data');
    }

    // 从预处理的数据中获取
    const cachedData = this.nzOperatorGraphDataMap.get(job.jobId);
    if (cachedData) {
      return cachedData;
    }

    // 如果缓存中没有，重新生成
    try {
      const graphDataDef: NzGraphDataDef = { nodes: [], edges: [] };
      
      if (job.operators && Array.isArray(job.operators) && job.operators.length > 0) {
        // 添加操作符节点
        job.operators.forEach((operator, index) => {
          if (operator) {
            graphDataDef.nodes.push({
              id: operator.id || `operator-${index}`,
              label: operator.name || `Operator ${index + 1}`,
              instance: operator.numOfInstances || 1
            });
          }
        });
        
        // 添加边
        for (let i = 1; i < job.operators.length; i++) {
          if (job.operators[i - 1] && job.operators[i]) {
            graphDataDef.edges.push({
              v: job.operators[i - 1].id || `operator-${i - 1}`,
              w: job.operators[i].id || `operator-${i}`
            });
          }
        }
      } else {
        graphDataDef.nodes.push({
          id: `job-${job.jobId}`,
          label: job.name || 'Unknown Job',
          instance: 1
        });
      }
      
      const graphData = new NzGraphData(graphDataDef);
      this.nzOperatorGraphDataMap.set(job.jobId, graphData);
      return graphData;
      
    } catch (error) {
      console.error('Error creating graph data for job:', job.name, error);
      return this.createDefaultGraphData(job.name || 'Error Job');
    }
  }

  // 创建默认图表数据的辅助方法
  private createDefaultGraphData(label: string): NzGraphData {
    const graphDataDef: NzGraphDataDef = {
      nodes: [{
        id: 'default',
        label: label,
        instance: 1
      }],
      edges: []
    };
    return new NzGraphData(graphDataDef);
  }
  
  /**
   * 优化面板变化处理
   */
  onPanelChange(jobId: string, active: boolean): void {
    try {
      if (active) {
        console.log(`Panel for job ${jobId} is now open`);
        // 确保图表数据已准备好
        const job = this.currentPageJob.find(j => j.jobId === jobId);
        if (job && !this.nzOperatorGraphDataMap.has(jobId)) {
          // 如果没有缓存的图表数据，创建它
          this.getOperatorGraphData(job);
        }
      }
    } catch (error) {
      console.error('Error handling panel change:', error);
    }
  }

  /**
   * 操作符图表初始化回调
   */
  onOperatorGraphInitialized(graphComponent: NzGraphComponent): void {
    console.log('Operator graph initialized:', graphComponent);
  }

  // 添加清理缓存的方法
  clearGraphCache(): void {
    this.graphDataCache.clear();
    this.operatorGraphDataMap.clear();
    this.nzOperatorGraphDataMap.clear();
  }

  // 在组件销毁时清理缓存
  ngOnDestroy(): void {
    this.clearGraphCache();
  }
}
