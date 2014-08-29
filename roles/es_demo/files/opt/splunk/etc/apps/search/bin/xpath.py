#   Version 4.0
import splunk.Intersplunk as si
import StringIO
from lxml import etree
import lxml

def tostr(node):
    if isinstance(node, lxml.etree._Element):
        if len(node.getchildren()) == 0:
            return node.text
        return etree.tostring(node)
    return str(node)

if __name__ == '__main__':
    try:
        keywords,options = si.getKeywordsAndOptions()
        defaultval = options.get('default', None)
        field = options.get('field', '_raw')
        outfield = options.get('outfield', 'xpath')
        if len(keywords) != 1:
            si.generateErrorResults('Requires exactly one path argument.')
            exit(0)
        path = keywords[0]
        results,dummyresults,settings = si.getOrganizedResults()
        # for each results
        for result in results:
            # get field value
            myxml = result.get(field, None)
            added = False
            if myxml != None:
                # make event value valid xml
                myxml = "<data>%s</data>" % myxml
                try:
                    et = etree.parse(StringIO.StringIO(myxml))
                    nodes = et.xpath(path)
                    values = [tostr(node) for node in nodes]
                    result[outfield] = values
                except Exception, e:
                    pass # consider throwing exception and explain path problem
                
            if not added and defaultval != None:
                result[outfield] = defaultval
                
        si.outputResults(results)
    except Exception, e:
        import traceback
        stack =  traceback.format_exc()
        si.generateErrorResults("Error '%s'. %s" % (e, stack))
