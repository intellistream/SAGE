"""SAGE Demo 命令 - 即开即用的体验入口."""

import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

app = typer.Typer(
    name="demo",
    help="🎮 Demo - 即开即用的 SAGE 体验",
    no_args_is_help=True,
)

console = Console()


# ============================================================================
# Demo: Hello World
# ============================================================================
HELLO_WORLD_CODE = '''
print("🚀 SAGE Hello World Demo")
print("=" * 40)
print()

# SAGE 使用声明式 Pipeline 处理数据流
# 这是一个简化的演示，展示 SAGE 的核心概念

# 1. 模拟数据流
data = [1, 2, 3, 4, 5]
print(f"📥 输入数据: {data}")

# 2. 定义转换操作 (类似 SAGE 的 map 算子)
def double(x):
    """翻倍算子"""
    return x * 2

def add_ten(x):
    """加10算子"""
    return x + 10

# 3. 应用 Pipeline: data -> double -> add_ten
result = [add_ten(double(x)) for x in data]
print(f"📤 输出结果: {result}")
print()

# 4. 在真实的 SAGE 中，你可以这样写:
print("💡 SAGE Pipeline 写法:")
print("""
   from sage.kernel import LocalEnvironment

   env = LocalEnvironment()
   stream = env.from_batch([1, 2, 3, 4, 5])
   stream.map(double).map(add_ten).print()
   env.submit()
""")
print()
print("✅ Hello SAGE! 了解更多: sage demo run streaming")
'''


# ============================================================================
# Demo: RAG Pipeline (需要可选依赖)
# ============================================================================
RAG_DEMO_CODE = """
from sage.libs.rag import SimpleRAG

# 创建简单的 RAG 实例
rag = SimpleRAG()

# 添加文档
rag.add_documents([
    "SAGE 是一个流式数据处理框架",
    "SAGE 支持 LLM 推理和 RAG 管道",
    "SAGE 使用 Python 3.10+ 开发",
])

# 查询
result = rag.query("SAGE 是什么?")
print(f"问题: SAGE 是什么?")
print(f"答案: {result}")
"""


# ============================================================================
# Demo: Streaming (完整 Pipeline 示例)
# ============================================================================
STREAMING_DEMO_CODE = """
from sage.kernel import LocalEnvironment
from sage.common.core import SinkFunction

print("🌊 SAGE 流式数据处理演示")
print("=" * 40)

# 收集结果的 Sink
class CollectorSink(SinkFunction):
    results = []
    def execute(self, data):
        CollectorSink.results.append(data)
        return data

# 模拟传感器数据
sensor_data = [
    {"sensor_id": 1, "value": 23.5},
    {"sensor_id": 2, "value": 18.2},
    {"sensor_id": 1, "value": 24.1},
    {"sensor_id": 2, "value": 19.0},
    {"sensor_id": 1, "value": 25.0},
]

print(f"📥 输入: {len(sensor_data)} 条传感器数据")

# 创建并执行 Pipeline
env = LocalEnvironment("demo")
stream = env.from_batch(sensor_data)
stream.filter(lambda x: x["sensor_id"] == 1).map(lambda x: {**x, "alert": x["value"] > 24}).sink(CollectorSink)
env.submit()

# 显示结果
print("📤 处理结果 (sensor_id=1):")
for item in CollectorSink.results:
    status = "🔴 告警" if item.get("alert") else "🟢 正常"
    print(f"  温度 {item['value']}°C - {status}")
print()
print("✅ Pipeline 执行完成!")
"""


# ============================================================================
# Commands
# ============================================================================
@app.command("list")
def list_demos():
    """📋 列出所有可用的 demo"""
    table = Table(title="🎮 SAGE Demos", show_header=True)
    table.add_column("名称", style="cyan", width=15)
    table.add_column("描述", style="white")
    table.add_column("依赖", style="yellow")

    table.add_row("hello", "Hello World - Pipeline 基础", "无")
    table.add_row("streaming", "流式数据处理演示", "无")
    table.add_row("rag", "RAG 检索增强生成", "ml, vdb")
    table.add_row("llm", "LLM 对话演示", "isagellm")

    console.print(table)
    console.print()
    console.print("[dim]运行示例: sage demo run hello[/dim]")


