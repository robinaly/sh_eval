from math import *
import re
import os
import sys

def reportError(line, errstr, t='error'):
  if line < 0:
    if t=='warning':
      return "Warning on line %5d: %s" % (line, errstr)
    else:
      return "Error: %s" % (line, errstr)
  if t == 'warning':
    return "Warning on line %5d: %s" % (line, errstr)
  return "Error on line %5d: %s" % (line, errstr)

  
def do_open(fn, mode):
  import gzip
  if fn.endswith('.gz'): 
    return gzip.open(fn, mode)
  else:
    return open(fn, mode)

def isAnchor(anchor):
  return anchor in anchors
  
def isItem(item):
  return item in items  
  
def isTime(s):
  m = re.match('(\d+).(\d+)', s)
  if m == None: 
    return False
  if int(m.group(1)) < 0 : 
    return False
  if int(m.group(2)) < 0 or int(m.group(2)) > 60: 
    return False
  return True

def sec2String(s):
  miliseconds= s * 1000
  minutes, milliseconds = divmod(miliseconds, 60000)
  seconds = float(milliseconds) / 1000
  return "%d.%02d" % (minutes, seconds)
  
reH = re.compile("(\d\d):(\d\d):(\d\d)(?:.(\d+))?")
def h2Sec(h): 
  '''
  00:05:53 to their number of seconds
  '''
  m = reH.match(h)
  if not m:
    print >>sys.stderr, h, 'doesn\'t match'
  return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3)) + 1  

def isRank(s):
  try:
    i =  int(s)
    return i > 0
  except:
    return False
  
def isScore(s):
  try:
    i =  float(s)
    return True
  except:
    return False

def readSearchResults(in_fn):
  with do_open(in_fn, 'r') as f:
    anchors = []
    lineno = 0
    for line in f:
      lineno += 1
      line = line.strip()
      field = line.split()
      record = { 'line': line, 'lineno': lineno }
      def error(s,v=''):
        record['errorStr'] = s
        record['status'] = 'e'
        record['errorValue'] = v
        
      if len(field) != 9:
        error("Invalid number of fields", len(field))
        yield record
        continue
      
      record['qid'] = field[0]
      record['video'] = field[2]
      record['run'] = field[-1]
      if not isTime(field[3]):
        error("Invalid start time", field[3])
      else:
        record['start'] = ToSec(field[3])
      if not isTime(field[4]):
        error("Invalid end time", field[4])
      else:
        record['end'] = ToSec(field[4])
      if not isTime(field[5]):
        error("Invalid jump-in time", field[5])
      else:
        record['jumpin'] = ToSec(field[5])
      rank = 0
      try:
        record['rank'] = int(field[6])
      except:
        error("Invalid rank", field[6])
      if not isScore(field[7]):
        error("Invalid score", field[7])
      else:
        record['score'] = float(field[7])
      yield record

# Field 
# Explanation 
# videoId     The identifier of the video (without extension) of the result segment
# "Q0"        a legacy constant 
# startTime   The starting time of the anchor (mins.secs) 
# endTime     The end time of the anchor (mins.secs) 
# rank        The rank of the result segment for this query  
# confidenceScore   A floating point value describing the confidence of the retrieval system that the segment is an anchor
# runName   A identifier for the retrieval system, see also RunSubmission2013 
def readAnchoringResults(in_fn):
  # def isTime(s):
  #   try:
  #     s = float(s)
  #     return True
  #   except:
  #     return False
  #
  # def ToSec(s):
  #   return int(float(s))
  
  with do_open(in_fn, 'r') as f:
    anchors = []
    lineno = 0
    for line in f:
      lineno += 1
      line = line.strip()
      field = line.split()
      record = { 'line': line, 'lineno': lineno, 'errors': [] }
      def error(s,v=''):
        record['errors'].append((s,v))
        
      if len(field) != 7:
        error("Invalid number of fields", len(field))
        yield record
        continue
      
      record['qid'] = field[0]
      record['run'] = field[-1]
      
      if not isTime(field[2]):
        error("Invalid start time", field[2])
      else:
        record['start'] = ToSec(field[2])
        
        
      if not isTime(field[3]):
        error("Invalid end time", field[3])
      else:
        record['end'] = ToSec(field[3])
        
        
      rank = 0
      try:
        record['rank'] = int(field[4])
      except:
        error("Invalid rank", field[4])
        
      if not isScore(field[5]):
        error("Invalid score", field[5])
      else:
        record['score'] = float(field[5])
        
      yield record


