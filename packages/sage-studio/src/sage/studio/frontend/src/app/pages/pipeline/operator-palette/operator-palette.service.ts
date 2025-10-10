// src/app/pipeline/operator-palette/operator-palette.service.ts

import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { OperatorInfo } from '../../../model/OperatorInfo';
import { environment } from '../../../../environments/environment';

// 配置API基础URL，指向Web UI服务
const apiConfig = {
  apiUrl: environment.api.baseUrl + environment.api.paths.operators
};

@Injectable({
  providedIn: 'root'
})
export class OperatorPaletteService {
  private apiUrl = apiConfig.apiUrl;

  constructor(private http: HttpClient) { }

  getOperators(): Observable<any> {
    return this.http.get<any>(`${this.apiUrl}/list`);
  }
}