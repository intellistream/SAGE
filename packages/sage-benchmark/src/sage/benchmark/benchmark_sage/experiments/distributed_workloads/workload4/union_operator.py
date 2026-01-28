"""
Union CoMap Operator for Workload 4
====================================

简单的 Union 算子，用于汇聚多个流的数据。
"""

from sage.common.core.functions.comap_function import BaseCoMapFunction


class UnionCoMap(BaseCoMapFunction):
    """
    简单的 Union 算子，将所有输入流数据直接转发。
    
    用于汇聚 VDB1, VDB2, Graph Memory 三个检索结果流。
    """
    
    def map0(self, data):
        """处理第一个输入流"""
        return data
    
    def map1(self, data):
        """处理第二个输入流"""
        return data
    
    def map2(self, data):
        """处理第三个输入流"""
        return data
