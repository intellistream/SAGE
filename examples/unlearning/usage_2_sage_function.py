"""
Usage 2: Using Unlearning in SAGE Function
===========================================

在 SAGE Function 中使用 unlearning 库。

适用场景：
- SAGE Pipeline 中的遗忘操作
- 与其他 Function 组合
- 流式处理场景
- 需要 SAGE 运行时能力（日志、状态等）

优势：
- 集成到 SAGE 生态
- 可以调用其他服务
- 支持状态持久化
- 完整的日志和监控
"""

import numpy as np
from sage.kernel.api.environment.local_environment import LocalEnvironment
from sage.kernel.api.function.base_function import BaseFunction
from sage.kernel.api.function.source_function import SourceFunction
from sage.kernel.api.function.sink_function import SinkFunction
from sage.libs.unlearning import UnlearningEngine
from sage.common.utils.logging.custom_logger import CustomLogger


class VectorGenerator(SourceFunction):
    """生成向量数据流"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.counter = 0
        self.max_count = 20
        self.dim = 128
    
    def execute(self):
        if self.counter >= self.max_count:
            return None
        
        # 生成一个向量
        vector = np.random.randn(self.dim).astype(np.float32)
        vector = vector / (np.linalg.norm(vector) + 1e-10)
        
        data = {
            'vector_id': f'doc_{self.counter}',
            'vector': vector,
            'should_forget': (self.counter % 5 == 0),  # 每5个标记为需要遗忘
            'metadata': {
                'category': 'sensitive' if self.counter % 5 == 0 else 'normal',
                'timestamp': self.counter
            }
        }
        
        self.counter += 1
        return data


class UnlearningProcessor(BaseFunction):
    """处理遗忘操作的 Function"""
    
    def __init__(self, epsilon=1.0, delta=1e-5, **kwargs):
        super().__init__(**kwargs)
        # 在 Function 中创建 unlearning engine
        self.unlearning_engine = UnlearningEngine(
            epsilon=epsilon,
            delta=delta,
            total_budget_epsilon=50.0,
            enable_compensation=True
        )
        
        # 缓存所有向量用于补偿
        self.all_vectors = []
        self.all_vector_ids = []
        
        # 待遗忘的向量
        self.vectors_to_forget = []
        self.ids_to_forget = []
        
        self.logger.info(f"UnlearningProcessor initialized with ε={epsilon}, δ={delta}")
    
    def execute(self, data):
        """处理每个向量"""
        vector = data['vector']
        vector_id = data['vector_id']
        should_forget = data['should_forget']
        
        # 记录所有向量
        self.all_vectors.append(vector)
        self.all_vector_ids.append(vector_id)
        
        if should_forget:
            # 标记为需要遗忘
            self.vectors_to_forget.append(vector)
            self.ids_to_forget.append(vector_id)
            self.logger.info(f"Marked {vector_id} for forgetting")
            
            # 积累到一定数量后批量处理
            if len(self.vectors_to_forget) >= 3:
                result = self._perform_unlearning()
                return {
                    'type': 'unlearning_result',
                    'result': result,
                    'forgotten_ids': self.ids_to_forget.copy(),
                    'privacy_status': self.unlearning_engine.get_privacy_status()
                }
        
        # 正常向量直接传递
        return {
            'type': 'normal_vector',
            'vector_id': vector_id,
            'vector': vector,
            'metadata': data['metadata']
        }
    
    def _perform_unlearning(self):
        """执行批量遗忘"""
        if not self.vectors_to_forget:
            return None
        
        vectors_array = np.array(self.vectors_to_forget)
        all_vectors_array = np.array(self.all_vectors)
        
        self.logger.info(f"Performing unlearning on {len(self.ids_to_forget)} vectors...")
        
        result = self.unlearning_engine.unlearn_vectors(
            vectors_to_forget=vectors_array,
            vector_ids_to_forget=self.ids_to_forget,
            all_vectors=all_vectors_array,
            all_vector_ids=self.all_vector_ids,
            perturbation_strategy="adaptive"
        )
        
        if result.success:
            self.logger.info(f"✓ Unlearning succeeded: {result.num_vectors_unlearned} vectors, "
                           f"Privacy cost: ε={result.privacy_cost[0]:.4f}")
            
            # 清空待遗忘列表
            self.vectors_to_forget = []
            self.ids_to_forget = []
        else:
            self.logger.error(f"✗ Unlearning failed: {result.metadata.get('error')}")
        
        return result


class ResultCollector(SinkFunction):
    """收集和展示结果"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.unlearning_count = 0
        self.normal_count = 0
    
    def execute(self, data):
        if data['type'] == 'unlearning_result':
            self.unlearning_count += 1
            result = data['result']
            privacy_status = data['privacy_status']
            
            print(f"\n{'='*60}")
            print(f"🔒 Unlearning Operation #{self.unlearning_count}")
            print(f"{'='*60}")
            print(f"Forgotten IDs: {', '.join(data['forgotten_ids'])}")
            print(f"Success: {result.success}")
            print(f"Vectors unlearned: {result.num_vectors_unlearned}")
            print(f"Neighbors compensated: {result.num_neighbors_compensated}")
            print(f"Privacy cost: ε={result.privacy_cost[0]:.4f}, δ={result.privacy_cost[1]:.6f}")
            
            remaining = privacy_status['remaining_budget']
            print(f"\nRemaining budget:")
            print(f"  ε: {remaining['epsilon_remaining']:.4f}")
            print(f"  Budget utilization: {privacy_status['accountant_summary']['budget_utilization']:.1%}")
            
        elif data['type'] == 'normal_vector':
            self.normal_count += 1
            if self.normal_count % 5 == 0:
                print(f"  Processed {self.normal_count} normal vectors...")


