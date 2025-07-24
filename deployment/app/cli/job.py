import typer
from sage_core.jobmanager_client import JobManagerClient
import time
import subprocess

app = typer.Typer(help="作业管理相关命令。支持作业列表、详情、停止、删除、状态、健康检查等。详细参数请用 --help 查看。")

@app.command()
def list(
    status: str = typer.Option(None, "--status", help="按状态过滤作业"),
    format: str = typer.Option("table", "--format", help="输出格式(table/json)"),
    full_uuid: bool = typer.Option(False, "--full-uuid", help="显示完整UUID")
):
    """列出所有作业。可按状态过滤，支持表格或JSON格式。"""
    client = JobManagerClient()
    try:
        jobs = client.get_actor_handle().list_jobs()
        if status:
            jobs = [job for job in jobs if job.get("status") == status]
        if format == "json":
            import json
            typer.echo(json.dumps(jobs, indent=2, ensure_ascii=False))
        else:
            typer.echo(f"共{len(jobs)}个作业：")
            for i, job in enumerate(jobs, 1):
                uuid = job.get("uuid", "unknown")
                uuid_disp = uuid if full_uuid else uuid[:8] + "..."
                typer.echo(f"{i}. {uuid_disp} | {job.get('name', 'unknown')} | {job.get('status', 'unknown')}")
    except Exception as e:
        typer.echo(f"[错误] 查询作业失败: {e}", err=True)

@app.command()
def show(job_identifier: str):
    """显示作业详情。"""
    client = JobManagerClient()
    try:
        job = client.get_actor_handle().get_job_status(job_identifier)
        import json
        typer.echo(json.dumps(job, indent=2, ensure_ascii=False))
    except Exception as e:
        typer.echo(f"[错误] 查询作业详情失败: {e}", err=True)

@app.command()
def stop(job_identifier: str, force: bool = typer.Option(False, "--force", help="强制停止，无需确认")):
    """停止作业。默认需确认，可用--force跳过。"""
    client = JobManagerClient()
    try:
        if not force:
            confirm = typer.confirm(f"确定要停止作业 {job_identifier} 吗？", abort=True)
        result = client.get_actor_handle().pause_job(job_identifier)
        typer.echo(f"停止结果: {result}")
    except Exception as e:
        typer.echo(f"[错误] 停止作业失败: {e}", err=True)

@app.command()
def delete(job_identifier: str, force: bool = typer.Option(False, "--force", help="强制删除，无需确认")):
    """删除作业。默认需确认，可用--force跳过。"""
    client = JobManagerClient()
    try:
        if not force:
            confirm = typer.confirm(f"确定要删除作业 {job_identifier} 吗？此操作不可恢复。", abort=True)
        result = client.get_actor_handle().delete_job(job_identifier, force=force)
        typer.echo(f"删除结果: {result}")
    except Exception as e:
        typer.echo(f"[错误] 删除作业失败: {e}", err=True)

@app.command()
def status(job_identifier: str):
    """获取作业状态。"""
    client = JobManagerClient()
    try:
        job = client.get_actor_handle().get_job_status(job_identifier)
        typer.echo(f"作业状态: {job.get('status', 'unknown')}")
    except Exception as e:
        typer.echo(f"[错误] 获取作业状态失败: {e}", err=True)

@app.command()
def health():
    """健康检查。"""
    client = JobManagerClient()
    try:
        result = client.health_check()
        typer.echo(f"健康检查: {result}")
    except Exception as e:
        typer.echo(f"[错误] 健康检查失败: {e}", err=True)

@app.command()
def monitor(refresh: int = typer.Option(5, "--refresh", help="刷新间隔（秒）")):
    """实时监控所有作业。可指定刷新间隔。Ctrl+C退出。"""
    client = JobManagerClient()
    try:
        while True:
            jobs = client.get_actor_handle().list_jobs()
            typer.echo(f"\n=== 作业监控 ===")
            for i, job in enumerate(jobs, 1):
                typer.echo(f"{i}. {job.get('uuid', '')[:8]}... | {job.get('name', '')} | {job.get('status', '')}")
            time.sleep(refresh)
    except KeyboardInterrupt:
        typer.echo("监控已停止")
    except Exception as e:
        typer.echo(f"[错误] 监控失败: {e}", err=True)

@app.command()
def shell():
    """进入交互式shell。"""
    try:
        subprocess.run(["sage-jm", "shell"], check=True)
    except subprocess.CalledProcessError:
        typer.echo("[错误] 进入shell失败。", err=True)

@app.command()
def main():
    """作业管理主入口（占位）。"""
    typer.echo("请使用子命令或 --help 查看可用功能。")
