我提出以下要求：
0. 本项目所有业务代码必须使用 C++ 编写，严禁使用 Python 编写业务代码，Python只允许用于构造用户接口。

1. 本项目主要分为 Message / DataStream / Function / Operator / Engine / Index 模块。

## Message 

要求对 python 程序友好，其中要允许包含 vector，利用pybind11的常用做法能与numpy相互转换，用于 RAG。
要足够简洁，严禁采用任何兼容性做法。

## DataStream 
要求为 fluent api，采用类似于flink和polars的接口，实现定义Function 构成的 DAG。

## Function 
包括 Map，Filter，Join， Source, Sink 等，此外 Index 也作为一种 Function，根据用户用python callable传入的内容执行。


## Operator 
实际负责执行 Function，严禁对用户暴露Operator抽象。

## Engine 
负责把 Operator 串在一起执行，目前只需要单线程，未来可能扩展到多线程。严禁对用户暴露接口。

## Index 
- 是 ANNS 向量数据库的 Index，目前只要求支持暴力kNN，未来需要支持HNSW / IVF / faiss等。
- 要求必须使用泛型，必须支持自定义的距离函数。
- 支持 Insert / delete / query 向量。

要求你修改本项目的cpp / cpp pybind / python / python test 等代码，要求：

1. binding时每个binding cpp文件必须只能bind不超过一个class。
