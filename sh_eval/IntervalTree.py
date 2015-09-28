#!/usr/bin/env python

class IntervalTree:
	def __init__(self, intervals):
		self.top_node = self.divide_intervals(intervals)
 
	def divide_intervals(self, intervals):
 
		if not intervals:
			return None
 
		x_center = self.center(intervals)
 
		s_center = []
		s_left = []
		s_right = []
 
		for k in intervals:
			if k.get_end() < x_center:
				s_left.append(k)
			elif k.get_begin() > x_center:
				s_right.append(k)
			else:
				s_center.append(k)
 
		return Node(x_center, s_center, self.divide_intervals(s_left), self.divide_intervals(s_right))
	
	def center(self, intervals):
		fs = sort_by_begin(intervals)
		length = len(fs)
 
		return fs[int(length/2)].get_begin()
 
	def search(self, begin, end=None):
		if end:
			result = []
			# was for j in xrange(begin, end+1): // not sure why the +1 is needed
			for j in xrange(begin, end):
				for k in self.search(j):
					result.append(k)
				result = list(set(result))
			return sort_by_begin(result)
		else:
			return [] if self.top_node == None else self._search(self.top_node, begin, [])
      
	def _search(self, node, point, result):
		
		for k in node.s_center:
			if k.get_begin() <= point < k.get_end():
				result.append(k)
		if point < node.x_center and node.left_node:
			for k in self._search(node.left_node, point, []):
				result.append(k)
		if point > node.x_center and node.right_node:
			for k in self._search(node.right_node, point, []):
				result.append(k)
 
		return list(set(result))
 
class Interval:
	def __init__(self, begin, end):
		self.begin = begin
		self.end = end
		
	def get_begin(self):
		return self.begin
	def get_end(self):
		return self.end
 
class Node:
	def __init__(self, x_center, s_center, left_node, right_node):
		self.x_center = x_center
		self.s_center = sort_by_begin(s_center)
		self.left_node = left_node
		self.right_node = right_node
 
def sort_by_begin(intervals):
	return sorted(intervals, key=lambda x: x.get_begin())

class Segment:
  videos = {}
  def __init__(self, segment):
      self.video = segment[0]
      self.start = segment[1]
      self.end = segment[2]
      self.segment = segment
      if self.video in Segment.videos:
        #print self.video, ' already known'
        self.ivideo = Segment.videos[self.video]
      else:
        #print self.video, ' new'
        Segment.videos[self.video] = len(Segment.videos) + 1
        self.ivideo = Segment.videos[self.video]
  def get_begin(self):
      return self.start 
  def get_end(self):
      return self.end
  def get_tuple(self):
    return (self.video, self.start, self.end)
  def includes(self, other):
    return self.get_start() >= other.get_start() and other.get_end() <= self.get_end()
  
  def __repr__(self):
      return ''.join([str((self.ivideo, self.start, self.end))])

from collections import defaultdict
class IT(object):
  def __init__(self, data):
    self.data = defaultdict(list)
    for x in data:
      self.data[x.ivideo].append(x)
    self.tree = {}
    for k,v in self.data.iteritems():
      self.tree[k] = IntervalTree(v)
  
  def search_seg(self, seg):
    if not seg.ivideo in self.tree: return []
    return self.tree[seg.ivideo].search(seg.get_begin(), seg.get_end())   
  
  # def search_seg_inc(self, seg):
  #   return filter(lambda x: x.includes(seg), self.tree.search(seg.get_begin(), seg.get_end()))
    
  def add(self,x):
    self.data[x.ivideo].append(x)
    self.tree[x.ivideo] = IntervalTree(self.data[x.ivideo])
    
  def __repr__(self):
    return '\n'.join([str(s) for s in self.data])

if __name__ == "__main__": 
  '''
  Test segments
  '''
  relevants = [
    Segment(('A', 25, 30)),
    Segment(('B', 1, 20)),
    Segment(('A', 15, 24)),
    Segment(('C', 15, 45)),
  ]

  ranking = [
    Segment(('X', 25, 30)),
    Segment(('A', 1, 10)),
    Segment(('A', 15, 20)),
    Segment(('A', 20, 16)),
    Segment(('A', 25, 45)),
  ]


  TOL = 5
  rels = IT(relevants)
  seen = IT([])
  relString = []
  relevants.sort(key=lambda x: x.get_begin())
  print 'Tolerance', TOL
  for rel in relevants:
    print 'Rel', rel

  for i,r in enumerate(ranking):
    # search segment that extends TOL after the start of the current segment
    search = Segment((r.video, r.start, r.start + TOL))
    r = rels.search_seg(search)
    # if the segment overlaps with a relevant segment
    if r:
      # check if we have already seen the segment
      s = seen.search_seg(search)
      # if the 
      if not s:
        relString.append('r')
        # calculate the longest relevant segment as seen
        end = max(map(lambda seg: seg.end, r))
        end = max(end, search.start + TOL)
        # add to the seen segments
        seen.add(Segment((search.video, search.start, end)))
      else:
        # segment was already seen
        relString.append('s')
    else:
      # doesn't overlap with something relevant => its not relevant
      relString.append('n')
    print 'Rank', i, search, relString[-1]
    
  print relString
  


  # print minutes_from_midnight('11:00AM')
  # T = IntervalTree([ScheduleItem(28374, "9:00AM", "10:00AM"), \
  #                 ScheduleItem(43564, "8:00AM", "12:00PM"), \
  #                 ScheduleItem(53453, "1:00PM", "2:00PM")])
  # print T.search(minutes_from_midnight("1:00PM"))