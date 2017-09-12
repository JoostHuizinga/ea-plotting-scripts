#!/usr/bin/env python
import argparse as ap
import random

parser = ap.ArgumentParser()
parser.add_argument('output', type=str, nargs='?', default="file",
help='The base name of the output file to write the data to.')
parser.add_argument('slope', type=float, nargs='?', default=0.03,
help='How fast the value increases for this set of data.')
parser.add_argument('number', type=int, nargs='?', default=1,
help='The number of files to generate at this time.')
args = parser.parse_args()

basename = args.output
slope = args.slope
number = args.number
for i in xrange(number):
    v = 0
    with open(basename + str(i) + ".dat", 'w') as f:
        for x in xrange(0, 101):
            f.write(str(x) + " " + str(v) + "\n")
            v = min(v + random.random() * slope, 1.0)

