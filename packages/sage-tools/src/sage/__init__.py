# This is a namespace package
# 下面这段话可以让 pylance 检查到 common，删除该文件将会导致 pylance 无法提示补全

__path__ = __import__("pkgutil").extend_path(__path__, __name__)
