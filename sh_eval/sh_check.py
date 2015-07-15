#!/usr/bin/env python
"""
This script checks the validity of a run submission to the Media Eval Search and Hyperlinking Task 
or TRECVid Hyperlinking Task.

Author: Robin Aly <r.aly@utwente.nl>
Date: 30-06-2016

Usage:
python ./sh_check/.py <F> ...
where <F> is either a path to a file or a directory that consists only of run files

Task_Team_RunType_Priority_Segmentation_TranscriptType_AdditionalFeatures_Description[.???], where
   Task: the identifier of the task
	 me15sava: MediaEal Search And Anchoring Task 2015
	  tv15lnk: TRECVid Hyperlinking Task 2015
	   me14sh: MediaEval Search and Hyperlinking 2014
   Team: the identifier of the team submitting the task
   RunType: the identifier for the sub-task (or runType)
	 S: Search run
	 L: Linking run
   Priority: a integer (low = high priority) assigned by the participant
   Segmentation: the way how the result segments were defined 
	 Ss: speech sentence segmentation
	 Sp: speech segment segmentation
	 Sh: shot segmentation
	  F: fixed length segmentation
	  L: lexical cohesian segmentation
	  P: use prosodic features for segmentation
	  O: other segmentation
   TranscriptType: the transcript being used 
	 I: LIMSI transcripts
	 M: Manual subtitles
	 S: NST/Sheffield
	 U: LIUM transcripts
	 N: No speech information
   AdditionalFeatures: other features being used, a concatenation of 
	 M: Metadata
	 V: Visual features
	 O: Other information
	 N: No additional features
   Description: a very short for the approach that produced the run.

History:
2015-06-30 made more general

2014-08-12 sorted the anchors that weren't mentioned in the run

"""
import sys, re, os, collections
from utils import *
from IntervalTree import *

lineno = 0
error = False

def reportError(line, errstr, t='error'):
  if line < 0:
    if t=='warning':
      return "Warning on line %5d: %s" % (line, errstr)
    else:
      return "Error: %s" % (line, errstr)
  if t == 'warning':
    return "Warning on line %5d: %s" % (line, errstr)
  return "Error on line %5d: %s" % (line, errstr)

def printList(l):
  maxlen = max(map(lambda e: len(e[0]), l))+1
  formatS = ('\t%' + str(maxlen) + 's: %s')
  return '\n'.join(map(lambda e: formatS % e, l))

def do_open(fn, mode):
  import gzip
  if fn.endswith('.gz'): 
    return gzip.open(fn, mode)
  else:
    return open(fn, mode)

NOTSEEN = []

#
# Check run name to conform to pattern
#
def checkRunName(runName):
  import os
  runName = os.path.basename(runName)
  generalPattern = '(?P<task>[^_]+)_(?P<team>[^_]+)_(?P<runType>[^_]+)_(?P<Priority>[^_]+)_(?P<segmentation>[^_]+)_(?P<asrFeature>[^_]+)_(?P<additionalFeatures>[^_.]+)(?P<description>_[^_]+)?(\..+)?$'
  result = {}
  result['filename'] = runName

  m = re.match(generalPattern, runName)
  if m == None:
    error = [ 
            "Error: invalid run name. Run names should follow the pattern:",
            "Task_Team_RunType_Priority_Segmentation_TranscriptType_AdditionalFeatures_Description[.???], where",
            "   Task: the identifier of the task\n" + printList(taskTypesList),
            "   Team: the identifier of the team submitting the task",
            "   RunType: the identifier for the sub-task (or runType)\n" + printList(runTypesList),
            "   Priority: a integer (low = high priority) assigned by the participant",
            "   Segmentation: the way how the result segments were defined \n" + printList(segmentationsList),
            "   TranscriptType: the transcript being used \n" + printList(asrFeaturesList),
            "   AdditionalFeatures: other features being used, a concatenation of \n" + printList(additionalFeaturesList),
            "   Description: a very short for the approach that produced the run."
            ]
    error = '\n'.join(error)
    return False, error

  ok = True
  errors = []
  result['team'] = m.group('team')

  task = m.group('task')
  if task not in tasks:
    ok = False
    errors.append("Invalid task '" + task + "'. Valid tasks are :\n" + printList(taskTypesList))
  else:
    result['task'] = task

  runType = m.group('runType')
  if runType not in runTypes:
    ok = False
    errors.append("Invalid run type '" + runType + "'. Valid run types are :\n" + printList(runTypesList))
  else:
    result['runType'] = runType
    
  m2 = re.match('\d+', m.group('Priority'))
  if not m:
    ok = False
    errors.append("Invalid priority number");
  else:
    result['priority'] = m.group('Priority')
  
  segmentation = m.group('segmentation')
  pattern = '(' + '|'.join(segmentations) + ')'
  mS = re.match('^'+pattern+'+$', segmentation)
  if mS == None:
    ok = False
    errors.append("Invalid segmentation '" + segmentation + "'. Segmentations should be a combination of: \n" + printList(segmentationsList))
  else:
    segmentation = re.findall(pattern, segmentation)
    result['segmentation'] = segmentation  

  asrFeature = m.group('asrFeature')
  pattern = '(' + '|'.join(asrFeatures) + ')'
  mS = re.match('^'+pattern+'+$', asrFeature)
  if mS == None:
    ok = False
    errors.append("Invalid transcript type '" + asrFeature + "'. Transcript type should be a combination of: \n" + printList(asrFeaturesList))
  else:
    asrFeature = re.findall(pattern, asrFeature)
    result['asrFeature'] = asrFeature  

  additionalFeature = m.group('additionalFeatures')
  if additionalFeature != None:
    pattern = '(' + '|'.join(additionalFeatures) + ')'
    mS = re.match('^'+pattern+'+$', additionalFeature)
    if mS == None:
      ok = False      
      errors.append("Invalid additionalFeature '" + additionalFeature + "'. Additional features should be a combination of: \n" + printList(additionalFeaturesList))
    else:
      additionalFeature = re.findall(pattern, additionalFeature)
      result['additionalFeature'] = additionalFeature 
  else:
    result['additionalFeature'] = '' 
  if ok:
    return True, result
  return False, '\n'.join(errors)


