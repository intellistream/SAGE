// src/sage_examples/pipeline/operator-palette/operator-palette.service.ts

import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { OperatorInfo } from '../../../model/OperatorInfo';

@Injectable({
  providedIn: 'root'
})
export class OperatorPaletteService {
  private apiUrl = "http://localhost:8080/api/operators"; // 根据实际API路径调整

  constructor(private http: HttpClient) { }

  getOperators(): Observable<any> {
    return this.http.get<any>(`${this.apiUrl}/get/operators`);
  }
}
