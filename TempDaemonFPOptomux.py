#!/usr/bin/env python

#This module can read data directly from the thermocouples in the
#cFP-TC-120 and give out the temperature value.
#it uses the optomux protocol

#import serial for serial communications
import serial, time

#a function for the checksum
def CheckSum(string):
    split_string = list(string)
    sum = 0
    for charecter in split_string:
        sum+=ord(charecter)
    modulo=sum%256
    chksum = hex(modulo)[2:]
    return chksum.upper()


def Read_TC(TempDataInStream, DaemonRunFlag, DeviceID):  
    #open serial
    device = serial.Serial(port=2,baudrate=115200, bytesize = 8, timeout = 1, rtscts=False)
    #construct the command to send
    cmd_string = "04!F"+str(DeviceID)
    #calculate checksum
    checksum_string = CheckSum(cmd_string)
    #finally construct the string to be sent
    send_string = ">"+cmd_string+checksum_string+"\r\n"
    
    while True:
        #get some data now!
        device.write(send_string)
        response = device.read(9)
        #strip the checksum and the "A" and CR LF
        data_response=response[1:5]
        #calculate temperature
        try:
            temperature_celcius = float(int(data_response,16))*(2040.0/65535.0)-270.0
        except:
            device.read(4)
            temperature_celcius = 0.0
        #put this to the queue
        TempDataInStream.put(temperature_celcius)
        
        
        #This routine checks if the stop flag is raised, and puts it in
        #variable "runflag" to stop the loop
        if DaemonRunFlag.qsize() != 0:
            if DaemonRunFlag.get(timeout=1) == True:
                RunFlag = False
                
                
    ##Note: I did not put time.sleep. its not needed, the ADC cant work faster than 1Hz.
    
def Read_TC_once(DeviceID):
    #open serial
    device = serial.Serial(port='/dev/ttyS2',baudrate=115200, bytesize = 8, timeout = 1, rtscts=False)
    #construct the command to send
    cmd_string = "04!F"+str(DeviceID)
    #calculate checksum
    checksum_string = CheckSum(cmd_string)
    #finally construct the string to be sent
    send_string = ">"+cmd_string+checksum_string+"\r\n"
    
    #get some data now!
    device.write(send_string)
    response = device.read(9)
    #strip the checksum and the "A" and CR LF
    data_response=response[1:5]
    #calculate temperature
    try:
        temperature_celcius = float(int(data_response,16))*(2040.0/65535.0)-270.0
    except:
        device.read(4)
        temperature_celcius = 0.0
        #put this to the queue
    return temperature_celcius
    