def readLinkingResults(in_fn):
  with do_open(in_fn, 'r') as f:
    anchors = []
    lineno = 0
    for line in f:
      lineno += 1
      line = line.strip()
      field = line.split()
      record = { 'line': line, 'lineno': lineno }
      def error(s,v=''):
        record['errorStr'] = s
        record['status'] = 'e'
        record['errorValue'] = v
        
      if len(field) != 8:
        error("Invalid number of fields", len(field))
        yield record
        continue
      
      record['qid'] = field[0]
      record['video'] = field[2]
      record['run'] = field[-1]
      if not isTime(field[3]):
        error("Invalid start time", field[3])
      else:
        record['start'] = ToSec(field[3])
      if not isTime(field[4]):
        error("Invalid end time", field[4])
      else:
        record['end'] = ToSec(field[4])
      rank = 0
      try:
        record['rank'] = int(field[5])
      except:
        error("Invalid rank", field[5])
      if not isScore(field[6]):
        error("Invalid score", field[6])
      else:
        record['score'] = float(field[6])
      yield record


def loadVideoFiles(task):
  '''
  Read data about the collection and the queries / anchors
  '''
  task2collection = {
    'me14sh': 'cAXES',
    'me15sava': 'cAXES',
    'tv15lnk': 'cAXES',
    'me15sava_anchoring': 'cAnchoring15',
    'tv16lnk': 'bliptv2'
  }
  if task in task2collection:
    collection = task2collection[task]
    fn = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'data', collection + '.txt')
    with open(fn) as f:
      videoFilesList = [ line.split() for line in f ]
      videoFiles = dict( map(lambda x: (x[0], (x[1], h2Sec(x[1]))), videoFilesList))
    blacklist = set()
    fn = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'data', collection + '.blacklist.txt')
    if os.path.isfile(fn):
      with open(fn) as f:
        for line in f:
          blacklist.add(line.strip())
  else:
    print "WARNING - function loadVideoFiles: cannot find video list for unknown task %s" % task
    sys.exit(1)
  return videoFiles, blacklist

def loadAnchorVideos(task):
  # read anchors 
  if task == 'me15sava_anchoring':
    fn = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'data', 'me15sava_anchoring_test_inputVideoFiles.txt')
    videos = [ line.strip() for line in do_open(fn, 'r') ]
  else:
    print "unknown task", task
    sys.exit(1)

  return videos
  
def loadAnchors(task):
  # read anchors 
  import xml.etree.ElementTree as ET
  if task == 'me14sh':
    fn = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'data', 'me14sh_linking_testSet_anchors.xml')
    tree = ET.parse(fn)
    anchorsDef = [ [anchor.find('anchorId').text, anchor.find('fileName').text, anchor.find('startTime').text, anchor.find('endTime').text] for anchor in tree.findall('.//anchor') ]
  elif task == 'tv15lnk':
    fn = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'data', 'tv15hlk_test_anchors.xml')
    tree = ET.parse(fn)
    anchorsDef = [ [anchor.find('anchorId').text, anchor.find('video').text, anchor.find('startTime').text, anchor.find('endTime').text] for anchor in tree.findall('.//anchor') ]
  elif task == 'tv16lnk':
    fn = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'data', 'tv16hlk_test_anchors.xml')
    tree = ET.parse(fn)
    anchorsDef = [ [anchor.find('anchorId').text, anchor.find('video').text, anchor.find('startTime').text, anchor.find('endTime').text] for anchor in tree.findall('.//anchor') ]    
  else:
    print "unknown task"
    sys.exit(1)
    
  anchorsDef = map(lambda x: {'anchorId': x[0], 'video': x[1], 'start': ToSec(x[2]), 'end': ToSec(x[3])}, anchorsDef)  
  anchorDefinitions = dict( map(lambda x: (x['anchorId'], x), anchorsDef))
  anchors = list(sorted(anchorDefinitions.keys()))

  return anchors, anchorDefinitions

def loadQueries(task):
  # read anchors
  import xml.etree.ElementTree as ET
  if task == 'me14sh':
    fn = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'data', 'me14sh_search_testSet_queries.xml')
    tree = ET.parse(fn)
    queryDef = [ [anchor.find('queryId').text, anchor.find('queryText').text] for anchor in tree.findall('.//top') ]

  elif task == 'me15sava':
    fn = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'data', 'me15sava_search_test_queries.xml')
    tree = ET.parse(fn)
    queryDef = [ [anchor.find('itemId').text, anchor.find('queryText').text] for anchor in tree.findall('.//top') ]
  else:
    print "unknown task"
    sys.exit(1)
    
  queryDef = map(lambda x: {'queryId': x[0], 'text': x[1]}, queryDef)
  queryDef = dict( map(lambda x: (x['queryId'], x), queryDef))
  queries = list(sorted(queryDef.keys()))
  
  return queries, queryDef 