def loadVideoFiles(runInfo):
  '''
  Read data about the collection and the queries / anchors
  '''
  import xml.etree.ElementTree as ET
  if runInfo['task'] == 'me14sh':
    fn = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'data', 'cAXES.txt')
  elif runInfo['task'] == 'tv15lnk':
  videoFiles = dict()
  if runInfo['task'] == 'me14sh' or runInfo['task'] == 'me15sava' or runInfo['task'] == 'tv15lnk':
    fn = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'data', 'cAXES.txt')
    with open(fn) as f:
      videoFilesList = [ line.split() for line in f ]
      videoFiles = dict( map(lambda x: (x[0], (x[1], h2Sec(x[1]))), videoFilesList))
  else:
    print "WARNING - function loadVideoFiles: cannot find video list for task type %s" % runInfo['task']
  return videoFiles
  
def loadAnchors(runInfo):
  # read anchors 
  import xml.etree.ElementTree as ET
  if runInfo['task'] == 'me14sh':
    fn = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'data', 'me14sh_linking_testSet_anchors.xml')
    tree = ET.parse(fn)
    anchorsDef = [ [anchor.find('anchorId').text, anchor.find('fileName').text, anchor.find('startTime').text, anchor.find('endTime').text] for anchor in tree.findall('.//anchor') ]
  elif runInfo['task'] == 'tv15lnk':
    fn = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'data', 'tv15hlk_test_anchors.xml')
    tree = ET.parse(fn)
    anchorsDef = [ [anchor.find('anchorId').text, anchor.find('video').text, anchor.find('startTime').text, anchor.find('endTime').text] for anchor in tree.findall('.//anchor') ]
  else:
    sys.exit(1)
    
  anchorsDef = map(lambda x: {'anchorId': x[0], 'video': x[1], 'start': ToSec(x[2]), 'end': ToSec(x[3])}, anchorsDef)
  
  anchorDefinitions = dict( map(lambda x: (x['anchorId'], x), anchorsDef))
  anchors = list(sorted(anchorDefinitions.keys()))

  return anchors, anchorDefinitions

def loadQueries(runInfo):
  # read anchors
  import xml.etree.ElementTree as ET
  if runInfo['task'] == 'me14sh':
    fn = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'data', 'me14sh_search_testSet_queries.xml')
    tree = ET.parse(fn)
    queryDef = [ [anchor.find('queryId').text, anchor.find('queryText').text] for anchor in tree.findall('.//top') ]

  elif runInfo['task'] == 'me15sava':
    fn = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'data', 'me15sava_search_test_queries.xml')
    tree = ET.parse(fn)
    queryDef = [ [anchor.find('itemId').text, anchor.find('queryText').text] for anchor in tree.findall('.//top') ]
  else:
    sys.exit(1)
    
  queryDef = map(lambda x: {'queryId': x[0], 'text': x[1]}, queryDef)
  
  queryDef = dict( map(lambda x: (x['queryId'], x), queryDef))
  queries = list(sorted(queryDef.keys()))
  
  return queries, queryDef 

