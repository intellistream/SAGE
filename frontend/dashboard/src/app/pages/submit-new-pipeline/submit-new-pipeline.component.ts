// src/sage_examples/submit-new-pipeline/submit-new-pipeline.component.ts

import { Component } from '@angular/core';

@Component({
  selector: 'sage_examples-submit-new-pipeline',
  templateUrl: './submit-new-pipeline.component.html',
  styleUrls: ['./submit-new-pipeline.component.scss']
})
export class SubmitNewPipelineComponent {
  // 这个组件本身可以不需要太多逻辑，主要作为 Palette 和 Environment Canvas 的容器
  constructor() { }
}
