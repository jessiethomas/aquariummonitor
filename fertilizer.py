#!/usr/bin/python

import sys, time, RPi.GPIO as GPIO, os, logging, pigpio
from time import gmtime, strftime
FERTILIZER_PUMP_1 = 9
FERTILIZER_PUMP_2 = 11
FERTILIZER_PUMP_3 = 15

if not len(sys.argv) > 1:
    print "You must provide one numerical argument to this function (duration in seconds). Exiting."
    sys.exit()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.FileHandler('/var/log/fertilizer.log')
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(message)s', "%Y-%m-%d %H:%M:%S")
handler.setFormatter(formatter)
logger.addHandler(handler)
GPIO.setmode(GPIO.BCM)
GPIO.setup(FERTILIZER_PUMP_1, GPIO.OUT)
GPIO.setup(FERTILIZER_PUMP_2, GPIO.OUT)
GPIO.setup(FERTILIZER_PUMP_3, GPIO.OUT)


def fertilization(duration):
    logger.info("Starting fertilization")
    logger.info("Starting pump 1")
    GPIO.output(FERTILIZER_PUMP_1, True)
    time.sleep(duration)
    GPIO.output(FERTILIZER_PUMP_1, False)
    logger.info("Starting pump 2")
    GPIO.output(FERTILIZER_PUMP_2, True)
    time.sleep(duration)
    GPIO.output(FERTILIZER_PUMP_2, False)
    logger.info("Starting pump 3")
    GPIO.output(FERTILIZER_PUMP_3, True)
    time.sleep(duration)
    GPIO.output(FERTILIZER_PUMP_3, False)
    logger.info("End of fertilization")

if sys.argv[1].isdigit():
    try:
        logger.info("Executing a micro AWC for " + sys.argv[1] + " seconds")
        logger.handlers[0].flush()
        fertilization(int(sys.argv[1]))
        sys.exit()
    except KeyboardInterrupt:          # cleanup in case we changed our minds and canceled the fertilization with CTRL+C
        GPIO.output(FERTILIZER_PUMP_1, False)
        GPIO.output(FERTILIZER_PUMP_2, False)
        GPIO.output(FERTILIZER_PUMP_3, False)
        sys.exit()
