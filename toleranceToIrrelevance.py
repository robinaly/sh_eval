#!/usr/bin/env python
from IntervalTree import *
'''
User model: 
 * A user investigates a ranked list of video segments from top to bottom
 * He starts watching videos at the start of the returned segment
 * If he watched the start point before, then he skips to the next segment (counted as non-relevant)
 * If not, he watches until his tolerance level is reached
   * If he encounters relevant content, he watches the content till the end; 
     the segment is counted as relevant
   * Else the segment is counted as non-relevant
'''
def getRelevanceTol(relTree, nonrelTree, seenTree, seg, TOL):
  targetTol = Segment((seg[0], seg[1], seg[1]+TOL))
  target = Segment((seg[0], seg[1], seg[2]))
  #print 'target', target
  rels = relTree.search_seg(targetTol)
  #print rels
  # if the segment overlaps with a relevant segment
  if rels:
    # check if we have already seen the segment
    s = seenTree.search_seg(target)
    # if the 
    if not s:   
      # calculate the longest relevant segment as seen
      end = max(map(lambda seg: seg.end, rels))
      end = max(end, targetTol.start + TOL)
      # add to the seen segments
      seenTree.add(Segment((target.video, target.start, end)))
      return 1
    else:
      return 's'
  else:
    #print 'not in rel'
    nonrels = nonrelTree.search_seg(target)
    if nonrels:
      #print 'in nonrel'
      s = seenTree.search_seg(target)
      if not s:
        #seenTree.add(target)
        return 0
      else:
        return 'S'
    else:
      return '-'

def printConfig(ranking, relSegs, nonrelSegs, tollerance):
  relSegs.sort()
  nonrelSegs.sort()
  
  ranking = map(lambda x: x[1], ranking)
  relSegs = map(lambda x: (x[1],x[2]), relSegs)

  endings = map(lambda x: x[1], relSegs)
  
  size = max(max(ranking), max(endings))+5
  output = [ (list(' ') * size) for i in range(9)]
  print len(output)
  def printAnyNum(line, at, num, growth=1):
    if num >= 10:
      output[line][at] = str(num / 10)
    line += growth
    output[line][at] = str(num % 10)
  
  def printNum(line, num, growth=1):
    printAnyNum(line, num, num, growth)
  
  for seg in relSegs:
    for i in range(seg[0], seg[1]+1):
      output[3][i] = '-'
    printNum(1, seg[0])
    printNum(1, seg[1])
  for i,r in enumerate(ranking):
    output[4][r] = '|'
    printNum(5,r)
    printAnyNum(7,r,i+1)
  
  print '\n'.join(map(lambda x: ''.join(x), output))

def testConfig(ranking, relSegs, nonrelSegs, tollerance):
  relTree = IT([ Segment(s) for s in relSegs ])
  nonrelTree = IT([ Segment(s) for s in nonrelSegs ])
  seen = IT([ ])
  
  rels = []
  for r in ranking:
    rels.append(getRelevanceTol(relTree, nonrelTree, seen, r, tollerance))
  return rels
  
if __name__ == "__main__":
  '''
  Relevance
               1       2       3   3
               5       5       0   5
               ---------       -----
  Ranking
          | | |       |      |
          0 5 1       2      2
              0       3      7
              
  Tolerance: 10
  
  Expected outcome [0, 1, 's', 's', 1]
  '''
  ranking    = [(1, 0, 5), (1, 5, 10), (1, 10, 15), (1, 23, 23), (1, 27, 27) ]
  relSegs    = [(1, 15, 25), (1, 30, 35) ]
  nonrelSegs = [(1, 0, 10)]
  printConfig(ranking, relSegs, nonrelSegs, 10)
  outcome = testConfig(ranking, relSegs, nonrelSegs, 10)
  print outcome
  expectedOutcome = [0, 1, 's', 's', 1]
  if outcome != expectedOutcome: raise ValueError("Wrong outcome")
  
  ranking    = [(1, 8, 5), (1, 5, 10), (1, 10, 15), (1, 23, 23), (1, 27, 27) ]
  relSegs    = [(1, 15, 25), (1, 30, 35) ]
  nonrelSegs = [(1, 0, 10)]
  printConfig(ranking, relSegs, nonrelSegs, 10)
  outcome = testConfig(ranking, relSegs, nonrelSegs, 10)
  print outcome
  expectedOutcome = [1, 's', 's', 's', 1]
  if outcome != expectedOutcome: raise ValueError("Wrong outcome")

  ranking    = [(1, 8, 12), (1, 20, 30) ]
  relSegs    = [(1, 5, 10), (1, 12, 30) ]
  nonrelSegs = []
  printConfig(ranking, relSegs, nonrelSegs, 10)
  outcome = testConfig(ranking, relSegs, nonrelSegs, 10)
  print outcome
  expectedOutcome = [1, 's']
  if outcome != expectedOutcome: raise ValueError("Wrong outcome")

  