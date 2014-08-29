#   Version 4.0
import re,sys,os,math
import splunk.Intersplunk as si


def getRanges(options):
    ranges = {}
    for name,startend in options.items():
        if name in ['field','default']:
            continue
        try:
            start,end = re.match("(-?\d+)-(-?\d+)", startend).groups()
            ranges[name] = (float(start),float(end))
        except:
            si.generateErrorResults("Invalid range: '%s'.  '<start_num>-<end_num>' expected." % startend)
            exit(0)
    return ranges

if __name__ == '__main__':
    try:

        keywords,options = si.getKeywordsAndOptions()

        # field=foo green[0::20] yellow[21::80] red[81::100]
        # field=foo green=0-20 yellow=21-80 red=81-100 default=black
        field = options.get('field', None)
        if field == None:
            si.generateErrorResults("'field' argument required, such as field=y")
            exit(0)

        ranges = getRanges(options)

        (isgetinfo, sys.argv) = si.isGetInfo(sys.argv)
        if isgetinfo:    # outputInfo automatically calls sys.exit()
            si.outputInfo(True, False, True, False, None, True, False, [field])

        defaultval = options.get('default', 'None')
        results,dummyresults,settings = si.getOrganizedResults()
        # for each results
        for result in results:
            # get field value
            myvalue = result.get(field, None)
            myranges = []
            if myvalue != None:
                try:
                    myvalue = float(myvalue)
                    for rangename,rangeval in ranges.items():
                        if rangeval[0] <= myvalue <= rangeval[1]:
                            # allows for multiple ranges
                            myranges.append(rangename)
                except:
                    pass
            if len(myranges) == 0:
                myranges = [defaultval]
            result['range'] = ' '.join(myranges)
        si.outputResults(results)
    except Exception, e:
        import traceback
        stack =  traceback.format_exc()
        si.generateErrorResults("Error '%s'. %s" % (e, stack))
