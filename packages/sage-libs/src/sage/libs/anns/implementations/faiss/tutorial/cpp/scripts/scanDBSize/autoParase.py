import csv


def paraseValidStageNames(a):
    nameList = []
    with open(a, 'r') as f:
        reader = csv.reader(f)
        # reader = [each for each in csv.DictReader(f, delimiter=',')]
        result = list(reader)
        rows = len(result)
        # print('rows=',rows)
        firstRow = result[0]
        # print(firstRow)
        index = 0
        # define what may attract our interest
        idxCpu = 0
        idxName = 0
        for i in firstRow:
            # print(i)
            if (i == 'cpu'):
                idxCpu = index
            if (i == 'name'):
                idxName = index
            index = index + 1
        # read the valid stages
        vdataEntries = 0

        for k in range(1, rows):
            if (result[k][idxCpu] != 'NA'):
                R1 = ((result[k][idxName]))
                nameList.append(R1)
        return nameList


def paraseValidColums(a, nameList, colTitle):
    with open(a, 'r') as f:
        reader = csv.reader(f)
        # reader = [each for each in csv.DictReader(f, delimiter=',')]
        result = list(reader)
        rows = len(result)
        # print('rows=',rows)
        firstRow = result[0]
        # print(firstRow)
        index = 0
        # define what may attract our interest
        idxCpu = 0
        idxName = 0
        idxTitle = 0
        for i in firstRow:
            # print(i)
            if (i == 'cpu'):
                idxCpu = index
            if (i == 'name'):
                idxName = index
            if (i == colTitle):
                idxTitle = index
            index = index + 1
        # read the valid stages
        vdataEntries = 0
        ru = []
        for k in range(1, rows):
            if (result[k][idxCpu] != 'NA'):
                R1 = ((result[k][idxName]))
                for j in range(len(nameList)):
                    if (R1 == nameList[j]):
                        s = int(result[k][idxTitle])
                        ru.append(s)
                        break
        return ru


def maxInList(a):
    # a in [[1,2] [3,4]]
    inLen = len(a[0])
    ru = []
    index = []
    ti = 0
    for i in range(len(a[0])):
        ts = 0
        ti = 0
        for k in range(len(a)):
            if (a[k][i] > ts):
                ts = a[k][i]
                ti = k
        ru.append(ts)
        index.append(ti)
    return ru, index