def sec2H(sec): 
  '''
  converts a number of seconds into the format 00:05:53
  '''
  h, sec = divmod(sec, 3600)
  m, sec = divmod(sec, 60)
  return '%02d:%02d:%02d' % (h,m,sec)

def overlapTime(s1, e1, s2, e2):
  if s1 <= s2 and s2 <= e1: return True
  if s2 <= s1 and s1 <= e2: return True
  if s2 <= e1 and e1 <= e2: return True
  if s1 <= e2 and e2 <= e1: return True
  return False

def overlaps(segment1,segment2):
  ''' checks if two time segments overlap '''
  video1, start1, end1 = segment1
  video2, start2, end2 = segment2
  if video1 != video2: return False
  if start1 <= start2 and start2 <= end1: return True
  if start2 <= start1 and start1 <= end2: return True
  return False

def isRank(s):
  try:
    i =  int(s)
    return i > 0
  except:
    return False
  
def isTime(s):
  m = re.match('(\d+).(\d+)', s)
  if m == None: 
    return False
  if int(m.group(1)) < 0 : 
    return False
  if int(m.group(2)) < 0 or int(m.group(2)) > 60: 
    return False
  return True


def ToSec(s):
  m = re.match('(\d+).(\d+)', s)
  if m == None: return 0
  return int(m.group(1)) * 60 + int(m.group(2))
  
def timesort(l):
  return (l['video'], l['start'], l['end'])
  
reVideo = re.compile('^v?(\d\d\d\d)(\d\d)(\d\d).*')
def video2day(v):
  m = reVideo.match(v)
  year = int(m.group(1))
  mon = int(m.group(2))
  day = int(m.group(3))
  mon = mon - 4
  return mon * 30 + day

reVideo = re.compile('^v?(\d\d\d\d)(\d\d)(\d\d).*')
def video2date(v):
  m = reVideo.match(v)
  year = int(m.group(1))
  mon = int(m.group(2))
  day = int(m.group(3))
  return '%02d.%02d.' % (day, mon)
  
def overlap(s1, s2):
  if s1['start'] <= s2['start'] and s2['start'] <= s1['end']: return True
  if s2['start'] <= s1['start'] and s1['start'] <= s2['end']: return True
  return False
  
def mean(v):
  if len(v) == 0: return 0.0
  return sum(v) / float(len(v))

class Stat:
  def __init__(self, relType="segment"):
    self.relTypeVal = relType
    
  def perQuery(self):
    return True
  
  def forAll(self):
    return True
    
  def format(self):
    return "%d"
    
  def relType(self):
    return self.relTypeVal

  def fullName(self):
    if self.relType() != "segment":
      return self.name() + '_' + self.relType()
    return self.name()    

class Measure:
  def __init__(self, relType="segment"):
    self.relTypeVal = relType
    
  def perQuery(self):
    return True
  
  def forAll(self):
    return True
  
  def relType(self):
    return self.relTypeVal
    
  def format(self):
    return "%.4f"

  def fullName(self):
    if self.relType() != "segment" and self.relType() != "maisp":
      return self.name() + '_' + self.relType()
    return self.name()

class Ap(Measure):
  def __init__(self, relType="segment"):
    Measure.__init__(self, relType=relType)
    
  def name(self):
    return "map"
  
  def calc(self, rels, nrel=None):
    rels = map(lambda x: 1 if type(x) == int and x > 0 else 0, rels)
    if nrel == None:
      nrel = sum(rels)
    ap = 0.0
    crel = 0
    for rank, r in enumerate(rels):
      if r >= 1:
        crel += 1.0
        ap += crel / (1.0+rank)
    if ap == 0: return 0.0
    return ap/nrel
  
  def agg(self):
    return mean  

class PrecisionAt(Measure):
  def __init__(self, n, relType="segment"):
    Measure.__init__(self, relType=relType)
    self.n = n
  
  def name(self):
    return "P_" + str(self.n)
  
  def calc(self, rels, nrel=None):
    rels = map(lambda x: 1 if type(x) == int and x > 0 else 0, rels)
    return sum(rels[:self.n]) / float(self.n)
    
  def agg(self):
    return mean
    
class JudgedAt(Measure):
  def __init__(self, n, relType="segment"):
    Measure.__init__(self,relType=relType)
    self.n = n
  
  def name(self):
    return "Judged_" + str(self.n)
  
  def calc(self, rels, nrel=None):
    rels = map(lambda x: 0 if x == '-' else 1, rels)
    return sum(rels[:self.n]) / float(self.n)

  def agg(self):
    return mean

