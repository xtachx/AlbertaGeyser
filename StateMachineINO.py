#!/usr/bin/env python
#################################################################
#This is the State Machine of the Geyser Contol Ops             #
#Eventually we may build a web based GUI, but dont count on it! #
#Made by Pitam Mitra for PICASSO detector R&D                   #
#Released under GNU GPL                                         #
#################################################################
#import time module for sleep functions
import time

#import the Finite State Machine class
from StateMachineCore import FSM

#import the stability class and make an object for controlling
from Stability import CheckStablity

#import sys for some extra functions like the status print to CLI etc
import sys

#These 2 are needed for the emergency Hari-Kari measure if things explode
import psutil, os

#this is to get the pressure from voltage
import ConvertVoltageToPressure as V2P

#Arduino Geyser control protocol
import GeyserProto as GP

#Function to run when Heat state transition is triggered
def onHeatState(e):
    #S96_instance.ReadPV()
    #while Update_State:
    #GeyserFSM.isAOK()
    if hasattr(e, 'msg'):
        print "Heating. Set Solo controller to heat, to: "+str(e.msg)
        S96_instance.SetPV(PV=float(e.msg), IsRead=False)
    else:
        print "Heating. Set Solo controller to heat"
        S96_instance.SetPV(PV=80.0, IsRead=False)

#Function to run when cool state transition is triggered
def onCoolstate(e): 
    #S96_instance.ReadPV()
    print "Cooling. Set Solo controller to 0!"
    S96_instance.SetPV(PV=0.0, IsRead=False)

#Function to run when Stable state transition is triggered
def onStableState(e):
    print 'Stable, set Solo controller to maintain temperature!'
    Solo_Current_Value=S96_instance.ReadPV()
    S96_instance.SetPV(PV=Solo_Current_Value+2.0, IsRead=False)

#Function to run when Unstable state transition is triggered
def onUnstableState(e):
    print 'Set Solo controller to 0 and set cooling tower to max'
    S96_instance.SetPV(PV=0.0, IsRead=False)

#Function to run when HardwareError state transition is triggered
def onHardwareError(e):
    print 'Crap and crap out I guess.'
    S96_instance.SetPV(PV=00.0, IsRead=False)

#This is where the stte machine is defined
#the state machine is automatically created from the transitions
#table provided to it.
#whenever, a change of state / transition is triggered, it will auto launch
#the start program of the dst state and stop program of src state.
GeyserFSM = FSM({
'initial': 'stable',
'events': [
{'name': 'SetCooling', 'src': ['heating','stable'], 'dst': 'cooling'},
{'name': 'SetStable', 'src': ['heating','cooling'], 'dst': 'stable'},
{'name': 'SetPanic', 'src': ['heating','cooling','stable'], 'dst': 'unstable'},
{'name': 'SetHeating', 'src': ['stable','heating','cooling','unstable'], 'dst': 'heating'},
{'name': 'SetHwerror', 'src': ['heating','cooling','stable','unstable'], 'dst': 'HardwareError'},
],
'callbacks': {
'onSetPanic': onUnstableState,
'onSetHeating': onHeatState,
'onSetCooling': onCoolstate,
'onSetStable': onStableState,
'onHwerror': onHardwareError
}
})


#Some HariKari measures in case stuff goes wrong...
#Seriously, this kills the whole Control system!
def killtree(pid, including_parent=True):    
    parent = psutil.Process(pid)
    for child in parent.get_children():
        child.kill()
    if including_parent:
        parent.kill()

#The governor function governs the process of the transitions between the
#states of the Finite State Machine. It decides if a transition should be
#triggered and triggers it.
def Governor(SetTemp, step, interval, leadAVG, trailAVG, parent_pid, SystemState, HeatCTower, PressureVoltage):
    #We define an object which checks the stability of the system before anything
    StabilityHelper = CheckStablity(step.value, interval.value)
    StabilityStatus = 0
    
    #Dont know why I have this here, I guess in case we want to stop everything?
    RunGovernor = True
    #...
    while RunGovernor:    
        #So, first we check if we are stable. If not, transition to unstable
        if GeyserFSM.current == "heating" or GeyserFSM.current=="stable" or GeyserFSM.current == "cooling":
            StabilityStatus = StabilityHelper.DetectEventAndAnomaly(leadAVG.value, trailAVG.value)
            if StabilityStatus == 1:
                print "Panic Issued!"
                GeyserFSM.SetPanic()
                HeatCTower.value = 0
        
        #If we are heating, then check if we can transition to anything else.
        if GeyserFSM.current == "heating":
            #set global status
            SystemState[0] = "h"
            #Transition Heating -> stable
            if leadAVG.value >= SetTemp.value-2.0 and leadAVG.value<=SetTemp.value+3.0:  #if the geyser temp > Set temp
                GeyserFSM.SetStable()
                HeatCTower.value = 1
            #Transition Heating -> cooling
            if leadAVG.value > SetTemp.value +3.0 :
                GeyserFSM.SetCooling()
                HeatCTower.value = 0
        
        #If we are stable, then check if we can transition to anything else.
        if GeyserFSM.current == "stable":
            #set global status
            SystemState[0] = "s"
            #Transition Stable -> Heating
            if leadAVG.value < SetTemp.value-2.0: 
                GeyserFSM.SetHeating(msg=SetTemp.value+2.0)
                HeatCTower.value = 1
            #Transition Stable -> cooling
            if leadAVG.value > SetTemp.value+3.0:
                GeyserFSM.SetCooling()
                HeatCTower.value = 0

        #If we are cooling, then check if we can transition to anything else.        
        if GeyserFSM.current == "cooling":
            #set global status
            SystemState[0] = "c"
            #Transition Cooling -> Stable
            if leadAVG.value >= SetTemp.value and leadAVG.value<SetTemp.value+3.0: 
                GeyserFSM.SetStable()
                HeatCTower.value = 1
            #Transition Cooling -> Heating
            if leadAVG.value <= SetTemp.value-3.0:
                GeyserFSM.SetHeating(msg=SetTemp.value+2.0)
                HeatCTower.value = 1
        
        #If we are unstable, then check if we can transition to anything else.
        if GeyserFSM.current == "unstable":
            #set global status
            SystemState[0] = "u"
            #Transition State Unstable --> Explosion
            #On explosion, probe should read atmospheric temperature, i.e. below 25C
            if leadAVG.value < 35:
                print "Something serious has happened! Stopping Run!"
                killtree(parent_pid)
            #Transition Unstable -> Heating
            if leadAVG.value < 55:
                GeyserFSM.SetHeating(msg=SetTemp.value+2.0)
                HeatCTower.value = 1
        
        Pressure = V2P.Voltage2Pressure(PressureVoltage.value)
        #The next few lines displays the status in CLI. Its not required,
        #but an extra feature. Comment it out if you dont want it!
        sys.stdout.flush()
        #sys.stdout.write("\rSystem State: "+str(GeyserFSM.current)+" Set: "+str(SetTemp.value)+" Current: "+str(leadAVG.value)+" P Transducer: "+str(PressureVoltage.value)+" Remark: ")
        
        sys.stdout.write("\rSystem State: "+str(GeyserFSM.current)+" Set: %.02f Current: %.02f P Transducer: %.03f Remark: " %(SetTemp.value, leadAVG.value, Pressure,) )
        #Wait 1 second before next round
        time.sleep(1)
    
