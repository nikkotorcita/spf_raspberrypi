#!/usr/bin/python
# -*- coding: utf-8 -*-

import MySQLdb as mdb
import sys
import serial
import time
import re
import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BOARD)
#Sensors
GPIO.setup(7, GPIO.IN, pull_up_down=GPIO.PUD_UP) # backing pusher out
GPIO.setup(11, GPIO.IN, pull_up_down=GPIO.PUD_UP) # backing pusher in
GPIO.setup(13, GPIO.IN, pull_up_down=GPIO.PUD_UP) # pickhead up
GPIO.setup(15, GPIO.IN, pull_up_down=GPIO.PUD_UP) # pickhead down
GPIO.setup(19, GPIO.IN, pull_up_down=GPIO.PUD_UP) # tabbing cutter up
GPIO.setup(21, GPIO.IN, pull_up_down=GPIO.PUD_UP) # tabbing cutter down
GPIO.setup(12, GPIO.IN, pull_up_down=GPIO.PUD_UP) # backing laser sensor
#Solenoids and switches
GPIO.setup(8, GPIO.OUT) # tabbing cutter solenoid
GPIO.setup(10, GPIO.OUT) # pick head solenoid
GPIO.setup(16, GPIO.OUT) # compressor
GPIO.setup(18, GPIO.OUT) # vacuum pump
GPIO.setup(22, GPIO.OUT) # backing pusher solenoid
GPIO.setup(24, GPIO.OUT) # suction solenoid

ser = None
port = "/dev/ttyUSB0"
arduino=None
arduinoPort="/dev/ttyUSB1"
for tries in range(1,5):
    try:
        print("Establishing connection with TinyG through port " + port)
        ser = serial.Serial(port, 115200)
    except: 
        pass
if ser is None:
        print("Cannot establish connection with TinyG. Exiting.")
        sys.exit()
print("TinyG found! Connection established.")


spfdb = mdb.connect('localhost', 'tinyg', 'ms', 'spfdb');


def setPin(solenoid, state):
    print "writing this out to the arduino"
    #arduino.write("!")
    #arduino.write(chr(solenoidMapping(solenoid)))
    #arduino.write(chr(state))
    print "told arduino to set %s to %d" % (solenoid, state)


def solenoidMapping(solenoid):
    print solenoid
    pin={
        'tabbing cutter': 2,
        'pick head': 3,
        'vacuum pump': 4,
        'backing pusher': 5,
        'suction': 6,
        }[solenoid]
    print pin
    return pin


def doWonders():
    with spfdb:
        cur = spfdb.cursor(mdb.cursors.DictCursor)
        cur.execute("select * from Jobs")
        try:
            row = cur.fetchone()
            id=row['id']
            parsable = row["JOB"]
            for cmd in parsable.split():
                if(cmd[0] == '!'):
                    substr = cmd[1:]
                    if(substr == '1'):
                        tabbingCutterUp()
                    elif(substr == '2'):
                        tabbingCutterDown()
                    elif(substr == '3'):
                        pickHeadUp()
                    elif(substr == '4'):
                        pickHeadDown()
                    elif(substr == '5'):
                        backingPusherIn()
                    elif(substr == '6'):
                        backingPusherOut()
                    elif(substr == '7'):
                        suctionSolenoidOn()
                    elif(substr == '8'):
                        suctionSolenoidOff()
                    elif(substr == '9'):
                        compressorOn()
                    elif(substr == '10'):
                        compressorOff()
                    elif(substr == '11'):
                        vacuumPumpOn()
                    elif(substr == '12'):
                        vacuumPumpOff()
                    elif(substr == 's'):
                        eStop()
                elif(cmd[:3]=="G4P"):   #  intercept a sleep GCode command and run it on the pi rather than the G
                    delay=float(cmd[3:])/1000
                    time.sleep(delay)
                elif(cmd == 'g28.1'):
                    cmd = parsable + chr(13)
                    print cmd
                    ser.write(cmd)
                    flushReceiveBuffer()
                    break
                else:
                    cmd = cmd + chr(13)
                    print cmd
                    ser.write(cmd)
                    #we need to block until the serial RX buffer is 
                    #empty as this will indicate that the tinyG 
                    #is done with the motion     
                    flushReceiveBuffer()

            print ("DELETE FROM Jobs where id='%s'") % id
            str = "DELETE FROM Jobs where id='%s'" % id
            cur.execute(str)
        except:
            #print "Unexpected error:", sys.exc_info()
            #print "definitely did NOT delete that"
            pass

def flushReceiveBuffer():
    while(True):
        bytes_in_buffer = ser.inWaiting()
        if(bytes_in_buffer == 0):
            break
        ser.read(bytes_in_buffer)

def tabbingCutterUp():
    print("tabbingCutterUp()")
    setPin("tabbing cutter", 1)
    GPIO.output(8, False)


def tabbingCutterDown():
    print("tabbingCutterDown()")
    setPin("tabbing cutter", 0)
    GPIO.output(8, True)

def pickHeadUp():
    print("pickHeadUp()")
    setPin("pick head", 1)
    GPIO.output(10, False)

def pickHeadDown():
    print("pickHeadDown()")
    setPin('pick head', 0)

    GPIO.output(10, True)

def backingPusherIn():
    print("backingPusherIn()")
    setPin("backing pusher", 1)
    GPIO.output(22, False)


def backingPusherOut():
    print("backingPusherOut()")
    setPin("backing pusher", 0)
    GPIO.output(22, True)

def suctionSolenoidOn():
    print("suctionSolenoidOn()")
    GPIO.output(24, True)
    setPin("suction", 1)
    print("danger will robinson")

def suctionSolenoidOff():
    print("suctionSolenoidOff()")
    GPIO.output(24, False)
    setPin("suction", 0)

def compressorOn():
    print("compressorOn()")
    GPIO.output(16, True)

def compressorOff():
    print("compressorOff()")
    GPIO.output(16, False)

def vacuumPumpOn():
    print("vacuumPumpOn()")
    GPIO.output(18, True)
    setPin("vacuum pump", 1)

def vacuumPumpOff():
    print("vacuumPumpOff()")
    GPIO.output(18, False)
    setPin("vacuum pump", 0)

def eStop():
    print("eStop()")
    e_stop = "^x" + chr(13)
    ser.write(e_stop)
    flushReceiveBuffer()

try:
    while(True):
        doWonders()
        time.sleep(1)

except KeyboardInterrupt:
    GPIO.cleanup()
