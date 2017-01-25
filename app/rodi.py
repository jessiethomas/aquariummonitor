#!/usr/bin/python

import sys, signal, logging, time, RPi.GPIO as GPIO

PUMP_ON = False
PUMP_OFF = True
FLOATSW_LOW_WL = 13
FLOATSW_HIGH_WL = 12               # high water level float switch
WATER_VALVE = 10                   # GPIO port for the Water Electo valve, High by default after boot
VALVE_CHGSTATE_TIMER = 25          # Electro valve needs roughly 20 seconds to switch from open to close and vice versa
logger = None


def Setup():
    global logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler('/var/log/rodi.log')
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(message)s', "%Y-%m-%d %H:%M:%S")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(WATER_VALVE, GPIO.OUT, initial=GPIO.HIGH)
    GPIO.setup(FLOATSW_HIGH_WL, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    if not sys.stdout.isatty():
        sys.stderr = open('/var/log/rodi_stderr.log', 'a')
        sys.stdout = open('/var/log/rodi_stdout.log', 'a')


def Alert(message):
    global logger
    logger.info(message)                                                # log the event
    print(message)
    logger.handlers[0].flush()


def Close_valve():
    GPIO.output(WATER_VALVE, PUMP_OFF)
    Alert("Closing the RO/DI valve")


def Open_valve():
    if GPIO.input(WATER_VALVE) == PUMP_ON:
        Alert("RO/DI Valve already opened")
        sys.exit(5)
    else:
        Alert("Opening the RO/DI valve")
        GPIO.output(WATER_VALVE, PUMP_ON)
        time.sleep(VALVE_CHGSTATE_TIMER)


def Refilling():
    if GPIO.input(WATER_VALVE) == PUMP_ON:
        return True
    else:
        return False


class GracefulKiller:
    kill_now = False

    def __init__(self):
         signal.signal(signal.SIGINT, self.exit_gracefully)
         signal.signal(signal.SIGTERM, self.exit_gracefully)

    def exit_gracefully(self, signum, frame):
         self.kill_now = True
           
if not len(sys.argv) > 1:
    print("You must provide one numerical argument to this function (duration in seconds). Exiting.")
    sys.exit(1)

if sys.argv[1] != "close" and sys.argv[1] != "stop" and not sys.argv[1].isdigit():
    print("Value is neither 'close', 'stop' or a refill duration expressed in seconds")
    sys.exit(1)

i = 0
killer = GracefulKiller()
Setup()

if sys.argv[1] == "close" or sys.argv[1] == "stop":
    Close_valve()
    
if GPIO.input(FLOATSW_HIGH_WL) == 0:
    Alert("Water level in sump already high, refilling would be dangerous, exiting")
    if GPIO.input(WATER_VALVE) == PUMP_ON:
        Alert("RO/DI Valve already opened while high water in the sump, closing.")
        Close_valve()
        sys.exit(3)

if sys.argv[1].isdigit():
    Alert("Not already refilling, sump water level normal, proceeding.")
    try:
        Open_valve()
        while GPIO.input(FLOATSW_HIGH_WL) == 1 and GPIO.input(FLOATSW_LOW_WL) == 0:
            Refilling() == True
        Alert("Refill done, exiting.")
        Close_valve()
        sys.exit(0)
    except (RuntimeError, IOError):        
        Alert("Caught an exception, exiting.")
        Close_valve()
        sys.exit(4)

# Exit code :
# 5 : already refilling or cannot create lock file
# 4 : Caught an exception
# 3 : water is high either at start or during the refill
# 2 : a sigkill, sigterm or keyboard CTRL+C signal was received
# 1 : incorrect parameter received
# 0 : all went fine
