"""
Calculates AccelStepper profile.
"""
import logging, math

log = logging.getLogger(__name__)

# HACK put this somewhere common to accelstepper too
DIRECTION_CCW = 0   # Clockwise
DIRECTION_CW  = 1   # Counter-Clockwise

class AccelStepperProfile:

  def __init__(self):
    #  Max velocity/speed in steps per second
    self._target_speed = 1.0
    # Acceleration in steps per second per second
    self._acceleration = 0.0
    # Precomputed sqrt(2*_acceleration)
    self._sqrt_twoa = 1.0
    # Used for calculating acceleration
    # Logical step number of current ramp. Not the same as physical step count.
    # 'n' in the Austin paper
    self._ramp_step_number = 0
    # _timer_count is 'c' in Austin paper
    self._ramp_delay_0_us = 0.0
    # All timer counts > _ramp_delay_0_us. _timer_count is 'c' in Austin paper
    self._ramp_delay_n_us = 0.0
    # Minimum microseconds for ramp delay
    self._ramp_delay_min_us = 1.0

  def set_target_speed(self, speed):
    """
    Set our requested ultimate cruising speed.

    Arguments:
      speed (float): Steps per second
    """
    if self._target_speed == speed:
      return
    self._target_speed = speed
    self._ramp_delay_min_us = 1000000.0 / speed
    # Recompute _ramp_step_number from current speed and adjust speed if accelerating or cruising
    if (self._ramp_step_number > 0):
      self._ramp_step_number = ((self.parent._speed * self.parent._speed) / (2.0 * self._acceleration)) # Equation 16
      self.compute_new_speed()

  def set_acceleration(self, acceleration):
    """
    Sets acceleration value in steps per second per second and computes new speed.
    Arguments:
      acceleration (float). Acceleration in steps per second per second.
    """
    if acceleration == 0.0 or self._acceleration == acceleration:
      return
    # Recompute _ramp_step_number per Equation 17
    self._ramp_step_number = self._ramp_step_number * (self._acceleration / acceleration)
    # New c0 per Equation 7, with correction per Equation 15
    self._ramp_delay_0_us = 0.676 * math.sqrt(2.0 / acceleration) * 1000000.0 # Equation 15
    self._acceleration = acceleration
    self.compute_new_speed()

  def compute_new_speed(self):
    distanceTo = self.parent.distance_to_go     # +ve is clockwise from curent location
    stepsToStop = int(((self.parent._speed * self.parent._speed) / (2.0 * self._acceleration))) # Equation 16

    if distanceTo == 0 and stepsToStop <= 1:
      # We are at the target and its time to stop
      self.parent._step_interval_us = 0
      self.parent._speed = 0.0
      self._ramp_step_number = 0
      return

    if distanceTo > 0:
      # We are anticlockwise from the target
      # Need to go clockwise from here, maybe decelerate now
      if self._ramp_step_number > 0:
        # Currently accelerating, need to decel now? Or maybe going the wrong way?
        if (stepsToStop >= distanceTo) or self.parent._direction == DIRECTION_CCW:
          # Start deceleration
          self._ramp_step_number = -stepsToStop
      elif self._ramp_step_number < 0:
        # Currently decelerating, need to accel again?
        if (stepsToStop < distanceTo) and self.parent._direction == DIRECTION_CW:
          # Start accceleration
          self._ramp_step_number = -self._ramp_step_number
    elif distanceTo < 0:
      # We are clockwise from the target
      # Need to go anticlockwise from here, maybe decelerate
      if self._ramp_step_number > 0:
        # Currently accelerating, need to decel now? Or maybe going the wrong way?
        if (stepsToStop >= -distanceTo) or self.parent._direction == DIRECTION_CW:
          # Start deceleration
          self._ramp_step_number = -stepsToStop
      elif self._ramp_step_number < 0:
        # Currently decelerating, need to accel again?
        if stepsToStop < -distanceTo and self.parent._direction == DIRECTION_CCW:
          # Start accceleration
          self._ramp_step_number = -self._ramp_step_number

    # Need to accelerate or decelerate
    if self._ramp_step_number == 0:
      # First step from stopped
      self._ramp_delay_n_us = self._ramp_delay_0_us
      self.parent._direction = DIRECTION_CW if distanceTo > 0 else DIRECTION_CCW
    else:
      # Subsequent step. Works for accel (n is +_ve) and decel (n is -ve).
      self._ramp_delay_n_us = self._ramp_delay_n_us - ((2.0 * self._ramp_delay_n_us) / ((4.0 * self._ramp_step_number) + 1)) # Equation 13
      self._ramp_delay_n_us = max(self._ramp_delay_n_us, self._ramp_delay_min_us)

    self._ramp_step_number += 1
    self.parent._step_interval_us = self._ramp_delay_n_us
    self.parent._speed = 1000000.0 / self._ramp_delay_n_us
    if self.parent._direction == DIRECTION_CCW:
      self.parent._speed = -self.parent._speed

    log.debug('Computed new speed. _direction=%s, _current_steps=%s, _target_steps=%s, distance_to_go=%s, _ramp_step_number=%s, _speed=%s, _step_interval_us=%s',
      self.parent._direction, self.parent._current_steps,
      self.parent._target_steps, self.parent.distance_to_go,
      self._ramp_step_number, self.parent._speed, self.parent._step_interval_us)

  def set_current_position(self, position):
    """
    Useful during initialisations or after initial positioning
    Sets speed to 0
    """
    self.parent._target_steps = self.parent._current_steps = position
    self._ramp_step_number = 0
    self.parent._step_interval_us = 0
    self.parent._speed = 0.0
