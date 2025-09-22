/**
 * Mock数据服务
 * 为Studio前端提供测试数据，便于开发和测试
 */
import { Injectable } from '@angular/core';
import { Observable, of, delay } from 'rxjs';
import { map } from 'rxjs/operators';
import { OperatorInfo } from '../model/OperatorInfo';
import { Job } from '../model/Job';
const MOCK_OPERATORS_DELAY_MS = 500; 
@Injectable({
  providedIn: 'root'
})
export class MockDataService {

  constructor() { }

  /**
   * Mock操作符数据
   */
  getMockOperators(): Observable<OperatorInfo[]> {
    const mockOperators: OperatorInfo[] = [
      {
        id: 1,
        name: 'FileSource',
        description: '从文件读取数据的源操作符',
        code: `
class FileSource:
    def __init__(self, file_path):
        self.file_path = file_path
    
    def read_data(self):
        with open(self.file_path, 'r') as f:
            return f.read()
        `,
        isCustom: true
      },
      {
        id: 2, 
        name: 'SimpleRetriever',
        description: '简单的检索操作符',
        code: `
class SimpleRetriever:
    def __init__(self, top_k=5):
        self.top_k = top_k
    
    def retrieve(self, query):
        # 简单的检索逻辑
        return query[:self.top_k]
        `,
        isCustom: true
      },
      {
        id: 3,
        name: 'TerminalSink', 
        description: '输出到终端的汇操作符',
        code: `
class TerminalSink:
    def __init__(self):
        pass
    
    def write(self, data):
        print(data)
        `,
        isCustom: false
      }
    ];

    return of(mockOperators).pipe(delay(MOCK_OPERATORS_DELAY_MS)); // 模拟网络延迟
  }

  /**
   * Mock作业数据
   */
  getMockJobs(): Observable<Job[]> {
    const mockJobs: Job[] = [
      {
        jobId: 'job_001',
        name: 'RAG问答管道', 
        isRunning: true,
        nthreads: '4',
        cpu: '80%',
        ram: '2GB',
        startTime: '2025-08-18 10:30:00',
        duration: '00:45:12',
        nevents: 1000,
        minProcessTime: 10,
        maxProcessTime: 500,
        meanProcessTime: 150,
        latency: 200,
        throughput: 800,
        ncore: 4,
        periodicalThroughput: [750, 800, 820, 785, 810],
        periodicalLatency: [180, 200, 190, 210, 195],
        totalTimeBreakdown: {
          totalTime: 2712000, // 45分12秒
          serializeTime: 50000,
          persistTime: 100000,
          streamProcessTime: 2500000,
          overheadTime: 62000
        },
        schedulerTimeBreakdown: {
          overheadTime: 50000,
          streamTime: 2600000,
          totalTime: 2712000,
          txnTime: 62000
        },
        operators: [
          {
            id: 1,
            name: 'FileSource',
            numOfInstances: 1,
            throughput: 800,
            latency: 50,
            explorationStrategy: 'greedy',
            schedulingGranularity: 'batch',
            abortHandling: 'rollback',
            numOfTD: 10,
            numOfLD: 5,
            numOfPD: 2,
            lastBatch: 999,
            downstream: [2]
          },
          {
            id: 2, 
            name: 'SimpleRetriever',
            numOfInstances: 2,
            throughput: 750,
            latency: 120,
            explorationStrategy: 'random',
            schedulingGranularity: 'tuple',
            abortHandling: 'skip',
            numOfTD: 8,
            numOfLD: 4,
            numOfPD: 3,
            lastBatch: 998,
            downstream: [3]
          },
          {
            id: 3,
            name: 'TerminalSink',
            numOfInstances: 1,
            throughput: 700,
            latency: 30,
            explorationStrategy: 'greedy',
            schedulingGranularity: 'batch',
            abortHandling: 'retry',
            numOfTD: 12,
            numOfLD: 6,
            numOfPD: 1,
            lastBatch: 997,
            downstream: []
          }
        ]
      },
      {
        jobId: 'job_002',
        name: '数据处理管道',
        isRunning: false,
        nthreads: '2',
        cpu: '45%',
        ram: '1GB',
        startTime: '2025-08-18 09:15:00',
        duration: '00:20:30',
        nevents: 500,
        minProcessTime: 15,
        maxProcessTime: 300,
        meanProcessTime: 120,
        latency: 150,
        throughput: 400,
        ncore: 2,
        periodicalThroughput: [380, 400, 420, 390],
        periodicalLatency: [140, 150, 160, 145],
        totalTimeBreakdown: {
          totalTime: 1230000, // 20分30秒
          serializeTime: 25000,
          persistTime: 50000,
          streamProcessTime: 1120000,
          overheadTime: 35000
        },
        schedulerTimeBreakdown: {
          overheadTime: 25000,
          streamTime: 1180000,
          totalTime: 1230000,
          txnTime: 25000
        },
        operators: [
          {
            id: 4,
            name: 'FileSource',
            numOfInstances: 1,
            throughput: 400,
            latency: 40,
            explorationStrategy: 'greedy',
            schedulingGranularity: 'batch',
            abortHandling: 'rollback',
            numOfTD: 6,
            numOfLD: 3,
            numOfPD: 1,
            lastBatch: 499,
            downstream: [5]
          },
          {
            id: 5,
            name: 'TerminalSink', 
            numOfInstances: 1,
            throughput: 380,
            latency: 110,
            explorationStrategy: 'greedy',
            schedulingGranularity: 'tuple',
            abortHandling: 'skip',
            numOfTD: 8,
            numOfLD: 4,
            numOfPD: 2,
            lastBatch: 498,
            downstream: []
          }
        ]
      }
    ];

    return of(mockJobs).pipe(delay(800)); // 模拟网络延迟
  }

  /**
   * Mock管道配置数据
   */
  getMockPipelineConfig(): Observable<{data: string}> {
    const mockConfig = {
      data: `# SAGE Pipeline Configuration
name: "示例RAG管道"
description: "演示RAG问答系统的数据处理管道"

operators:
  - id: "source1"
    type: "FileSource"
    config:
      file_path: "/data/documents.txt"
      encoding: "utf-8"
    
  - id: "retriever1" 
    type: "SimpleRetriever"
    config:
      top_k: 5
      similarity_threshold: 0.8
    
  - id: "sink1"
    type: "TerminalSink"
    config:
      format: "json"

connections:
  - from: "source1"
    to: "retriever1"
  - from: "retriever1" 
    to: "sink1"
`
    };

    return of(mockConfig).pipe(delay(300));
  }

  /**
   * Mock操作符列表响应
   */
  getMockOperatorListResponse(page: number = 1, pageSize: number = 10): Observable<{items: OperatorInfo[], total: number}> {
    return this.getMockOperators().pipe(
      delay(600),
      // 简单分页模拟
      map(operators => ({
        items: operators.slice((page - 1) * pageSize, page * pageSize),
        total: operators.length
      }))
    );
  }
}
