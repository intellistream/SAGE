# 第一步：停止老的 Ray 实例
ray stop --force

# 第二步：清理 tmp 下残留的 Ray 文件
rm -rf /tmp/ray