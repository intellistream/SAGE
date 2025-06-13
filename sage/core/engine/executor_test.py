from sage.core.dag.dag_manager import DAGManager
from sage.core.dag.dag import DAG
from sage.core.dag.dag_node import OneShotDAGNode,ContinuousDAGNode
from executor_manager import ExecutorManager
import time
import logging
import ray
from ray import state
# 用于测试的operator
"""用于测试的operator,其中spout负责生成数据源，末节点generator负责将收到的数据处理后写进该dag对应的一个文件里面"""

@ray.remote
class Spout :
    def __init__(self,config={}):
        self.logger=logging.getLogger(self.__class__.__name__)
        self.config=config
    def execute(self,input="streaming query test"):
        dagid=self.config['id']
        self.logger.debug(f"spout_{dagid} execute start")
        time.sleep(0.1)
        return input
@ray.remote
class Retriever:
    def __init__(self,config={}):
        self.logger=logging.getLogger(self.__class__.__name__)
        self.config=config
    def execute(self,input):
        dagid=self.config["id"]
        self.logger.debug(f"retriever_{dagid} execute start")
        time.sleep(0.1)
        return input+"retriever done"

@ray.remote
class PromptOperator:
    def __init__(self,config={}):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config=config
    def execute(self, input):
        dagid=self.config["id"]
        self.logger.debug(f"prompt_{dagid} execute start")
        time.sleep(0.1)
        return input+"prompt done"

@ray.remote
class Generator:
    def __init__(self,config={}):
        self.config=config
        self.logger = logging.getLogger(self.__class__.__name__)
    def execute(self, input):
        dagid=self.config["id"]
        self.logger.debug(f"generator_{dagid} execute start")
        file_name=self.config["file_name"]
        with open(f"test_output_{dagid}.txt", "a", encoding="utf-8") as f:
            f.write(input +"generator done"+  "\n")  # 写入内容并换行

        return input+"generator done"

def create_test_streaming_dag(dag_manager: DAGManager) :
    #用于测试的dag
    """创建一个用于测试的流式dag，默认形态为spout->retriever->prompt->generator"""
    dag=DAG(dag_manager.next_id,strategy="streaming")
    dag_manager.next_id+=1

    spout_node=ContinuousDAGNode(
        name='Spout',
        operator=Spout.remote(config={"id": dag.id}),
        config={},
        is_spout=True
    )
    retriever_node =ContinuousDAGNode(
        name="Retriever",
        operator=Retriever.remote(config={"id": dag.id}),
        config={}
    )
    prompt_node = ContinuousDAGNode(
        name="PromptGenerator",
        operator=PromptOperator.remote(config={"id": dag.id})
    )
    generator_node =ContinuousDAGNode(
        name="Generator",
        operator=Generator.remote(config={"id": dag.id,"file_name": f"test_output_{dag.id}"})
    )
    dag.add_node(spout_node)
    dag.add_node(retriever_node)
    dag.add_node(prompt_node)
    dag.add_node(generator_node)
    dag.add_edge(spout_node, retriever_node)
    dag.add_edge(retriever_node, prompt_node)
    dag.add_edge(prompt_node, generator_node)
    dag_manager.dags[dag.id] = dag
    return dag.id
def create_test_oneshot_dag(dag_manager: DAGManager) :
    """创建一个用于测试的非流式dag，默认形态为spout->retriever->prompt->generator"""
    dag=DAG(dag_manager.next_id,strategy="one_shot")
    dag_manager.next_id+=1

    spout_node=OneShotDAGNode(
        name='Spout',
        operator=Spout.remote(config={"id": dag.id}),
        config={},
        is_spout=True
    )
    retriever_node =OneShotDAGNode(
        name="Retriever",
        operator=Retriever.remote(config={"id": dag.id}),
        config={}
    )
    prompt_node = OneShotDAGNode(
        name="PromptGenerator",
        operator=PromptOperator.remote(config={"id": dag.id})
    )
    generator_node = OneShotDAGNode(
        name="Generator",
        operator=Generator.remote(config={"id": dag.id,"file_name": f"test_output_{dag.id}"})
    )
    dag.add_node(spout_node)
    dag.add_node(retriever_node)
    dag.add_node(prompt_node)
    dag.add_node(generator_node)
    dag.add_edge(spout_node, retriever_node)
    dag.add_edge(retriever_node, prompt_node)
    dag.add_edge(prompt_node, generator_node)
    dag_manager.dags[dag.id] = dag
    return dag.id

def streaming_dag_test():
#测试多线程流式rag
    ray.init(  dashboard_port=8265 )
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",)
    dag_manager = DAGManager()
    dag_ids=[]
    for i in range(1) :   #测试的dag个数为10
        dag_id=create_test_streaming_dag(dag_manager)
        dag_manager.run_dag(dag_id)
        dag_ids.append(dag_id)
    executor_manager = ExecutorManager(dag_manager,max_slots=5)
    executor_manager.run_dag()
    #dag 运行10s
    time.sleep(1000)


    actors = state.actors()
    for actor_id, actor_info in actors.items():
        print(f"actor_id {actor_id}: {actor_info}")

    #依次停止dag
    for dag_id in dag_ids :
        time.sleep(1)
        executor_manager.stop_dag(dag_id)
    time.sleep(1)
    print(f"num of tasks is {len(executor_manager.dag_to_tasks)}")
    print(f"num of dags is {len(executor_manager.dag_to_tasks)}")
    print(f"num if running dags is {len(executor_manager.dag_manager.running_dags)}")
    print(f"num if created dags is {len(executor_manager.dag_manager.dags)}")

def oneshot_dag_test():
    #测试多线程非流式rag
    """测试多线程非流时rag,模拟多轮对话模式"""
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", )
    dag_manager = DAGManager()
    dag_ids = []
    for i in range(10):  # 测试的dag个数为10
        dag_id = create_test_oneshot_dag(dag_manager)
        dag_manager.run_dag(dag_id)
        dag_ids.append(dag_id)
    executor_manager = ExecutorManager(dag_manager, max_slots=5)
    executor_manager.run_dag()
    # dag 运行10s
    time.sleep(10)
    # 查询 Actor 分配情况
    actors = state.actors()
    for actor_id, actor_info in actors.items():
        print(f"Actor ID: {actor_id}")
        print(f"类名: {actor_info['class_name']}")
        print(f"节点 IP: {actor_info['address']['ip']}")
        print(f"资源请求: {actor_info['required_resources']}")
    for i in dag_ids :
        dag_manager.run_dag(i)
        executor_manager.run_dag()
    time.sleep(5)

    print(f"num of tasks is {len(executor_manager.task_to_slot)}")
    print(f"num of dags is {len(executor_manager.dag_to_tasks)}")
    print(f"num if running dags is {len(executor_manager.dag_manager.running_dags)}")
    print(f"num if created dags is {len(executor_manager.dag_manager.dags)}")



if __name__ == '__main__':
    streaming_dag_test()





