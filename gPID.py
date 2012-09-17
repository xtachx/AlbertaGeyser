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
class gPID():
    def __init__(self):
        #This is the data we need from the user
        self.SetPoint = 0.0
        self.SampleTime = 1.0
        #This is the data we need, but we can start with an initial guess
        self.kp = 1.176   #Proportional constant Kp
        self.ki = 0.0033  #Integral Gain Kp/Ti
        self.kd = 102.9   #Derivative Gain Kp*Td
        #this is what we generate
        self.Output = 0.0 
        #and this is what we use during our computation
        self.errSum = 0
        self.lastErr = 0
        
        
    #This routine computes the PID Values
    def Compute(self,Input):
        #Compute the error, and update sum:
        error = self.SetPoint - Input
        self.errSum += error
        #compute the derivative dErr
        dErr = error - self.lastErr
        #Compute PID Output
        self.Output = self.kp*error + self.ki*self.errSum + self.kd*dErr
        