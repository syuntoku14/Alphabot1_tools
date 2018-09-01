#!/usr/bin/env python
import pigpio
import math


class AlphaBot1():
    def __init__(self, pi):
        self.wheel = Wheel(pi)
        self.sensor = Sensor(pi)

        self.x = 0
        self.y = 0
        self.theta = 0

    def uni2diff(self, v, w):
        R = self.wheel.wheel_radius
        L = self.wheel.wheel_base_length
        vel_l = (2*v-w*L)/(2*R)
        vel_r = (2*v+w*L)/(2*R)

        return vel_l, vel_r

    def set_pose(self, x, y, theta):
        self.x = x
        self.y = y
        self.theta = math.atan2(math.sin(theta), math.cos(theta))

    def update_odometry(self):
        R = self.wheel.wheel_radius
        L = self.wheel.wheel_base_length
        left_diff = (self.sensor.encoder_ticks_left -
                     self.sensor.encoder_prev_ticks_left)*self.wheel.m_per_tick
        right_diff = (self.sensor.encoder_ticks_right -
                      self.sensor.encoder_prev_ticks_right)*self.wheel.m_per_tick

        center_diff = (left_diff + right_diff)/2.0
        phi = (right_diff - left_diff)/L

        x_dt = center_diff*math.cos(self.theta)
        y_dt = center_diff*math.sin(self.theta)
        theta_dt = phi

        theta_new = self.theta + theta_dt
        x_new = self.x + x_dt
        y_new = self.y + y_dt

        # update odometry
        self.set_pose(x_new, y_new, theta_new)

        # save the previous ticks for the next estimate
        self.sensor.encoder_prev_ticks_left = self.sensor.encoder_ticks_left
        self.sensor.encoder_prev_ticks_right = self.sensor.encoder_ticks_right


class Wheel():
    def __init__(self, pi, left_front=12, left_back=13, right_back=20, right_front=21, enable_left=6, enable_right=26):
        # pin assignment
        self.left_front = left_front
        self.left_back = left_back
        self.right_back = right_back
        self.right_front = right_front
        self.enable_left = enable_left
        self.enable_right = enable_right

        # all unit is meter
        self.wheel_radius = 0.065
        self.wheel_base_length = 0.135
        self.ticks_per_rev = 20
        self.m_per_tick = (2.0*math.pi*self.wheel_radius)/self.ticks_per_rev

        # initialize gpio
        self.pi = pi  # pigpio.pi()
        self.pi.set_mode(self.left_front, pigpio.OUTPUT)
        self.pi.set_mode(self.left_back, pigpio.OUTPUT)
        self.pi.set_mode(self.right_back, pigpio.OUTPUT)
        self.pi.set_mode(self.right_front, pigpio.OUTPUT)
        self.pi.set_mode(self.enable_left, pigpio.OUTPUT)
        self.pi.set_mode(self.enable_right, pigpio.OUTPUT)
        self.set_wheel_speeds(0, 0)

    def vel2duty(self, vel):
        # convert velocity to duty ratio
        duty = int(255 * vel)  # 255 == duty 1
        return duty

    def set_left_speed(self, vel):
        self.pi.set_PWM_dutycycle(self.enable_left, self.vel2duty(vel))

    def set_right_speed(self, vel):
        self.pi.set_PWM_dutycycle(self.enable_right, self.vel2duty(vel))

    def set_wheel_speeds(self, vl, vr):
        # set wheel speeds accordint to vl and vr
        if vl >= 0:
            self.pi.write(self.left_front, 1)
            self.pi.write(self.left_back, 0)
        else:
            self.pi.write(self.left_front, 0)
            self.pi.write(self.left_back, 1)

        if vr >= 0:
            self.pi.write(self.right_front, 1)
            self.pi.write(self.right_back, 0)
        else:
            self.pi.write(self.right_front, 0)
            self.pi.write(self.right_back, 1)
        # set velocities
        self.set_left_speed(vl)
        self.set_right_speed(vr)


class Sensor():
    def __init__(self, pi, encoder_left=7, encoder_right=8):
        # photo interupter of encoders
        self.encoder_left = encoder_left
        self.encoder_right = encoder_right

        self.encoder_ticks_right = 0
        self.encoder_ticks_left = 0
        self.encoder_prev_ticks_right = 0
        self.encoder_prev_ticks_left = 0

        self.pi = pi  # pigpio.pi()
        self.pi.set_mode(self.encoder_left, pigpio.INPUT)
        self.pi.set_mode(self.encoder_right, pigpio.INPUT)

        self.cbf_left = self.pi.callback(self.encoder_left, pigpio.RISING_EDGE,
                                         self.callback_function_encoder_left)
        self.cbf_right = self.pi.callback(self.encoder_right, pigpio.RISING_EDGE,
                                          self.callback_function_encoder_right)

    def __del__(self):
        self.cbf_left.cancel()
        self.cbf_right.cancel()

    def read_encoder_vals(self):
        l = self.pi.read(self.encoder_left)
        r = self.pi.read(self.encoder_right)
        return l, r

    def callback_function_encoder_left(self, GPIO, level, tick):
        self.encoder_ticks_left += 1

    def callback_function_encoder_right(self, GPIO, level, tick):
        self.encoder_ticks_right += 1