# 1. Search sub-task: 
# Workshop participants are required to submit their search results using the following whitespace separated fields in one line for each found result segment:
# Field 
# Explanation 
# queryId   The identifier of the query for which this result was found 
# "Q0"     a legacy constant 
# fileName    The identifier of the video (without extension) of the result segment
# startTime   The starting time of the result segment (mins.secs) 
# endTime   The end time of the result segment (mins.secs) 
# jumpInPoint   The time offset where a users should start playing the video (mins.secs) . If your system considers the beginning of the segment as the jump-in point, please copy the startTime to the jumpInPoint field
# rank    The rank of the result segment for this query  
# confidenceScore   A floating point value describing the confidence of the retrieval system that the result segment is the known-item 
# runName   A identifier for the retrieval system, see also RunSubmission2013 
def checkSearchRun(runName, runInfo):
  lineno = 0
  error = False
  errors = []
  queries, queryDefs = loadQueries(runInfo)
  videoFiles = loadVideoFiles(runInfo)
  lastAnchor = ""
  lastRank = 0
  foundItems = set()
  seenSegments = IT([])
  with do_open(runName, 'r') as f:
    for line in f:
      lineno += 1
      line = line.strip()
      field = line.split()
      if len(field) != 9:
        errors.append(reportError(lineno, "Invalid number of fields: " + line))
        continue
      if field[0] not in queries:
        errors.append(reportError(lineno, "Invalid item id: " + field[0]))
        continue
      # mark item as seen
      foundItems.add(field[0])
      if field[0] != lastAnchor:
        lastAnchor = field[0]
        lastRank = 0
        seenSegment = IT([])
      if field[2] not in videoFiles:
        errors.append(reportError(lineno, "Invalid video file: " + field[2]))
        continue
      hours, videoSec = videoFiles[field[2]]
      if int(field[6]) != lastRank + 1:
        errors.append(reportError(lineno, "Non-consecutive rank: " + field[6]))
        continue
      lastRank = int(field[6])      
      if not isTime(field[3]):
        errors.append(reportError(lineno, "Invalid start time: " + field[3]))
        continue  
      if not isTime(field[4]):
        errors.append(reportError(lineno, "Invalid end time: " + field[4]))
        continue
      if not isTime(field[5]):
        errors.append(reportError(lineno, "Invalid jumpin time: " + field[5]))
        continue
      if ToSec(field[4]) <= ToSec(field[3]):
        errors.append(reportError(lineno, "Segments end time before start time: start %s end %s" %(field[3], field[4]) ))
        continue
      if not isRank(field[6]):
        errors.append(reportError(lineno, "Invalid rank " + field[6]))
        continue
      if not isScore(field[7]):
        errors.append(reportError(lineno, "Invalid score " + field[5]))
        continue
      if ToSec(field[3]) > videoSec:
        errors.append(reportError(lineno, "Segment from %s to %s is longer than the video '%s' (length: %s)." % (field[3], field[4], field[2], sec2String(videoSec)), t='warning'))
        continue
      s = Segment((field[2], ToSec(field[3]), ToSec(field[4])))
      f = seenSegment.search_seg(s)
      if f:
        f=f[0].get_tuple()
        errors.append(reportError(lineno, "Segment from %s [%s:%s] overlaps with previously returned segment [%s:%s]." % (field[2], field[3], field[4], sec2String(f[1]), sec2String(f[2]))))
        continue
      seenSegment.add(s)
  notseen = set(queries) - foundItems
  if len(notseen) > 0:
    errors.append(reportError(-1,"Following queries weren't mentioned: " + ','.join(sorted(notseen)), t='warning'))
    NOTSEEN.extend(notseen)
  return errors

