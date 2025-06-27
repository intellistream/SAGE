import unittest
from sage.core.compiler.logical_graph_constructor import LogicGraphConstructor
from sage.core.dag.local.dag import DAG
from sage.core.compiler.query_compiler import QueryCompiler
from sage.core.compiler.query_parser import QueryParser
from sage.core.dag.local.dag_node import BaseDAGNode


class MyTestCase(unittest.TestCase):
    def test_graph(self):
        # 创建 LogicGraphConstructor 实例
        graph_constructor = LogicGraphConstructor()

        # 创建一个 DAG 和 Spout 节点
        dag = DAG(id="test_dag",strategy="streaming")
        spout_node = BaseDAGNode(name="Spout", operator=None, is_spout=True)
        dag.add_node(spout_node)

        # 调用 construct_logical_qa_graph 方法
        graph_constructor.construct_logical_qa_graph(dag, spout_node)

        # 验证 dag 是否是 DAG 的实例
        self.assertIsInstance(dag, DAG)

    def test_query_parser(self):
        def generate(prompt, temperature=0.01):
            base_url = "http://localhost:8000"
            api_key = "empty"
            model = "meta-llama/Llama-2-13b-chat-hf"

            import openai
            client = openai.OpenAI(
                base_url=f"{base_url}/v1",
                api_key=api_key
            )
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=100,
                top_p=0.1,
                frequency_penalty=0,
                presence_penalty=0
            )
            return response.choices[0].message.content.strip()

        # Test the query parser with a sample query
        query = "What is the capital of France?"

        query_parser = QueryParser(generate_func=generate)
        parsed_query = query_parser.parse_query(query)
        self.assertIsInstance(parsed_query, str)
        self.assertIn(parsed_query,["question-answering", "retrieval", "generation","classification","transformation","summarization","other"])



    def test_query_compiler(self):
        def generate(prompt, temperature=0.01):
            base_url = "http://localhost:8000"
            api_key = "empty"
            model = "meta-llama/Llama-2-13b-chat-hf"

            import openai
            client = openai.OpenAI(
                base_url=f"{base_url}/v1",
                api_key=api_key
            )
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=100,
                top_p=0.1,
                frequency_penalty=0,
                presence_penalty=0
            )
            return response.choices[0].message.content.strip()
        # Create an instance of QueryCompiler
        query_compiler = QueryCompiler(generate_func=generate)

        # Test the compilation of a sample query
        query = "What is the capital of France?"
        dag,strategy = query_compiler.compile(query)
        self.assertIsInstance(dag, DAG)
        self.assertIsInstance(strategy, str)
        self.assertIn(strategy,["streaming","one-shot"])

if __name__ == '__main__':
    unittest.main()
