#!/usr/bin/env python
"""
This script checks the validity of a run submission to the Media Eval Search and Hyperlinking Task 
or TRECVid Hyperlinking Task.

Author: Robin Aly <r.aly@utwente.nl>
Date: 30-06-2016


"""
import sys, re, os, collections,gzip, random
from utils import *
from optparse import OptionParser
import itertools


def randomize(opt, out_fn):
  anchors, anchorDefinitions = loadAnchors(opt.task)
  videoFiles, blacklist = loadVideoFiles(opt.task)
  files = videoFiles.keys()
  with do_open(out_fn, 'w') as f:
    for anchor in anchors:
      for i in range(opt.rank):
        v = random.sample(files, 1)[0]
        s, length = videoFiles[v]
        start = random.randint(0, length)
        dur = random.randint(8, 130)
        end = start + dur
        f.write("{anchor} Q0 {video} {start} {end} {rank} {score:.3e} {run}\n".format(
          anchor = anchor,
          video = v,
          start = sec2String(start),
          end = sec2String(end),
          rank = str(i+1),
          score = 1.0 / (i+1),
          run = 'test'
        )) 

def main():
  parser = OptionParser(usage="usage: %prog [options] submission-file outptut-submission-file" )
  parser.add_option("-t", "--task", dest="task", help=".", metavar="task", default='tv16lnk')
  parser.add_option("-r", "--rank", dest="rank", help=".", metavar="rank", default='100')
  (opt, args) = parser.parse_args()  
  opt.rank = int(opt.rank)
  out_fn, = args
  
  randomize(opt, out_fn)

if __name__ == '__main__':
  main()
