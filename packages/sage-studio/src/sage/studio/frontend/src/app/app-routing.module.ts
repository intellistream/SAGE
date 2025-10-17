import { NgModule } from '@angular/core';
import { Routes, RouterModule } from '@angular/router';
import {OverviewComponent} from "./pages/overview/overview.component";
import {JobInformationComponent} from "./pages/application-information/job-information.component";
import {SubmitNewJobComponent} from "./pages/submit-new-job/submit-new-job.component";
import {CodeEditorComponent} from "./pages/code-editor/code-editor.component";
import {OperatorEditorComponent} from "./pages/operator-editor/operator-editor.component";
import {PipelineComponent} from "./pages/pipeline/pipeline.component"
import {SubmitNewPipelineComponent} from "./pages/submit-new-pipeline/submit-new-pipeline.component"

const routes: Routes = [
  // Home
  { path: '', pathMatch: 'full', redirectTo: '/overview' },
  { path: 'job/:id', component: JobInformationComponent },
  // { path: 'overview/application-details', component: JobInformationComponent },
  { path: 'overview', component: OverviewComponent },
  // { path: 'applications/finished-applications', component: FinishedApplicationsComponent },
  // { path: 'applications/processing-applications', component: ProcessingApplicationsComponent },
  { path: 'submit-new-job', component: SubmitNewJobComponent },
  { path: 'submit-new-pipeline', component: SubmitNewPipelineComponent},
  { path: 'code-editor', component: CodeEditorComponent },
  { path: 'operator-editor', component: OperatorEditorComponent }

];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule { }
