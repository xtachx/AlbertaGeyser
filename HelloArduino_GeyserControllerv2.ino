/*
 * HelloArduino GeyserController
 *
 * Controls the heating and cooling elements of the geyser.
 * This code is written to talk to the GeyserInit program
 * All of this is GNU GPL and you will find it in the 
 * AutoGeyser folder in the source code.
 
 *Written by Pitam Mitra for PICASSO detector R&D.

 *Changelog: 23.6.2012: Created the file.
 */
 
#include <Wire.h> //Wire library for SMBus devices
 
/*The headers defining the SMBus Temperature device */
#define deviceID 0x5A
#define RAM 0x00
#define TEMPERATURE_SENSOR 0x07


/* We start the arduino and start the SMBus sensors first */
void setup(){
  Serial.begin(9600); //begin serial, 9600 baud
  Wire.begin(); //begin SMBus
}

/* Function to read the Infrared Sensor */
 
double readInfraredTemperature(){
   
  byte highBit, lowBit, pec; //declare space for variables
  double temperature; //and the temperature
   
  Wire.beginTransmission(deviceID); //start SMBus communication
  Wire.write(RAM | TEMPERATURE_SENSOR); //send the register address we want to read
    
  Wire.endTransmission(false); //bus direction reversal
  
  Wire.requestFrom(deviceID, 3); //read 3 bytes from sensor
  lowBit = Wire.read(); //read lowbit
  highBit = Wire.read(); //read highbit
  pec = Wire.read(); //read pec
  
  temperature = (double)(((highBit & 0x7F) << 8) + lowBit)/50.0-273.15; //calculate temperature
  
  return temperature;  
 }
 
void loop(){
  // read the sensor:
  if (Serial.available() > 0) {
    int inByte = Serial.read();
    //We will use charecters h and c which stands
    //for hot or cold
    switch (inByte) {
    case 'h':
      Serial.println("Start Heat");
      break;
    case 'c':
      Serial.println("Start cool");
      break;
    case 't':
      Serial.println(readInfraredTemperature());
      break;
    case 'p':
      int PWM_Pin5;
      PWM_Pin5 = Serial.parseInt();
      break;
    case 'q':
      int PWM_Pin6;
      PWM_Pin6 = Serial.parseInt();
      break;
    default:
      Serial.println("Ready");
     } //switch
  } //if serial.availbale
  
  
}//loop
 
