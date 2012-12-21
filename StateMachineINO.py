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
        self.PIDVal = 0
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
        self._isRunning = False
        runDispatcher = task.LoopingCall(self.UpdateDispatcher)
        runDispatcher.start(0.1)
        ####
        procDispatcher = task.LoopingCall(self.ProcessDispatcher)
        procDispatcher.start(1)
        ####
        self.writeHalt = False
        
        ####RunDataRecorder Params####
        RunNumber = 0
    
    def ProcessDispatcher(self):
        if self._isRunning == True:
            reactor.callWhenRunning(self.UpdateVars)
        
    def UpdateDispatcher(self):
        reactor.callWhenRunning(self.SQLInterrupts)
        if self._isRunning == True:
            #reactor.callWhenRunning(self.UpdateVars)
            self.Pressure = GP.getPressure()
            reactor.callWhenRunning(self.dataRecorder.UpdateDatapoint, self.LeadAvg, self.Pressure)
            sys.stdout.flush()
            sys.stdout.write("\rTemperature: %.02f | PID: %.01f | Pressure: %.01f" % (self.LeadAvg, self.PIDVal, self.Pressure))
        
    
    def changeRun(self):
        self._isRunning = False
        onSetTable = self.dataRecorder.makeNewRun(self.setPoint)
        onSetTable.addCallback(self.setRunNumberandStart)

            
    def setRunNumberandStart(self, RunNumber):
        print "Set new run number success; Run# "+ str(RunNumber)+" is now live!"
        self.RunNumber = RunNumber
        self._isRunning = True
        return None
    
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
        #self.Pressure = GP.getPressure()
        #Call stability check
        
        reactor.callWhenRunning(self.StabilityWrapper)
        #get PID Value
        PIDValue = self.gPID.Compute(float(self.LeadAvg))
        
        if int(PIDValue) != int(self.PIDVal) :
            #write PID Value
            GP.HeaterControl(PIDValue)
            self.PIDVal = PIDValue
        
    
    def Initialize(self):
        self.TemperatureData += [float(GP.getcFP())] * self.BoxCarSize()
    
    def SetPointInterruptCallback(self, SP):
        NewSP = float(SP)
        if NewSP != self.setPoint:
            self.gPID.ChangeSetPoint(NewSP)
            self.setPoint = NewSP
            print "Set Point Changed, new run started by SetPointChange!"
            #self.changeRun()
    
    def ONOFFCallback(self, new_instruction):
        NewInstruction = bool(new_instruction)
        if NewInstruction != self._isRunning:
            if NewInstruction == False:
                self.setPoint = 0.0
                self.UpdateVars()
            self._isRunning = NewInstruction
            print "Detector status has been toggled. New run started by OGetInterrupt...!"
            if NewInstruction == True:
                self.changeRun()

    def SQLInterrupts(self):
        AuSQL.AUpdateSQLPool(self.LeadAvg, self.Pressure)
        AuSQL.AGetUserInterrupt().addCallback(self.SetPointInterruptCallback)
        AuSQL.OGetUserInterrupt().addCallback(self.ONOFFCallback)
        
        
GeyserEventDispacher = GeyserEvent()
#reactor.callWhenRunning(GeyserEventDispacher.Initialize())
reactor.run()
