import logging, RPi.GPIO as GPIO, sys, time, signal

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

handler = logging.FileHandler('/var/log/aquamonitor.log')
handler.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', "%Y-%m-%d %H:%M:%S")
handler.setFormatter(formatter)

logger.addHandler(handler)

floats = {"HIGH_WL": 13,
          "LOW_WL": 12,
          "LOW_RO_WL": 19}

LED_PIN_R = 4
LED_PIN_G = 17
LED_PIN_B = 27
WATER_VALVE = 10
FERTILIZER_PUMP_1 = 16
FERTILIZER_PUMP_2 = 20
FERTILIZER_PUMP_3 = 21
RED = 0xFF0000
GREEN = 0x00FF00
BLUE = 0x00FFFF
PUMP_ON = False
PUMP_OFF = True
LOOP_WAIT_TIMER = 5
p_r = None
p_g = None
p_b = None
tank_status = ''


def setup():
    global logger
    logger.debug('Entering Setup')
    global p_r
    global p_g
    global p_b
    global tank_status
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(floats["HIGH_WL"], GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(floats["LOW_WL"], GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(floats["LOW_RO_WL"], GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(WATER_VALVE, GPIO.OUT, initial=GPIO.HIGH)
    GPIO.setup(LED_PIN_R, GPIO.OUT, initial=GPIO.HIGH)       # high = LEDs off
    GPIO.setup(LED_PIN_G, GPIO.OUT, initial=GPIO.HIGH)
    GPIO.setup(LED_PIN_B, GPIO.OUT, initial=GPIO.HIGH)
    p_r = GPIO.PWM(LED_PIN_R, 2000)
    p_g = GPIO.PWM(LED_PIN_G, 2000)
    p_b = GPIO.PWM(LED_PIN_B, 2000)
    p_r.start(0)
    p_g.start(0)
    p_b.start(0)
    logger.debug('Exiting Setup')


# LED set up
def Map(x, in_min, in_max, out_min, out_max):
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min


def set_led_color(col):
    r_val = (col & 0x110000) >> 16
    g_val = (col & 0x001100) >> 8
    b_val = (col & 0x000011) >> 0
    r_val = Map(r_val, 0, 255, 0, 100)
    g_val = Map(g_val, 0, 255, 0, 100)
    b_val = Map(b_val, 0, 255, 0, 100)
    p_r.ChangeDutyCycle(r_val)
    p_g.ChangeDutyCycle(g_val)
    p_b.ChangeDutyCycle(b_val)


def stop_led():
    p_r.stop()
    p_g.stop()
    p_b.stop()


def alert(message, probe):
    logger.debug('Entering Alert')
    logger.info('{m} : {p}'.format(m=message, p=probe))                                         # and alert


def open_valve():
    global tank_status
#   logger.debug('Entering open_valve')
    logger.info('Starting RO fill')
    tank_status = 'refilling'
    set_led_color(BLUE)
    while (GPIO.input(floats["LOW_WL"]) == 0) and (GPIO.input(floats["HIGH_WL"]) == 0) and (GPIO.input(floats["LOW_RO_WL"]) == 0) :
        # logger.debug("Starting pump loop")
        # logger.debug('Low water float:')
        # logger.debug(GPIO.input(floats["LOW_WL"]))
        # logger.debug('High water float:')
        # logger.debug(GPIO.input(floats["HIGH_WL"]))
        # logger.debug('RO water float:')
        # logger.debug(GPIO.input(floats["LOW_RO_WL"]))
        GPIO.output(WATER_VALVE, PUMP_ON)
        time.sleep(LOOP_WAIT_TIMER)
    logger.info("Refill done, exiting.")
    logger.debug('Exiting open_valve')
    close_ro()
    sys.exit(0)


def close_ro():
    global tank_status
    logger.debug('Entering close_ro')
    GPIO.output(WATER_VALVE, PUMP_OFF)
    logger.info("Closing the RO/DI valve")
    logger.debug('Exiting close_ro')
    tank_status = 'normal'


def monitor_probe():
    logger.debug('Entering monitor_probe')
    global tank_status
    logger.debug('Low water float:')
    logger.debug(GPIO.input(floats["LOW_WL"]))
    logger.debug('High water float:')
    logger.debug(GPIO.input(floats["HIGH_WL"]))
    logger.debug('RO water float:')
    logger.debug(GPIO.input(floats["LOW_RO_WL"]))
    for probe in floats:
        if GPIO.input(floats[probe]) == 0:
            logger.info('alert detected')
            if probe == "LOW_WL":
                logger.debug('low water alert')
                alert("Not refilling, start filling", probe)
                tank_status = 'refilling'
                set_led_color(BLUE)
                open_valve()
            elif probe == "HIGH_WL":
                logger.debug('high water alert', probe)
                if tank_status == 'refilling':
                    logger.debug('stopping refill')
                    alert("High water level in the tank, stopping the current refill.", probe)
                    tank_status = 'alert'
                    set_led_color(RED)
                    close_ro()
                else:
                    logger.debug('not refilling, cont.')
                    tank_status = 'normal'
                    set_led_color(GREEN)
            elif probe == "LOW_RO_WL":
                logger.debug('RO is getting low')
                alert("The RO water reserve is nearly empty.", probe)
                tank_status = 'alert'
                set_led_color(RED)
                close_ro()
        elif GPIO.input(floats[probe]) == 1:
            logger.debug('no alert')
            tank_status = 'normal'
            set_led_color(GREEN)
    logger.debug('Exiting monitor_probe')


class GracefulKiller:
    logger.debug('Entering GracefulKiller')
    kill_now = False

    def __init__(self):
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

    def exit_gracefully(self, signum, frame):
        self.kill_now = True


if sys.argv[1] == "start":
    logger.debug('Entering startup')
    setup()
    set_led_color(GREEN)
    killer = GracefulKiller()
    alert("Starting Aquamonitor continuous monitoring.", None)
    while True:
        monitor_probe()
        logger.debug('sleep')
        time.sleep(LOOP_WAIT_TIMER)
        if killer.kill_now:
            alert("Caught a SIGINT or SIGTERM, exiting cleanly", None)
            alert("Terminating Aquamonitor", None)
            close_ro()
            GPIO.cleanup()
            stop_led()
            sys.exit(3)
elif sys.argv[1] == "close" or sys.argv[1] == "stop":
    close_ro()