class UnlearningWithStateFunction(BaseFunction):
    """带状态管理的遗忘 Function"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.unlearning_engine = UnlearningEngine(epsilon=0.5, delta=1e-5)
        self.processed_count = 0
        self.forgotten_count = 0
    
    def execute(self, data):
        """根据策略决定是否遗忘"""
        self.processed_count += 1
        
        # 示例策略：基于元数据决定是否遗忘
        if data['metadata']['category'] == 'sensitive':
            vector = data['vector']
            vector_id = data['vector_id']
            
            result = self.unlearning_engine.unlearn_vectors(
                vectors_to_forget=np.array([vector]),
                vector_ids_to_forget=[vector_id],
                perturbation_strategy="selective"
            )
            
            if result.success:
                self.forgotten_count += 1
                perturbed = result.metadata['perturbed_vectors'][0]
                
                return {
                    'vector_id': vector_id,
                    'vector': perturbed,  # 返回扰动后的向量
                    'was_forgotten': True,
                    'privacy_cost': result.privacy_cost,
                    'metadata': data['metadata']
                }
        
        # 正常向量不变
        return {
            'vector_id': data['vector_id'],
            'vector': data['vector'],
            'was_forgotten': False,
            'metadata': data['metadata']
        }
    
    def get_state(self):
        """获取 Function 状态（可用于持久化）"""
        return {
            'processed_count': self.processed_count,
            'forgotten_count': self.forgotten_count,
            'privacy_status': self.unlearning_engine.get_privacy_status()
        }


class StateSink(SinkFunction):
    """展示状态的 Sink"""
    
    def execute(self, data):
        if data['was_forgotten']:
            print(f"🔒 {data['vector_id']}: FORGOTTEN (ε={data['privacy_cost'][0]:.4f})")
        else:
            print(f"✓ {data['vector_id']}: Normal")


def example_basic_pipeline():
    """示例1：基础 Pipeline"""
    print("\n" + "="*70)
    print("Example 1: Basic Unlearning Pipeline")
    print("="*70)
    
    env = LocalEnvironment("unlearning_basic")
    
    # 构建 Pipeline
    env.from_source(VectorGenerator) \
       .map(UnlearningProcessor, epsilon=1.0) \
       .sink(ResultCollector)
    
    # 运行
    env.submit(autostop=True)
    
    print("\n✓ Basic pipeline completed\n")


def example_stateful_pipeline():
    """示例2：带状态的 Pipeline"""
    print("\n" + "="*70)
    print("Example 2: Stateful Unlearning Pipeline")
    print("="*70)
    
    env = LocalEnvironment("unlearning_stateful")
    
    # 构建 Pipeline
    env.from_source(VectorGenerator) \
       .map(UnlearningWithStateFunction) \
       .sink(StateSink)
    
    # 运行
    env.submit(autostop=True)
    
    print("\n✓ Stateful pipeline completed\n")


def example_conditional_unlearning():
    """示例3：条件遗忘"""
    print("\n" + "="*70)
    print("Example 3: Conditional Unlearning")
    print("="*70)
    
    class ConditionalUnlearning(BaseFunction):
        """根据条件决定遗忘策略"""
        
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.engine_high_privacy = UnlearningEngine(epsilon=0.1, delta=1e-6)
            self.engine_low_privacy = UnlearningEngine(epsilon=2.0, delta=1e-5)
        
        def execute(self, data):
            vector = data['vector']
            vector_id = data['vector_id']
            category = data['metadata']['category']
            
            if category == 'sensitive':
                # 高隐私保护
                engine = self.engine_high_privacy
                strategy = "selective"
                print(f"  {vector_id}: Using HIGH privacy (ε=0.1)")
            else:
                # 低隐私保护（更高效用）
                engine = self.engine_low_privacy
                strategy = "uniform"
                print(f"  {vector_id}: Using LOW privacy (ε=2.0)")
            
            result = engine.unlearn_vectors(
                vectors_to_forget=np.array([vector]),
                vector_ids_to_forget=[vector_id],
                perturbation_strategy=strategy
            )
            
            return {
                'vector_id': vector_id,
                'privacy_level': 'high' if category == 'sensitive' else 'low',
                'privacy_cost': result.privacy_cost,
                'success': result.success
            }
    
    class ConditionalSink(SinkFunction):
        def execute(self, data):
            level = data['privacy_level']
            cost = data['privacy_cost'][0]
            emoji = "🔐" if level == 'high' else "🔓"
            print(f"{emoji} {data['vector_id']}: {level.upper()} privacy, ε={cost:.4f}")
    
    env = LocalEnvironment("unlearning_conditional")
    
    env.from_source(VectorGenerator) \
       .map(ConditionalUnlearning) \
       .sink(ConditionalSink)
    
    env.submit(autostop=True)
    
    print("\n✓ Conditional pipeline completed\n")


def main():
    """运行所有示例"""
    print("\n" + "="*70)
    print("SAGE Unlearning Library - Function Integration Examples")
    print("="*70)
    print("\n这些示例展示了如何在 SAGE Function 中使用 unlearning 库。")
    print("适合：Pipeline 集成、流式处理、与其他服务组合\n")
    
    # 禁用调试日志以保持输出清晰
    CustomLogger.disable_global_console_debug()
    
    # 运行示例
    example_basic_pipeline()
    example_stateful_pipeline()
    example_conditional_unlearning()
    
    print("="*70)
    print("✅ All examples completed successfully!")
    print("="*70)
    print("\n💡 Next steps:")
    print("  1. Try different perturbation strategies")
    print("  2. Implement custom forgetting policies")
    print("  3. See usage_3_memory_service.py for service integration\n")


if __name__ == "__main__":
    main()
