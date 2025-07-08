import {Component, ElementRef, OnInit, ViewChild} from '@angular/core';

import {JobInformationService} from "./job-information.service";
import {Job} from "../../model/Job";
import {ActivatedRoute} from "@angular/router";
import * as jsyaml from 'js-yaml';
import * as d3 from 'd3';
import {
  NzGraphComponent,
  NzGraphData,
  NzGraphDataDef,
  NzGraphZoomDirective,
} from "ng-zorro-antd/graph";
import {Batch} from "../../model/Batch";
import {FormControl, FormGroup, NonNullableFormBuilder, Validators, FormArray, ValidatorFn} from "@angular/forms";
import {NzMessageService} from "ng-zorro-antd/message";
import { v4 } from 'uuid';

@Component({
  selector: 'app-application-information',
  templateUrl: './job-information.component.html',
  styleUrls: ['./job-information.component.less']
})
export class JobInformationComponent implements OnInit {
  @ViewChild('tpgContainer') private tpgContainer!: ElementRef; // tpg container
  @ViewChild(NzGraphZoomDirective, {static: true}) zoomController!: NzGraphZoomDirective;

  job: Job; // job entity
  statisticBatch: Batch; // statistic batch entity
  tpgBatch: Batch | null = null; // TPG batch entity
  use_ray: boolean = false;
  tpgSvg: any;            // tpg svg
  tpgSvgSimulation: any;  // tpg graph drawing force simulation
  isTpgModalVisible = false;

  operatorGraphData: NzGraphDataDef = {nodes: [], edges: []} // operator graph data {v: '1', w: '2'}, {id: '101', label: 'Spout'}
  nzOperatorGraphData: any; // operator graph data for nz-graph

  // Batch data
  batchOptions: any[] = [];
  throughputAndLatency: any[] = [
    {name: 'Throughput (x1000 tuples/s)', series: []},
    {name: 'Latency (ms)', series: []}
  ];
  onShowingThroughputAndLatency: any[] = [
    {name: 'Throughput (x1000 tuples/s)', series: []},
    {name: 'Latency (ms)', series: []}
  ];

  timePieData: any[] = [{name: 'construct time (ns)', value: 0,},
    {name: 'explore time (ns)', value: 0,},
    {name: 'useful time (ns)', value: 0,},
    {name: 'abort time (ns)', value: 0}];
  tpgData: any[] = [{name: 'TD', value: 0,}, {name: 'LD', value: 0,}, {name: 'PD', value: 0,}];

  operatorLatestBatchNum: { [key: string]: number } = {} // key: operator name, value: latest batch
  operatorAccumulativeLatency: { [key: string]: number } = {} // key: operator name, value: accumulative latency
  operatorAccumulativeThroughput: { [key: string]: number } = {} // key: operator name, value: accumulative throughput

  // batch-tpg data
  tpgNodes: any[] = [];
  tpgLinks: any[] = [];
  numOfTD = 0;
  numOfLD = 0;
  numOfPD = 0;

  nodesSelections: any;
  linksSelections: any;

  jobStarted = false;
  throughputLatencyGraphSize = 10;
  throughputLatencyStartBatch = 1;
  realTimePerformanceBoxChecked = false;
  startBatchOptionDisabled = false;

  configContent: string = '';
  configError: string | null = null;
  configSuccess: boolean = false;
  isSubmitting: boolean = false;
  activeConfigTab: number = 0; // 0: 表单模式, 1: 原始模式

  batchForm: FormGroup<{
    batch: FormControl<string>;
    operator: FormControl<string>;
  }>;

  tpgForm: FormGroup<{
    batch: FormControl<string>;
    operator: FormControl<string>;
  }>;

  runtimeDuration = 0;
  listenIntervalId: number;     // interval id for listening to the performance data

  // 动态配置表单
  configForm: FormGroup;
  configStructure: any = {}; // 存储配置结构
  configSections: any[] = []; // 存储配置分组

  iframeRefreshIntervalId: any;
  @ViewChild('actorsIframe') actorsIframe: ElementRef;

  constructor(private route: ActivatedRoute,
              private jobInformationService: JobInformationService,
              private fb: NonNullableFormBuilder,
              private message: NzMessageService) {
    this.batchForm = this.fb.group({
      batch: ['', [Validators.required]],
      operator: ['', [Validators.required]]
    });
    this.tpgForm = this.fb.group({
      batch: ['', [Validators.required]],
      operator: ['', [Validators.required]]
    });

    // 初始化为空的配置表单
    this.configForm = this.fb.group({});
  }

