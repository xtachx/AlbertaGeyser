#!/usr/bin/env python

#Geyser PID Control module for heating.
#Made by Pitam Mitra for the PICASSO R&D Project.
#From http://brettbeauregard.com/blog/2011/04/improving-the-beginner%E2%80%99s-pid-sample-time/

#This is not the basic PID Module, for controlling the geyser. This has
#several different additions to it, such as "time correction", "derivative kick"
#etc etc.

#The geyser PID Class. BTW, why is this an OO program
#and not procedural? Simply put, the PID processes
#a LOT of data, and so an OO is more suited
#than procedural.

#we need the time module to keep a track of the time change
#DO NOT USE BLOCKIG CALLS LIKE time.sleep!!!!
import time


class gPID():
    def __init__(self):
        #This is the data we need from the user
        self.SetPoint = 0.0
        self.SampleTime = 1.0
        self.lastTime = time.time()
        #This is the data we need, but we can start with an initial guess
        self.kp = 1.576   #Proportional constant Kp
        self.ki = 0.033  #Integral Gain Kp/Ti
        self.kd = 30.29   #Derivative Gain Kp*Td
        
        self.outMin = 0.0
        self.outMax = 100.0
        #this is what we generate
        self.Output = 0.0 
        #and this is what we use during our computation
        self.lastInput = 0.0
        self.ITerm = 0.0
        self.inAuto = True
        
        self._MANUAL = 0
        self._AUTOMATIC = 1
        self.isInitialized = False
        
        #To prevent integral windup, we need this
        self.Integral = []
        self.IntegralHisterisis = 10
        self.IntegralLimit = [-63, 63]
    
    def UpdateIntegral(self, data):
        data = float(data)
        if (len(self.Integral)) < self.IntegralHisterisis:
            self.Integral.append(data)
        if (len(self.Integral) >=self.IntegralHisterisis):
            self.Integral.append(data)
            self.Integral.pop(0)
        
        return sum(self.Integral)
        
        #if sum(self.Integral) >= self.IntegralLimit[1]:
        #    return self.IntegralLimit[1]
        #elif sum(self.Integral) <= self.IntegralLimit[0]:
        #    return self.IntegralLimit[1]
        #else:
        #    return sum(self.Integral)
    
    
        
        
        
    #This routine computes the PID Values
    def Compute(self, Input):
        #check if we are in manual mode
        if(self.inAuto == False): return
        #did we "resume"?
        if self.isInitialized == True:
            self.lastInput = Input
            self.ITerm = Output
            if self.ITerm > self.outMax:
                self.ITerm = self.outMax
            elif self.ITerm < self.outMin:
                self.ITerm = self.outMin
            self.isInitialized = False
        #store the time now here
        timeNow = time.time()
        timeDelta = timeNow - self.lastTime
        if(timeDelta >=self.SampleTime):
            #Compute the error, and update sum:
            error = self.SetPoint - Input
            errSum = error*timeDelta
            self.ITerm = self.UpdateIntegral(self.ki*errSum)
            
            
            if self.ITerm > self.outMax:
                self.ITerm = self.outMax
            elif self.ITerm<self.outMin:
                self.ITerm = self.outMin
            #compute the derivative input
            dInput = Input - self.lastInput
            #Compute PID Output
            self.Output = self.kp*error + self.ITerm - self.kd*dInput
            if self.Output > self.outMax:
                self.Output = self.outMax
            elif self.Output<self.outMin:
                self.Output = self.outMin
            
            #Remember some variables for the next time
            self.lastInput = Input
            self.lastTime = time.time()
        #return PID value
        return self.Output
    
    def SetTunings(self, new_kp, new_ki, new_kd):
        self.kp = new_kp
        self.kd = new_kd
        self.ki = new_ki
        
    def SetSampleTime(self, NewSampleTime):
        if (NewSampleTime > 0):
            ratio = NewSampleTime / self.SampleTime
            self.ki *= ratio
            self.kd /= ratio
            self.SampleTime = NewSampleTime
            
    def SetOutputLimits(self, outMin, outMax):
        if (outMin>outMax):
            return
        self.outMin = outMin
        self.outMax = outMax
        
        if self.Output > self.outMax:
            self.Output = self.outMax
        elif self.Output < self.outMin:
            self.Output = self.outMin
        
        if self.ITerm > self.outMax:
            self.ITerm = self.outMax
        elif self.ITerm < self.outMin:
            self.ITerm = self.outMin
        
    def SetMode(self, mode):
        newAuto = (mode == self._AUTOMATIC)
        #if we go from manual to automatic
        if newAuto and (self.inAuto == False):
            self.Initialize()
        self.inAuto = newAuto
        
    def ChangeSetPoint(self, newSetPoint):
        self.SetPoint = float(newSetPoint)
    
    