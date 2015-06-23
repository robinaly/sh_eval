#!/usr/bin/env python
from IntervalTree import *
import itertools
'''

'''

def mkBin(target, binSize):
  start = (target[1] / binSize) * binSize
  end = ((target[1] / binSize)+1) * binSize
  return (target[0], start, end)

def makeBinList(ranking, binSize):
  '''
  Groups segments by their bin and returns a list of them 
  '''
  res = []
  seen = set()
  def mkBinL(t):
    return mkBin(t, binSize)
    
  for binT, recs in itertools.groupby(ranking, key=mkBinL):
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
  Groups segments by their video id 
  '''
  judged = defaultdict(list)
  for video, segments in sorted(qrels.iteritems()):
    for binT, segs in itertools.groupby(segments, key=lambda rec: mkBin(rec, binSize)):
      t = list(segs)
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

  ranking    = [(1, 0, 5), (1, 5, 10), (1, 10, 15), (1, 23, 23), (1, 27, 27), (1, 100, 200), (3, 10, 15)]
  relSegs    = [(1, 15, 25), (1, 30, 35), (2, 3, 20) ]
  nonrelSegs = [(1, 0, 10), (1, 105, 2005)]
  binSize = 20
  expectedOutcome = [1, 1, 0, '-']
  
  # Binning
  relJudged = makeBinDict(groupIntoVideos(relSegs), binSize)
  nonrelJudged = makeBinDict(groupIntoVideos(nonrelSegs), binSize)
  ranking = makeBinList(ranking, binSize)
  
  # Calculation of relevance string
  outcome = map(lambda seg: getRelevanceExact(relJudged, nonrelJudged, seg), ranking)
  
  if outcome != expectedOutcome:
    raise ValueError("Calculated " + repr(outcome) + " where " + repr(expectedOutcome) + " was expected.")
    
  print "Correctly calculated " + repr(outcome)
  
  ranking    = [(1, 0, 5), (1, 5, 10), (1, 10, 15), (1, 23, 23), (1, 27, 27), (1, 100, 200), (3, 10, 15)]
  relSegs    = [(1, 15, 25), (1, 30, 35), (2, 3, 20) ]
  nonrelSegs = [(1, 0, 10), (1, 105, 2005)]
  binSize = 5
  expectedOutcome = [0, '-', '-', '-', '-', '-', '-']

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
  
  if outcome != expectedOutcome:
    raise ValueError("Calculated " + repr(outcome) + " where " + repr(expectedOutcome) + " was expected.")
    
  print "Correctly calculated " + repr(outcome)
  