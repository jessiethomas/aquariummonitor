#!/usr/bin/python

import sys, time, smtplib, httplib, urllib, logging, RPi.GPIO as GPIO, os.path, os, traceback, signal, pygame
from subprocess import call, Popen, PIPE
from email.mime.text import MIMEText
from datetime import datetime, timedelta


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

handler = logging.FileHandler('/var/log/aquamonitor.log')
handler.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', "%Y-%m-%d %H:%M:%S")
handler.setFormatter(formatter)

logger.addHandler(handler)


# Alarm flags dictionary
alarms = {"FLOATSW_HIGH_WL": 0, "FLOATSW_LOW_WL": 0, "FLOATSW_LOW_RO_WL": 0}
# Alarms_messages/GPIO Pins mapping
pins = {"WATER_LEAK_DETECTOR_1": 23, "WATER_LEAK_DETECTOR_2": 24, "FLOATSW_HIGH_WL": 12, "FLOATSW_LOW_WL": 13,
        "FLOATSW_LOW_RO_WL": 19, "LED_PIN_R": 4, "LED_PIN_G": 17, "LED_PIN_B": 27}
# Color Table
colors = {"RED": 0xFF0000, "GREEN": 0x00FF00, "YELLOW": 0xFFFF00, "PURPLE": 0xFF00FF, "BLUE": 0x00FFFF,
          "DEEPBLUE": 0x0000FF, "WHITE": 0xFFFFFF}

WATER_VALVE = 10
FERTILIZER_PUMP_1 = 16
FERTILIZER_PUMP_2 = 20
FERTILIZER_PUMP_3 = 21
PUMP_ON = False
PUMP_OFF = True
TEST_FLAG = 0                                    # if in debug mode, set flag to 1 and no mail or pushover will be sent
LOOP_WAIT_TIMER = 5                              # defines how many seconds interval between polling
VERSION = 1.7                                    # Code version number
p_r = None
p_g = None
p_b = None
refilling = ''

# Need to fix
MAIL_TO = ''                                     # Your destination email for alerts
MAIL_FROM = ''                                   # The source address for emails (can be non existent)
MAIL_SUBJECT = 'ALERT AQUARIUM'                  # The subject
SMTP_AUTH_USERNAME = ''                          # The SMTP server authentication username
SMTP_AUTH_PASSWD = ''                            # The SMTP server authentication passwd
SMTP_SERVER = ""                                 # The SMTP server address
SMTP_PORT = 25                                   # The SMTP server port
PUSHOVER_TOKEN = ""                              # your Pushover APP toker
PUSHOVER_USER = ""                               # your Pushover USER token


def audio_alarm():
    logger.info('Entering Audio_alarm')
    pygame.mixer.init()
    pygame.mixer.music.load("/usr/local/python/aquariummonitor/alarm.wav")
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy() == True:
        continue