  ngOnInit(): void {
    
    this.route.params.subscribe(params => {
      const jobId = params['id'];
      this.jobInformationService.getJob(jobId).subscribe(res => {
        this.job = res;
        let duration = this.job.duration;
        this.runtimeDuration = parseInt(duration, 10)
        this.jobStarted = this.job.isRunning;
        for (let i = 0; i < this.job.operators.length; i++) {
          this.operatorLatestBatchNum["sl"] = 1;  // initialize the latest batch number
          this.operatorAccumulativeLatency["sl"] = 0;  // initialize the accumulative latency
          this.operatorAccumulativeThroughput["sl"] = 0;  // initialize the accumulative throughput
          this.operatorGraphData.nodes.push({id: this.job.operators[i].id, label: this.job.operators[i].name, instance: this.job.operators[i].numOfInstances});
          // if (i > 0) {
          //   this.operatorGraphData.edges.push({v: this.job.operators[i - 1].id, w: this.job.operators[i].id});
          // }
     
          if(i>0) {
            let downstream = this.job.operators[i-1].downstream;
            for (let j = 0 ; j < downstream.length ; ++ j){
              let v = String(this.job.operators[i-1].id);
              let w = String(downstream[j]);
              this.operatorGraphData.edges.push({v: v, w:w });
            }
          }
        }
        // for (let i = 0; i < this.job.operators.length; i++) {
        //   const op = this.job.operators[i];
        //   console.log(op.downstream)
        //   this.operatorLatestBatchNum["sl"] = 1;
        //   this.operatorAccumulativeLatency["sl"] = 0;
        //   this.operatorAccumulativeThroughput["sl"] = 0;

        //   this.operatorGraphData.nodes.push({
        //     id: op.id,
        //     label: op.name,
        //     instance: op.numOfInstances
        //   });

        //   // 建图：根据下游信息建立有向边
        //   if (op.downstream && op.downstream.length > 0) {
        //     for (let j = 0; j < op.downstream.length; ++j) {
        //       this.operatorGraphData.edges.push({ v: op.id, w: op.downstream[j] });
        //     }
        //   }
        // }
        this.drawOperatorGraph();
        this.getHistoricalData();

        if (this.jobStarted) {
          this.startListening();
        }
        this.loadConfig();
      });
    });
  }

  getHistoricalData() {
    this.jobInformationService.getAllBatches(this.job.jobId, 'sl').subscribe(res => {
      res.sort((a, b) => {
        return a.batchId - b.batchId;
      });
      this.operatorLatestBatchNum['sl'] = res.length + 1;
      for (let batch of res) {
        batch = this.transformTime(batch);
        this.batchOptions.push({
          value: batch.batchId.toString(),
          label: batch.batchId.toString()
        });
        this.throughputAndLatency[0].series.push({name: `batch${batch.batchId}`, value: parseFloat((batch.throughput / 10 ** 3).toFixed(1))});
        this.throughputAndLatency[1].series.push({name: `batch${batch.batchId}`, value: batch.avgLatency});
        this.operatorAccumulativeLatency['sl'] = batch.accumulativeLatency;
        this.operatorAccumulativeThroughput['sl'] = batch.accumulativeThroughput;
        this.runtimeDuration += batch.batchDuration;
        this.updateOnShowingThroughputAndLatency();
      }
      this.runtimeDuration = parseFloat((this.runtimeDuration / 10**9).toFixed(1)); // s
    });
  }

  updateOnShowingThroughputAndLatency() {
    if (this.realTimePerformanceBoxChecked) {
      if (this.operatorLatestBatchNum['sl'] - this.throughputLatencyGraphSize + 1 > 0) {
        this.throughputLatencyStartBatch = this.operatorLatestBatchNum['sl'] - this.throughputLatencyGraphSize + 1;
        this.onShowingThroughputAndLatency[0].series = this.throughputAndLatency[0].series.slice(this.throughputLatencyStartBatch - 1, this.throughputLatencyStartBatch + this.throughputLatencyGraphSize - 1);
        this.onShowingThroughputAndLatency[1].series = this.throughputAndLatency[1].series.slice(this.throughputLatencyStartBatch - 1, this.throughputLatencyStartBatch + this.throughputLatencyGraphSize - 1);
      } else {
        this.throughputLatencyStartBatch = 1;
        this.onShowingThroughputAndLatency[0].series = this.throughputAndLatency[0].series.slice(0, this.throughputLatencyGraphSize);
        this.onShowingThroughputAndLatency[1].series = this.throughputAndLatency[1].series.slice(0, this.throughputLatencyGraphSize);
      }
    } else {
      this.onShowingThroughputAndLatency[0].series = this.throughputAndLatency[0].series.slice(this.throughputLatencyStartBatch - 1, this.throughputLatencyStartBatch + this.throughputLatencyGraphSize - 1);
      this.onShowingThroughputAndLatency[1].series = this.throughputAndLatency[1].series.slice(this.throughputLatencyStartBatch - 1, this.throughputLatencyStartBatch + this.throughputLatencyGraphSize - 1);
    }
    this.onShowingThroughputAndLatency = this.onShowingThroughputAndLatency.slice();
  }

