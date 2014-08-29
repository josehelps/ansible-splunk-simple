import splunk.Intersplunk as si
import urllib, urllib2, json, sys, time
import xml.sax.saxutils as sax

GOOGLE_REST_URL = "http://ajax.googleapis.com/ajax/services/search/web?v=1.0&%s"


def stripCommonHTML(text):
    tags = ['<b>', '</b>', '<i>', '</i>', '<a>', '</a>', '<a ', '<br>', '<br />', '&quot;']
    for tag in tags:
        text = text.replace(tag, "")
    return text

if __name__ == '__main__':
    try:
        keywords,options = si.getKeywordsAndOptions()
        maxresults = int(options.get('maxresults', '10'))
        if len(keywords) == 0:
            si.generateErrorResults('Requires search terms.')
            exit(0)
        search = ' '.join(keywords)
        # results,dummyresults,settings = si.getOrganizedResults()
        results = []

        now = str(int(time.mktime(time.gmtime())))
        start = 0
        # google rest api returns very few results, get many pages of a small number of results
        for loop in range(0, 20):
            try:
                # Define the query to pass to Google Search API
                query = urllib.urlencode({'q' : search, 'start' : start})
                # Fetch the results and convert to JSON
                search_results = urllib2.urlopen(GOOGLE_REST_URL % query)
                data = json.loads(search_results.read())
                hits = data['responseData']['results']
                for h in hits:
                    raw = stripCommonHTML(sax.unescape(h['content']))
                    title = stripCommonHTML(h['titleNoFormatting'])
                    url = h['unescapedUrl']
                    results.append({'title' : title , 'url' : url , '_time' : now, 'description' : raw, '_raw' : title + "... " + raw})
                start += len(hits)
                if len(results) > maxresults:
                    break
            except:
                break
        si.outputResults(results[:maxresults])
    except Exception, e:
        import traceback
        stack =  traceback.format_exc()
        si.generateErrorResults("Error '%s'. %s" % (e, stack))


