import typer

# 导入各功能模块的 Typer app
from deployment.app.cli import install, deploy, job, cli_tools, diagnose, config

app = typer.Typer(help="SAGE 统一命令行工具 - SAGE CLI")

# 注册子命令
app.add_typer(install.app, name="install", help="安装与环境管理")
app.add_typer(deploy.app, name="deploy", help="系统部署与管理")
app.add_typer(job.app, name="job", help="作业管理")
app.add_typer(cli_tools.app, name="cli", help="CLI工具管理")
app.add_typer(diagnose.app, name="diagnose", help="诊断与维护")
app.add_typer(config.app, name="config", help="配置与信息")

if __name__ == "__main__":
    app()