# 2. Linking sub-task:
# The participants are required to submit their results in the following format: 
# Field 
# Explanation 
# anchorId   The identifier of the anchor from which the links originate
# "Q0"     a legacy constant 
# fileName   The identifier of the video (without extension) of the target segment
# startTime   The starting time of the target segment (mins.secs) 
# endTime   The end time of the target segment (mins.secs) 
# rank    The rank of the target segment within the links for this anchor
# confidenceScore   A floating point value describing the confidence of the retrieval system that the target segment is a suitable link target
# runName   A identifier for the retrieval system used, see also RunSubmission2013  
def checkLinkingRun(runName, runInfo):
  
  anchors, anchorDefinitions = loadAnchors(runInfo)
  videoFiles = loadVideoFiles(runInfo)
  anchors = set(anchors)
  seenSegments = IT([])
  with do_open(runName, 'r') as f:
    lineno = 0
    foundAnchors = set()
    errors = []
    lastRank = 0
    lastAnchor = ""
    for line in f:
      lineno += 1
      line = line.strip()
      field = line.split()
      if len(field) != 8:
        errors.append(reportError(lineno, "Invalid number of fields. " + line))
        continue
      if not field[0] in anchors:
        errors.append(reportError(lineno, "Invalid anchor id: " + field[0]))
        continue
      if lastAnchor != field[0]:
        if field[0] in foundAnchors:
          errors.append(reportError(lineno, "Rementioning of anchor: " + field[0]))
          continue
        lastAnchor = field[0]
        lastRank = 0
        seenSegments = IT([])
      foundAnchors.add(field[0])

      if field[2] not in videoFiles:
        errors.append(reportError(lineno, "Invalid video file: " + field[2]))
        continue
      hours, videoSec = videoFiles[field[2]]
      if not isTime(field[3]):
        errors.append(reportError(lineno, "Invalid start time: " + field[3]))
        continue  
      if not isTime(field[4]):
        errors.append(reportError(lineno, "Invalid end time: " + field[4]))
        continue
      if not isRank(field[5]):
        errors.append(reportError(lineno, "Invalid rank: " + field[5]))
        continue
      if int(field[5]) != lastRank + 1:
        errors.append(reportError(lineno, "Non-consecutive rank: " + field[5]))
        continue
      lastRank = int(field[5])
      if isScore(field[7]):
        errors.append(reportError(lineno, "Invalid score: " + field[6]))
        continue
      if ToSec(field[4]) <= ToSec(field[3]):
        vals = (field[4], ToSec(field[4]), field[3], ToSec(field[3]))
        errors.append(reportError(lineno, "Segments end time %s (%d) before start time %s (%d)." % vals ))
        continue
      if ToSec(field[3]) > videoSec:
        errors.append(reportError(lineno, "Segment from %s to %s is longer than the video '%s' (length: %s)." % (field[3], field[4], field[2], sec2String(videoSec)), t='warning'))
        continue      
      start = ToSec(field[3])
      end = ToSec(field[4])
      duration = end - start
      if duration < 10 or duration > 2 * 60:
        errors.append(reportError(lineno, "Link segment from %s to %s is %d seconds long. Must be between 10sec and 2min " % (field[3], field[4], duration)))
        continue
      # check for overlap with anchor
      anchor = anchorDefinitions[field[0]]
      if field[2] == anchor['video']:
        if overlapTime(start, end, anchor['start'], anchor['end']):
          errors.append(reportError(lineno, "Segment from %s to %s in video '%s' overlaps with anchor (from %s to %s)." % (field[3], field[4], field[2], sec2String(anchor['start']), sec2String(anchor['end']))))
          continue
      # check for overlap with previously returned segment
      s = Segment((field[2], ToSec(field[3]), ToSec(field[4])))
      f = seenSegments.search_seg(s)
      if f:
        f=f[0].get_tuple()
        errors.append(reportError(lineno, "Segment from %s [%s:%s] overlaps with previously returned segment [%s:%s]." % (field[2], field[3], field[4], sec2String(f[1]), sec2String(f[2]))))
        continue
      seenSegments.add(s)
      
    notseen = set(anchors) - foundAnchors
    if len(notseen) > 0:
      errors.append(reportError(0,"Following anchors weren't mentioned: " + ','.join(sorted(notseen)), t='warning'))
      NOTSEEN.extend(notseen)
    return errors

def recursiveAdd(f):
  if os.path.isfile(f):
    return [f]
  if os.path.isdir(f):
    runs = []
    for fi in os.listdir(f):
      if fi.startswith('.'): continue
      runs.extend(recursiveAdd(os.path.join(f,fi)))
    return runs
  print >>sys.stderr, "File ", f, " does not exist"
  return []

def main():
  anyErrors = False
  #
  runs = []
  for file in sys.argv[1:]:
      runs.extend(recursiveAdd(file))
      
  for runName in runs:
    ok, runInfo = checkRunName(runName)
    error = not ok
    if ok:
      if runInfo['runType'] == 'S':
        errors = checkSearchRun(runName, runInfo)
      else:
        errors = checkLinkingRun(runName, runInfo)
      nerrors = len(errors)
      if nerrors > 0:
        error = True
        if nerrors > 10:
          errors = errors[0:20]
          errors.append('... %d more errors ...' % (nerrors - 10))
        report = '\n'.join(errors)
    else:
      report = runInfo
    
    if error:
      print 'Run file:', runName
      print re.sub('(^|\n)','\\1\t', report)
      anyErrors = True
      print ""

  if anyErrors:
    sys.exit(1)
  else:
    sys.exit(0)

if __name__ == '__main__':
  main()