class MAiSP_RelRetSecs(Measure):
  def __init__(self, relType="maisp"):
    Measure.__init__(self,relType=relType)

  def name(self):
    return "num_rel_ret_secs"

  def calc(self, maisp_calc):
    return maisp_calc.get_rel_ret_secs()

  def format(self):
    return "%d"

  def agg(self):
    return sum

class MAiSP_RelSecs(Measure):
  def __init__(self, relType="maisp"):
    Measure.__init__(self,relType=relType)

  def name(self):
    return "num_rel_secs"

  def calc(self, maisp_calc):
    return maisp_calc.get_rel_secs()

  def format(self):
    return "%d"

  def agg(self):
    return sum

class MAiSP_RetSecs(Measure):
  def __init__(self, relType="maisp"):
    Measure.__init__(self,relType=relType)

  def name(self):
    return "num_ret_secs"

  def calc(self, maisp_calc):
    return maisp_calc.get_ret_secs()

  def format(self):
    return "%d"

  def agg(self):
    return sum

class MAiSP_PrecisionAtRecall(Measure):
  def __init__(self, relType="maisp", recallPt=1):
    Measure.__init__(self,relType=relType)
    self.recallPt = max(0, min(recallPt, 100))

  def name(self):
    return "maisp_%.2f" % (self.recallPt/100.0)

  def calc(self, maisp_calc):
    isp = maisp_calc.get_isp()
    if self.recallPt < len(isp):
      return isp[self.recallPt]
    else:
      return 0.0

  def agg(self):
    return mean

class MAiSP_iAsp(Measure):
  def __init__(self, relType="maisp"):
    Measure.__init__(self,relType=relType)

  def name(self):
    return "maisp"

  def calc(self, maisp_calc):
    return maisp_calc.get_iAsp()

  def agg(self):
    return mean

class NumRel(Stat):
  def __init__(self, relType="segment"):
     Stat.__init__(self, relType=relType)
  
  def name(self):
    return "num_rel"
  
  def calc(self, rels, nrel=None):
    if nrel == None:
      nrel = sum(map(lambda x: 1 if type(x) == int and x > 0 else 0, rels))
    return nrel
  
  def agg(self):
    return sum
    
class NumRet(Stat):
  def __init__(self, relType="segment"):
     Stat.__init__(self, relType=relType)
  
  def name(self):
    return "num_ret"
  
  def calc(self, rels, nrel=None):
    return len(rels)    
    
  def agg(self):
    return sum

class NumQ(Stat):
  def __init__(self, relType="segment"):
    Stat.__init__(self, relType=relType)

  def name(self):
    return "num_q"
  
  def calc(self, rels, nrel=None):
    return 1
    
  def agg(self):
    return sum
    
  def perQuery(self):
    return False

class NumRelRet(Stat):
  def __init__(self, relType="segment"):
    Stat.__init__(self, relType=relType)
  
  def name(self):
    return "num_rel_ret"
  
  def calc(self, rels, nrel=None):
    rels = map(lambda x: 1 if type(x) == int and x > 0 else 0, rels)
    return sum(rels)

  def agg(self):
    return sum
    
class VideosRet(Stat):
  def __init__(self):
    Stat.__init__(self, "ranking")
  
  def name(self):
    return "videos_ret"
  
  def fullName(self):
    return self.name()
  
  def calc(self, trecs, nrel=None):
    rels = set(map(lambda trec: trec['target'][0], trecs))
    return len(rels)

  def agg(self):
    return mean

class VideosRel(Stat):
  def __init__(self):
    Stat.__init__(self, "qrel")
  
  def name(self):
    return "videos_rel"
  
  def fullName(self):
    return self.name()
  
  def calc(self, qrel, nrel=None):
    return len(qrel)

  def agg(self):
    return mean

class LengthRet(Stat):
  def __init__(self):
    Stat.__init__(self, "ranking")
  
  def name(self):
    return "avglength_ret"
  
  def fullName(self):
    return self.name()
  
  def calc(self, trecs, nrel=None):
    lengths = map(lambda trec: trec['target'][2]-trec['target'][1], trecs)
    return sum(lengths) / float(len(lengths))

  def agg(self):
    return mean

class LengthRel(Stat):
  def __init__(self):
    Stat.__init__(self, "qrel")
  
  def name(self):
    return "avglength_rel"
  
  def fullName(self):
    return self.name()
  
  def calc(self, qrel, nrel=None):
    lengths = []
    for video, segments in qrel.iteritems():
       lengths.extend(map(lambda trec: trec[2]-trec[1], segments))
    if len(lengths) == 0: return 0.0
    return sum(lengths) / float(len(lengths))

  def agg(self):
    return mean
    

