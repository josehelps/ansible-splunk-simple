#   Version 4.0
import csv
import sys

rowcount = 5
if len(sys.argv) >= 2:
    rowcount = int(sys.argv[1])

r = csv.reader(sys.stdin)

rows = [['column']]

i = 0
for l in r:
    if i > rowcount:
        break
    
    if not i:
        for c in l:
            rows.append([c])
    else:
        rows[0].append("row %d" % i)
        j = 1
        for c in l:
            rows[j].append(c)
            j = j+1

    i = i+1

if(i > 1): 
    csv.writer(sys.stdout).writerows(rows)

