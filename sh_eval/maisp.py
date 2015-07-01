import math

class MAiSPCalculator:

  def __init__(self, qrels, user_consumes='rel'):
    self.isp = list()    # interpolated segment precision for each recall point
    self.sp = list()     # segment precision for each recall point
    self.recall_pt = 1   # index of the current recall point
    self.ret_secs = 0    # num of retrieved seconds
    self.rel_ret_secs = 0 # num of retrieved seconds that are relevant
    self.qrels = dict()
    for t in qrels.keys():
      self.qrels[t] = [ (e[1], e[2]) for e in qrels[t] ]
    self.user_consumes = user_consumes
    self.init_recall_points()
    self.relsec_list = list()

  def init_recall_points(self):
    self.recall_pts = list()
    self.rel_secs = 0
    for t in self.qrels.keys():
      self.rel_secs += sum(map(lambda w: max(w[1]-w[0], 0), self.qrels[t]))
    if self.rel_secs > 100:
      d = self.rel_secs / 100.0
      m = self.rel_secs % 100
      self.recall_pts = range(0, self.rel_secs, int(math.floor(d)) if m <= 50 else int(math.ceil(d)))
      self.recall_pts[-1] = self.recall_pts[-1] + m
    else:
      self.recall_pts = range(0, self.rel_secs, 1)
      self.recall_pts.append(self.rel_secs)

  def calc_one(self, trec):
    trans = trec['target'][0]
    stime = trec['target'][1]
    etime = trec['target'][2]
    w = (stime, etime)

    if not self.qrels.has_key(trans):
      self.ret_secs += max(etime - stime, 0)
      return

    # calculate segment's precision and mark relevant content seen by the user
    rels = self.qrels[trans]  # relevant segments (ground truth)
    new_rels = list()    # relevant segments that do not overlap with w
    seen_ret_secs = 0

    for j in range(len(rels)):

      if overlap_windows(rels[j], w):
        over_w = ( max(rels[j][0], w[0]), min(rels[j][1], w[1]) )
        if self.user_consumes == 'rel':
          over_w = (over_w[0], rels[j][1])
        rel_over = max(over_w[1] - over_w[0], 0)
        nrel_over = over_w[0] - w[0]
        self.rel_ret_secs += rel_over
        seen_ret_secs += nrel_over + rel_over
        i = self.recall_pt
        while i < len(self.recall_pts) and self.recall_pts[i] <= self.rel_ret_secs:
          self.sp.append(1.0 * self.recall_pts[i] / \
              (self.ret_secs + seen_ret_secs - (self.rel_ret_secs - self.recall_pts[i])))
          i += 1
        self.recall_pt = i
        # remove the relevant content already seen by the user
        # opt 1: the user consumes the relevant segment
        # opt 2: the user consumes the retrieved segment
        new_rels += substract_window(rels[j], over_w, epsilon=1)
        w = (w[0] + seen_ret_secs, w[1])
      else:
        new_rels.append(rels[j])

    self.ret_secs += max(seen_ret_secs, etime - stime)
    self.qrels[trans] = new_rels

  def calc(self, trecs):
    for trec in trecs:
      self.calc_one(trec)
    self.interpolate()

  def get_iAsp(self):
    return sum([1.0] + self.isp) / len(self.recall_pts) if len(self.isp) > 0 else 0.0

  def get_rel_secs(self):
    return self.rel_secs

  def get_rel_ret_secs(self):
    return self.rel_ret_secs

  def get_ret_secs(self):
    return self.ret_secs

  def get_recall_pts(self):
    return self.recall_pts

  def get_sp(self):
    return self.sp

  def get_isp(self):
    return self.isp

  def interpolate(self):
    self.isp = list()
    for i in range(len(self.sp)):
      self.isp.append( max(self.sp[i:]) )

def substract_window(w1, w2, epsilon=0.01):
  res = list()
  if overlap_windows(w1, w2):
    if w1[0] < w2[0] and w2[1] < w1[1]:
        res.append( (w1[0], w2[0]-epsilon) )
        res.append( (w2[1]+epsilon, w1[1]) )
    elif w1[0] < w2[0]:
        res.append( (w1[0], w2[0]-epsilon) )
    elif w2[1] < w1[1]:
        res.append( (w2[1]+epsilon, w1[1]) )
  else:
    res.append(w1)
  return remove_empty_windows(res)

def overlap_windows(w1, w2):
  w2_in_w1 = w1[0] <= w2[0] and w2[0] <= w1[1]
  w1_in_w2 = w2[0] <= w1[0] and w1[0] <= w2[1]
  return w1_in_w2 or w2_in_w1

def remove_empty_windows(windows, epsilon=0.01):
    return [w for w in windows if w[1] - w[0] >= epsilon]

