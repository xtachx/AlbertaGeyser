#!/usr/bin/env python

#This will need tons of documentation, but we will try to address all of it
#as we go and in documents we write later.
#
#This is the Service Module / Server for the geyser hardware control.
#It is written in TwistedMatrix for Python, a framework for ASYNC programming.
#
#CAUTION: DO NOT USING BLOCKING METHODS IN THIS! The AsyncReactor expects
#NON-BLOCKING commands STRICTLY. Refrain from using things like:
#
#time.sleep(t)
#
#These commands will block the reactor, and the async program will malfunction!

#we need the reactor from twisted.internet, and the protocol
#factory for our server.
from twisted.internet import reactor, protocol, task

#serial port implementation
from twisted.internet.serialport import SerialPort

#Twisted basic protocol implementations
from twisted.protocols.basic import LineReceiver, NetstringReceiver

#this module converts our ADC voltage values to pressure
from ConvertAtmelADCtoPressure import ADC2Pressure as A2P


#serial port definition
SerialPortAddress = '/dev/ttyACM0'

#This is the protocol which defines how to "talk" to the arduino board
#running the geyser. It is very simple, and constructed
#from twisted.protocols.basic
class GeyserProtocol(LineReceiver):
    
    #first, since this is the thing that sits right behind the transport,
    #we would want it to get a callback associated with it, so when it gets
    #data, it "calls home" with it.
    def __init__(self, callback):
        self.callback = callback
        
    #This is what is does when connection is established. Right now,
    #sitting here for debugging reasons
    def connectionMade(self):
        print 'Connected to Arduino'
        
    #this defines what to do, when you want to send a line.
    #it just sends the line ot the transport WITH delimiter "\r\n"
    def sendLine(self, line):
        print "Transport Start, sending ", repr(line)
        self.transport.write(line)
    
    #this defines what to do when transport gives some data which was received
    #it essentially "calls home" to tell about it!
    def lineReceived(self, line):
        self.callback(line)
        
    #What to to when connection is lost or closed. If in future, you want to
    #issue a recovery method for serial disconnection, use this
    def connectionLost(self, reason):
        print "connection lost, reason: ", repr(reason)
########################################################

#This is the protocol, which talks over the internet
#to other threads, requesting info. We use netstrings, as they are a viable
#way to communicate between the server and client. Our protocol is simple,
#instead of using AMP or Perspective Broker, we can use this simple but
#genius RPC like method from krondo. (Hell, one day for giggles I want to write
#this whole thing in OSCAR bwahaha)


class OutboundProtocol(NetstringReceiver):
    
    #this is what we do when we receive strings.
    def stringReceived(self, request):
        #check for the "." in te string
        if '.' not in request:
            self.transport.loseConnection("Bad Request")
            return
        #separate the "." and the 2 parts and send it for processing
        request_name , request_value = request.split('.', 1)
        self.processRequest(request_name, request_value)
    
    #You might be wondering, why we are doing this redundant step. We could
    #have sent the request directly to the factory! Yes, we could. But
    #the work of the protocol is to RESPOND as well. 
    def processRequest(self, request_name, request_value):
        responseFromProcess = self.factory.processRequest(request_name, request_value)
        #if there is a response, send it to transport.
        if responseFromProcess is not None:
            self.sendString(responseFromProcess)
        #and close the connection
        self.transport.loseConnection()
    
        
    #def connectionMade(self):
    #    self.transport.write(str(self.factory.temperature))
    #    self.transport.loseConnection()

#This is the service which writes data to the board
class GeyserService(object):
    
    def WriteToDevice(self, Device, what):
        reactor.callWhenRunning(self.Device.sendLine, what)

#This is the protocol factory, which constructs the outbound service.
#Note, the hardware bound service "calls back" here to report
#on new variables coming in, so this is where the data is stored.

class OutboundFactory(protocol.ServerFactory):
    
    #specify the internet side protocol
    protocol = OutboundProtocol
    
    #initializer, manages memory and hardware device callbacks
    def __init__(self, SerialPortAddress, reactor):
        
        #allocate space for temperature
        self.temperature = 0
        self.pressure = 0
        
        #Assign a device i.e. the hardware
        self.Device = GeyserProtocol(self.AssignFromCallback)
        
        #assign a transport to the hardware i.e. serial
        self.transport = SerialPort(self.Device, SerialPortAddress, reactor, baudrate=9600)
        
        #####################
        #Looping calls. This is here so in future we can implement a safety
        #feature, where we can "poll" the hardware to tell it that we
        #are still talking and something didnt go wrong
        #l = task.LoopingCall(self.UpdateVariables)
        #l.start(6.0)
        #####################
        
    #this function assigns values from callback to memory
    def AssignFromCallback(self, data):
        temperature, pressure_ADC = data.split(',', 1)
        self.temperature = temperature
        self.pressure = A2P(pressure_ADC)
        #print "Got update from Ino", repr(data)
    
    def processRequest(self, request_name, request_value):
        thunk = getattr(self, '%s' % (request_name,), None)

        if thunk is None: # no such transform
            return None

        try:
            return thunk(request_value)
        except:
            return None # transform failed
        
    def CurrentTemperature(self, input_part_2):
        return self.temperature
    
    def CurrentPressure(self, input_part_2):
        return self.pressure
    
    def SendToArduino(self, what):
        reactor.callWhenRunning(self.Device.sendLine, str(what))        

    
reactor.listenTCP(44444, OutboundFactory(SerialPortAddress, reactor))
reactor.run()
    
    


