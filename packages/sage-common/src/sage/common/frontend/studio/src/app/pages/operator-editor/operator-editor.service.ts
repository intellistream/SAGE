import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import {OperatorInfo} from "../../model/OperatorInfo";
import { MockDataService } from "../../services/mock-data.service";
import { environment } from "../../../environments/environment";

// 配置API基础URL，指向Web UI服务
const apiConfig = {
  apiUrl: environment.api.baseUrl + environment.api.paths.operators
};

interface OperatorListResponse {
  items: OperatorInfo[];
  total: number;
}

@Injectable({
  providedIn: 'root'
})
export class OperatorService {
  private apiUrl = apiConfig.apiUrl;

  constructor(
    private http: HttpClient,
    private mockDataService: MockDataService
  ) {}

  // 获取操作符列表
  getOperators(page: number, pageSize: number, searchText: string = ''): Observable<OperatorListResponse> {
    // 如果启用了Mock数据，返回Mock数据
    if (environment.dev.enableMockData) {
      return this.mockDataService.getMockOperatorListResponse(page, pageSize);
    }
    
    let params = new HttpParams()
      .set('page', page.toString())
      .set('size', pageSize.toString());
    
    if (searchText) {
      params = params.set('search', searchText);
    }

    // 注意：这个路径需要后端实际支持，目前可能需要Mock数据
    return this.http.get<OperatorListResponse>(`${this.apiUrl}/list`, { params });
  }

  getOperatorById(id: string): Observable<OperatorInfo> {
    // 如果启用了Mock数据，返回Mock数据中的第一个
    if (environment.dev.enableMockData) {
      return new Observable(observer => {
        this.mockDataService.getMockOperators().subscribe(operators => {
          const operator = operators.find(op => op.id.toString() === id);
          if (operator) {
            observer.next(operator);
          } else {
            observer.error('Operator not found');
          }
          observer.complete();
        });
      });
    }
    
    return this.http.get<OperatorInfo>(`${this.apiUrl}/${id}`);
  }

  // 修改返回类型和参数类型
  createOperator(operator: Omit<OperatorInfo, 'id'>): Observable<OperatorInfo> {
    return this.http.post<OperatorInfo>(`${this.apiUrl}/create`, operator);
  }

  
  updateOperator(operator: OperatorInfo,old_name:string): Observable<any> {
    return this.http.put<OperatorInfo>(`${this.apiUrl}/update/${operator.id}/${old_name}`, operator);
  }

  deleteOperator(id: number, name: string): Observable<any> {
    
    return this.http.delete<any>(`${this.apiUrl}/delete/${id}/${name}`);
  }

  // 可选：验证Operator代码
  validateOperatorCode(code: string): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/validate`, { code });
  }

  // 可选：部署Operator
  deployOperator(id: string): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/${id}/deploy`, {});
  }
}