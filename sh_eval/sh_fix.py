#!/usr/bin/env python
"""
This script checks the validity of a run submission to the Media Eval Search and Hyperlinking Task 
or TRECVid Hyperlinking Task.

Author: Robin Aly <r.aly@utwente.nl>
Date: 30-06-2016

Usage:
python ./sh_check/.py <F> ...
where <F> is either a path to a file or a directory that consists only of run files



"""
import sys, re, os, collections
from utils import *
from IntervalTree import *
from optparse import OptionParser
import itertools


NOTSEEN = []

def removeSeg(seg1, seg2):
  s1,e1 = seg1
  s2,e2 = seg2
  if not overlapTime(s1,e1,s2,e2):
    return seg1
  # test overlap to the right
  oR = max(e1, e2) - max(s1, e2)
  oL = min(e1, s2) - min(s1, s2)
  if oL == 0 and oR == 0:
    return None
  if oL > oR:
    return min(s1, s2), min(e1, s2)
  else:
    return max(s1, e2), max(e1, e2)

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
def fixSearchRun(opt, in_fn, out_fn):
  lineno = 0
  error = False
  errors = []
  queries, queryDefs = loadQueries(opt)
  videoFiles, blacklist = loadVideoFiles(opt.task)
  lastAnchor = ""
  lastRank = 0
  foundItems = set()
  foundQueries = set()
  seenSegments = IT([])
  def formatSegment(rec):
    return "Anchor {qid}: Segment {video} [{start}:{end}] at rank {rank}".format(
      qid=rec['qid'], 
      video=rec['video'], 
      start=sec2String(rec['start']),
      end=sec2String(rec['end']),
      rank=rec['rank']
    )

    
  with do_open(out_fn, 'w') as out:
    for qid, recs in itertools.groupby(readSearchResults(in_fn), key=lambda rec: rec['qid']):
      recs = list(recs)
      
      if qid not in queries:
        errors.append(reportError(0, "Unknown item id: " + qid))
        continue
        
      # mark item as seen
      if qid in foundItems:
        errors.append(reportError(lineno, "Item mentioned before: " + qid))
        continue
        
      foundItems.add(qid)
      seenSegment = IT([])
      rank = 0
      
      for rec in recs:
        lineno = rec['lineno']
        
        if rec.get('errorStr', None):
          errors.append(reportError(lineno, rec['errorStr'] + ': ' + rec['errorValue']))
        
        if rec['video'] not in videoFiles:
          errors.append(reportError(lineno, "%s: Invalid video file. Ignoring video" % formatSegment(rec)))
          continue
          
        if rec['video'] in blacklist:
          errors.append(reportError(lineno, "%s: Video was blacklisted. Ignoring video" % formatSegment(rec)))
          continue
                  
        if rec['end'] < rec['start']:
          errors.append(reportError(lineno, "%s: end time before start time" % (formatSegment(rec))))
          temp = rec['end']
          rec['end'] = rec['start']
          rec['start'] = temp
          
        if rec['start'] == rec['end']:
          errors.append(reportError(lineno, "%s: end time equal start time" % (formatSegment(rec))))
          rec['end'] = rec['start'] + 10

        wasModified = False
        hasError = False
        for i in range(3):
          wasModified = False
          s = Segment((rec['video'], rec['start'], rec['end']))
          overlap = seenSegment.search_seg(s)
          if overlap:
            f=overlap[0].get_tuple()
            mod = rec['start'], rec['end']
            for o in overlap:
              seg = o.get_tuple()[1], o.get_tuple()[2]
              mod = removeSeg(mod, seg)
              if mod == None: break
            if mod != None:
              errors.append(reportError(lineno, "%s: overlap with previously returned segment [%s:%s]. Corrected segment: [%s:%s]" % (
                formatSegment(rec), sec2String(f[1]), sec2String(f[2]), sec2String(mod[0]), sec2String(mod[1])), t='warning')
              )
              rec['start'], rec['end'] = mod
              wasModified = True
            else:
              errors.append(reportError(lineno, "%s: overlap with previously returned segment [%s:%s]. Ignoring segment." % (formatSegment(rec), sec2String(f[1]), sec2String(f[2]))))
              hasError = True
              break

          duration = rec['end'] - rec['start']
          if duration < 10:
            errors.append(reportError(lineno, "%s: %d seconds long and shorter than 10sec; using 10 sec." % (formatSegment(rec), duration)))
            rec['end'] = rec['start'] + 10
            wasModified = True
          
          if duration > 2 * 60:
            errors.append(reportError(lineno, "%s: %d seconds long and longer than 2min; using 2 min." % (formatSegment(rec), duration)))
            rec['end'] = rec['start'] + 2 * 60
            wasModified = True

          hours, videoSec = videoFiles[rec['video']]
          if rec['end'] > videoSec:
            if rec['start'] < videoSec - 10:
              errors.append(reportError(lineno, "%s: longer than the video (length: %s). Fixing it to [%s:%s]" % (formatSegment(rec), sec2String(videoSec), sec2String(rec['start']), sec2String(rec['end'])), t='warning'))
              rec['end'] = videoSec
              wasModified = True
            else:
              errors.append(reportError(lineno, "%s: longer than the video (length: %s). Start is also after video length. Ignoring" % (formatSegment(rec), sec2String(videoSec))))
              hasError = True
              break
              
          if not wasModified: break
        if hasError: continue
        if wasModified: continue

        s = Segment((rec['video'], rec['start'], rec['end']))
        seenSegment.add(s)

        rank += 1 
        if rank > opt.rank: break
      
        print >>out, '{qid} Q0 {video} {start} {end} {jumpin} {rank} {score} {run}'.format(
          qid = qid,
          video = rec['video'],
          start = sec2String(rec['start']),
          end = sec2String(rec['end']),
          jumpin = sec2String(rec['jumpin']),
          rank = rank,
          score = rec['score'],
          run = rec['run'],
        )
    notseen = set(queries) - foundItems
    if len(notseen) > 0:
      errors.append(reportError(-1,"Following queries weren't mentioned: " + ','.join(sorted(notseen)), t='warning'))
      NOTSEEN.extend(notseen)
    return errors

