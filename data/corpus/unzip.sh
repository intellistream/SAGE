#!/bin/bash


for zipfile in *.zip; do
    if [ -f "$zipfile" ]; then
        unzip "$zipfile"
        echo "解压完成: $zipfile"
    else
        echo "当前目录下没有需要解压的文件"
    fi
done
