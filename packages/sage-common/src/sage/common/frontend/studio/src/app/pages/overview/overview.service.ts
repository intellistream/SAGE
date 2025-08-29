import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { Job } from "../../model/Job";
import { HttpClient } from "@angular/common/http";
import { MockDataService } from "../../services/mock-data.service";
import { environment } from "../../../environments/environment";

@Injectable({
  providedIn: 'root'
})
export class OverviewService {
  constructor(
    private http: HttpClient,
    private mockDataService: MockDataService
  ) {}

  /**
   * Get all jobs from backend
   */
  public getAllJobs(): Observable<Job[]> {
    // 如果启用了Mock数据，返回Mock数据
    if (environment.dev.enableMockData) {
      return this.mockDataService.getMockJobs();
    }
    
    // 否则调用真实API
    return this.http.get<Job[]>(`${environment.api.baseUrl}${environment.api.paths.jobs}/all`);
  }
}