@app.command("run")
def run_demo(
    name: str = typer.Argument(..., help="Demo 名称 (hello, streaming, rag, llm)"),
    show_code: bool = typer.Option(False, "--show-code", "-c", help="只显示代码，不执行"),
):
    """▶️ 运行指定的 demo"""
    demos = {
        "hello": ("Hello World", HELLO_WORLD_CODE, []),
        "streaming": ("流式处理", STREAMING_DEMO_CODE, []),
        "rag": ("RAG Pipeline", RAG_DEMO_CODE, ["torch", "faiss"]),
        "llm": ("LLM 对话", None, ["isagellm"]),
    }

    if name not in demos:
        console.print(f"[red]❌ 未知的 demo: {name}[/red]")
        console.print(f"[dim]可用的 demo: {', '.join(demos.keys())}[/dim]")
        raise typer.Exit(1)

    title, code, deps = demos[name]

    # 检查依赖
    if deps:
        missing = _check_dependencies(deps)
        if missing:
            console.print(f"[yellow]⚠️ 缺少依赖: {', '.join(missing)}[/yellow]")
            console.print()
            console.print("[dim]安装方式:[/dim]")
            if "torch" in missing or "faiss" in missing:
                console.print("  pip install isage-middleware[ml,vdb]")
            if "isagellm" in missing:
                console.print("  pip install isagellm")
            console.print()
            if not show_code:
                raise typer.Exit(1)

    # 显示代码
    if code:
        console.print(Panel(f"[bold cyan]{title}[/bold cyan]", expand=False))
        syntax = Syntax(code.strip(), "python", theme="monokai", line_numbers=True)
        console.print(syntax)
        console.print()

    if show_code:
        return

    # 执行代码
    if name == "llm":
        _run_llm_demo()
    elif code:
        console.print("[bold green]▶️ 执行中...[/bold green]")
        console.print()

        # 抑制 SAGE 内部日志
        import logging
        import os

        os.environ["SAGE_LOG_LEVEL"] = "ERROR"
        logging.basicConfig(level=logging.ERROR, force=True)
        for logger_name in ["sage", "JobManager", "ray", "asyncio", "Dispatcher", "ExecutionGraph"]:
            logging.getLogger(logger_name).setLevel(logging.ERROR)

        try:
            exec(code, {"__name__": "__main__"})
        except Exception as e:
            console.print(f"[red]❌ 执行错误: {e}[/red]")
            raise typer.Exit(1)


@app.command("hello")
def hello_world():
    """👋 运行 Hello World 示例（最简单的入门）"""
    run_demo("hello")


@app.command("interactive")
def interactive_mode():
    """🎯 进入交互式 SAGE Shell"""
    console.print(Panel("[bold cyan]SAGE Interactive Shell[/bold cyan]", expand=False))
    console.print()
    console.print("[dim]提示: 输入 Python 代码，或使用以下快捷命令:[/dim]")
    console.print("  [cyan]!help[/cyan]     - 显示帮助")
    console.print("  [cyan]!demo[/cyan]     - 列出可用 demo")
    console.print("  [cyan]!exit[/cyan]     - 退出")
    console.print()

    # 预导入常用模块
    namespace = {}
    try:
        exec("from sage.kernel import LocalEnvironment", namespace)
        exec("env = LocalEnvironment()", namespace)
        console.print("[green]✅ 已导入: LocalEnvironment (已创建 env 实例)[/green]")
        console.print("[dim]   用法: stream = env.from_collection([1,2,3])[/dim]")
    except ImportError as e:
        console.print(f"[yellow]⚠️ 导入警告: {e}[/yellow]")

    console.print()

    # 简单 REPL
    import code

    code.interact(banner="", local=namespace, exitmsg="[dim]Goodbye![/dim]")


# ============================================================================
# Helper Functions
# ============================================================================
def _check_dependencies(deps: list[str]) -> list[str]:
    """检查依赖是否已安装"""
    import importlib.util

    missing = []
    for dep in deps:
        spec = importlib.util.find_spec(dep)
        if spec is None:
            missing.append(dep)
    return missing


def _run_llm_demo():
    """运行 LLM 对话演示"""
    try:
        from isagellm import UnifiedInferenceClient
    except ImportError:
        console.print("[red]❌ 需要安装 isagellm: pip install isagellm[/red]")
        raise typer.Exit(1)

    console.print("[bold]🤖 LLM 对话演示[/bold]")
    console.print("[dim]提示: 输入问题，或输入 'exit' 退出[/dim]")
    console.print()

    try:
        client = UnifiedInferenceClient.create()
        console.print("[green]✅ 已连接到 LLM 服务[/green]")
    except Exception as e:
        console.print(f"[yellow]⚠️ 连接失败: {e}[/yellow]")
        console.print("[dim]请先启动 LLM 服务: sage gateway start[/dim]")
        raise typer.Exit(1)

    while True:
        try:
            user_input = console.input("[cyan]You: [/cyan]")
            if user_input.lower() in ("exit", "quit", "q"):
                break

            response = client.chat([{"role": "user", "content": user_input}])
            console.print(f"[green]AI: [/green]{response}")
            console.print()
        except KeyboardInterrupt:
            break
        except Exception as e:
            console.print(f"[red]错误: {e}[/red]")

    console.print("[dim]Goodbye![/dim]")
