from dotenv import load_dotenv
import os, time
from sage_core.api.env import LocalEnvironment
from sage_common_funs.io.source import FileSource
from sage_common_funs.io.sink import TerminalSink
from sage_libs.rag import OpenAIGenerator
from sage_libs.rag import QAPromptor
from sage_libs.rag import DenseRetriever
from sage_utils.config_loader import load_config
import gc, threading

def run_gc_report(verbose: bool = True):
    print("📦 [GC] 开始垃圾回收扫描...")
    
    # 启动一次垃圾回收
    collected = gc.collect()
    print(f"🧹 [GC] 回收完成，清理了 {collected} 个不可达对象")

    # 获取无法自动释放的对象（因为引用环或 __del__ 存在）
    uncollectables = gc.garbage
    if uncollectables:
        print(f"⚠️ [GC] 有 {len(uncollectables)} 个无法释放的对象:")
        for i, obj in enumerate(uncollectables):
            print(f"   #{i+1}: {type(obj)} {repr(obj)}")
    else:
        print("✅ [GC] 没有不可回收的垃圾对象")

    # 可选：列出当前所有的“可达对象”
    if verbose:
        print("\n🔍 [GC] 正在分析当前内存中的对象引用:")
        objs = gc.get_objects()
        print(f"👁️  当前总共跟踪了 {len(objs)} 个对象")
        
        counter = {}
        for o in objs:
            typename = type(o).__name__
            counter[typename] = counter.get(typename, 0) + 1
        
        top_types = sorted(counter.items(), key=lambda x: -x[1])[:10]
        for typename, count in top_types:
            print(f"   {typename:<25}: {count}")
    
    print("🌈 [GC] 垃圾回收报告完成\n")

def pipeline_run():
    """创建并运行数据处理管道"""
    env = LocalEnvironment()
    env.set_memory(config=None)
    # 构建数据处理流程
    query_stream = (env
                    .from_source(FileSource, config["source"])
                    .map(DenseRetriever, config["retriever"])
                    .map(QAPromptor, config["promptor"])
                    .map(OpenAIGenerator, config["generator"])
                    .sink(TerminalSink, config["sink"])
                    )
    try:
        env.submit()
        env.run_streaming()  # 启动管道
        time.sleep(30)  # 等待管道运行
        env.stop()
        time.sleep(60)
    finally:
        env.close()
    
    # run_gc_report()  # 强制垃圾回收，清理内存

if __name__ == '__main__':


    # 加载配置
    config = load_config("config.yaml")
    load_dotenv(override=False)

    api_key = os.environ.get("ALIBABA_API_KEY")
    if api_key:
        config.setdefault("generator", {})["api_key"] = api_key

    pipeline_run()
    run_gc_report()
    print("[DEBUG] 活跃线程列表：")
    for t in threading.enumerate():
        print(f" - {t.name} (daemon={t.daemon})")

    time.sleep(2)  # 等2秒看是否自动退出
    print("[DEBUG] 程序还没退出，说明有挂住的线程")


