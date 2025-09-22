#!/usr/bin/env python3
"""
SAGE Config Command - Refactored Version
========================================

使用 sage.cli.core 模块重构的配置管理命令
演示如何将原有的配置命令迁移到新的核心架构
"""

import typer
from pathlib import Path

# 使用新的核心模块
from sage.common.cli.core import (
    BaseCommand, cli_command, CLIException,
    OutputFormatter, print_status
)
from sage.common.cli.core.config import (
    create_default_config, load_and_validate_config
)
from sage.common.cli.core.utils import save_yaml_file

app = typer.Typer(name="config", help="⚙️ Configuration management")


class ConfigShowCommand(BaseCommand):
    """显示配置信息命令"""
    
    def execute(self, section: str = None):
        """显示配置信息"""
        try:
            self.validate_config_exists()
            
            self.print_section_header("📋 SAGE Configuration Information")
            self.formatter.print_info(f"Configuration file: {self.config_path}")
            
            if section:
                # 显示特定配置节
                if section in self.config:
                    self.formatter.print_data({section: self.config[section]})
                else:
                    raise CLIException(f"Configuration section '{section}' not found")
            else:
                # 显示所有配置
                summary = {
                    "Data Directory": self.config.get('data_dir', 'Not set'),
                    "Log Level": self.config.get('log_level', 'Not set'), 
                    "Work Directory": self.config.get('work_dir', 'Not set')
                }
                
                # Ray配置
                if 'ray' in self.config:
                    ray_config = self.config['ray']
                    summary["Ray Address"] = ray_config.get('address', 'Not set')
                    summary["Ray Port"] = ray_config.get('port', 'Not set')
                
                # Head节点配置
                if 'head' in self.config:
                    head_config = self.config['head']
                    summary["Head Host"] = head_config.get('host', 'Not set')
                    summary["Head Port"] = head_config.get('head_port', 'Not set')
                
                # SSH配置
                if 'ssh' in self.config:
                    ssh_config = self.config['ssh']
                    summary["SSH User"] = ssh_config.get('user', 'Not set')
                    summary["SSH Key Path"] = ssh_config.get('key_path', 'Not set')
                
                self.formatter.print_data(summary)
                
        except Exception as e:
            exit_code = self.handle_exception(e)
            raise typer.Exit(exit_code)


class ConfigInitCommand(BaseCommand):
    """初始化配置文件命令"""
    
    def execute(self, force: bool = False):
        """初始化配置文件"""
        try:
            if self.config_path.exists():
                if not force:
                    self.formatter.print_info(f"Configuration file already exists: {self.config_path}")
                    self.formatter.print_info("Use --force option to overwrite existing configuration")
                    return
                else:
                    self.formatter.print_info("🔄 Overwriting existing configuration file...")
            
            # 创建默认配置
            default_config = create_default_config()
            
            # 保存配置文件
            save_yaml_file(default_config, self.config_path)
            
            self.formatter.print_success(f"Configuration file created: {self.config_path}")
            self.formatter.print_info("🔧 You can edit the configuration file to customize settings")
            
            # 显示下一步操作提示
            self.formatter.print_info("\n💡 Next steps:")
            self.formatter.print_info("1. Edit the configuration file to match your environment")
            self.formatter.print_info("2. Run 'sage config show' to verify settings")
            self.formatter.print_info("3. Run 'sage doctor' to check system requirements")
            
        except Exception as e:
            exit_code = self.handle_exception(e)
            raise typer.Exit(exit_code)


class ConfigValidateCommand(BaseCommand):
    """验证配置文件命令"""
    
    def execute(self):
        """验证配置文件"""
        try:
            self.validate_config_exists()
            
            self.print_section_header("🔍 Configuration Validation")
            
            # 重新加载并验证配置
            validated_config = load_and_validate_config(self.config_path)
            
            # 检查各个配置节
            validation_results = []
            
            # 检查head配置
            if 'head' in validated_config:
                head_config = validated_config['head']
                validation_results.append({
                    "Section": "head",
                    "Status": "✅ Valid",
                    "Host": head_config.get('host', 'N/A'),
                    "Port": head_config.get('head_port', 'N/A')
                })
            else:
                validation_results.append({
                    "Section": "head", 
                    "Status": "❌ Missing",
                    "Host": "N/A",
                    "Port": "N/A"
                })
            
            # 检查SSH配置
            if 'ssh' in validated_config:
                ssh_config = validated_config['ssh']
                key_path = Path(ssh_config.get('key_path', ''))
                key_exists = key_path.exists() if key_path.name else False
                
                validation_results.append({
                    "Section": "ssh",
                    "Status": "✅ Valid" if key_exists else "⚠️ Key not found",
                    "User": ssh_config.get('user', 'N/A'),
                    "Key Path": str(key_path) if key_path.name else 'N/A'
                })
            
            # 检查daemon配置
            if 'daemon' in validated_config:
                daemon_config = validated_config['daemon']
                validation_results.append({
                    "Section": "daemon",
                    "Status": "✅ Valid",
                    "Host": daemon_config.get('host', 'N/A'),
                    "Port": daemon_config.get('port', 'N/A')
                })
            
            # 显示验证结果
            headers = ["Section", "Status", "Details"]
            formatted_results = []
            for result in validation_results:
                details = []
                for key, value in result.items():
                    if key not in ["Section", "Status"]:
                        details.append(f"{key}: {value}")
                
                formatted_results.append({
                    "Section": result["Section"],
                    "Status": result["Status"],
                    "Details": "; ".join(details)
                })
            
            self.formatter.print_data(formatted_results, headers)
            
            self.formatter.print_success("Configuration validation completed")
            
        except Exception as e:
            exit_code = self.handle_exception(e)
            raise typer.Exit(exit_code)


# 命令注册
@app.command("show")
@cli_command(require_config=False)  # show命令可以在没有配置时运行
def show_config(
    section: str = typer.Option(None, "--section", "-s", help="Show specific configuration section")
):
    """Show configuration information"""
    cmd = ConfigShowCommand()
    cmd.execute(section)


@app.command("init")
@cli_command(require_config=False)  # init命令不需要现有配置
def init_config(
    force: bool = typer.Option(False, "--force", "-f", help="Force overwrite existing configuration")
):
    """Initialize SAGE configuration file"""
    cmd = ConfigInitCommand()
    cmd.execute(force)


@app.command("validate")
@cli_command()  # 需要配置文件存在
def validate_config():
    """Validate configuration file"""
    cmd = ConfigValidateCommand()
    cmd.execute()


# 为了向后兼容，提供一个默认的config命令
@app.callback(invoke_without_command=True)
def config_callback(ctx: typer.Context):
    """Show configuration information (default behavior)"""
    if ctx.invoked_subcommand is None:
        show_config()


if __name__ == "__main__":
    app()
