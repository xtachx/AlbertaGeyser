#!/usr/bin/env python

#This module can read data directly from the Arduino!
#it uses the serial protocol

#import serial for serial communications
import serial, time
import GeyserProto as GP

def ControlArduino(TempDataInStream, DaemonRunFlag, PressureVoltage):
    while True:
        #get some data now!
        temperature_celcius = float(GP.getTemperature())
        
        #put this to the queue
        TempDataInStream.put(temperature_celcius)
        
        #get the pressure transducer data and put that on memory
        PressureVoltage.value = float(GP.getPressure())
        
        
        
        #This routine checks if the stop flag is raised, and puts it in
        #variable "runflag" to stop the loop
        if DaemonRunFlag.qsize() != 0:
            if DaemonRunFlag.get(timeout=1) == True:
                RunFlag = False
                
        time.sleep(1)    
    
    
    
    
    
