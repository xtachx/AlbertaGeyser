#!/usr/bin/env python
#################################################################
#This is the State Machine of the Geyser Contol Ops             #
#Eventually we may build a web based GUI, but dont count on it! #
#Made by Pitam Mitra for PICASSO detector R&D                   #
#Released under GNU GPL                                         #
#################################################################

#Ok so I have given this a lot of thought about this program. FSMs, or
#Finite state machines are not supposed to run in a "superloop" like we are
#doing at the moment. We should be using Event based triggers ala
#Twisted.internet. So I will attempt to redo the entire thing
#based on twisted.

#we need the reactor from twisted.internet, and the protocol
#factory for our server.
from twisted.internet import reactor, protocol, task, threads, defer

#import time module for sleep functions
import time

#import the Finite State Machine class
from StateMachineCore import FSM

#import the stability class and make an object for controlling
from Stability import CheckStablity

#import sys for some extra functions like the status print to CLI etc
import sys

#Arduino Geyser control protocol
import GeyserProto as GP

#import PID MODULE
from gPID import gPID

#numpy module for averaging
import numpy as np

#this is for the SQL updates
import UpdateSQLdbA as AuSQL


#Some HariKari measures in case stuff goes wrong...
#Seriously, this kills the whole Control system!
def killall():    
    GP.HeaterControl(0)
    reactor.stop()

class GeyserEvent():
    
    def __init__(self):
        self.isStable = True
        self.LeadAvg = 1.0
        self.TrailAvg = 0.0
        self.TemperatureData = []
        self.Pressure = 0.0
        
        self.gPID = gPID()
        
        #####
        self.step = 9
        self.interval = 2
        self.setPoint = 0.0
        ####
        self.Initialize()
        self.CheckStablity = CheckStablity(self.step,self.interval)
        AuSQL.CleanTables()
        self.dataRecorder = AuSQL.DataRecorder()
        ####
        
        ####
        
        ####RunDataRecorder Params####
        RunNumber = 0
    
    def UpdateDispatcher(self):
        if self._isRunning == True:
            l = task.LoopingCall(self.UpdateVars)
            l.start(1.0)
            m = task.LoopingCall(self.SQLInterrupts)
            m.start(1.0)
            
    def setRunNumber(runList):
        return int(runList[:-1])
    
    BoxCarSize = lambda self : 2*self.step + self.interval
    
    def RunStabilityCheck(self):
        StabilityStatus = defer.Deferred()
        StabilityAnalysisResult = self.CheckStablity.DetectEventAndAnomaly(self.LeadAvg, self.TrailAvg)
        StabilityStatus.callback(StabilityAnalysisResult)
        return StabilityStatus
    
    def StabilityAnalysis(self, StabilityResponse):
        if StabilityResponse == 1:
            print "StabilityResponse - Geyser is Unstable!!", repr(StabilityResponse)
            self.gPID.ChangeSetPoint(0)
    
    def StabilityWrapper(self):
        Status = self.RunStabilityCheck()
        Status.addCallback(self.StabilityAnalysis)
    
    def UpdateVars(self):
        #Update the temperature variables!
        self.TemperatureData.append(GP.getcFP())
        self.TemperatureData.pop(0)
        self.TrailAvg = np.average(self.TemperatureData[:self.step])
        self.LeadAvg = np.average(self.TemperatureData[-self.step:])
        #Update Pressure Variable
        self.Pressure = GP.getPressure()
        #Call stability check
        
        reactor.callWhenRunning(self.StabilityWrapper)
        #get PID Value
        PIDValue = self.gPID.Compute(float(self.LeadAvg))
        #write PID Value
        GP.HeaterControl(PIDValue)
        sys.stdout.flush()
        sys.stdout.write("\rTemperature: %.02f | PID: %.01f | Pressure: %.01f" % (self.LeadAvg, PIDValue, self.Pressure))
    
    def Initialize(self):
        self.TemperatureData += [float(GP.getcFP())] * self.BoxCarSize()
    
    def SetPointInterruptCallback(self, SP):
        NewSP = float(SP)
        if NewSP != self.setPoint:
            self.gPID.ChangeSetPoint(NewSP)
            self.setPoint = NewSP
            print "Set Point Changed"

    def SQLInterrupts(self):
        AuSQL.AUpdateSQLPool(self.LeadAvg, self.Pressure)
        AuSQL.AGetUserInterrupt().addCallback(self.SetPointInterruptCallback)
        
        
GeyserEventDispacher = GeyserEvent()
#reactor.callWhenRunning(GeyserEventDispacher.Initialize())
reactor.run()