  startListening() {
    this.listenIntervalId = setInterval(() => {
      this.update();
      this.runtimeDuration = parseFloat((this.runtimeDuration + 1).toFixed(1));  // seconds
    }, 1000);
  }

  update() {}

  transformTime(batch: Batch): Batch {
    batch.throughput = parseFloat(batch.throughput.toFixed(1)); // tuples/s
    batch.avgLatency = parseFloat((batch.avgLatency / 10**6).toFixed(1)); // ms
    batch.minLatency = parseFloat((batch.minLatency / 10**6).toFixed(1)); // ms
    batch.maxLatency = parseFloat((batch.maxLatency / 10**6).toFixed(1)); // ms
    batch.accumulativeLatency = parseFloat((batch.accumulativeLatency / 10**6).toFixed(1)); // ms
    batch.accumulativeThroughput = parseFloat(batch.accumulativeThroughput.toFixed(1)); // tuples/s
    return batch;
  }

  updatePerformanceGraph(batch: Batch) {
    this.throughputAndLatency[0].series.push({
      name: this.operatorLatestBatchNum['sl'].toString() + " batch",
      value: parseFloat((batch.throughput / 10 ** 3).toFixed(1))  // 1000 tuples/s
    });
    this.throughputAndLatency[1].series.push({
      name: this.operatorLatestBatchNum['sl'].toString() + " batch",
      value: batch.avgLatency
    });
    this.updateOnShowingThroughputAndLatency();
  }

  submitBatchStatisticForm(): void {
    if (this.batchForm.valid) {
      this.jobInformationService.getBatchById(this.job.jobId, "sl", this.batchForm.controls.batch.value).subscribe(res => {
        if (res) {
          res = this.transformTime(res);
          this.statisticBatch = res;
          this.statisticBatch.batchDuration = parseFloat((this.statisticBatch.batchDuration / 10**6).toFixed(1)); // ms
          this.updatePieChart(res);
          this.message.success(`Information of SL Batch ${this.batchForm.controls.batch.value} is Fetched Successfully`);
        }
      });
    } else {
      Object.values(this.batchForm.controls).forEach(control => {
        if (control.invalid) {
          control.markAsDirty();
          control.updateValueAndValidity({onlySelf: true});
        }
      });
    }
  }

  submitTpgForm(): void {
    if (this.tpgForm.valid) {
      this.jobInformationService.getBatchById(this.job.jobId, "sl", this.tpgForm.controls.batch.value).subscribe(res => {
        if (res) {
          this.tpgBatch = res;
          this.tpgNodes = [];
          this.tpgLinks = [];
          this.numOfTD = 0;
          this.numOfLD = 0;
          this.numOfPD = 0;
          for (let node of res.tpg) {
            this.tpgNodes.push(node);
            for (let edge of node.edges) {
              if (edge.dstOperatorID != edge.srcOperatorID) {
                this.tpgLinks.push({source: node.operationID, target: edge.dstOperatorID, type: edge.dependencyType});
                if (edge.dependencyType == "TD") {
                  this.numOfTD++;
                } else if (edge.dependencyType == "LD") {
                  this.numOfLD++;
                } else {
                  this.numOfPD++;
                }
              }
            }
          }
          this.tpgData = [{name: 'TD', value: this.numOfTD,}, {name: 'LD', value: this.numOfLD,}, {name: 'PD', value: this.numOfPD,}];
          this.message.success(`TPG of SL batch ${this.tpgForm.controls.batch.value} is fetched successfully`);
        }
      });
    } else {
      Object.values(this.tpgForm.controls).forEach(control => {
        if (control.invalid) {
          control.markAsDirty();
          control.updateValueAndValidity({onlySelf: true});
        }
      });
    }
  }

