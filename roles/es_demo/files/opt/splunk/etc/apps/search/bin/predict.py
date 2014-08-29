import csv
import sys
import splunk.Intersplunk
import string
from math import sqrt
from time import time
from time import localtime
from time import mktime
import re

from splunk.stats_util.statespace import *
from splunk.stats_util.dist import Erf


(isgetinfo, sys.argv) = splunk.Intersplunk.isGetInfo(sys.argv)

options = {'field':None, 'algorithm':None, 'holdback':'0', 'correlate':None, 'upper':None, 'lower':None,
           'period':None, 'newname':None, 'future_timespan':'5', 'ci':'95', 'vals':[], 'last':None, 'start':0, 'nonnegative':'f'}

erf = Erf()
root2 = sqrt(2)
algorithms = ['LL', 'LLP', 'LLT', 'LLB', 'LLP2']

#default values
conf = [erf.inverf(.95)*root2]*2
upper_conf = 95.
lower_conf = 95.

def parseOps(argv):
    argc = len(argv)
    if argc == 0: raise ValueError
    i = 0
    while i < argc:
        arg = string.lower(argv[i])
        
        if arg == "as":
            if i+1 == argc or argv[i+1].find('=') != -1:
                raise ValueError("missing new name after AS")
            options['newname'] = argv[i+1]
            i += 2
            continue
        
        pos = arg.find("=")
        if pos != -1:
            attr = arg[:pos]
            if attr in options:
                options[attr] = argv[i][pos+1:]
            elif attr[:5]=="upper":
                try:
                    upper_conf = float(attr[5:])
                    if upper_conf < 0 or upper_conf >= 100: raise ValueError
                    conf[0] = erf.inverf(upper_conf/100.)*root2
                except ValueError:
                    raise ValueError("bad upper confidence interval")
                options['upper'] = argv[i][pos+1:]
            elif attr[:5]=="lower":
                try:
                    lower_conf = float(attr[5:])
                    if lower_conf < 0 or lower_conf >= 100: raise ValueError
                    conf[1] = erf.inverf(lower_conf/100.)*root2
                except ValueError:
                    raise ValueError("bad lower confidence interval")
                options['lower'] = argv[i][pos+1:]
            else:
                raise ValueError("unknown option %s" %arg)
            i += 1
            continue

        # argv is not an option, so must be the field.
        # If the field was already set, we flag error.
        if options['field'] != None:
            raise ValueError("too many variables")
        
        options['field'] = argv[i]
        i += 1
        
    if options['newname'] == None:
        options['newname'] = 'prediction(' + options['field'] + ')'
            
    if options['upper'] == None:
        options['upper'] = 'upper' + options['ci'] + '(' + options['newname'] + ')'
                    
    if options['lower'] == None:
        options['lower'] = 'lower' + options['ci'] + '(' + options['newname'] + ')'



if len(sys.argv) < 2:
    splunk.Intersplunk.parseError("No arguments provided")

forecastInfoList = [] # list of dictionaries 

try:
    parseOps(sys.argv[1:])
except ValueError as err:
    splunk.Intersplunk.parseError("Invalid argument: '%s'" %str(err))


forecastInfoList.append(options)

try:
    future_timespan = int(options['future_timespan'])
    if future_timespan < 0: raise ValueError
except ValueError:
    splunk.Intersplunk.parseError("Invalid future_timespan: '%s'" %options['future_timespan'])

period = options['period']
if period != None:
    try:
        period = int(period)
        if period < 1: raise ValueError
    except ValueError:
        splunk.Intersplunk.parseError("Invalid period value")

if isgetinfo:
    splunk.Intersplunk.outputInfo(False, False, True, False, None, True)
    # outputInfo automatically calls sys.exit()    

holdback = options['holdback']
try:
    holdback = int(options['holdback'])
    if holdback < 0: raise ValueError
except ValueError:
    splunk.Intersplunk.parseError("Invalid holdback value: '%s'" %options['holdback'])

results = splunk.Intersplunk.readResults(None, None, False)

correlate = []

# variable 'beginning' counts the number of empty or non-numerical rows at the beginning in the original data
beginning = 0
# variable to help compute 'beginning'
databegun = False 

for res in results:
    # each res is a dict of fields to values
    ti = forecastInfoList[0]
    if ti['field'] in res:
        try:
            ti['vals'].append(float(res[ti['field']]))
            databegun = True
        except ValueError:
            if not databegun:
                beginning += 1 # increase 'beginning' only when no numbers have been encountered
    if ti['correlate'] in res:
        try:
            correlate.append(float(res[ti['correlate']]))
        except ValueError:
            splunk.Intersplunk.parseError("bad correlate field value")


