#!/bin/bash
mapfile expNames <expList.txt
for element in "${expNames[@]}"
#也可以写成for element in ${array[*]}
do
cd "$element" || exit
echo "$element"
python3 drawTogether.py 2
cd ../
done
cd downstream_combine || exit
python3 drawTogether.py
cd ..