  updatePieChart(batch: Batch) {
    this.timePieData = [{
      name: 'construct time (ns)',
      value: batch.schedulerTimeBreakdown.constructTime // ns
    },
      {
        name: 'explore time (ns)',
        value: batch.schedulerTimeBreakdown.exploreTime // ns
      },
      {
        name: 'useful time (ns)',
        value: batch.schedulerTimeBreakdown.usefulTime // ns
      },
      {
        name: 'abort time (ns)',
        value: batch.schedulerTimeBreakdown.abortTime // ns
      }
    ];
    this.timePieData = this.timePieData.slice();
  }

  drawOperatorGraph() {
    this.nzOperatorGraphData = new NzGraphData(this.operatorGraphData);
  }

  onOperatorGraphInitialized(_ele: NzGraphComponent): void {
    this.zoomController?.fitCenter();
  }

  drawTpgGraph() {
    this.tpgSvg = d3.select(this.tpgContainer.nativeElement)
      .append('svg')
      .attr('width', '100%')
      .attr('height', '100%')
      .attr("viewBox", [0, 0, 640, 480]);

    this.tpgSvgSimulation = d3.forceSimulation(this.tpgNodes)
      .force('charge', d3.forceManyBody().strength(-15))
      .force('link', d3.forceLink(this.tpgLinks).id((d: any) => d.operationID))
      .force('center', d3.forceCenter(250, 250));

    this.linksSelections = this.tpgSvg.selectAll('.link')
      .data(this.tpgLinks)
      .enter().append('line')
      .attr('class', 'link')
      .style("stroke", (d: any) => {
        if (d.type == "FD") {
          return "#A37EA9"
        } else if (d.type == "LD") {
          return "#7DA3E4"
        } else {
          if (Math.random()>0.3) {
            return "#A93B5E"
          } else {
            return "#7DA3E4"
          }
        }
      })
      .style('stroke-dasharray', (d: any) => {
        if (d.type === 'PD') {
          return '5,5';
        } else {
          return 'none';
        }
      })
      .style('stroke-width', 3);

    this.nodesSelections = this.tpgSvg.selectAll('.node')
      .data(this.tpgNodes)
      .enter().append('circle')
      .attr('class', 'node')
      .attr('r', 4)
      .style("fill", "#e79722");

    this.tpgSvgSimulation.on('tick', this.simulationTick.bind(this));

    this.tpgSvg.call(d3.zoom()
      .extent([[0, 0], [648, 480]])
      .scaleExtent([0.5, 10])
      .on("zoom", this.tpgZoomed.bind(this)));
    this.tpgSvgSimulation.alpha(0.3).restart();
    setTimeout(() => {
      this.tpgSvgSimulation.stop();
      }, 4000);

    const tooltip = d3.select(this.tpgContainer.nativeElement)
        .append('div')
        .attr('class', 'tooltip')
        .style('height', '30px')
        .style('opacity', 0);

    this.nodesSelections.on('mouseover', (event, d) => {
      tooltip.transition()
          .duration(200)
          .style('opacity', 0.9);

      tooltip.html(`transaction id: ${d.operationID}&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;transaction type: ${d.txnType}&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;targetTable: ${d.targetTable}&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;targetKey: ${d.targetKey}`)
          .style('left', (event.pageX + 10) + 'px')
          .style('top', (event.pageY - 28) + 'px');
    });

    this.nodesSelections.on('mouseout', () => {
      tooltip.transition()
          .duration(500)
          .style('opacity', 0);
    });
  }

  simulationTick() {
    this.nodesSelections
      .attr('cx', (d: any) => d.x)
      .attr('cy', (d: any) => d.y);
    this.linksSelections
      .attr('x1', (d: any) => d.source.x)
      .attr('y1', (d: any) => d.source.y)
      .attr('x2', (d: any) => d.target.x)
      .attr('y2', (d: any) => d.target.y);
  }

  onStart() {
    this.jobStarted = true;
    this.startListening();
    this.jobInformationService.startJob(this.job.jobId).subscribe(data=> {
      if (data.status == "success") {
        this.use_ray = data.use_ray
        this.runtimeDuration = data.duration || 0;
        console.log(data);
      }
    });
  }

  onStop() {
    if (this.realTimePerformanceBoxChecked) {
      this.onCheckBoxChanged(false);
    }
    clearInterval(this.listenIntervalId);
    this.jobInformationService.stopJob(this.job.jobId,String(this.runtimeDuration)+'s').subscribe(success => {
      if (success) {
      }
    });
    this.jobStarted = false;
  }