data_start = int(options['start'])
if data_start < 0:
    splunk.Intersplunk.parseError("Invalid start value: %d" %data_start)
ti = forecastInfoList[0]
vals = ti['vals'][data_start:]
if options['algorithm'] != None:
    algorithm = options['algorithm'].upper()
else:
    algorithm = None


data_end = len(vals) - holdback
if data_end < LL.least_num_data():
    splunk.Intersplunk.generateErrorResults("Too few data points: %d. Need at least %d" %(data_end,LL.least_num_data()))
    sys.exit()


# My understanding of the span fields is that:
# 1. If _spandays isn't set, then _span is correct and counts the number of seconds since the epoch as defined in python.
#    In particular, minute and hour spans are converted to _span correctly.
# 2. If _spandays is set, then _span isn't always correct because of daylight time saving. So one should ignore _span in this case
#    and use _spandays instead. One needs to convert _spandays to seconds oneself by using python's struct_time, localtime() and mktime() .
# 3. There is no explicit _spanmonths, but our convention is: if _spandays >= 28, then the month must be incremented by 1 while the span in days
#    is ignored. Hence, _spandays >= 28 is exactly equivalent to span month = 1 (no matter how much _spandays is larger than 28).
if len(results) < 2:
    splunk.Intersplunk.generateErrorResults("Too few data points: %d. Need at least %d" %(len(results),LL.least_num_data()))
    sys.exit()

spandays = spanmonths = None
if '_span' in results[0].keys():
    span = int(results[0]['_span'])
    if '_spanmons' in results[0].keys():
        spanmonths = int(results[0]['_spanmons'])
    elif '_spandays' in results[0].keys():
        spandays = int(results[0]['_spandays'])
        if spandays >= 28: 
            spanmonths = 1
elif '_time' in results[0].keys() and '_time' in results[1].keys(): 
    span = int(results[1]['_time']) - int(results[0]['_time'])
else:
    splunk.Intersplunk.generateErrorResults("Unable to predict: data has no time")
    sys.exit()

if algorithm == None:
    model = LLP5(vals[:data_end],future_timespan)
else:
    if algorithm == 'LL':
        model = LL(vals[:data_end],future_timespan)
    elif algorithm == 'LLP':
        if period == None:
            period = findPeriod(vals)
            if period == -1:
                splunk.Intersplunk.generateErrorResults('Invalid algorithm: no periodicity detected in time series')
                sys.exit()
        if data_end < LL.least_num_data()*period:
            splunk.Intersplunk.generateErrorResults("Too few data points: %d. Need at least %d" %(data_end,LL.least_num_data()*period))
            sys.exit()
        model = LLP(vals[:data_end],period,future_timespan)
    elif algorithm == 'LLP1':
        if period == None:
            period = findPeriod(vals)
            if period == -1:
                splunk.Intersplunk.generateErrorResults('Invalid algorithm: no periodicity detected in time series')
                sys.exit()
        if data_end < LL.least_num_data()*period:
            splunk.Intersplunk.generateErrorResults("Too few data points: %d. Need at least %d" %(data_end,LL.least_num_data()*period))
            sys.exit()
        model = LLP1(vals[:data_end],period,future_timespan)
    elif algorithm == 'LLP2':
        if period == None:
            period = findPeriod(vals)
            if period == -1:
                splunk.Intersplunk.generateErrorResults('Invalid algorithm: no periodicity detected in time series')
                sys.exit()
            elif data_end < LL.least_num_data()*period:
                splunk.Intersplunk.parseError("Too few data points: %d. Need at least %d" %(data_end,LL.least_num_data()*period))
                sys.exit()
        model = LLP2(vals[:data_end],period,future_timespan)
    elif algorithm == 'LLP3':
        model = LLP3(vals[:data_end],future_timespan)
    elif algorithm == 'LLP4':
        model = LLP4(vals[:data_end],future_timespan)
    elif algorithm == 'LLP5':
        model = LLP5(vals[:data_end],future_timespan)
    elif algorithm == 'LLT':
        model = LLT(vals[:data_end],future_timespan)
    elif algorithm == 'LLB':
        if len(correlate)==0:
            splunk.Intersplunk.parseError("No correlate values")
        if data_end < LLB.least_num_data(): 
            splunk.Intersplunk.generateErrorResults("Too few data points: %d. Need at least %d" %(data_end,LLB.least_num_data()))
            sys.exit()
        model = LLB.instance(vals,correlate)
    else:
        splunk.Intersplunk.parseError('Invalid algorithm')

