from sage.core.dag.dag_manager import DAGManager
from sage.core.dag.dag import DAG
from sage.core.dag.dag_node import OneShotDAGNode,ContinuousDAGNode
from executor_manager import ExecutorManager
import time
import logging

# 用于测试的operator
class Spout :
    def __init__(self,config={}):
        self.logger=logging.getLogger(self.__class__.__name__)
        self.config=config
    def execute(self,input="streaming query test"):
        dagid=self.config['id']
        self.logger.debug(f"spout_{dagid} execute start")
        time.sleep(0.1)
        return input

class Retriever:
    def __init__(self,config={}):
        self.logger=logging.getLogger(self.__class__.__name__)
        self.config=config
    def execute(self,input):
        dagid=self.config["id"]
        self.logger.debug(f"retriever_{dagid} execute start")
        time.sleep(0.1)
        return input+"retriever done"

class PromptOperator:
    def __init__(self,config={}):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config=config
    def execute(self, input):
        dagid=self.config["id"]
        self.logger.debug(f"prompt_{dagid} execute start")
        time.sleep(0.1)
        return input+"prompt done"
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
    dag=DAG(dag_manager.next_id,strategy="streaming")
    dag_manager.next_id+=1

    spout_node=ContinuousDAGNode(
        name='Spout',
        operator=Spout(config={"id": dag.id}),
        config={},
        is_spout=True
    )
    retriever_node =ContinuousDAGNode(
        name="Retriever",
        operator=Retriever(config={"id": dag.id}),
        config={}
    )
    prompt_node = ContinuousDAGNode(
        name="PromptGenerator",
        operator=PromptOperator(config={"id": dag.id})
    )
    generator_node =ContinuousDAGNode(
        name="Generator",
        operator=Generator(config={"id": dag.id,"file_name": f"test_output_{dag.id}"})
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

if __name__ == '__main__':

    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",)
    dag_manager = DAGManager()
    dag_ids=[]
    for i in range(10) :   #测试的dag个数为10
        dag_id=create_test_streaming_dag(dag_manager)
        dag_manager.submit_dag(dag_id)
        dag_ids.append(dag_id)
    executor_manager = ExecutorManager(dag_manager,max_slots=5)
    executor_manager.submit_dag()
    #dag 运行10s
    time.sleep(5)
    #依次停止dag
    for dag_id in dag_ids :
        time.sleep(1)
        executor_manager.stop_dag(dag_id)
    time.sleep(1)
    print(f"num of tasks is {len(executor_manager.dag_to_tasks)}")
    print(f"num of dags is {len(executor_manager.dag_to_tasks)}")
    print(f"num if running dags is {len(executor_manager.dag_manager.running_dags)}")
    print(f"num if created dags is {len(executor_manager.dag_manager.dags)}")






