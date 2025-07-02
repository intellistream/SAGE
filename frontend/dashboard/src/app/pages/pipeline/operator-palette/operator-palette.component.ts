// src/sage_examples/pipeline/operator-palette/operator-palette.component.ts

import { Component, OnInit } from '@angular/core';
import { Node } from '../models/pipeline-data.model'; // Use the Node interface
import { OperatorInfo } from '../../../model/OperatorInfo';
import { OperatorPaletteService } from './operator-palette.service';

@Component({
  selector: 'sage_examples-operator-palette',
  templateUrl: './operator-palette.component.html',
  styleUrls: ['./operator-palette.component.scss']
})
export class OperatorPaletteComponent implements OnInit {
  // Define available operators. These will be the basis for new nodes.
  // Note: These are templates, the actual nodes on the canvas will get unique IDs and positions.
  operators: Partial<Node>[] = [ // Use Partial<Node> as they don't have id, x, y yet
    { type: 'source', name: '数据源' },
    { type: 'processor', name: '数据处理' },
    { type: 'sink', name: '数据汇' },
    { type: 'filter', name: '数据过滤' },
    // Add more operator types here
  ];

  constructor(private operatorPaletteService: OperatorPaletteService) { }

  ngOnInit(): void {
    // 在组件初始化时获取操作符信息
    this.getOperatorInfo();
  }

  getOperatorInfo(): void {
    this.operatorPaletteService.getOperators().subscribe({
      next: (response) => {
        console.log(response);
        const items = response.items;
        const total = response.total;
        console.log(items);
        console.log(total);
        // 处理响应数据，将其转换为 OperatorInfo 数组
        this.operators = items.map(item => ({
          type: "op",
          // 截断长名称，保留前8个字符，超出部分用...表示
          name: this.truncateName(item.name, 8),
          // 将原始id保存为operatorId，节点的实际id将在拖放时生成
          operatorId: item.id,
          // 保存完整名称用于提示
          fullName: item.name,
          description: item.description
        }));
        console.log(this.operators);
      },
      error: (error) => {
        console.error('获取操作符信息失败:', error);
      }
    });
  }

  // 添加一个辅助方法来截断长文本
  truncateName(name: string, maxLength: number): string {
    if (name.length <= maxLength) {
      return name;
    }
    return name.substring(0, maxLength) + '...';
  }
}
