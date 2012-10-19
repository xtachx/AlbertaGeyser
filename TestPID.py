#!/usr/bin/env python

import gPID
import numpy.random as random
import time

a = gPID.gPID()

a.ChangeSetPoint(60)


print a.Compute(20)
time.sleep(1.1)
print a.Compute(20)
time.sleep(1.1)
print a.Compute(20)
time.sleep(1.1)
print a.Compute(20)
time.sleep(1.1)
print a.Compute(20)


def SeePID(start):
    
    bbb = start
    for i in xrange(1,150):
        print "---------------------------------"
        print "Input: "+str(bbb)
        PIDout = a.Compute(bbb)
        print PIDout
        bbb += PIDout*random.random()/10
        time.sleep(1.1)

SeePID(20)