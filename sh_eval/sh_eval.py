#!/usr/bin/env python
# Evaluation script for free-segment based search tasks.
# See readme for usage

# author: Robin Aly <r.aly@utwente.nl>
# date: 2015-06-10
#
import sys, re
from utils import *
import itertools
from collections import defaultdict
from bisect import *
from toleranceToIrrelevance import *
from binnedRelevance import *
from maisp import MAiSPCalculator
from optparse import OptionParser
from IntervalTree import *
import os

def printUsage():
  print """
  Evaluation script for unrestricted segment based retrieval.
  Author: Robin Aly <r.aly@utwente.nl>
  Date: 2015-06-10

  Usage: 
  * Point the PYTHONPATH variable to the directory where util.py resides
  * call python sh_eval.py --kind linking <qrel_file> <run_file>
  where
    * each line of <qrel_file> has to comply with the following format:
      <anchor/query_id> Q0 <video id> <start> <end> <relevance>
      for example:
      anchor_23 Q0 v20080508_234000_bbcfour_inside_the_medieval_mind 15.20 15.40 1
      
    * each line of <run_file> has to comply with the following format:
      <anchor/query_id> Q0 <video id> <start> <end> <rank> <score> <run>
      for example:
      anchor_1 Q0 v20080403_232000_bbcone_holiday_weather 0.00 0.26 1 0.0607 run_1
    
  Output: 
  The produced output is similar to the output of the trec_eval tool:
  <measure>  <subject> <value>
  where
  <measure> is one of the calculated measures by this tool
  <subject> is for what anchor this example applies, and
  <value>   is the result of the measure.  
  """

def formatQrel(line):
  fields = line.split()
  return {'anchorId': fields[0], 'target':(fields[2], ToSec(fields[3]), ToSec(fields[4])), 'rel': int(fields[5])}
  
def formatTrec(line):
  fields = line.split()
  return {'anchorId': fields[0], 'target':(fields[2], ToSec(fields[3]), ToSec(fields[4])), 'rank': int(fields[5]), 'score': float(fields[6])}  
  
def formatTrecSearch(line):
  fields = line.split()
  return {'anchorId': fields[0], 'target':(fields[2], ToSec(fields[3]), ToSec(fields[4])), 'rank': int(fields[6]), 'score': float(fields[7])}  

def getRelevance(qrels, qnonrels, target):
  ''' checks if two time segments overlap ''' 
  targetVideo, targetStart, targetEnd = target
  c = None
  # iterate over all qrels
  for qrel in qrels.get(targetVideo,[]):
    if overlaps(qrel, target): return 1
  for qrel in qnonrels.get(targetVideo,[]):
    if overlaps(qrel, target): return 0
  return '-'

def merge(segment1, segment2):
  video1, start1, end1 = segment1
  video2, start2, end2 = segment2
  return (video1, min(start1, start2), max(end1, end2))

def mergeList(recs):
  merged = defaultdict(list)
  seen = set()
  if not recs: return {}
  last = recs[0]
  for rec in recs[1:]:
    if overlaps(last, rec):
      last = merge(last, rec)
    else:      
      merged[last[0]].append(last)
      seen.add(last)
      last = rec
  merged[last[0]].append(last)
  return merged 
  
def toDict(l):
  res = defaultdict(list)
  for e in l:
    res[e[0]].append(e)
  return res
  
def getTarget(rec):
  return rec['target']

def do_open(fn):
  import gzip
  if fn.endswith('.gz'):
    return gzip.open(fn)
  else:
    return open(fn)