  tpgZoomed({transform}) {
    const { k, x, y } = transform;
    this.tpgSvg.selectAll('.node').attr('transform', transform);
    this.tpgSvg.selectAll('.link').attr('transform', transform);
    this.tpgSvg.select('.tooltip').attr('transform', `scale(${1 / k})`);
  }

  onExpandTpgModal() {
    const tpgLoading = this.message.loading(`Loading TPG: ${this.tpgForm.value.operator} batch ${this.tpgForm.value.batch} in progress..`, { nzDuration: 0 }).messageId;
    setTimeout(() => {
      this.message.remove(tpgLoading);
    }, 1000);
    this.isTpgModalVisible = true;
    setTimeout(() => {
      this.drawTpgGraph();
    }, 1000);
  }

  onClearTpgModal() {
    this.isTpgModalVisible = false;
  }

  onPerformanceGraphConfigChange(event: any) {
    this.updateOnShowingThroughputAndLatency();
  }

  onCheckBoxChanged(newValue: boolean) {
    this.realTimePerformanceBoxChecked = newValue;
    this.startBatchOptionDisabled = newValue;
  }

  loadConfig() {
    const id = this.job.jobId;
    this.jobInformationService.getConfigFile(id).subscribe(
      (res) => {
        this.configContent = res.data;
        this.parseConfigToForm(this.configContent);
        this.validateConfig();
        console.log(this.configContent)
      },
      (error) => {
        this.configError = '无法加载配置文件: ' + error.message;
      }
    );
  }

  parseConfigToForm(configContent: string) {
    try {
      const config = jsyaml.load(configContent) as any;
      this.configStructure = config;
      this.configSections = [];
      
      // 重新构建表单
      const formControls: any = {};
      
      // 遍历配置对象，为每个顶级键创建配置分组
      Object.keys(config).forEach(sectionKey => {
        const sectionValue = config[sectionKey];
        const sectionFields: any[] = [];
        
        if (sectionValue && typeof sectionValue === 'object' && !Array.isArray(sectionValue)) {
          // 处理对象类型的配置节
          const sectionFormGroup: any = {};
          
          Object.keys(sectionValue).forEach(fieldKey => {
            const fieldValue = sectionValue[fieldKey];
            const fieldConfig = this.createFieldConfig(fieldKey, fieldValue);
            
            sectionFields.push(fieldConfig);
            sectionFormGroup[fieldKey] = this.createFormControl(fieldValue, fieldConfig.type);
          });
          
          formControls[sectionKey] = this.fb.group(sectionFormGroup);
        } else {
          // 处理简单类型的配置项
          const fieldConfig = this.createFieldConfig(sectionKey, sectionValue);
          sectionFields.push(fieldConfig);
          formControls[sectionKey] = this.createFormControl(sectionValue, fieldConfig.type);
        }
        
        this.configSections.push({
          key: sectionKey,
          label: this.formatLabel(sectionKey),
          fields: sectionFields,
          isObject: sectionValue && typeof sectionValue === 'object' && !Array.isArray(sectionValue)
        });
      });
      
      // 重新创建表单
      this.configForm = this.fb.group(formControls);
      
    } catch (e) {
      console.error('解析配置文件失败:', e);
      this.message.error('配置文件格式错误，无法解析');
    }
  }

  createFieldConfig(key: string, value: any) {
    const fieldType = this.detectFieldType(value);
    return {
      key: key,
      label: this.formatLabel(key),
      type: fieldType,
      value: value,
      required: this.isRequiredField(key),
      placeholder: this.generatePlaceholder(key, fieldType),
      options: this.getFieldOptions(key, fieldType)
    };
  }

  detectFieldType(value: any): string {
    if (typeof value === 'boolean') {
      return 'boolean';
    } else if (typeof value === 'number') {
      return 'number';
    } else if (typeof value === 'string') {
      if (value.includes('\n')) {
        return 'textarea';
      } else if (value.toLowerCase().includes('password') || value.toLowerCase().includes('key')) {
        return 'password';
      } else if (this.isUrl(value)) {
        return 'url';
      } else if (this.isFilePath(value)) {
        return 'file';
      } else {
        return 'text';
      }
    } else if (Array.isArray(value)) {
      return 'array';
    } else if (value === null || value === undefined || value === '') {
      return 'text';
    } else {
      return 'text';
    }
  }

