#!/usr/bin/env python
"""
This script checks the validity of a run submission to the Media Eval Search and Hyperlinking Task 
or TRECVid Hyperlinking Task.

Author: Robin Aly <r.aly@utwente.nl>
Date: 30-06-2016

Usage:
python ./sh_check/.py <F> ...
where <F> is either a path to a file or a directory that consists only of run files

The format of the filename depends on the task. Please see the data/ directory for relevant descriptions.

History:
2016-08-18 options now optionl
2015-06-30 made more general

2014-08-12 sorted the anchors that weren't mentioned in the run

"""
import sys, re, os, collections
from utils import *
from IntervalTree import *

lineno = 0
error = False

NOTSEEN = []
  
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
  videoFiles, blacklist = loadVideoFiles(runInfo['task'])
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
        errors.append(reportError(lineno, "Unknown item id: " + field[0]))
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
  
  anchors, anchorDefinitions = loadAnchors(runInfo['task'])
  videoFiles, blacklist = loadVideoFiles(runInfo['task'])
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
        #errors.append(reportError(lineno, "Unknown anchor id: " + field[0], t='warning'))
        continue
      if lastAnchor != field[0]:
        if field[0] in foundAnchors:
          errors.append(reportError(lineno, "Re-mentioning of anchor: " + field[0]))
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
    ok, result = checkRunName(runName)
    if ok:
      runInfo = result
      if runInfo['runType'] == 'S':
        errors = checkSearchRun(runName, runInfo)
      else:
        errors = checkLinkingRun(runName, runInfo)
    else:
      errors = result
        
    # print error indented
    if len(errors) > 0:
      print 'Run file:', runName
      report = '\n'.join(errors)
      print re.sub('(^|\n)','\\1\t', report)
      anyErrors = True
      print ""

  if anyErrors:
    sys.exit(1)
  else:
    sys.exit(0)

if __name__ == '__main__':
  main()
