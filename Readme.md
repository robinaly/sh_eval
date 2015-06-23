# Search and Hyperlinking Evaluation

This repository contains evaluation scripts for the search and hyperlinking task 
(hosted at workshops MediaEval 2011- and TRECVid 2015-). This evaluation script
outputs measurements for anchors and queries in a format that is similar to the
well-known trec_eval script.

Example call (using the provided example data)
```
python sh_eval/sh_eval.py --kind linking test_data/me14sh_linking_testSet.qrel test_data/me14sh_UT-HMI2014_L_1_Sh_U_N.txt.gz
```
or for 
```
python sh_eval/sh_eval.py --kind search test_data/me14sh_linking_testSet.qrel test_data/me14sh_UT-HMI2014_L_1_Sh_U_N.txt.gz
```
Note the following:
* by default --kind linking is assumed (and can therefore be ignored)
* run and relevance files can be also gziped - in which case they have 
  to end with .gz

