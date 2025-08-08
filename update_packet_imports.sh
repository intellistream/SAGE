#!/bin/bash

# 批量更新所有 sage-core operator 文件中的 packet 导入
FILES=(
    "/home/flecther/workspace/SAGE/packages/sage-core/src/sage/core/operator/source_operator.py"
    "/home/flecther/workspace/SAGE/packages/sage-core/src/sage/core/operator/flatmap_operator.py" 
    "/home/flecther/workspace/SAGE/packages/sage-core/src/sage/core/operator/keyby_operator.py"
    "/home/flecther/workspace/SAGE/packages/sage-core/src/sage/core/operator/sink_operator.py"
    "/home/flecther/workspace/SAGE/packages/sage-core/src/sage/core/operator/map_operator.py"
    "/home/flecther/workspace/SAGE/packages/sage-core/src/sage/core/operator/comap_operator.py"
)

for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "Updating $file"
        sed -i 's|from sage.core.communication.packet import Packet|from sage.core.communication.packet import Packet|g' "$file"
    fi
done

echo "Update complete!"
