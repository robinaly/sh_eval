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

  """

def readAnchorQrel(fn):
  with open(fn) as f:
    for line in f:
      line = line.strip()
      fields = line.split()
      yield {
        'qid': fields[0], 
        'start': ToSec(fields[1]),
        'end': ToSec(fields[2]),
        'rel': int(fields[3])
      }

#
# MAIN
#
if __name__ == "__main__":
  parser = OptionParser(usage="usage: %prog [options] qrel submission-file" )
  parser.add_option("-k", "--kind", dest="kind", help="Input format kind ['linking', 'search'], default linking.", metavar="kind", default='anchoring')
  parser.add_option("-t", "--task", dest="task", help="Comman separated list of items to evaluate", metavar="task", default='me15sava_anchoring')

  (opt, args) = parser.parse_args()  
  
  if len(args) != 2:
    printUsage()
    sys.exit(1)
    
  videoFiles, blacklist = loadVideoFiles(opt)
  
  # command line arguments  
  qrel = args[0]
  trec = args[1]

  qrels = list(readAnchorQrel(qrel))
  segs = [ Segment((anchor['qid'], anchor['start'], anchor['end'])) for anchor in sorted(qrels, key= lambda x: x['qid']) ]
  ItAll = IT(segs)
  qrels = filter(lambda q: q['rel'] > 0, qrels)
  segs = [ Segment((anchor['qid'], anchor['start'], anchor['end'])) for anchor in sorted(qrels, key= lambda x: x['qid']) ]
  It = IT(segs)
  
  relSegs = defaultdict(list)
  for q in qrels:
    relSegs[q['qid']].append((q['start'], q['end']))
  
  #import xml.etree.ElementTree as ET
  # tree = ET.parse(qrel)
  # anchorsDef = [ {'qid': anchor.find('anchorId').text,
  #                 'video': anchor.find('fileName').text,
  #                 'start': ToSec(anchor.find('startTime').text),
  #                 'end': ToSec(anchor.find('endTime').text)} for anchor in tree.findall('.//anchor') ]
  #
  # segs = [ Segment((anchor['video'], anchor['start'], anchor['end'])) for anchor in sorted(anchorsDef, key= lambda x: x['video']) ]

  allrecs = readAnchoringResults(trec)
  
  measures = []
  
  def regM(s,m,v):
    measures.append((s,m,v))
  
  regM('all', 'runid', os.path.basename(trec))
  regM('all', 'num_q', len(relSegs))
  
  cnt = 0
  # for each anchor
  for qid, recs in itertools.groupby(allrecs, key=lambda rec: rec['qid']):
    cnt += 1
    recs = list(recs)
    found = False
    
    # calculate MRR
    for rank, rec in enumerate(recs):
      seg = Segment((rec['qid'], rec['start'], rec['end']))
      findings = It.search_seg(seg)
      if findings:
        found = True
        regM(qid,'MRR', 1.0 / (rank+1))
        break
    if not found:
      regM(qid,'MRR', 0.0)

    # calculate missed
    for n in [10,1000]:
      nfound = 0
  
      for rank, rec in enumerate(recs[:n]):
        seg = Segment((rec['qid'], rec['start'], rec['end']))
        findings = ItAll.search_seg(seg)
        if not findings:        
          nfound += 1
          
      regM(qid,'Unjudged_' + str(n), float(nfound))
    
    # calculate precision
    n = 10
    nfound = 0
    found = set()
    for rank, rec in enumerate(recs[:n]):
      seg = Segment((rec['qid'], rec['start'], rec['end']))
      findings = It.search_seg(seg)
      new_found = False
      if findings:        
        for f in findings:
          if not f in found:
            new_found = True
            found.add(f)
      if new_found: nfound += 1
    regM(qid,'P_'+str(n), nfound / float(n))
    
    # calculate recall
    nfound = 0
    found = set()
    n = len(relSegs[qid])
    for rank, rec in enumerate(recs[:n]):
      seg = Segment((rec['qid'], rec['start'], rec['end']))
      findings = It.search_seg(seg)
      new_found = False
      if findings:        
        for f in findings:
          if not f in found:
            new_found = True
            found.add(f)
      if new_found: nfound += 1
    regM(qid,'recall', nfound / float(n))
  
  regM('all', 'num_q_ret', cnt)
    
  #
  # Output
  #
  sums = {}
  lm = max( len(m) for s,m,v in measures )
  ls = max( len(s) for s,m,v in measures )
  sformat = '{measure:%d} {subject:%d} {value:0.5f}' % (lm,ls)
  stformat = '{measure:%d} {subject:%d} {value}' % (lm,ls)
  
  
  for s,m,v in measures:
    if type(v) is str or type(v) is int:
      print stformat.format(
        subject=s,
        measure=m,
        value=v
      )
    else:
      print sformat.format(
        subject=s,
        measure=m,
        value=v
      )
      sums[m] = sums.get(m, 0.0) + v
      
  for m in sums:

    avg = sums.get(m, 0.0) / float(len(relSegs))
    print sformat.format(
      subject='all',
      measure=m,
      value=avg
    )