def setup():
    global logger
    logger.info('Entering Setup')
    global p_r
    global p_g
    global p_b
    global refilling
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(pins["FLOATSW_HIGH_WL"], GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(pins["FLOATSW_LOW_WL"], GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(pins["FLOATSW_LOW_RO_WL"], GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(WATER_VALVE, GPIO.OUT, initial=GPIO.HIGH)
    GPIO.setup(FERTILIZER_PUMP_1, GPIO.OUT, initial=GPIO.HIGH)
    GPIO.setup(FERTILIZER_PUMP_2, GPIO.OUT, initial=GPIO.HIGH)
    GPIO.setup(FERTILIZER_PUMP_3, GPIO.OUT, initial=GPIO.HIGH)
    GPIO.setup(pins["LED_PIN_R"], GPIO.OUT, initial=GPIO.HIGH)       # high = LEDs off
    GPIO.setup(pins["LED_PIN_G"], GPIO.OUT, initial=GPIO.HIGH)
    GPIO.setup(pins["LED_PIN_B"], GPIO.OUT, initial=GPIO.HIGH)
    p_r = GPIO.PWM(pins["LED_PIN_R"], 2000)
    p_g = GPIO.PWM(pins["LED_PIN_G"], 2000)
    p_b = GPIO.PWM(pins["LED_PIN_B"], 2000)
    p_r.start(0)
    p_g.start(0)
    p_b.start(0)
    logger.info('Exiting Setup')


def Map(x, in_min, in_max, out_min, out_max):
    logger.info('Entering map')
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min
    logger.info('Exiting map')


def set_led_color(col):                      # For example : col = 0x112233
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
    logger.info('Entering stop_led')
    p_r.stop()
    p_g.stop()
    p_b.stop()
    logger.info('Exiting stop_led')


# Need to fix
def send_email(mail_content):
    logger.info('Entering Send_email')
    smtpserver = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
    smtpserver.ehlo()
    smtpserver.starttls()
    smtpserver.ehlo
    smtpserver.login(SMTP_AUTH_USERNAME, SMTP_AUTH_PASSWD)
    header = 'To:' + MAIL_TO + '\n' + 'From: ' + MAIL_FROM + '\n' + 'Subject:' + MAIL_SUBJECT + '\n'
    msg = header + '\n' + mail_content + '\n\n'
    smtpserver.sendmail(SMTP_AUTH_USERNAME, MAIL_TO, msg)
    smtpserver.close()


# Need to fix
def send_pushover(pushover_content):
    logger.info('Entering Send_pushover')
    conn = httplib.HTTPSConnection("api.pushover.net:443")
    conn.request("POST", "/1/messages.json",
                urllib.urlencode({
                "token": PUSHOVER_TOKEN,
                "user": PUSHOVER_USER,
                "message": pushover_content,
                 }),
                 {"Content-type": "application/x-www-form-urlencoded" }
                 )
    conn.getresponse()


def close_ro():
    logger.info('Entering close_ro')
    GPIO.output(WATER_VALVE, PUMP_OFF)
    logger.info("Closing the RO/DI valve")
    logger.info('Exiting close_ro')


def open_valve():
    logger.info('Entering open_valve')
    while GPIO.input(pins["FLOATSW_HIGH_WL"]) == 1 and GPIO.input(pins["FLOATSW_LOW_WL"]) == 0:
        logger.info("Starting the RO pump")
        GPIO.output(WATER_VALVE, PUMP_ON)
        set_led_color(colors["BLUE"])
    logger.info("Refill done, exiting.")
    close_ro()
    sys.exit(0)
    logger.info('Exiting open_valve')


def send_alert(message):
    logger.info('Entering send_alert')
    logger.info(message)
    print(message)


def alert_cooldown(probe, timer):
    logger.info('Entering Alert_cooldown')
    if '{:%H:%M}'.format(alarms[probe] + timedelta(minutes=timer)) == '{:%H:%M}'.format(datetime.now()):
        alarms[probe] = datetime.now()                                  # reset alarm timestamp to reset the counter
        return True                                                     # time has come to resend an alarm
        logger.info("alert cooldown true")
    else:
        return False
        logger.info("alert cooldown false")


def alert(message, probe):
    logger.info('Entering Alert')
    if probe == None:                                                   # If there is no probe declared
        logger.info('sending alert message')
        send_alert(message)                                             # Just send it, and do not repeat
    else:                                                               # Alarm
        if alarms[probe] == 0:
            logger.info(probe)
            alarms[probe] = datetime.now()                              # set a timestamp for recurring alarm cooldown
            send_alert(message)                                         # and alert
        elif alert_cooldown(probe, 2):
            logger.info('repeating alert')
            send_alert("Repeated: " + message)


def monitor_probe(probe, mesg):
    logger.info('Entering monitor_probe')
    if GPIO.input(pins[probe]) == 0 and alarms[probe] == 0:
        logger.info('alert detected')
        if probe == "FLOATSW_LOW_WL":
            logger.info('low water alert')
            alert("Not refilling, start filling)", probe)
            logger.info('calling to open_valve')
            set_led_color(colors["RED"])
            open_valve()
        elif probe == "FLOATSW_HIGH_WL":
            logger.info('high water alert')
            alert("High water level in the tank, stopping the current refill.", probe)
            logger.info('setting color to red')
            set_led_color(colors["RED"])
            close_ro()
        elif probe == "FLOATSW_LOW_RO_WL":
            alert("The RO water reserve is nearly empty.", probe)
            logger.info('setting color to red')
            set_led_color(colors["RED"])
        else:
            alert('alert not set')
    elif GPIO.input(pins[probe]) == 1 and alarms[probe] != 0:             # no alarm
        logger.info('alert cleared')
        alert(mesg + " stopped", probe)
        alarms[probe] = 0
        logger.info('setting color to green')
        set_led_color(colors["GREEN"])
    logger.info('Exiting monitor_probe, no alert')


class GracefulKiller:
    logger.info('Entering GracefulKiller')
    kill_now = False

    def __init__(self):
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

    def exit_gracefully(self, signum, frame):
        self.kill_now = True

if len(sys.argv) < 2:
    logger.info('Entering len(sys.argv) < 2')
    print("Too few argument provided")
    close_ro()
    sys.exit(2)
else:
    if sys.argv[1] != "status" and sys.argv[1] != "start":
        print("Incorrect argument provided, must be either start or status")
        close_ro()
        sys.exit(2)
    
if sys.argv[1] == "start":
    logger.info('Entering sys.argv[1] == "start"')
    setup()
    killer = GracefulKiller()
    alert("Starting Aquamonitor v" + str(VERSION) + " continuous monitoring.", None)    # we (re)started
    logger.info('setting color to green')
    set_led_color(colors["GREEN"])
    while True:
        monitor_probe("FLOATSW_LOW_WL", "Low water level in the tank")
        monitor_probe("FLOATSW_HIGH_WL", "High water level in the tank")
        monitor_probe("FLOATSW_LOW_RO_WL", "Low water in the RO reserve")
        time.sleep(LOOP_WAIT_TIMER)                        # Execute loop only every minute to lower CPU footprint
        if killer.kill_now:
            alert("Caught a SIGINT or SIGTERM, exiting cleanly", None)
            logger.info("Terminating Aquamonitor")
            close_ro()
            GPIO.cleanup()
            stop_led()
            sys.exit(3)


if sys.argv[1] == "close" or sys.argv[1] == "stop":
    close_ro()


# Exit code
# 0 : Normal exit
# 1 : Keyboard CTRL+C exit
# 2 : Incorrect argument provided
# 3 : Sigterm or Sigint
# 4 : Crash
