import { Component, OnInit } from '@angular/core';
import { FormControl,FormBuilder, FormGroup,NonNullableFormBuilder, Validators } from '@angular/forms';
import { NzMessageService } from 'ng-zorro-antd/message';
import { OperatorService } from './operator-editor.service';
import {OperatorInfo} from "../../model/OperatorInfo";

import 'codemirror/mode/clike/clike';

interface Operator {
  id: string;
  name: string;
  description: string;
  implementation: string;
  icon?: string;
}

@Component({
  selector: 'app-operator-editor',
  templateUrl: './operator-editor.component.html',
  styleUrls: ['./operator-editor.component.less']
})
export class OperatorEditorComponent implements OnInit {
  // 列表相关
  operators: OperatorInfo[] = [];
  totalOperators = 0;
  currentPage = 1;
  pageSize = 10;
  searchText = '';

  // 弹窗相关
  isOperatorModalVisible = false;
  modalTitle = 'Add Operator';
  operatorForm!: FormGroup;
  currentOperator: OperatorInfo | null = null;
  operator_name = '';

  // 编辑器配置
  editorOptions = {
    theme: 'vs-dark',
    language: 'python',
    automaticLayout: true,
    minimap: {
      enabled: true
    }
  };

  constructor(
    private fb: FormBuilder,
    private operatorService: OperatorService,
    private message: NzMessageService
  ) {}

  ngOnInit(): void {
    this.initForm();
    this.loadOperators();
  }

  initForm(): void {
    this.operatorForm = this.fb.group({
      name: [null, [Validators.required]],
      description: [null, [Validators.required]],
      implementation: [null, [Validators.required]]
    });
  }

  loadOperators(): void {
    this.operatorService.getOperators(this.currentPage, this.pageSize, this.searchText)
      .subscribe({
        next: (response) => {
          this.operators = response.items;
          this.totalOperators = response.total;
        },
        error: (error) => {
          this.message.error('加载Operator列表失败');
          console.error('Failed to load operators', error);
        }
      });
  }

  showAddOperatorModal(): void {
    this.modalTitle = 'Add Operator';
    this.currentOperator = null;
    this.operatorForm.reset();
    this.operatorForm.patchValue({
      implementation: `
class CustomFunction(BaseFunction):
    def __init__(self):
        super().__init__()

    def execute(self):
        raise NotImplementedError("RerankerFunction must implement execute().")
        
class CustomOperator(CustomFunction):
    def __init__(self, config):
    
        super().__init__()
        self.config = config["custom_operator"]
        self.info = self.config["info"]

    def execute(self, data: Data[Tuple[str, str]]) ->  Data[Tuple[str, str]]:
    
        #print("CustomOperator execute method called")
        #print(f"config_test: {self.info}")
        return data
`
    });
    this.isOperatorModalVisible = true;
  }

  editOperator(operator: OperatorInfo): void {
    if (!operator.isCustom) {
      this.message.warning('系统Operator不可编辑');
      return;
    }
    this.operator_name = operator.name; // Store the name for later use in the patc
    this.modalTitle = 'Edit Operator';
    this.currentOperator = operator;
    this.operatorForm.patchValue({
      name: operator.name,
      description: operator.description,
      implementation: operator.code
    });
    this.isOperatorModalVisible = true;
  }

  deleteOperator(operator: OperatorInfo): void {
    this.operatorService.deleteOperator(operator.id,operator.name)
      .subscribe({
        next: () => {
          this.message.success(`Operator "${operator.name}" 已删除`);
          this.loadOperators();
        },
        error: (error) => {
          this.message.error('删除Operator失败');
          console.error('Failed to delete operator', error);
        }
      });
  }

  handleModalOk(): void {
    if (this.operatorForm.valid) {
      const formData = this.operatorForm.value;
      
      if (this.currentOperator) {
        const new_operator :OperatorInfo = {
          id:this.currentOperator.id,
          name: formData.name,
          description: formData.description,
          code: formData.implementation,
          isCustom: true
        };
        // 更新现有Operator
        this.operatorService.updateOperator(new_operator, this.operator_name).subscribe({
          next: () => {
            this.message.success(`Operator "${formData.name}" 已更新`);
            this.isOperatorModalVisible = false;
            this.loadOperators();
          },
          error: (error) => {
            this.message.error('更新Operator失败');
            console.error('Failed to update operator', error);
          }
        });
        
      } else {
        // 创建新Operator
        const newOperator = {
          name: formData.name,
          description: formData.description,
          code: formData.implementation, // Make sure the property name matches what the backend expects
          isCustom: true // Ensure this flag is set for new operators
        };
        this.operatorService.createOperator(newOperator)
        .subscribe({
          next: (response) => {
            this.message.success(`Operator "${formData.name}" 已创建`);
            this.isOperatorModalVisible = false;
            this.loadOperators();
          },
          error: (error) => {
            if (error.status === 422) {
              // Display more specific error message from the server if available
              const errorMsg = error.error?.message || '创建Operator失败: 请检查输入数据格式';
              this.message.error(errorMsg);
            } else {
              this.message.error('创建Operator失败');
            }
            console.error('Failed to create operator', error);
          }
        });
      }
    } else {
      Object.values(this.operatorForm.controls).forEach(control => {
        if (control.invalid) {
          control.markAsDirty();
          control.updateValueAndValidity({ onlySelf: true });
        }
      });
    }
  }

  handleModalCancel(): void {
    this.isOperatorModalVisible = false;
  }
}