#
# MAIN
#
if __name__ == "__main__":
  parser = OptionParser(usage="usage: %prog [options] qrel submission-file" )
  parser.add_option("-k", "--kind", dest="kind", help="Input format kind ['linking', 'search'], default linking.", metavar="kind", default='linking')
  parser.add_option("-s", "--segments", dest="segments", help="Calculate Segment Statistics", metavar="segments", default=True)
  parser.add_option("-b", "--binned", dest="binned", help="Calculate Binned Statistics", metavar="binned", default=True)
  parser.add_option("-B", "--binSize", dest="binSize", help="Bin Size", metavar="binSize", default=5*60)
  parser.add_option("-t", "--tollerance", dest="tollerance", help="Calculate Binned Statistics", metavar="tollerance", default=True)
  parser.add_option("-T", "--tWindow", dest="tolleranceWindow", help="Tollerance Window", metavar="tolleranceWindow", default=15)
  parser.add_option("-m", "--maisp", dest="maisp", help="Calculate MAiSP", metavar="maisp", default=True)

  (opt, args) = parser.parse_args()  
  
  if len(args) != 2:
    printUsage()
    sys.exit(1)
    
  # Measures to use
  measures = [ NumQ(), VideosRet(), VideosRel(), LengthRet(), LengthRel() ]
  measures.extend([ NumRel(), NumRet(), NumRelRet(), Ap(), PrecisionAt(5), PrecisionAt(10), PrecisionAt(20), JudgedAt(10), JudgedAt(20), JudgedAt(30), RelJudge() ])

  # if we are using binned evaluation
  if opt.binned:
    measures.extend(
       [ NumRel("bin"), NumRet("bin"), NumRelRet("bin"), Ap("bin"), PrecisionAt(5,"bin"), PrecisionAt(10,"bin"), PrecisionAt(20,"bin"), JudgedAt(10,"bin"), JudgedAt(20,"bin"), JudgedAt(30,"bin"), RelJudge("bin"), ]
    )  

  # if we are using tollerance to relevance models
  if opt.tollerance:
    measures.extend(
      [ NumRel("tol"), NumRet("tol"), NumRelRet("tol"), Ap("tol"), PrecisionAt(5,"tol"), PrecisionAt(10,"tol"), PrecisionAt(20,"tol"), JudgedAt(10,"tol"), JudgedAt(20,"tol"), JudgedAt(30,"tol"), RelJudge("tol"), ]
    )

  # if we are calculating MAiSP
  if opt.maisp:
    measures.extend( [MAiSPRel(), MAiSPRet(), MAiSPRelRet(), MAiSPiAsp()] )
  
  # command line arguments  
  qrel = args[0]
  trec = args[1]
  BIN_SIZE = opt.binSize
  TOLERANCE = opt.tolleranceWindow

  # read the qrel 
  recs = map(formatQrel, do_open(qrel))
  recs.sort(key=lambda rec: (rec['anchorId'], rec['target']))
  anchors = set(map(lambda rec: rec['anchorId'], recs))
  rels = dict()
  nonRels = dict()
  judged = dict()
  rawRels = dict()
  rawNonRels = dict()
  
  # Group qrel by anchor id
  for anchorId, recs in itertools.groupby(recs, key=lambda rec: rec['anchorId']):
    recs = list(recs)
    # get relevant and non-relevant targets
    relTargets = map(getTarget, filter(lambda rec: rec['rel'] > 0, recs))
    nonrelTargets = map(getTarget, filter(lambda rec: rec['rel'] <= 0, recs))

    rels[anchorId] = mergeList(relTargets)
    rawRels[anchorId] = toDict(relTargets)
    rawNonRels[anchorId] = toDict(nonrelTargets)
    nonRels[anchorId] = mergeList(nonrelTargets)
    judged[anchorId] = defaultdict(list)
    for video, recs in itertools.groupby(recs, key=lambda rec: rec['target'][0]):
      for rec in recs:
        judged[anchorId][video].append(rec)

  # Prepare output
  out = []

  #Add constants to output
  out.append(['runid', 'all', os.path.basename(trec) ])
  out.append(['size_bin', 'all', str(BIN_SIZE) ])
  out.append(['tol_len', 'all', str(TOLERANCE) ])
  out.append(['mark_relevant', 'all', str(1) ])
  out.append(['mark_non_relevant', 'all', str(0) ])
  out.append(['mark_relevant_seen', 'all', 's' ])
  out.append(['mark_non-relevant_seen', 'all', 'S' ])
  out.append(['mark_unjudged', 'all', '-' ])

  if opt.kind == 'linking':
    trec = map(formatTrec, do_open(trec))
  else:
    trec = map(formatTrecSearch, do_open(trec))
  
  # sort by rank
  trec.sort(key=lambda rec: (rec['anchorId'], rec['rank']))
  values = []

    # Group ranking by anchor id
  for anchorId, recs in itertools.groupby(trec, key=lambda rec: rec['anchorId']):
    trecs = list(recs)
  
    # only consider anchors from the predefined list
    if anchorId not in anchors:
      continue
      
    # get relevant / nonrelevant / judged items for this anchor
    qrels = rels[anchorId]
    qnonrels = nonRels[anchorId]
    qjudged = judged[anchorId]
  
    numrel = sum([ len(v) for v in qrels.values()])
    
    targets = map(lambda x: x['target'], trecs)
    
    #
    # Create binary array of relevant / non relevant states for the ranking
    #
    relevanceStati = [getRelevance(qrels, qnonrels, target) for target in targets]

    #
    # Tolerance to intollerance measures
    #

    def seg2Seg(segDict):
      res = []
      for segments in segDict.values():
        res.extend([ Segment(s) for s in segments ])
      return res
    relTree = IT( seg2Seg(qrels) )
    nonRelTree = IT( seg2Seg(qnonrels) )
    seenTree = IT([])
  
    relevanceStatiTol = [ getRelevanceTol(relTree, nonRelTree, seenTree, target, TOLERANCE) for target in targets]
    numrelTol = numrel
 
    #
    # Create a MAiSP calculator for each query
    #
    maisp_calc = None
    if opt.maisp:
      maisp_calc = MAiSPCalculator()
      maisp_calc.calc(targets)

    #
    # Binned relevance judgments
    #  
    trecsBin = makeBinList(targets, BIN_SIZE)
    qrelsBin = makeBinDict(rawRels[anchorId], BIN_SIZE)
    qnonrelsBin = makeBinDict(rawNonRels[anchorId], BIN_SIZE)

    numrelBin = sum([ len(v) for v in qrelsBin.values()])
    relevanceStatiBin = map(lambda target: getRelevanceExact(qrelsBin, qnonrelsBin, target), trecsBin)

    # calculate all measurs and append them to the list vals
    vals = []
    for m in measures:
      if m.relType() == "segment":      
        v = m.calc(relevanceStati, nrel=numrel)
      elif m.relType() == "bin":
        v = m.calc(relevanceStatiBin, nrel=numrelBin)
      elif m.relType() == "tol":
        v = m.calc(relevanceStatiTol, nrel=numrelTol)
      elif m.relType() == "maisp":
        v = m.calc(maisp_calc)
      elif m.relType() == "ranking":
        v = m.calc(trecs)
      elif m.relType() == "qrel":
        v = m.calc(qrels)
      
      if m.forAll():
        vals.append(v)
      if m.perQuery():
        out.append([m.fullName(), anchorId, m.format() % v ])
  
    # now append the list of measures to the list of measurs for all
    # anchors
    values.append(vals)

  for i,m in enumerate(filter(lambda m: m.forAll(), measures)):
    if not m.forAll(): continue
    v = m.agg()(map(lambda x: x[i], values))
    out.append([ m.fullName(), 'all', m.format() % v ])

  mlen = [ max(map(lambda x: min(20,len(x[i])), out)) for i in range(len(out[0]))]
  f = '\t'.join(['%%-%ds' % l for l in mlen ])
  for o in out: 
    print f % tuple(o)
