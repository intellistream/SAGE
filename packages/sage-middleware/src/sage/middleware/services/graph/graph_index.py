import collections
import uuid
import networkx as nx
import matplotlib.pyplot as plt
#from sage_memory.search_engine.graph_index.base_graph_index import BaseGraphIndex

class KnowledgeGraphIndex():
    """
    Simple knowledge graph storage.
    基于图的知识存储器。
    """

    def __init__(self):
        # 初始化成员变量
        self.qid2name = collections.defaultdict(str)  # QID ---> entity name
        self.triples = collections.defaultdict(set)  # (head, rel) ---> set(tail, sentence)
        self.qid_relations = collections.defaultdict(set)  # QID ---> set(rel)

    def construct_graph(self, batch):
        """
        从批次数据中构建知识图谱
        输入格式: batch = [["head", "relation", "tail"], ...]
        """
        for head, relation, tail in batch:
            # 构造三元组的句子
            sentence = f"{head} --[{relation}]--> {tail}"
            # 插入三元组
            self.insert_edge(head, relation, tail, sentence)

    def insert_edge(self, head, relation, tail, sentence):
        """
        插入一条新的边 (head, relation, tail)
        """
        head_id=uuid.uuid5(uuid.NAMESPACE_DNS, head)
        tail_id=uuid.uuid5(uuid.NAMESPACE_DNS, tail)
        
        # 添加 head 和 tail 的名称映射
        if head_id not in self.qid2name:
            self.qid2name[head_id] = head
        if tail_id not in self.qid2name:
            self.qid2name[tail_id] = tail

        # 检查 triples 中是否已存在该三元组
        if (tail_id, sentence) not in self.triples[(head_id, relation)]:
            self.triples[(head_id, relation)].add((tail_id, sentence))

        # 检查 qid_relations 中是否已存在该关系
        if relation not in self.qid_relations[head_id]:
            self.qid_relations[head_id].add(relation)

    
    def delete_edge(self, head, relation, tail):
        """
        删除知识图谱中的一条边 (head, relation, tail)
        """
        # 生成唯一的 ID
        head_id = uuid.uuid5(uuid.NAMESPACE_DNS, head)
        tail_id = uuid.uuid5(uuid.NAMESPACE_DNS, tail)
        # 从 triples 中删除对应的三元组
        if (head_id, relation) in self.triples:
            self.triples[(head_id, relation)] = {
                t for t in self.triples[(head_id, relation)] if t[0] != tail_id
            }
            # 如果关系为空，则从 qid_relations 中移除
            if not self.triples[(head_id, relation)]:
                del self.triples[(head_id, relation)]
                self.qid_relations[head_id].remove(relation)
    
    def modify_edge(self, head, relation, tail, new_tail):
        """
        修改知识图谱中的一条边 (head, relation, tail) 为 (head, relation, new_tail)
        """
        # 生成唯一的 ID
        head_id = uuid.uuid5(uuid.NAMESPACE_DNS, head)
        tail_id = uuid.uuid5(uuid.NAMESPACE_DNS, tail)
        new_tail_id = uuid.uuid5(uuid.NAMESPACE_DNS, new_tail)

        # 检查是否存在该关系
        if (head_id, relation) in self.triples:
            # 获取当前关系中的所有尾节点
            current_tails = self.triples[(head_id, relation)]
            

            # 检查是否存在指定的尾节点
            tail_exists = False
            for tail_id_in_graph, sentence in current_tails:
                if tail_id_in_graph == tail_id:
                    tail_exists = True
                    # 修改尾节点为 new_tail
                    current_tails.remove((tail_id_in_graph, sentence))
                    new_sentence = f"{head} --[{relation}]--> {new_tail}"
                    current_tails.add((new_tail_id, new_sentence))
                    if new_tail_id not in self.qid2name:
                        self.qid2name[new_tail_id] = new_tail
                    break

            if not tail_exists:
                print(f"Edge ({head}, {relation}, {tail}) does not exist.")
                return
        else:
            print(f"Relation ({head}, {relation}) does not exist in the graph.")


    def clear_relation(self, head, relation):
        head_id = uuid.uuid5(uuid.NAMESPACE_DNS, head)
        if (head_id, relation) in self.triples:
            del self.triples[(head_id, relation)]
            self.qid_relations[head_id].remove(relation)

    def get_neighbors(self, entity):
        neighbors = set()
        head_id = uuid.uuid5(uuid.NAMESPACE_DNS, entity)
        for relation in self.qid_relations[head_id]:
            for tail, _ in self.triples[(head_id, relation)]:
                neighbors.add((relation, tail))
        for relation, tail in neighbors:
            print(f"Relation: {relation}, Tail: {self.qid2name[tail]}")
        return neighbors
    

    def print_graph(self):
        """
        打印知识图谱的内容
        """
        print("Knowledge Graph:")
        for (head_id, relation), tails in self.triples.items():
            for tail_id, sentence in tails:
                print(f"{self.qid2name[head_id]} --[{relation}]--> {self.qid2name[tail_id]}")


    def visualize_knowledge_graph(self):
        """
        可视化知识图谱
        """
        # 创建一个有向图
        G = nx.DiGraph()

        # 添加节点和边
        for (head_id, relation), tails in self.triples.items():  # 使用 self 访问成员变量
            head_name = self.qid2name[head_id]
            for tail_id, sentence in tails:
                tail_name = self.qid2name[tail_id]
                G.add_edge(head_name, tail_name, label=relation)

        # 绘制图形
        pos = nx.spring_layout(G)  # 使用 spring 布局
        plt.figure(figsize=(12, 8))

        # 绘制节点和边
        nx.draw(G, pos, with_labels=True, node_size=3000, node_color="lightblue", font_size=10, font_weight="bold")
        
        # 绘制边上的标签
        edge_labels = nx.get_edge_attributes(G, 'label')
        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=8)

        # 显示图形
        plt.title("Knowledge Graph Visualization", fontsize=16)
        plt.savefig("knowledge_graph.png")  # 保存图形到文件

if __name__ == "__main__":
    # 创建 KnowledgeGraphStorage 实例
    kg_storage = KnowledgeGraphIndex()

    # 定义测试数据
    batch = [
        ["Trump", "president_of", "USA"],
        ["Trump", "fans_of", "CR7"],
        ["Trump", "fans_of", "Mask"],
        ["CR7", "rival_of", "Messi"],
        ["CR7", "play_for", "Manchester United"],
        ["CR7", "born_in", "Portugal"],
        ["Manchester United", "located_in", "England"],
    ]

    # 构建知识图谱
    kg_storage.construct_graph(batch)

    # 打印知识图谱内容
    print("测试输出:")
    kg_storage.print_graph()
    print()

    print("CR7效力的球队发生了变化，需要修改知识图谱中的边:")
    kg_storage.modify_edge("CR7", "play_for", "Manchester United", "Al-Nassr FC")
    kg_storage.print_graph()
    print()

    print("Trump和Mask闹掰了，需要删除知识图谱中的边:")
    kg_storage.delete_edge("Trump", "fans_of", "Mask")
    kg_storage.print_graph()

    kg_storage.get_neighbors("CR7")
    # 可视化知识图谱
    kg_storage.visualize_knowledge_graph()