class RelJudge(Stat):
  def __init__(self, relType="segment"):
    Stat.__init__(self, relType=relType)
  
  def name(self):
    return "relString"
  
  def calc(self, rels, nrel=None):
    def transform(r):
      if type(r) == int and r > 0:
        return '1'
      elif type(r) == int and r == 0:
        return '0'
      else:
        return str(r)      
    return ''.join(map(transform,rels)) + ' ' + str(len(rels))

  def forAll(self):
    return False

  def format(self):
    return "%s"

  def agg(self):
    return None

tasks = {
  'me15sava': {'description': 'MediaEal Search And Anchoring Task 2015', 'filenameFormat': 'pre16filenames.json'},
  'tv15lnk':  {'description': 'TRECVid Hyperlinking Task 2015', 'filenameFormat': 'pre16filenames.json'},
  'me14sh':   {'description': 'MediaEval Search and Hyperlinking 2014', 'filenameFormat': 'pre16filenames.json'},
  'tv16lnk':  {'description': 'TRECVid Hyperlinking Task 2016', 'filenameFormat': 'tv16lnkFilenames.json', 'runType': 'L'},
}

#
# Check run name to conform to pattern
#
def checkRunName(runName):
  import os, json
  runName = os.path.basename(runName)
  result = {}
  result['filename'] = runName
  
  if '_' not in runName:
    error = "Error, invalid filename. Filename should start with one of " + ', '.join(tasks.keys())
    return False, error
    
  pos = runName.index('_')
  task = runName[:pos]
  remainder = runName[pos+1:]
  # chop off things after the last . 
  try:
    rpos = remainder.rindex('_')
    rposdot = remainder.rindex('.')
    if rposdot > rpos: remainder = remainder[:rposdot]
  except:
    pass
    
  result['task'] = task
  
  if task not in tasks:
    error = "Error, invalid filename. Filename should start with one of " + ', '.join(tasks.keys())
    return False, error
  
  fn = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'data', tasks[task]['filenameFormat'])
  fields = json.load(open(fn))
  
  errors = []
  
  # check whether there was only one sub task
  if 'runType' in tasks[task]:
    result['runType'] = tasks[task]['runType']
  
  values = remainder.split('_', len(fields))
  if len(values) != len(fields):
    errors = ["Error, invalid number of fields: %d (should be %d) " % (len(values), len(fields)) ]
  else:
    for field, value in zip(fields, values):
      if 're' in field:
        if re.match(field['re'], value) == None: errors.append('Invalid value for field ' + field['name'])
        result[field['name']] = value
      else:
        optionCodes = map(lambda o: o['code'], field['options'])
        pattern = '(' + '|'.join(optionCodes) + ')'
        ms = re.match('^' + pattern + '+$', value)
        if not ms:
          errors.append('Invalid value for field ' + field['name'])
        else:
          result[field['name']] = re.findall(pattern, value)

  if len(errors) > 0:
    prefix = [ "Error: invalid run name. Run names should follow the pattern:" ]
    prefix.append('_'.join(['Task'] + [ field['name'] for field in fields]) + '.???, where')
    prefix.append('')
    for field in fields:
      prefix.append('  %s: %s' % (field['name'], field['description'] ))
      if 're' in field:
        prefix.append('    matching ' + field['re'])
      else:
        for option in field['options']:
          prefix.append('    %s: %s' % (option['code'], option['description'] ))
    errors = prefix + errors
  
  if len(errors)>0:
    return False, errors
  else:
    return True, result

def toSegment(anchor):
  return (anchor['video'], anchor['start'], anchor['end'])

def segToString(seg):
  return "%s %s %s" % (seg[0], sec2String(seg[1]), sec2String(seg[2]))

def sameVideo(s1,s2):
  return s1[0] == s2[0]

def statval(l,percentiles=None):
  n = len(l)
  s = sum(l)
  s2 = sum([ x**2 for x in l ])
  mi = min(l)
  ma = max(l)
  e = s/float(n)
  e2 = s2/float(n)
  v = e2 - e*e
  sd = 0
  if v > 0:
    sd = sqrt(v)
  result = { 'n': n, 'sum': s, 'e': e, 'v': v, 'sd':sd, 'min': mi, 'max': ma }
  if percentiles != None:
    l = sorted(l)
    p = dict(map(lambda x: (x,l[int(len(l)*x)]), percentiles))
    result['percentiles'] = p
  return result
  
