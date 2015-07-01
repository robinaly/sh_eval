#!/usr/bin/env python
from IntervalTree import *
import itertools
'''

'''

def segment2Bins(target, binSize):
  '''
  Transforms a single segment into list of binned segments (according to binSize):
  For example
  (1,2,30) with binSize=10
  results in
  [(1,0,10), (1,10,20), (1,20,30)]
  '''
  start_bin = target[1] / binSize
  end_bin = (target[2]-1) / binSize + 1
  res = []
  for i in range(start_bin, end_bin):
    start = i * binSize
    end = (i+1) * binSize
    res.append((target[0], start, end))
  return res

def map2bin(ranking, binSize):
  '''
  Maps a list of segments into a binned list of segment.
  For example:
  [ (1,2,10), (1,35,45) ] with binSize = 10 
  results in 
  [ (1,0,10), (1,30,40), (1,40,50) ]
  '''
  import operator
  def mkBinL(t):
    return segment2Bins(t, binSize)
  ranking = map(mkBinL, ranking)
  ranking = sorted(reduce(operator.add, ranking))
  for binT, recs in itertools.groupby(ranking):
    recs = list(recs)
    yield binT

def makeBinList(ranking, binSize):
  '''
  Groups segments by their bin and returns a list of them 
  : ranking list of video,start,end tuples
  '''
  res = []
  seen = set()
    
  for binT in map2bin(ranking, binSize):
    if not binT in seen:
      seen.add(binT)
      res.append(binT)
  return res

def groupIntoVideos(segments):
  '''
  Groups segments by their video id 
  '''
  grouped = defaultdict(list)
  for video, segments in itertools.groupby(segments, key=lambda rec: rec[0]):
    segments = list(segments)
    grouped[video].extend(segments)
  return grouped
  
def makeBinDict(qrels, binSize):
  '''
  Takes a map from video id to a list of segments.
  For each segment in this list, it bins the list
  '''
  judged = defaultdict(list)
  for video, segments in sorted(qrels.iteritems()):
    for binT  in map2bin(segments, binSize):
      judged[video].append(binT)
  return judged
  
def getRelevanceExact(qrels, qnonrels, target):
  ''' checks for exact relevance ''' 
  targetVideo, targetStart, targetEnd = target
  # iterate over all qrels
  if target in qrels.get(targetVideo,[]):
    return 1  
  if target in qnonrels.get(targetVideo,[]):
    return 0
  return '-'
  
'''
Testing code
'''
def compareDict(a,b):
  ka = set(a.keys())
  kb = set(b.keys())
  if ka - kb:
    return False
  if kb - ka:
    return False
  for k in ka:
    if a[k] != b[k]:
      return False
  return True

if __name__ == "__main__":

  binSize = 20

  print "Test1"
  relSegs    = [(1, 0, 20),  (1, 30, 45), (2, 3, 20) ]
  print makeBinDict(groupIntoVideos(relSegs), binSize)
  
  print "Test2"
  ''' 
  First segment is expanded to two,
  Others are only expanded
  First two are relevant
  Second is non-relevant
  Last is unknown
  '''
  ranking    = [(1, 0, 40),  (1, 100, 120), (3, 10, 15)]
  relSegs    = [(1, 0, 20),  (1, 30, 45), (2, 3, 20) ]
  nonrelSegs = [(1, 0, 10),  (1, 105, 124)]
  expectedOutcome = [1, 1, 0, '-']
  
  # Binning
  ranking = makeBinList(ranking, binSize)
  relJudged = makeBinDict(groupIntoVideos(relSegs), binSize)
  nonrelJudged = makeBinDict(groupIntoVideos(nonrelSegs), binSize)

  # Calculation of relevance string
  outcome = map(lambda seg: getRelevanceExact(relJudged, nonrelJudged, seg), ranking)
  
  if outcome != expectedOutcome:
    raise ValueError("Calculated " + repr(outcome) + " where " + repr(expectedOutcome) + " was expected.")
  print "Correctly calculated " + repr(outcome)
  
  
  print "Test3"
  ranking    = [(1, 0, 5), (1, 5, 10), (1, 10, 15), (1, 23, 23), (1, 27, 27), (1, 100, 200), (3, 10, 15)]
  relSegs    = [(1, 15, 25), (1, 30, 35), (2, 3, 20) ]
  nonrelSegs = [(1, 0, 10), (1, 105, 120)]
  binSize = 10
  expectedOutcome = [0, 1, 1, 0, 0, '-', '-', '-', '-', '-', '-', '-', '-', '-']

  # Binning
  relJudged = makeBinDict(groupIntoVideos(relSegs), binSize)
  nonrelJudged = makeBinDict(groupIntoVideos(nonrelSegs), binSize)
  ranking = makeBinList(ranking, binSize)
  
  for k,v in relJudged.iteritems():
    print 'rel', k, v
  for k,v in nonrelJudged.iteritems():
    print 'nonrel', k, v
  print 'ranking', ranking
  # Calculation of relevance string
  outcome = map(lambda seg: getRelevanceExact(relJudged, nonrelJudged, seg), ranking)
  
  # Make test
  if outcome != expectedOutcome:
    raise ValueError("Calculated " + repr(outcome) + " where " + repr(expectedOutcome) + " was expected.")
  print "Correctly calculated " + repr(outcome)
  