# 2. Search sub-task: 
def fixAnchoringRun(opt, in_fn, out_fn):
  lineno = 0
  error = False
  errors = []
  anchorVideos = loadAnchorVideos(opt.task)
  videoFiles, blacklist = loadVideoFiles(opt.task)
  foundItems = set()
  foundQueries = set()
  seenSegments = IT([])
  def formatSegment(rec):
    return "Anchor {qid} [{start}:{end}] at rank {rank}".format(
      qid=rec['qid'], 
      start=sec2String(rec['start']),
      end=sec2String(rec['end']),
      rank=rec['rank']
    )

  with do_open(out_fn, 'w') as out:
    allrecs = list(readAnchoringResults(in_fn))
    allrecs.sort(key=lambda rec: (rec['qid'], rec['lineno']))
    for qid, recs in itertools.groupby(allrecs, key=lambda rec: rec['qid']):
      recs = list(recs)
      
      if not qid.startswith('v') and ('v' + qid) in videoFiles:          
        errors.append(reportError(lineno, "%s: does not start with 'v'; added" % qid))
        qid = 'v' + qid
        
      if qid not in anchorVideos:
        errors.append(reportError(0, "Unknown anchor video: " + qid))
        continue
        
      # mark item as seen
      if qid in foundItems:
        errors.append(reportError(lineno, "Item mentioned before: " + qid))
        continue        
      foundItems.add(qid)
      
      seenSegment = IT([])
      rank = 0
      
      for rec in recs:
        lineno = rec['lineno']
        
        if rec['errors']:
          errorStr = ' '.join([error[0] + ':' + error[1] for error in rec['errors']])
          errorStr += '   ' + rec['line']
          errors.append(reportError(lineno, errorStr))
          continue
          
        if not rec['qid'].startswith('v'):          
          rec['qid'] = 'v' + rec['qid']
          #errors.append(reportError(lineno, "%s: does not start with 'v', added" % formatSegment(rec)))
        
        if rec['qid'] not in videoFiles:
          errors.append(reportError(lineno, "%s: Invalid video file. Ignoring video" % formatSegment(rec)))
          continue
          
        if rec['qid'] in blacklist:
          errors.append(reportError(lineno, "%s: Video was blacklisted. Ignoring video" % formatSegment(rec)))
          continue
        
        if 'start' not in rec or 'end' not in rec:
          print rec
          continue
                  
        if rec['end'] < rec['start']:
          errors.append(reportError(lineno, "%s: end time before start time" % (formatSegment(rec))))
          temp = rec['end']
          rec['end'] = rec['start']
          rec['start'] = temp
          
        if rec['start'] == rec['end']:
          errors.append(reportError(lineno, "%s: end time equal start time" % (formatSegment(rec))))
          rec['end'] = rec['start'] + 10

        wasModified = False
        hasError = False
        for i in range(3):
          wasModified = False
          s = Segment((rec['qid'], rec['start'], rec['end']))
          overlap = seenSegment.search_seg(s)
          if overlap:
            f=overlap[0].get_tuple()
            mod = rec['start'], rec['end']
            for o in overlap:
              seg = o.get_tuple()[1], o.get_tuple()[2]
              mod = removeSeg(mod, seg)
              if mod == None: break
            if mod != None:
              errors.append(reportError(lineno, "%s: overlap with previously returned segment [%s:%s]. Corrected segment: [%s:%s]" % (
                formatSegment(rec), sec2String(f[1]), sec2String(f[2]), sec2String(mod[0]), sec2String(mod[1])), t='warning')
              )
              rec['start'], rec['end'] = mod
              wasModified = True
            else:
              errors.append(reportError(lineno, "%s: overlap with previously returned segment [%s:%s]. Ignoring segment." % (formatSegment(rec), sec2String(f[1]), sec2String(f[2]))))
              hasError = True
              break

          duration = rec['end'] - rec['start']
          if duration < 10:
            errors.append(reportError(lineno, "%s: %d seconds long and shorter than 10sec; using 10 sec." % (formatSegment(rec), duration)))
            rec['end'] = rec['start'] + 10
            wasModified = True
          
          if duration > 2 * 60:
            errors.append(reportError(lineno, "%s: %d seconds long and longer than 2min; using 2 min." % (formatSegment(rec), duration)))
            rec['end'] = rec['start'] + 2 * 60
            wasModified = True

          hours, videoSec = videoFiles[rec['qid']]
          if rec['end'] > videoSec:
            if rec['start'] < videoSec - 10:
              errors.append(reportError(lineno, "%s: longer than the video (length: %s). Fixing it to [%s:%s]" % (formatSegment(rec), sec2String(videoSec), sec2String(rec['start']), sec2String(rec['end'])), t='warning'))
              rec['end'] = videoSec
              wasModified = True
            else:
              errors.append(reportError(lineno, "%s: longer than the video (length: %s). Start is also after video length. Ignoring" % (formatSegment(rec), sec2String(videoSec))))
              hasError = True
              break
              
          if not wasModified: break
        if hasError: continue
        if wasModified: continue

        s = Segment((rec['qid'], rec['start'], rec['end']))
        seenSegment.add(s)

        rank += 1 
        if rank > opt.rank: break
      
        print >>out, '{qid} Q0 {start} {end} {rank} {score} {run}'.format(
          qid = qid,
          start = sec2String(rec['start']),
          end = sec2String(rec['end']),
          rank = rank,
          score = rec['score'],
          run = rec['run'],
        )
    notseen = set(anchorVideos) - foundItems
    if len(notseen) > 0:
      errors.append(reportError(-1,"Following queries weren't mentioned: " + ','.join(sorted(notseen)), t='warning'))
      NOTSEEN.extend(notseen)
    return errors


