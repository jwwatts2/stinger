# read excel file and compute metrics
import pandas as pd

xls = pd.read_excel('testingvidanalysis.xlsx', sheet_name='5th run')

#print(xls)
detected = xls.iloc[:, 2]
#print(detected)
observed = xls.iloc[:, 5]
#print(observed)

metricsFile = open('metrics.csv', 'w')

actualPositives = 0
actualNegatives = 0

for i in range(1,155):
    if type(detected[i]) is float:
        detectedNames = ['']
    else:
        detectedNames = detected[i].split()
        detectedNames.sort()
    if type(observed[i]) is float:
        observedNames = ['']
    else:
        observedNames = observed[i].split()
        observedNames.sort()
    falsePositives = 0
    falseNegatives = 0
    truePositives = 0
    trueNegatives = 0
    lenDNames = len(detectedNames)
    lenONames = len(observedNames)
    lenMax = max(lenDNames, lenONames)
    for j in range(lenMax):
        if j >= lenDNames:
            detectedNames.append('')
        if j >= lenONames:
            observedNames.append('')
        dname = detectedNames[j]
        oname = observedNames[j]
        if oname == 'Unknown':
            actualNegatives += 1
        elif len(oname) > 0:
            actualPositives += 1
        if dname == oname:
            if dname == 'Unknown':
                trueNegatives += 1
            elif len(dname) > 0:
                truePositives += 1
        else:
            if dname == 'Unknown':
                falseNegatives += 1
            elif oname == 'Unknown':
                falseNegatives += 1
            elif len(dname) == 0:
                falseNegatives += 1
            else:
                falsePositives += 1    

    print(f'detected: {detectedNames} observed: {observedNames} tp: {truePositives} tn: {trueNegatives} fp: {falsePositives} fn: {falseNegatives}')
    metricsFile.write(f'{truePositives},{trueNegatives},{falsePositives},{falseNegatives}\n')

    #if i > 30:
    #    break
metricsFile.close()
print(f'actual positives: {actualPositives} actual negatives: {actualNegatives}')
