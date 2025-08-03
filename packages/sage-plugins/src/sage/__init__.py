# 这是一个命名空间包标识文件
# 使得 sage.plugins 可以作为命名空间包工作
__path__ = __import__('pkgutil').extend_path(__path__, __name__)