nonnegative = False
if options['nonnegative'].lower() == 't':
    nonnegative = True

countpattern = re.compile('^(c|count|dc|distinct_count|estdc)($|\()')
if countpattern.match(options['field'].lower()) != None or (options['newname'] != None and countpattern.match(options['newname'].lower()) != None):
    nonnegative = True

datalen = model.datalen()

if datalen < model.least_num_data():
    splunk.Intersplunk.generateErrorResults("Too few data points: %d. Need at least %d" %(datalen,model.least_num_data()))
    sys.exit()


lag = 1
if algorithm != 'LLB':
    lag = model.first_forecast_index() + data_start # FIX THIS FOR LLB and LLT


if algorithm == 'LLB':
    start = max(data_end,1)
    model.predict(0,start)
    future_timespan = 0
    lag = start + data_start 

else:
    model.predict(future_timespan)

ext = len(ti['vals'])-holdback+future_timespan  
if algorithm=='LLB': 
    kk = min(len(results)-beginning,len(ti['vals']))
else:
    kk = min(len(results)-beginning,ext)    

# Since no numbers were present before 'beginning', we should leave those positions empty in the results.
# All predictions are pushed forward (in the results array) by the 'beginning' amount. Without this forward push the 
# predictions would be displayed at the wrong positions in the graphs: the predictions would appear
# before(!) the actual data.
# See SPL-80502.
for i in xrange(beginning):
    results[i][ti['newname']] = None


for i in xrange(min(lag,datalen)):
    I = i + beginning
    results[I][ti['newname']] = None

for i in xrange(lag,kk):
    j = i - data_start
    tmp = sqrt(abs(model.variance(j)))
    upper = model.fc[j] + conf[0]*tmp
    lower = model.fc[j] - conf[1]*tmp
    if nonnegative and lower < 0: lower = 0.0

    I = i + beginning
    results[I][ti['upper']] = str(upper)
    results[I][ti['lower']] = str(lower)
    results[I][ti['newname']] = str(model.fc[j])
    results[I]['_predicted'] = ti['newname']
    results[I]['_upper'] = ti['upper']
    results[I]['_lower'] = ti['lower']


lasttime = float(results[kk-1]['_time'])
lasttime_struct = list(localtime(lasttime)) # convert to list since localtime() returns readonly objects
hour = lasttime_struct[3]
for i in xrange(kk,ext): # if this range is non-empty, that means ext > len(results); hence we should do results.append()
    j = i - data_start 
    newval = model.fc[j]

    if spanmonths != None:
        lasttime_struct[1] += spanmonths # increment the tm_mon field in python's struct_time
    elif spandays != None:
        lasttime_struct[2] += spandays # increment the tm_mday field in python's struct_time
    else:
        lasttime_struct[5] += span

    extendtime = mktime(lasttime_struct) # convert back to seconds

    lasttime_struct = list(localtime(extendtime))

    # Dealing with daylight saving time. If the previous timestamp shows 12AM, we want the next timestamp to still be 12AM (not 1AM or 23PM) when users set span=1d or span=1mon
    # even when DST is in effect.
    if spandays != None:
        if lasttime_struct[8]==1 and (lasttime_struct[3] > hour or (hour==23 and lasttime_struct[3]==0)):
            extendtime -= 3600
            lasttime_struct = list(localtime(extendtime))
        elif lasttime_struct[8]==0 and (lasttime_struct[3] < hour or (hour==0 and lasttime_struct[3]==23)):
            extendtime += 3600            
            lasttime_struct = list(localtime(extendtime))

    tmp = sqrt(abs(model.variance(j)))
    upper = newval + conf[0]*tmp
    lower = newval - conf[1]*tmp
    if nonnegative and lower < 0: lower = 0.0

    newdict = {ti['newname']: str(newval), \
                   ti['upper']: str(upper), \
                   ti['lower']: str(lower), \
                   '_predicted': ti['newname'], \
                   '_upper': ti['upper'], \
                   '_lower': ti['lower'], \
                   '_time': str(extendtime)}

    results.append(newdict)
    

splunk.Intersplunk.outputResults(results)
