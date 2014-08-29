#   Version 4.0
#!/usr/bin/env python

import os, time, stat, re, sys, subprocess
import crawl
import logging as logger

BAD_CLASSIFICATIONS = set(["known_binary", "ignored_type", "failed_stat", "binary", "cannot_read", "named_pipe"])
COLLAPSING_DEPTH = 4 # collapse directory up to N levels deep

# add sourcetype info to file
def addFileTypesInfo(files, parentDir=None):
     filenames = []
     for filename in files:
          if parentDir != None:
               filename = parentDir + filename
          filenames.append(filename)
     text = "\n".join(filenames)
     p = subprocess.Popen(['classify', 'manyfiles'],stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
     output = p.communicate(text + "\n")[0]
     lines = output.split("\n")
     for line in lines:
          vals = line.split("\t")
          if "Classified" in line and len(vals) == 3:
               try:
                    filename = vals[1]
                    # filename = filename.replace("\\ ", " ")
                    sourcetype = vals[2].strip()
                    # set sourcetype
                    files[filename][3] = sourcetype
               except:
                    logger.warn('Problem with filename: "%s"' % filename)

def throwAwayFilesIfDirectoryCoversIt(files, packed_extensions):

     doomed = set()
     for file1 in files:
          for file2 in files:
               if file1 != file2 and file1.endswith(os.sep):
                    if file2.startswith(file1):
                         doomed.add(file2)
     for d in doomed:
          if not isCompressed(d, packed_extensions):
               files.remove(d)
     return files

def safeAppend(list, val):
    if val not in list:
        list.append(val)

def addToMapList(map, key, value):
    if map.has_key(key):
        l = map[key]
    else:
        l = list()
        map[key] = l
    safeAppend(l, value)
    return l

def addToMapSet(map, key, value):                                               
    if map.has_key(key):
        s = map[key]
    else:
        s = set()
        map[key] = s
    s.add(value)
    return s

# find promising directories and use instead of individual files
# sort results by recency*best_directories
def findCommonDirectories(files, collapseThreshold, packed_extensions):
     files = throwAwayFilesIfDirectoryCoversIt(files, packed_extensions)
     counts = {}
     for file in files:
          last = file.rfind(os.sep)
          if last > 0:
               directory = file[:last+1]
               addToMapSet(counts, directory, file)
     collapsedFiles = []
     for directory, files in counts.items():
          if len(files) >= collapseThreshold:
               collapsedFiles.append(directory)
               logger.info("Collapsed dir (%s) from %s" % (directory, str(files)))
          else:
               collapsedFiles.extend(files)
     return collapsedFiles

def isCompressed(filename, packed_ext):
     for ext in packed_ext:
          if filename.endswith(ext):
               return True
     return False




# recursively find promising directories and use instead of individual
# files, up to N times up.

def recursivelyFindCommonDirectories(files, collapseThreshold, packed_extensions):
     if collapseThreshold <= 0:
        return
     compressed = []
     regular = []
     for file in files:
          if isCompressed(file, packed_extensions):
               compressed.append(file)
          else:
               regular.append(file)
          
     for i in range(0, COLLAPSING_DEPTH):
          oldlen = len(regular)
          regular = findCommonDirectories(regular, collapseThreshold, packed_extensions)
          if len(regular) == oldlen:
               break
     return regular + compressed


# returns terms that occur between min and max times.
def sortByTime(files):
    filesAndTimes = files.items()
    filesAndTimes.sort( lambda x, y: y[1][0] - x[1][0] ) 
    return [ft[0] for ft in filesAndTimes]

def getSortedLogs(files):
    "sorts files by most recent to least recent. putting all files that have 'log' in their name ahead of all those that do not."
    ##sortedFiles = sortByTime(g_log_files)
    sortedFiles = list(files.keys())
    sortedFiles.sort()
    best = []
    medium = []
    worst = []
    zipped = []
    for fname in sortedFiles:
        modtime, size, bytes, sourcetype = files[fname]
        if sourcetype.startswith("preprocess"):
            zipped.append(fname)
        elif sourcetype in ['too_small', 'unknown']:
            worst.append(fname)
        elif "-U" in sourcetype or sourcetype.startswith("unknown-"):
            medium.append(fname)
        else:
            best.append(fname)
    result = best + medium + worst + zipped
    return result



def parsePairs(vals):
    try:
        pairs = []
        for val in vals:
            day,size = val.split("-")
            pairs.append((int(day),int(size)))
        return pairs
    except Exception, e:
        logger.warn('Using default DAYS_SIZEK_PAIRS (less than 30 days old and more than empty in size) because given value is invalid')
        return [(30,0)]

class FileCrawler(crawl.Crawler):

    def __init__(self, mgr, args):
         name = args.get("name", "files")
         crawl.Crawler.__init__(self, name, mgr, args)
         self.log_files = {}
         self.dir_count = 0
        # GET SETTINGS
         self.index = self.getSetting("index", "main")
         self.too_big_dir_threshold = self.getNumericSetting('big_dir_filecount', -1)
         self.collapse_threshold = self.getNumericSetting('collapse_threshold', -1)         # Collapse threshold
         self.searchpaths = [d.strip() for d in self.getSetting('root',os.sep, False).split(";")]
         splunkhome = os.getenv("SPLUNK_HOME")
         self.ignored_paths = []
         if splunkhome != None:
              self.ignored_paths.append(splunkhome)
         self.bad_dir = self.getSetting('bad_directories_list')
         self.bad_ext = self.getSetting('bad_extensions_list')
         bad_file_matches = self.getSetting('bad_file_matches_list')
         self.bad_pat = re.compile("(?i)^(" + "|".join([pattern.replace(".", "\.").replace("*", ".*") for pattern in bad_file_matches]) + ")$")
         self.day_size_pairs = parsePairs(self.getSetting('days_sizek_pairs_list'))
         self.max_badfiles_per_dir = self.getNumericSetting('max_badfiles_per_dir', -1)
         self.packed_extensions = self.getSetting('packed_extensions_list')
     
    def execute(self):
        # CRAWL
        self._doCrawl()
        logger.info("Processed %s directories." % str(self.dir_count))
        # SORT
        sortedNames = getSortedLogs(self.log_files)
        # POSSIBLY COLLAPSE POPULAR DIRECTORIES
        sortedNames = recursivelyFindCommonDirectories(sortedNames, self.collapse_threshold, self.packed_extensions)
        
        # CREATE RESULT ACTIONS
        actions = []
        #print sortedNames
        #print self.log_files
        for filename in sortedNames:
            if not filename in self.log_files:
                 modtime, size, bytes, sourcetype = os.stat(filename).st_mtime, None, None, None
            else:
                 modtime, size, bytes, sourcetype = self.log_files[filename]
            if sourcetype != None and (sourcetype == "unknown" or sourcetype == "too_small" or sourcetype.startswith("preprocess")):
                sourcetype = None
            action = crawl.AddTailAction(filename, self.index, modtime, size, bytes, sourcetype, self.name)                
            actions.append(action)
        return actions
            
    def _doCrawl(self):
        # PUT SETTINGS INTO ONE TUPLE
        args = (self.searchpaths, self.ignored_paths, self.bad_dir, self.bad_ext, self.bad_pat, self.day_size_pairs)
        # for each search path, walk
        files = {}
        for path in self.searchpaths:
             self.log_files.update(self._crawlDir(path))
        addFileTypesInfo(self.log_files)
        # KILL ANY FILES WITH BAD SOURCETYPES (binary, can't read, etc)
        doomed = []
        for filename in self.log_files:
             sourcetype = self.log_files[filename][3]
             if sourcetype in BAD_CLASSIFICATIONS:
                  doomed.append(filename)
        for d in doomed:
             del self.log_files[d]


    def _crawlDir(self, root):
         stack = [root]
         result = {}
         # while more to process
         while stack:
              # get a directory to process
              directory = stack.pop()
              self.dir_count += 1
              # get files from directory
              files = []
              try:
                   if not os.path.lexists(directory):
                        logger.warn("Skipping non-existent directory (%s)" % (directory))
                        continue
                   # omg, root is a file
                   if not os.path.isdir(directory):
                        directory, thisfile = os.path.split(directory) # fix dir to be parent
                        files = [thisfile]                             # files list is just that one file
                   else:
                        files = os.listdir(directory)
              except Exception, e:
                   logger.warn("Skipping directory (%s) when error encountered: %s" % (directory, str(e)))
                   continue
              # if too many files, skip
              if self.too_big_dir_threshold > 0 and len(files) > self.too_big_dir_threshold:
                   logger.info("Directory %s has too many files (%s) and is ignored. " % (directory, str(len(files))))
                   continue
              parent, lastDir = os.path.split(directory)
              # if known bad directory, skip
              if len(lastDir) > 0 and lastDir.lower() in self.bad_dir:
                   continue
              # for each file
              count = 0
              foundGoodFile = False
              for filename in files:
                   # if it's not a known bad filename
                   if not self._badFileName(filename):
                        fullname = os.path.join(directory, filename)
                        count += 1
                        # if directory, add recurse info
                        # print "FULLNAME:", fullname
                        if os.path.isdir(fullname):
                             if not os.path.islink(fullname):
                                  stack.append(fullname)
                        else:
                            # get stats for file
                            stats = self._getFileStat(fullname)
                            # if it's good
                            if stats != None:
                                 # add info about file
                                 result[fullname] = stats
                                 foundGoodFile = True
                            # if didn't find a single good file after looking at lots of files, skip
                            elif not foundGoodFile and self.max_badfiles_per_dir > 0 and count > self.max_badfiles_per_dir:
                                 logger.info("Skipping unpromising directory: %s" % directory)
                                 break
         return result
                  

    # given a list of filenames, remove those that contain bad
    # patterns, directories, and extensions
    def _badFileName(self, filename):
         bad = False
         # if bad pattern, remove
         if re.search(self.bad_pat, filename) != None:
              bad = True
         else:
              # if bad extension, remove
              endsplit = filename.split(os.sep)[-1].split(".")
              if len(endsplit) > 1:
                   extension = endsplit[-1]
                   if extension in self.bad_ext:
                        bad = True
              if not bad:
                   # if ignored path, bad
                   for path in self.ignored_paths:
                        if filename.startswith(path):
                             bad = True
         return bad

    def _getHumanSize(self, val):
         labels = ["B", "KB", "MB", "GB", "TB"]
         pos = 0
         for label in labels:
              if (val < 1024):
                   break
              val = val / 1024
         return "%s%s" % (val, label)

    # remove files that have bad stats -- pipe, modified date, min size 
    def _getFileStat(self, filename):
         try:
              now = time.time()
              t = os.stat(filename)
              # IGNORE IRREGULAR FILES (NAMED PIPE, SPECIAL DEVICES, LINKED FILES, SOCKETS)
              if not stat.S_ISREG(t.st_mode):
                   return None
              sizeK = max(1, t.st_size / 1024)
              modtime = t.st_mtime
              # IF BIG ENOUGH AND RECENT ENOUGH AND LOOKS LIKE TEXT OR COMPRESSED FILE
              for days, minSizeK in self.day_size_pairs:
                   timeCutoff = now - (days * 24*60*60)
                   if sizeK > minSizeK and modtime > timeCutoff:
                        sizeH = self._getHumanSize(t.st_size)
                        return [modtime, sizeH, t.st_size, "unknown"]
         except Exception, e:
              logger.warn("Skipping file (%s) when error encountered: %s" % (filename, str(e)))
         return None
   
def test(args):
     import splunk.auth
     sessionKey = splunk.auth.getSessionKey('admin', 'changeme')
     owner = "admin"
     namespace = "search"
     mgr = crawl.CrawlerManager(sessionKey, owner, namespace, args)
     mgr.addCrawler(FileCrawler(mgr, args))
     results = mgr.execute()
     for result in results:
          print result

if __name__ == '__main__':
     import sys
     argc = len(sys.argv)
     argv = sys.argv
     args = {'root': '/', 'add-all':'true', 'name':'files', 'index':'preview'}
     if argc == 2:
          args['root'] = argv[1]
     test(args)
 