# 3. Linking sub-task:
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
def fixLinkingRun(opt, in_fn, out_fn):
  anchors, anchorDefinitions = loadAnchors(opt.task)
  videoFiles, blacklist = loadVideoFiles(opt.task)
  anchors = set(anchors)
  seenSegments = IT([])
  def formatSegment(field):
    return "Anchor %s: Segment %s [%s:%s] at rank %s" % (field[0], field[2], field[3], field[4], field[5]) 
  with do_open(in_fn, 'r') as f, do_open(out_fn, 'w') as out:
    lineno = 0
    foundAnchors = set()
    errors = []
    rank = 0
    lastAnchor = ""
    results = defaultdict(list)
    anchorList = []
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
      if field[0] != opt.qid and opt.qid != '*':
        continue
      if lastAnchor != field[0]:
        if not field[0] in anchorList:
          anchorList.append(field[0])
        lastAnchor = field[0]
      rank = 0
      try:
        rank = int(field[5])
      except:
        errors.append(reportError(lineno, "Invalid video file: " + field[2]))
        continue
      results[field[0]].append((rank, lineno, field))
    
    for a in anchorList:
      res = sorted(results[a])
      rank = 0
      seenSegments = IT([])
      foundAnchors.add(a)
      for r, lineno, field in res:
        if rank >= opt.rank: break
        if field[2] not in videoFiles:
          errors.append(reportError(lineno, "Invalid video file: " + field[2] + "; ignoring result"))
          continue
        if field[2] in blacklist:
          errors.append(reportError(lineno, "Video file was blacklisted: " + field[2] + "; ignoring result"))
          continue
        hours, videoSec = videoFiles[field[2]]
        if not isTime(field[3]):
          errors.append(reportError(lineno, "Invalid start time: " + field[3] + "; ignoring result"))
          continue  
        if not isTime(field[4]):
          errors.append(reportError(lineno, "Invalid end time: " + field[4] + "; ignoring result"))
          continue
        if not isRank(field[5]):
          #errors.append(reportError(lineno, "Invalid rank: " + field[5]))
          field[5] = str(rank)
        if not isScore(field[6]):
          errors.append(reportError(lineno, "Invalid score: " + field[6] + "; ignoring result"))
          continue
        if ToSec(field[4]) < ToSec(field[3]):
          errors.append(reportError(lineno, "%s end time before start time; ignoring result." % formatSegment(field)))
          continue
        if ToSec(field[3]) > videoSec:
          errors.append(reportError(lineno, "%s is longer than the video [%s]; ignoring result." % (formatSegment(field), sec2String(videoSec))))
          continue      
        start = ToSec(field[3])
        end = ToSec(field[4])
        field[3] = sec2String(start)
        field[4] = sec2String(end)
        duration = end - start
        if duration < 10:
          errors.append(reportError(lineno, "%s is %d seconds long, which is shorter than 10sec; using 10 sec." % (formatSegment(field), duration), t='warning'))
          field[4] = sec2String(start + 10)
        if duration > 2 * 60:
          errors.append(reportError(lineno, "%s is %d seconds long, which is longer than 2min; using 2 min." % (formatSegment(field), duration), t='warning'))
          field[4] = sec2String(start + 2 * 60)
          
        # check for overlap with anchor
        anchor = anchorDefinitions[field[0]]
        if field[2] == anchor['video']:
          errors.append(reportError(lineno, "%s is in the same video as the anchor; ignoring result." % (formatSegment(field))))
          continue
        # check for overlap with previously returned segment
        s = Segment((field[2], ToSec(field[3]), ToSec(field[4])))
        f = seenSegments.search_seg(s)
        if f:
          f=f[0].get_tuple()
          errors.append(reportError(lineno, "%s overlaps with previously returned segment [%s:%s]; ignoring result." % (formatSegment(field), sec2String(f[1]), sec2String(f[2]))))
          continue
        seenSegments.add(s)
        rank +=  1
        field[5] = str(rank)
        print >>out, ' '.join(field)
      
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
  parser = OptionParser(usage="usage: %prog [options] submission-file outptut-submission-file" )
  parser.add_option("-k", "--kind", dest="kind", help="Run kind ['linking', 'search'], default linking.", metavar="kind", default='linking')
  parser.add_option("-t", "--task", dest="task", help=".", metavar="task", default='tv15lnk')
  parser.add_option("-q", "--qid", dest="qid", help=".", metavar="qid", default='*')
  parser.add_option("-r", "--rank", dest="rank", help=".", metavar="rank", default='1000')
  (opt, args) = parser.parse_args()  
  opt.rank = int(opt.rank)
  anyErrors = False
  #
  runs = []
  in_fn = args[0]
  out_fn = args[1]
  errors = []
  if opt.kind == 'search':
    errors = fixSearchRun(opt, in_fn, out_fn)
  elif opt.kind == 'anchoring':
    errors = fixAnchoringRun(opt, in_fn, out_fn)
  else: # must be linking
    errors = fixLinkingRun(opt, in_fn, out_fn)
    
  if errors:
    print 'Run:', in_fn
    print re.sub('(^|\n)','\\1\t', '\n'.join(errors))
    anyErrors = True
    print ""

  if errors:
    sys.exit(1)
  else:
    sys.exit(0)

if __name__ == '__main__':
  main()
