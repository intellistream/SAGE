#!/bin/bash
function changeName(){
  sudo rm -rf __pycache__
}
# 遍历文件夹
function travFolder(){
   flist=`ls $1`   # 第一级目录
   cd $1        
   for f in $flist  # 进入第一级目录
   do
     if test -d $f  # 判断是否还是目录
     then 
       travFolder $f # 是则继续递归
     else
       changeName $f # 否则改名
     fi
   done
   cd ../     # 返回目录
}
dir=.
travFolder $dir
