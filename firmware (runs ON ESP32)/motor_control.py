from machine import Pin  #will work once we install/flash micropython firmware on the ESP32C3
import time


# This class contains all information needed to control one axis
# of the carriage, such as the motor pins, home switch, position
# and movement limits.


class Axis:

    def __init__(
        self,
        name,
        step_pin,
        dir_pin,
        home_pin,
        steps_per_mm,
        max_mm,
        home_direction,
        home_active_level=0,
        dir_invert=False
    ):

        self.name = name

        self.step_pin = Pin(step_pin, Pin.OUT)
        self.dir_pin = Pin(dir_pin, Pin.OUT)

        self.home_pin = Pin(
            home_pin,
            Pin.IN,
            Pin.PULL_UP
        )

        self.steps_per_mm = steps_per_mm
        self.max_mm = max_mm

        self.home_direction = home_direction
        self.home_active_level = home_active_level

        self.dir_invert = dir_invert

        self.position_steps = 0

        self.homed = False


    # --------------------------------------------------------
    # BASIC MOTOR FUNCTIONS
    # --------------------------------------------------------

    # These helper functions control the low-level motor signals:
    # - _set_direction() chooses which way the motor rotates
    # - _pulse() sends one STEP pulse to move the motor by one step/microstep
    # - _step_rate_to_delay() converts the desired stepping frequency
    #   into the delay needed between HIGH and LOW pulses



    def _set_direction(self, direction):
    # Convert software direction (-1 or +1) into the
    # electrical LOW/HIGH signal sent to the DIR pin.

        if direction not in (-1, 1):
            raise ValueError(
                "Direction must be -1 or +1"
            )

        level = 1 if direction > 0 else 0

        if self.dir_invert:
            level = 1 - level

        self.dir_pin.value(level)


    def _pulse(self, half_period_us):
        # Send one complete STEP pulse by switching the
        # STEP pin HIGH and then LOW.
        self.step_pin.value(1)
        time.sleep_us(half_period_us)

        self.step_pin.value(0)
        time.sleep_us(half_period_us)


    def _step_rate_to_delay(self, step_rate_hz):
        # Convert the requested step frequency [steps/s]
        # into the half-period delay [microseconds] used
        # to generate the STEP signal.
        if step_rate_hz <= 0:
            raise ValueError(
                "Step rate must be greater than zero"
            )

        half_period_us = int(
            500000 / step_rate_hz    #one full pulse has high and low half. there are 1000000 microseconds in one second.
                                     #t=1/2f=500000/f in microseconds
        )

        # Keep a minimum pulse duration.
        if half_period_us < 10:
            half_period_us = 10

        return half_period_us


    # --------------------------------------------------------
    # HOME SWITCH
    # --------------------------------------------------------

    def home_switch_triggered(self):

        return (
            self.home_pin.value()
            == self.home_active_level
        )


    # --------------------------------------------------------
    # POSITION
    # --------------------------------------------------------

    def get_position_mm(self):

        return (
            self.position_steps
            / self.steps_per_mm
        )


    # --------------------------------------------------------
    # MOVEMENT
    # --------------------------------------------------------

    def move_steps(
        self,
        signed_steps,
        speed_mm_s
    ):

        if signed_steps == 0:
            return

        direction = (
            1 if signed_steps > 0 else -1
        )

        number_of_steps = abs(
            int(signed_steps)
        )

        self._set_direction(direction)

        step_rate_hz = (
            speed_mm_s
            * self.steps_per_mm
        )

        delay = self._step_rate_to_delay(
            step_rate_hz
        )

        for _ in range(number_of_steps):

            # If travelling toward home and the
            # home switch is reached, stop immediately.
            if (
                direction == self.home_direction
                and self.home_switch_triggered()
            ):
                raise RuntimeError(
                    f"{self.name} home switch "
                    "triggered during movement"
                )

            self._pulse(delay)

            self.position_steps += direction


    def move_to_mm(
        self,
        target_mm,
        speed_mm_s
    ):

        if not self.homed:
            raise RuntimeError(
                f"{self.name} axis has not been homed"
            )

        if target_mm < 0:
            raise ValueError(
                f"{self.name} target is below 0 mm"
            )

        if target_mm > self.max_mm:
            raise ValueError(
                f"{self.name} target exceeds "
                f"{self.max_mm} mm"
            )

        target_steps = round(
            target_mm
            * self.steps_per_mm
        )

        difference = (
            target_steps
            - self.position_steps
        )

        self.move_steps(
            difference,
            speed_mm_s
        )


    # --------------------------------------------------------
    # HOMING
    # --------------------------------------------------------

    def _move_untracked(
        self,
        direction,
        number_of_steps,
        speed_mm_s
    ):

        self._set_direction(direction)

        step_rate_hz = (
            speed_mm_s
            * self.steps_per_mm
        )

        delay = self._step_rate_to_delay(
            step_rate_hz
        )

        for _ in range(number_of_steps):
            self._pulse(delay)


    def home(
        self,
        fast_speed_mm_s,
        slow_speed_mm_s,
        backoff_mm
    ):

        self.homed = False

        backoff_steps = round(
            backoff_mm
            * self.steps_per_mm
        )

        max_home_steps = round(
            (self.max_mm + 20)
            * self.steps_per_mm
        )

        # ----------------------------------------------------
        # If switch is already pressed, first move away.
        # ----------------------------------------------------

        if self.home_switch_triggered():

            self._move_untracked(
                -self.home_direction,
                backoff_steps,
                slow_speed_mm_s
            )

            if self.home_switch_triggered():
                raise RuntimeError(
                    f"{self.name} home switch "
                    "did not release"
                )


        # ----------------------------------------------------
        # FAST APPROACH
        # ----------------------------------------------------

        self._set_direction(
            self.home_direction
        )

        fast_rate = (
            fast_speed_mm_s
            * self.steps_per_mm
        )

        fast_delay = (
            self._step_rate_to_delay(
                fast_rate
            )
        )

        found_home = False

        for _ in range(max_home_steps):

            if self.home_switch_triggered():
                found_home = True
                break

            self._pulse(fast_delay)

        if not found_home:
            raise RuntimeError(
                f"{self.name} home switch "
                "was not reached"
            )


        # ----------------------------------------------------
        # BACK AWAY
        # ----------------------------------------------------

        self._move_untracked(
            -self.home_direction,
            backoff_steps,
            slow_speed_mm_s
        )


        # ----------------------------------------------------
        # SLOW SECOND APPROACH
        # ----------------------------------------------------

        self._set_direction(
            self.home_direction
        )

        slow_rate = (
            slow_speed_mm_s
            * self.steps_per_mm
        )

        slow_delay = (
            self._step_rate_to_delay(
                slow_rate
            )
        )

        found_home = False

        for _ in range(
            backoff_steps * 2
        ):

            if self.home_switch_triggered():
                found_home = True
                break

            self._pulse(slow_delay)

        if not found_home:
            raise RuntimeError(
                f"{self.name} home switch "
                "was not found during slow approach"
            )


        # ----------------------------------------------------
        # DEFINE ZERO
        # ----------------------------------------------------
        # The home switch has been found successfully.
        # Define this physical location as position zero and
        # mark the axis as homed so normal position commands can be used.
        self.position_steps = 0
        self.homed = True  #set this to zero when the system first starts because the ESP32 does not know where the carriage is


        #this file now knows how to:
        # rotate the motor
        # choose direction
        # convert movement to steps
        # prevent movement outisde software limits
        #check the home switch
        # home the axis
        # keep track of position

        #Start
         #↓
        #Is switch already pressed?
         #↓ yes
        #Move away
         #↓
        #Fast movement toward switch
         #↓
        #Switch triggers
         #↓
        #Back away 5 mm
         #↓
        #Slow movement toward switch
         #↓
        #Switch triggers
         #↓
        #Position = 0 mm