  createFormControl(value: any, type: string) {
    const validators: ValidatorFn[] = [];
    
    if (this.isRequiredField(type)) {
      validators.push(Validators.required);
    }
    
    if (type === 'number') {
      return this.fb.control(value || 0, validators);
    } else if (type === 'boolean') {
      return this.fb.control(value || false, validators);
    } else {
      return this.fb.control(value || '', validators);
    }
  }

  formatLabel(key: string): string {
    return key.replace(/_/g, ' ')
              .replace(/([A-Z])/g, ' $1')
              .replace(/^./, str => str.toUpperCase())
              .trim();
  }

  isRequiredField(key: string): boolean {
    const requiredFields = ['api_key', 'model_name', 'data_path'];
    return requiredFields.some(field => key.toLowerCase().includes(field.toLowerCase()));
  }

  generatePlaceholder(key: string, type: string): string {
    if (key.toLowerCase().includes('path')) {
      return '请输入文件路径';
    } else if (key.toLowerCase().includes('url')) {
      return '请输入URL地址';
    } else if (key.toLowerCase().includes('key')) {
      return '请输入API密钥';
    } else if (key.toLowerCase().includes('model')) {
      return '请输入模型名称';
    } else if (type === 'number') {
      return '请输入数字';
    } else {
      return `请输入${this.formatLabel(key)}`;
    }
  }

  getFieldOptions(key: string, type: string): any[] {
    if (key.toLowerCase().includes('method')) {
      return [
        { label: 'OpenAI', value: 'openai' },
        { label: 'huggingface', value: 'hf' },
        { label: 'Local', value: 'local' }
      ];
    } else if (key.toLowerCase() === 'stm' || key.toLowerCase() === 'ltm' || key.toLowerCase() === 'dcm') {
      return [
        { label: '启用', value: true },
        { label: '禁用', value: false }
      ];
    }
    return [];
  }

  isUrl(str: string): boolean {
    try {
      new URL(str);
      return true;
    } catch {
      return false;
    }
  }

  isFilePath(str: string): boolean {
    return str.includes('/') || str.includes('\\') || str.includes('.');
  }

  formToConfigContent(): string {
    const formValue = this.configForm.value;
    
    const config: any = {};
    
    this.configSections.forEach(section => {
      if (section.isObject) {
        config[section.key] = formValue[section.key] || {};
      } else {
        config[section.key] = formValue[section.key];
      }
    });
    
    return jsyaml.dump(config, { indent: 2 });
  }

  getFormControl(sectionKey: string, fieldKey?: string): any {
    if (fieldKey) {
      return this.configForm.get([sectionKey, fieldKey]);
    } else {
      return this.configForm.get(sectionKey);
    }
  }

  validateConfig() {
    try {
      jsyaml.load(this.configContent);
      this.configError = null;
    } catch (e) {
      this.configError = e instanceof Error ? e.message : '未知错误';
    }
  }

  resetConfig() {
    this.loadConfig();
    this.configSuccess = false;
  }

  onConfigTabChange(index: number) {
    // 当从表单模式切换到原始模式时，同步表单数据到configContent
    if (this.activeConfigTab === 0 && index === 1 && this.configForm.valid) {
      this.configContent = this.formToConfigContent();
    }
    // 当从原始模式切换到表单模式时，解析configContent到表单
    else if (this.activeConfigTab === 1 && index === 0 && !this.configError) {
      this.parseConfigToForm(this.configContent);
    }
    this.activeConfigTab = index;
  }

  submitConfig() {
    // 根据当前活动的标签页决定使用哪种数据源
    if (this.activeConfigTab === 0) {
      // 表单模式：检查表单有效性并同步数据
      if (this.configForm.valid) {
        this.configContent = this.formToConfigContent();
      } else {
        this.message.error('表单数据无效，请检查输入');
        return;
      }
    }
    // 原始模式：直接使用当前的configContent
    
    if (this.configError) {
      return;
    }
    
    this.isSubmitting = true;
    this.configSuccess = false;
    
    this.jobInformationService.updateConfigFile(String(this.job.jobId), this.configContent).subscribe(
      () => {
        this.configSuccess = true;
        this.isSubmitting = false;
        this.message.success('配置更新成功');
        // 重新解析配置到表单，保持表单和原始模式同步
        this.parseConfigToForm(this.configContent);
      },
      (error) => {
        this.configError = '更新配置失败: ' + error.message;
        this.isSubmitting = false;
        this.message.error('配置更新失败');
      }
    );
  }
}
