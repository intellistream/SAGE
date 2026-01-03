mapfile expNames <expList.txt
for element in ${expNames[@]}
#也可以写成for element in ${array[*]}
do
cd $element
echo $elment
python3 drawTogether.py 2
cd ../
done
