#   Version 4.0
import splunk.Intersplunk as si
import time

MINUTE = 60
HOUR = 60 * MINUTE
DAY = 24 * HOUR
MONTH = 30 * DAY
YEAR = 12 * MONTH

# handle plurals nicely
def unitval(unit, val):
    plural = ""
    if val >= 2: plural = "s"
    return "%s %s%s ago" % (int(val), unit, plural)

if __name__ == '__main__':
    try:
        keywords,options = si.getKeywordsAndOptions()
        results,dumb1, dumb2 = si.getOrganizedResults()

        now = time.time()
        # for each result
        for result in results:
            utc = result.get('_time', None)
            if utc == None:
                reltime = "unknown"
            else:
                diff = int(now - float(utc))
                if diff < -60:
                    reltime = "future"
                elif diff < 0: # handle weird case of client clock off slightly
                    reltime = "now"
                elif diff == 0:
                    reltime = "now"
                elif diff < MINUTE:
                    reltime = unitval("second", diff)
                elif diff < HOUR:
                    reltime = unitval("minute", diff / MINUTE)
                elif diff < DAY:
                    reltime = unitval("hour", diff / HOUR)
                elif diff < MONTH:
                    reltime = unitval("day", diff / DAY)
                elif diff < YEAR:
                    reltime = unitval("month", diff / MONTH)
                else:
                    reltime = unitval("year", diff / YEAR)
            result['reltime'] = reltime
        si.outputResults(results)

    except Exception, e:
        import traceback
        stack =  traceback.format_exc()
        si.generateErrorResults("Error '%s'" % e)
