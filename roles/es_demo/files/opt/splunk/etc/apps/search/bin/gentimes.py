#   Version 4.0
import re,sys,time, splunk.Intersplunk

def midnightToday():
    now = time.localtime()
    midnightlastnight = time.mktime((now[0], now[1], now[2], 0, 0, 0, 0, 0, -1))
    return midnightlastnight

# "5/4/9999:34:33:33"
def getTime(val):
    if not val:
        return None
    match = re.findall("(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?(?::(\d{1,2}):(\d{2}):(\d{2}))?", val)
    # if timestamp.  default year to current year and time to midnight
    if len(match) > 0:
        now = time.localtime()
        vals = match[0]
        month = int(vals[0])
        day   = int(vals[1])
        if len(vals[2]) > 0:
            year = int(vals[2])
            if year < 100:
                year += 2000
        else:
            year = now[0]
        if len(vals[3]) > 0:
            hour   = int(vals[3])
            minute = int(vals[4])
            sec    = int(vals[5])
        else:
            hour = 0
            minute = sec = 0
        return time.mktime((year, month, day, hour, minute, sec, 0, 0, -1)) 
    else:
        daysago = int(val)
        midnightlastnight = midnightToday()
        midnightago = midnightlastnight + (24*60*60 * daysago)
        return midnightago
    return None

def getIncrement(val):
    if not val:
        return None
    match = re.findall("(\d+)([smhd])", val)
    # if timestamp.  default year to current year and time to midnight
    if len(match) > 0:
        val = int(match[0][0])
        units = match[0][1]
        if units == 'm':
            val *= 60
        elif units == 'h':
            val *= 60 * 60
        elif units == 'd':
            val *= 24 * 60 * 60
        return val
    return None

def generateTimestamps(results, settings):

    try:
        keywords, argvals = splunk.Intersplunk.getKeywordsAndOptions()
        startagostr        = argvals.get("start", None)
        endagostr          = argvals.get("end", None)
        incrementstr       = argvals.get("increment", None)

        starttime = getTime(startagostr)
        endtime   = getTime(endagostr)
        increment = getIncrement(incrementstr)

        if not endtime:
            endtime = midnightToday()
        if not increment:
            increment = 24 * 60 * 60 # 1 day
        if not starttime:
            return splunk.Intersplunk.generateErrorResults("generatetimestamps requires start=mm/dd/yyyy:hh:mm:ss and optional takes 'end' and 'increment' values.")

        results = []
        for start in range(int(starttime), int(endtime), int(increment)):
            result = {}
            end = start + increment - 1 # 1 sec less than next range
            result['starttime'] = str(start)
            result['endtime']   = str(end) 

            result['starthuman'] = time.asctime(time.localtime(start))
            result['endhuman'] = time.asctime(time.localtime(end))

            results.append(result)
    except Exception, e:
        import traceback
        stack =  traceback.format_exc()
        results = splunk.Intersplunk.generateErrorResults(str(e) + ". Traceback: " + str(stack))
    return results
        

results, dummyresults, settings = splunk.Intersplunk.getOrganizedResults()
results = generateTimestamps(results, settings)
splunk.Intersplunk.outputResults(results)


