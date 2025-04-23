import logging
from typing import Dict, List, Set

from sympy.strategies.core import switch

from sage.core.dag.dag import DAG  # 假设已存在DAG类
from sage.core.dag.dag_node import BaseDAGNode, ContinuousDAGNode, OneShotDAGNode


class DAGManager:
    """
    DAG管理系统，实现全生命周期管理
    - 通过逻辑DAG创建实例化DAG
    - 提交DAG执行
    - 提供运行中DAG查询
    - 安全删除DAG
    """

    def __init__(self):
        self.dags: Dict[int, DAG] = {}  # 所有DAG存储 {dag_id: dag_instance} 包括代运行、运行中、运行结束的dag
        self.running_dags: Set[int] = set()  # 待运行的dag的集合
        self.next_id = 0  # 自增ID生成器
        self.logger = logging.getLogger(self.__class__.__name__)

    def create_dag(self, logical_dag: DAG, operator_mapping: Dict) -> int:
        """
        通过逻辑DAG创建实例化DAG
        :param logical_dag: 不含operator的逻辑DAG
        :param operator_mapping: 算子映射 {node_name: {"config":config,"operator_class": class,"init_kwargs": kwargs}}
        :return: 新DAG的ID
        """
        # 生成唯一ID
        dag_id = self.next_id
        self.next_id += 1

        new_dag = DAG(id=dag_id,strategy=logical_dag.strategy)
        node_mapping = {}  # 原节点到新节点的映射

        # 实例化节点
        for orig_node in logical_dag.nodes:
            # 从映射表获取算子配置
            node_info = operator_mapping.get(orig_node.name, {})

            # 创建具体类型节点
            if logical_dag.strategy == "streaming" :
                new_node = ContinuousDAGNode(
                    name=orig_node.name,
                    operator=node_info["operator"](node_info.get("kwargs", {})),
                    config=node_info.get("config", {}),
                    is_spout=orig_node.is_spout
                )
            else:  # 默认为OneShot
                new_node = OneShotDAGNode(
                    name=orig_node.name,
                    operator=node_info["operator"](node_info.get("kwargs", {})),
                    config=node_info.get("config", {}),
                    is_spout=orig_node.is_spout
                )

            new_dag.add_node(new_node)
            node_mapping[orig_node] = new_node
        # 重建边关系
        for parent, children in logical_dag.edges.items():
            for child in children:
                new_dag.add_edge(node_mapping[parent], node_mapping[child])

        self.dags[dag_id] = new_dag
        self.logger.info(f"Created DAG {dag_id} with {len(new_dag.nodes)} nodes")
        return dag_id

    def add_dag(self,dag:DAG):
        dag_id = self.next_id
        self.next_id += 1
        self.dags[dag_id] = dag
        return dag_id

    def submit_dag(self, dag_id: int) -> None:
        """
        提交DAG到运行队列
        :param dag_id: 要执行的DAG ID
        """
        # 有效性检查
        if dag_id not in self.dags:
            raise ValueError(f"DAG {dag_id} does not exist")
        if dag_id in self.running_dags:
            self.logger.warning(f"DAG {dag_id} is already running")
            return

        # 获取DAG实例并启动
        dag = self.dags[dag_id]

        # 加入运行集合
        self.running_dags.add(dag_id)
        self.logger.info(f"DAG {dag_id} submitted for execution")

    def get_running_dags(self) -> List[int]:
        """获取所有运行中DAG ID列表"""
        return list(self.running_dags)

    def clear_running_dags(self) -> None:
         """清除running_dags列表"""
         self.running_dags.clear()

    def delete_dag(self, dag_id: int) -> None:
        """
        删除非运行中的DAG
        :param dag_id: 要删除的DAG ID
        """
        try :
            if dag_id in self.running_dags:
                raise PermissionError(f"Cannot delete running DAG {dag_id}")
            if dag_id not in self.dags:
                raise ValueError(f"DAG {dag_id} does not exist")

            del self.dags[dag_id]
            self.logger.info(f"DAG {dag_id} deleted")
        except Exception as e:
            self.logger.error(f"Failed to delete DAG {dag_id}: {e}")

    def remove_from_running(self, dag_id: int) -> None:
        """
        将DAG移出运行队列
        :param dag_id: 要停止的DAG ID
        """
        if dag_id not in self.running_dags:
            self.logger.warning(f"DAG {dag_id} is not running")
            return

        self.running_dags.remove(dag_id)
        self.logger.info(f"DAG {dag_id} removed from running")

    def get_dag(self, dag_id: int) -> DAG:
        #通过dag_id获取dag
        try :
            if not dag_id in self.dags:
                raise ValueError(f"DAG {dag_id} does not exist")
            return self.dags[dag_id]
        except Exception as e:
            self.logger.error(f"Failed to get DAG {dag_id}: {e}")
            return None

