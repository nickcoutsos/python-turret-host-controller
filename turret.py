import logging
import math
import time
import usb.core

DEFAULT_DURATION = 0.5

# Direction
DOWN  = 0x01
UP    = 0x02
LEFT  = 0x04
RIGHT = 0x08

# Action
FIRE = 0x10
STOP = 0x20

# States
MOVING = UP | DOWN | LEFT | RIGHT
FIRING = FIRE
STOPPED = STOP

logger = logging.getLogger('turret')
logger.setLevel(logging.DEBUG)

def zeroish(num, epsilon=0.0001):
    return abs(num) < epsilon

def find_usb_devices():
    return usb.core.find(idVendor=0x2123, idProduct=0x1010, find_all=True)

class Turret(object):

    def __init__(self, rockets=4):
        self._device = None
        self._rockets = rockets
        self._state = STOP
        self._connect()

    def __del__(self):
        self._disconnect()

    def _connect(self):
        logger.info('%r initiating connection to turret', self)
        self._device = usb.core.find(idVendor=0x2123, idProduct=0x1010)
        if self._device is None:
            raise ValueError('Launcher not found.')
        if self._device.is_kernel_driver_active(0) is True:
            self._device.detach_kernel_driver(0)
        self._device.set_configuration()
        self._device.ctrl_transfer(0x21, 0x09, 0, 0, [0x03, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        logger.info('%r connected successfully.', self)

    def _disconnect(self):
        self._device.ctrl_transfer(0x21, 0x09, 0, 0, [0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        try:
            self._device.attach_kernel_driver(0)
        except usb.core.USBError:
            pass
        logger.info('%r disconnected successfully.', self)

    def send(self, command, duration=None):
        self._state = command
        self._device.ctrl_transfer(0x21, 0x09, 0, 0,
            [0x02, command, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])

        if duration != None and command != STOP:
            time.sleep(duration)
            self.send(STOP)

    def up(self, duration=DEFAULT_DURATION):
        self.send(UP, duration)
    def down(self, duration=DEFAULT_DURATION):
        self.send(DOWN, duration)
    def left(self, duration=DEFAULT_DURATION):
        self.send(LEFT, duration)
    def right(self, duration=DEFAULT_DURATION):
        self.send(RIGHT, duration)

    def stop(self):
        self.send(STOP)

    def fire(self):
        self.send(FIRE)


class InteractiveTurret(Turret):

    def aim(self, yaw, pitch):
        """
       Accepts relative yaw and pitch (in seconds) to "smoothly" transition
       to a new direction.

       Pitch and yaw are mapped to a primary (the longer) and secondary (the
       shorter) commands. A ratio of primary:secondary is calculated to
       determine how many times the primary command should be sent before
       the secondary is sent.

       Rounding makes this implementation suck.
       """

        yaw = float(yaw)
        pitch = float(pitch)

        if zeroish(yaw):
            yaw_cmd = STOP
        else:
            yaw_cmd = RIGHT if yaw > 0 else LEFT
            yaw = abs(yaw)

        if zeroish(pitch):
            pitch_cmd = STOP
        else:
            pitch_cmd = UP if pitch > 0 else DOWN
            pitch = abs(pitch)

        start = time.time()
        total = max(yaw, pitch)
        ratio = int(math.ceil(total / min(yaw, pitch)))

        primary = pitch_cmd if pitch > yaw else yaw_cmd
        secondary = yaw_cmd if pitch > yaw else pitch_cmd

        while(True):
            now = time.time()
            for __ in range(ratio):
                print "primary", primary
                self.send(primary, 0.05)
            print "secondary", secondary
            self.send(secondary, 0.05)

            if now > start + total:
                break

class DirectedTurret(Turret):

    YAW_MIN = -135.0
    YAW_MAX = 135.0
    YAW_SEC = 6.127

    PITCH_MIN = -5.0
    PITCH_MAX = 25.9
    PITCH_SEC = 1.014

    def __init__(self):
        super(DirectedTurret, self).__init__()
        self._pitch = 0.0
        self._pitch_rate = self.PITCH_SEC / (self.PITCH_MAX - self.PITCH_MIN)
        self._yaw = 0.0
        self._yaw_rate = self.YAW_SEC / (self.YAW_MAX - self.YAW_MIN)

 
    def _pitch_to_seconds(self, angle):
        return abs(angle * self._pitch_rate)

    def _yaw_to_seconds(self, angle):
        return abs(angle * self._yaw_rate)

    def pitch(self, angle):
        """
       Set turret pitch to an absolute angle.
       """

        target = max(self.PITCH_MIN, angle)
        target = min(self.PITCH_MAX, target)
        delta = target - self._pitch
        seconds = self._pitch_to_seconds(delta)

        logger.debug('%r pitching to angle %.2f (%fseconds)', self, delta, seconds)
        turn = self.down if delta < 0 else self.up
        turn(self._pitch_to_seconds(delta))

        self._pitch = target
        logger.info('%r set to heading %.2f', self, target)

    def yaw(self, angle):
        """
       Set turret yaw to an absolute angle.
       """

        target = max(self.YAW_MIN, angle)
        target = min(self.YAW_MAX, target)
        delta = target - self._yaw
        seconds = self._pitch_to_seconds(delta)

        logger.debug('%r turning to heading %.2f (%fseconds)', self, delta, seconds)
        turn = self.right if delta > 0 else self.left
        turn(self._yaw_to_seconds(delta))

        self._yaw = target
        logger.info('%r set to heading %.2f', self, target)

    def calibrate(self, opposite=False, and_center=False):
        """
       Put turret in a known direction to correct internal tracking.
       """

        command = DOWN | LEFT
        targets = (self.PITCH_MIN, self.YAW_MIN)

        if opposite:
            command = UP | RIGHT
            targets = (self.PITCH_MAX, self.YAW_MAX)

        self.send(command)
        logger.info("%r CALIBRATING", self)
        time.sleep(max(self.YAW_SEC, self.PITCH_SEC) + 0.5)

        self._pitch, self._yaw = targets
        logger.info('%r CALIBRATED', self)

        if and_center:
            self.center()

    def center(self):
        logger.info('%r CENTERING', self)
        self.pitch(0.0)
        self.yaw(0.0)
        logger.info('%r CENTERED', self)