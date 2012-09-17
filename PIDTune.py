#!/usr/bin/env python

#This file implements an automatic tuning of PID Algorithms.
import PIDbase
import time
import TempDaemonFPOptomux
import GeyserProto as GP
import numpy as np
import matplotlib.pyplot as plt
import sys



class PIDProcess():
    def __init__(self):

        self.pid_control = PIDbase.PID()
        self.pid_control.Kp=1.176
        self.pid_control.Ki=0.0033
        self.pid_control.Kd=102.9

        #Params
        self.T_Memory_size = 30 #MUST be > binSize*2+interval!!
        self.averageSampleSize = 10 #keep this SMALL!!
        self.T_Memory  = np.array(())
        
        self.approachStable = False
        self.TimerStart = 0
        
        self.pid_control.set_point = 110.0
        self.start_point = TempDaemonFPOptomux.Read_TC_once("0004")
        #######################3Crit points
        
        self.DeadTimePredicted = False
        self.DeadTime = 0.0
        self.TimeConstantPredicted = False
        self.TimeConstant = 0.0

        
        ##########plot params
        self.x = np.array((0,20))
        self.y = np.array((0,40))

        # You probably won't need this if you're embedding things in a tkinter plot...
        plt.ion()

        self.fig = plt.figure()
        self.ax = self.fig.add_subplot(111)
        self.line1, = self.ax.plot(self.x, self.y, 'r.') # Returns a tuple of line objects, thus the comma
        
        self.lastFakeData=22.0

        
    def DataFaker(self):
        self.lastFakeData+=.2
        return self.lastFakeData
    

    def stop(self):
        GP.HeaterControl(0)
        print "Stopped"
        sys.exit("Overheat. Stopped.")
    
    def getTemperature(self):
        if len(self.T_Memory) < self.T_Memory_size-1:
            sys.stdout.flush()
            sys.stdout.write("\rFilling memory, please wait. %d / %d" % (len(self.T_Memory),self.T_Memory_size) )
        if len(self.T_Memory) == self.T_Memory_size-1:
            print("\nMemory Load complete.")
        new_data = TempDaemonFPOptomux.Read_TC_once("0004")
        #new_data = self.DataFaker()
        if len(self.T_Memory) <= self.T_Memory_size:
            self.T_Memory=np.append(self.T_Memory, new_data)
            
            return self.getTemperature()
            #print self.T_Memory
        else:
            self.T_Memory=np.append(self.T_Memory, new_data)
            self.T_Memory=np.delete(self.T_Memory, 0)
        
        
    def MeasureCritPoints(self):
        if self.DeadTimePredicted == False:
            if self.T_Memory[:-1]>=self.start_point + 1:
                self.DeadTime = self.T_Memory[:-1]
                self.DeadTimePredicted = True
                print "Dead Time: "+str(self.DeadTime)
                
        if self.TimeConstantPredicted == False:
            if self.T_Memory[:-1]>=self.start_point+(self.pid_control.set_point - self.start_point)/3 :
                self.TimeConstant = self.T_Memory[:-1]
                self.TimeConstantPredicted = True
        
        
    def Constrain(self, input, min, max):
        if input <= min:
            return min
        elif input >= max:
            return max
        else:
            return input
    
    def RunPIDonce(self,measurement_value):
        pid_raw = self.pid_control.update(measurement_value)
        pid = self.Constrain(pid_raw,0.0,100.0)
        sys.stdout.flush()
        sys.stdout.write("\rPID RAW: %.02f | PID: %.02f | Temperature: %.02f" %(pid_raw,pid,measurement_value))
        if measurement_value >= self.pid_control.set_point+30.0:
            self.stop()
        GP.HeaterControl(pid)
        
    def IsProcessStable(self):
        rampUpFlag = False
        self.RunPIDonce(self.T_Memory[-1:])
        T_Average_val = np.average(self.T_Memory[-self.averageSampleSize:])
        if T_Average_val >= self.pid_control.set_point-1 and T_Average_val <=self.pid_control.set_point + 1:
            self.approachStable = True
        else:
            self.approachStable = False
            self.TimerStart = 0
            
        if self.approachStable:
            self.TimerStart += 1
            if self.TimerStart >= 30:
                return 0.0
        return 1.0
    
    def PlotAnim(self):
        x_data = np.arange(0,len(self.T_Memory),1)
        y_data = self.T_Memory
        self.line1.set_xdata(x_data)
        self.line1.set_ydata(y_data)
        self.fig.canvas.draw()
        
    def RUNCalib(self):
        self.getTemperature()
        checkStable = self.IsProcessStable()
        self.PlotAnim()
        time.sleep(1)
        return 0
        
    
def ZeiglerNichols():
    calibrate_PID =  PIDProcess()
    x_range = xrange(0,100)
    while True:
        calib_status = calibrate_PID.RUNCalib()
    
ZeiglerNichols()  

#while True:
#    pid = pid_control.update(measurement_value)


    
#print getTemperature()