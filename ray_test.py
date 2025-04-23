# # test_ray.py
# import os
# import ray
#
# ray.init()
#
# print('''This cluster consists of
#     {} nodes in total
#    {} cpu
# '''.format(len(ray.nodes()), ray.cluster_resources()))
import ray

context = ray.init()
print(context.dashboard_url)