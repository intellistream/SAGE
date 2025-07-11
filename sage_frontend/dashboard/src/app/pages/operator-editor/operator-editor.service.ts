import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import {OperatorInfo} from "../../model/OperatorInfo";
let environment = {
  apiUrl: "http://localhost:8080/api"
};

interface OperatorListResponse {
  items: OperatorInfo[];
  total: number;
}

@Injectable({
  providedIn: 'root'
})
export class OperatorService {
  private apiUrl = `${environment.apiUrl}/operators`;

  constructor(private http: HttpClient) {}

  getOperators(page: number, pageSize: number, searchText: string = ''): Observable<OperatorListResponse> {
    let params = new HttpParams()
      .set('page', page.toString())
      .set('size', pageSize.toString());
    
    if (searchText) {
      params = params.set('search', searchText);
    }

    return this.http.get<OperatorListResponse>(`${this.apiUrl}/get/all`, { params });
  }

  getOperatorById(id: string): Observable<OperatorInfo> {
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