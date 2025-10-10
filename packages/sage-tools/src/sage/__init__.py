# This is a namespace package
# 下面这段话可以让 pylance 检查到 tools，删除该文件将会导致 pylance 无法提示补全

# 使用 pkg_resources 方式声明命名空间包（更可靠）
try:
    __import__('pkg_resources').declare_namespace(__name__)
except ImportError:
    # 如果 pkg_resources 不可用，回退到 pkgutil 方式
    __path__ = __import__("pkgutil").extend_path(__path__, __name__)
