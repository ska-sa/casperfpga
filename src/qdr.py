"""
Created on Fri Mar  7 07:15:45 2014

@author: paulp
"""

import logging
import numpy
import struct
import register

from memory import Memory

LOGGER = logging.getLogger(__name__)
LOGGER.propagate = True

USE_JACK_CAL = True

LEVEL0 = logging.INFO
LEVEL1 = LEVEL0 - 1
LEVEL2 = LEVEL1 - 1
LEVEL3 = LEVEL2 - 1

QDR_WORD_WIDTH = 36
QDR_WW_LIMITED = 32
NUM_DELAY_TAPS = 32

MINIMUM_WINDOW_LENGTH = 4

CAL_DATA = [
    [0xAAAAAAAA, 0x55555555, 0xAAAAAAAA, 0x55555555,
     0xAAAAAAAA, 0x55555555, 0xAAAAAAAA, 0x55555555,
     0xAAAAAAAA, 0x55555555, 0xAAAAAAAA, 0x55555555,
     0xAAAAAAAA, 0x55555555, 0xAAAAAAAA, 0x55555555,
     0xAAAAAAAA, 0x55555555, 0xAAAAAAAA, 0x55555555,
     0xAAAAAAAA, 0x55555555, 0xAAAAAAAA, 0x55555555,
     0xAAAAAAAA, 0x55555555, 0xAAAAAAAA, 0x55555555,
     0xAAAAAAAA, 0x55555555, 0xAAAAAAAA, 0x55555555],
    [0, 0, 0xFFFFFFFF, 0, 0, 0, 0, 0],
    numpy.arange(256) << 0,
    numpy.arange(256) << 8,
    numpy.arange(256) << 16,
    numpy.arange(256) << 24,
]


def logl0(msg):
    logging.log(LEVEL0, msg)


def logl1(msg):
    logging.log(LEVEL1, msg)


def logl2(msg):
    logging.log(LEVEL2, msg)


def logl3(msg):
    logging.log(LEVEL3, msg)


def find_cal_area(a):
    """
    Given a vector of pass (1) and fail (-1), find contiguous chunks of 'pass'.

    :param a: Vector input (list?)
    :return: Tuple - (max_so_far, begin_index, end_index)
    """
    max_so_far = a[0]
    max_ending_here = a[0]
    begin_index = 0
    begin_temp = 0
    end_index = 0
    for i in range(len(a)):
        if max_ending_here < 0:
            max_ending_here = a[i]
            begin_temp = i
        else:
            max_ending_here += a[i]
        if max_ending_here >= max_so_far:
            max_so_far = max_ending_here
            begin_index = begin_temp
            end_index = i
    return max_so_far, begin_index, end_index


class Qdr(Memory):
    """
    Qdr memory on an FPGA.
    """
    def __init__(self, parent, name, address, length_bytes,
                 device_info, ctrlreg_address):
        """
        Make the QDR instance, given a parent, name and info from Simulink.
        
        * Most often called from_device_info

        :param parent: Parent device who owns this Qdr
        :param name: A unique device name
        :param address: Address of the Qdr in memory
        :param length_bytes: Length of the Qdr in memory
        :param device_info: Information about this Qdr device
        :param ctrlreg_address:
        """
        super(Qdr, self).__init__(name=name, width_bits=32,
                                  address=address, length_bytes=length_bytes)
        self.parent = parent
        self.block_info = device_info
        self.which_qdr = self.block_info['which_qdr']
        self.ctrl_reg = register.Register(
            self.parent, self.which_qdr+'_ctrl', address=ctrlreg_address,
            device_info={'tag': 'xps:sw_reg', 'mode': 'one\_value',
                         'io_dir': 'From\_Processor', 'io_delay': '0',
                         'sample_period': '1', 'names': 'reg',
                         'bitwidths': '32', 'arith_types': '0',
                         'bin_pts': '0', 'sim_port': 'on',
                         'show_format': 'off'})
        self.memory = self.which_qdr + '_memory'
        self.control_mem = self.which_qdr + '_ctrl'
        # self.qdr_cal()

        # some readability tweaks
        self.p_write_int = self.parent.write_int
        self.p_read_uint = self.parent.read_uint
        self.p_bwrite = self.parent.blindwrite
        self.p_read = self.parent.read

        # print('QDR %s logger name(%s) id(%i) level(%i)' % ()
        #     self.name, LOGGER.name, id(LOGGER), LOGGER.level)
        # print('qdr logger handlers:', LOGGER.handlers)

        LOGGER.debug('New Qdr %s' % self)
        # TODO - Link QDR ctrl register to self.registers properly

    @classmethod
    def from_device_info(cls, parent, device_name, device_info, memorymap_dict, **kwargs):
        """
        Process device info and the memory map to get all necessary info and
        return a Qdr instance.

        :param parent:
        :param device_name: the unique device name
        :param device_info: information about this device
        :param memorymap_dict: a dictionary containing the device memory map
        :return: a Qdr object
        """
        def find_info(suffix):
            address, length = -1, -1
            fullname = device_info['which_qdr'] + suffix
            for mem_name in memorymap_dict.keys():
                if mem_name == fullname:
                    address = memorymap_dict[mem_name]['address']
                    length = memorymap_dict[mem_name]['bytes']
                    break
            if address == -1 or length == -1:
                raise RuntimeError('QDR %s: could not find memory address and'
                                   'length for device %s' % (device_name,
                                                             fullname))
            return address, length

        mem_address, mem_length = find_info('_memory')
        ctrlreg_address, ctrlreg_length = find_info('_memory')
        # TODO - is the ctrl reg a register or the whole 256 bytes?
        return cls(parent, device_name, mem_address, mem_length,
                   device_info, ctrlreg_address)

    def __repr__(self):
        """
        :return: a string representation of the Qdr Class
        """
        return '%s:%s' % (self.__class__.__name__, self.name)

    def reset(self):
        """
        Reset the QDR controller by toggling the lsb of the control register.
        Sets all taps to zero (all IO delays reset).
        """
        LOGGER.debug('qdr reset')
        self.ctrl_reg.write_int(1, blindwrite=True)
        self.ctrl_reg.write_int(0, blindwrite=True)

    def _control_mem_write(self, value, offset):
        """
        Write to this QDR's control memory on the parent's mem bus

        :param value:
        :param offset:
        """
        self.p_write_int(self.control_mem, value,
                         blindwrite=True, word_offset=offset)

    def _disable_fabric(self):
        """
        Disable the fabric write to the QDR.
        """
        self._control_mem_write(1, 2)

    def _enable_fabric(self):
        """
        Enable the fabric write to the QDR.
        """
        self._control_mem_write(0, 2)

    def _add_extra_latency(self, extra_lat):
        """
        If input argument is True, add an extra cycle of latency to QDR
        input data. Useful for clock rates <~200.
        If false, remove any extra latency already applied.

        :param extra_lat:
        """
        self._control_mem_write(1 if extra_lat else 0, 9)

    def qdr_reset(self):
        """
        Resets the QDR and the IO delays (sets all taps=0).
        """
        self._control_mem_write(1, 0)
        self._control_mem_write(0, 0)
        # these two should just do nothing if support is not compiled into
        # the running fpg
        self._add_extra_latency(False)
        self._enable_fabric()

    def _qdr_delay_clk_step(self, step):
        """
        Steps the output clock by 'step' amount.

        :param step:
        """
        if step == 0:
            return
        self._control_mem_write(0 if step < 0 else 0xffffffff, 7)
        logl1('Applying clock delay: {}'.format(step))
        for _ctr in range(abs(step)):
            self._control_mem_write(0, 5)
            self._control_mem_write(1 << 8, 5)

    def _qdr_delay_inout_step(self, inout, bitmask, step):
        """
        Steps all bits in bitmask by 'step' number of taps.

        :param bitmask:
        :param step:
        """
        if step == 0:
            return
        self._control_mem_write(0 if step < 0 else 0xffffffff, 7)
        if inout == 'in':
            offset = 4
            maskval = 0xf & (bitmask >> 32)
        elif inout == 'out':
            offset = 6
            maskval = (0xf & (bitmask >> 32)) << 4
        else:
            raise ValueError('Unknown delay type: {}'.format(inout))
        for _ctr in range(abs(step)):
            self._control_mem_write(0, offset)
            self._control_mem_write(0, 5)
            self._control_mem_write(0xffffffff & bitmask, offset)
            self._control_mem_write(maskval, 5)

    def _qdr_delay_out_step(self, bitmask, step):
        """
        Steps all bits in bitmask by 'step' number of taps.

        :param bitmask:
        :param step:
        """
        self._qdr_delay_inout_step('out', bitmask, step)

    def _qdr_delay_in_step(self, bitmask, step):
        """
        Steps all bits in bitmask by 'step' number of taps.

        :param bitmask:
        :param step:
        :return:
        """
        self._qdr_delay_inout_step('in', bitmask, step)

    def _qdr_delay_clk_get(self):
        """
        Gets the current value for the clk delay.
        """
        raw = self.p_read_uint(self.control_mem, word_offset=8)
        if (raw & 0x1f) != ((raw & (0x1f << 5)) >> 5):
            raise RuntimeError('Counter values not the same -- logic error! '
                               'Got back %i.' % raw)
        return raw & 0x1f

    def qdr_cal_check(self, step=-1, quickcheck=True):
        """
        Checks calibration on a qdr. Raises an exception if it failed.

        :param step: the current step
        :param quickcheck: if True, return after the first error, else process
            all test vectors before returning
        """
        patfail = 0
        for pattern in CAL_DATA:
            data_format = '>%iL' % len(pattern)
            self.p_bwrite(
                self.memory, struct.pack(data_format, *pattern))
            curr_val = self.p_read(self.memory, len(pattern)*4)
            curr_val = struct.unpack(data_format, curr_val)
            for word_n, word in enumerate(pattern):
                faildiff = word ^ curr_val[word_n]
                # logl2('step({}) written({:032b}) read({:032b}) '
                #       'faildiff({:032b})'.format(step, word,
                #                                  curr_val[word_n], patfail))
                if faildiff and quickcheck:
                    return False, faildiff
                patfail |= faildiff
        return patfail == 0, patfail

    def _find_in_delays(self):
        """
        :return:
        """
        per_step_fail = []
        per_bit_cal = [[] for _ in range(QDR_WW_LIMITED)]
        logl2('QDR({}) checking cal over {} steps'.format(
            self.name, NUM_DELAY_TAPS))
        for step in range(NUM_DELAY_TAPS):
            # check this step
            res, fail_pattern = self.qdr_cal_check(step, False)
            per_step_fail.append(fail_pattern)
            # check each bit of the failure pattern
            for bit in range(QDR_WW_LIMITED):
                masked_bit = (fail_pattern >> bit) & 0x01
                bit_value = -1 if masked_bit else 1
                per_bit_cal[bit].append(bit_value)
            logl3('\tstep input delays to {}'.format(step+1))
            self._qdr_delay_in_step(0xfffffffff, 1)

        # print(the failure patterns)
        logl2('Eye for QDR {:s} (0 is pass, 1 is fail):'.format(self.name))
        for step, fail_pattern in enumerate(per_step_fail):
            logl2('\tdelay_step {:2d}: {:032b}'.format(step, fail_pattern))
        # print(the per-bit eye diagrams)
        logl3('Per-bit cal:')
        for bit, bit_eye in enumerate(per_bit_cal):
            logl3('\tbit_{:d}: {}'.format(bit, bit_eye))

        # # find indices where calibration passed and failed:
        # for bit in range(n_bits):
        #     try:
        #         bit_cal[bit].index(1)
        #     except ValueError:
        #         raise RuntimeError('Calibration failed for bit %i.' % bit)
        # logl0('valid_steps for bit {} {}'.format(bit, valid_steps[bit]))

        cal = {
            'steps': numpy.array([0] * (QDR_WW_LIMITED + 4)),
            'area': numpy.array([0] * QDR_WW_LIMITED),
            'start': numpy.array([0] * QDR_WW_LIMITED),
            'stop': numpy.array([0] * QDR_WW_LIMITED)
        }
        # for each bit, calculate the area that is best calibrated
        for bit, bit_eye in enumerate(per_bit_cal):
            area, start, stop = find_cal_area(bit_eye)
            if area < MINIMUM_WINDOW_LENGTH:
                raise RuntimeError('Could not find a robust calibration '
                                   'setting for QDR %s' % self.name)
            # original was 1/2
            # running on /4 for some months, but seems to be giving errors
            # with hot roaches
            cal['start'][bit] = start
            cal['stop'][bit] = stop
            cal['steps'][bit] = (start + stop) // 2
            # cal['steps'][bit] = (start + stop) // 3
            # cal['steps'][bit] = (start + stop) // 4

        # since we don't have access to bits 32-36, we guess the number of
        # taps required based on the lower 32 bits:
        # MEDIAN
        median_taps = numpy.median(cal['steps'])
        logl1('Median taps: {}'.format(median_taps))
        for bit in range(QDR_WW_LIMITED, QDR_WORD_WIDTH):
            cal['steps'][bit] = median_taps

        logl1('Selected per-bit delays: {}'.format(cal['steps']))

        # # MEAN
        # mean_taps = numpy.mean(cal_steps)
        # logl1('Mean taps: {}'.format(mean_taps))
        # for bit in range(32, QDR_WORD_WIDTH):
        #     cal_steps[bit] = mean_taps
        #     logl1('Selected tap for bit {}: {}'.format(
        #         bit, cal_steps[bit]))

        return cal['steps'], cal['area'], cal['start'], cal['stop']

    def _apply_calibration(self, in_delays, out_delays, clk_delay, extra_clk=0):
        """

        :param in_delays:
        :param out_delays:
        :param clk_delay:
        :param extra_clk:
        """
        assert len(in_delays) == QDR_WORD_WIDTH
        assert len(out_delays) == QDR_WORD_WIDTH

        # reset all the taps to zero
        self.qdr_reset()

        if USE_JACK_CAL:
            self._add_extra_latency(extra_clk)

        self._qdr_delay_clk_step(clk_delay)

        for delays, delaypref in [(in_delays, 'in'), (out_delays, 'out')]:
            _maxdelay = int(max(delays))
            if _maxdelay == 0:
                logl2('No {}put delays to apply'.format(delaypref))
            else:
                logl1('Applying {}put delays up to {}:'.format(
                    delaypref, _maxdelay))
            for step in range(_maxdelay):
                mask = 0
                for bit in range(len(delays)):
                    mask += (1 << bit if (step < delays[bit]) else 0)
                logl1('\tstep {} {} {:036b}'.format(delaypref, step, mask))
                self._qdr_delay_inout_step(delaypref, mask, 1)

    def qdr_cal(self, fail_hard=True):
        if not USE_JACK_CAL:
            return self._qdr_cal_ours(fail_hard)
        else:
            return self._qdr_cal_jacks(fail_hard)

    def _qdr_cal_ours(self, fail_hard=True):
        """
        Calibrates a QDR controller, stepping input delays and (if that fails)
        output delays. Returns True if calibrated, raises a runtime
        exception if it doesn't.

        :param fail_hard:
        """
        cal = False
        failure_pattern = 0xffffffff
        out_step = 0
        while (not cal) and (out_step < NUM_DELAY_TAPS - 1):
            # reset all the in delays to zero, and the out delays to
            # this iteration.
            in_delays = [0] * QDR_WORD_WIDTH
            _out_delays = [out_step] * QDR_WORD_WIDTH
            _current_step = self._qdr_delay_clk_get()
            logl1('Output delay: current({}) set_to({})'.format(
                _current_step, out_step))
            self._apply_calibration(in_delays=in_delays,
                                    out_delays=_out_delays,
                                    clk_delay=out_step)
            try:
                in_delays, area, start, stop = self._find_in_delays()
            except AssertionError:
                in_delays = [0] * QDR_WORD_WIDTH
            except Exception as e:
                raise RuntimeError('Unknown exception in qdr_cal - '
                                   '{!s}'.format(e.message))

            # update the out delays with the current input delays
            _out_delays = [out_step] * QDR_WORD_WIDTH
            self._apply_calibration(in_delays=in_delays,
                                    out_delays=_out_delays,
                                    clk_delay=out_step)
            cal, failure_pattern = self.qdr_cal_check()
            out_step += 1

        if (not cal) and fail_hard:
            raise RuntimeError('QDR %s calibration failed.' % self.name)
        return cal, failure_pattern

    def qdr_check_cal_any_good(self, current_step, checkoffset=2**22):
        """
        Checks calibration on a qdr.

        :param current_step: what is the current output delay step
        :param checkoffset: where to write the test data
        :return: True if *any* of the bits were good
        """
        patfail = 0
        for pn, pattern in enumerate(CAL_DATA):
            logl2('pattern[0]: {:x}'.format(pattern[0]))
            _patternstr = '>%iL' % len(pattern)
            _wrdata = struct.pack(_patternstr, *pattern)
            self.p_bwrite(self.memory, _wrdata, offset=checkoffset)
            _rdata = self.p_read(self.memory, len(pattern) * 4,
                                 offset=checkoffset)
            retdat = struct.unpack(_patternstr, _rdata)
            for word_n, word in enumerate(pattern):
                patfail |= word ^ retdat[word_n]
                # logl2('\tcurstep({}) written({:032b}) read({:032b}) '
                #       'faildiff({:032b})'.format(current_step, word,
                #                                  retdat[word_n], patfail))
                if patfail == 0xffffffff:
                    # none of the bits were correct, so bail
                    logl2('No good bits found, bailing.')
                    return False
        return True

    def _scan_out_to_edge(self):
        """
        Step through the possible output delays. When any of the bits are OK,
        use this as the start point for the input delay scan. This makes life
        a little simpler than letting the input and output delays of all bits
        be completely independent.
        
        If no good bits are found, that's fine, we'll just leave the output
        delay set to the maximum allowed
        """
        out_step = 0
        for out_step in range(NUM_DELAY_TAPS):
            if self.qdr_check_cal_any_good(out_step):
                break
            if out_step < NUM_DELAY_TAPS - 1:
                self._qdr_delay_out_step(2**QDR_WORD_WIDTH - 1, 1)
                self._qdr_delay_clk_step(1)
        return out_step

    def _qdr_cal_jacks(self, fail_hard=True, min_eye_width=8):
        """
        Calibrates a QDR controller
        Step output delays until some of the bits reach their eye.
        Then step input delays
        Returns True if calibrated, raises a runtime exception if it doesn't.

        :param fail_hard: throw an exception on cal fail if True, else
            return False
        :param min_eye_width: What is the minimum eye width we'll accept?
        """
        def _find_out_delay(add_extra_latency=False):
            # reset all delays and set extra latency to zero.
            self.qdr_reset()
            self._disable_fabric()
            if add_extra_latency:
                self._add_extra_latency(1)
            # find the first output delay that may work with no input delay
            out_step = self._scan_out_to_edge()
            logl1('Output delays set to {}'.format(out_step))
            # find input delays for this output delay
            in_dels, areas, starts, stops = self._find_in_delays()
            return out_step, in_dels, areas, starts, stops

        # find an initial solution
        out_step0, in_delays0, good_area0, good_starts0, \
            good_stops0 = _find_out_delay()

        # if any of the calibration eyes are less than some minimum width,
        # and there is a chance that adding an extra cycle of latency will
        # help, give that a go!
        # Default values to replace if we rescan
        in_delays = in_delays0
        out_delay = out_step0
        extra_clk = False
        max_input_delay_required = numpy.any(good_stops0 == NUM_DELAY_TAPS-1)
        eyes_too_small = numpy.any(good_area0 < min_eye_width)
        if max_input_delay_required and eyes_too_small:
            logl1('Adding extra latency and checking for better solutions')
            out_step1, in_delays1, good_area1, good_starts1, \
                good_stops1 = _find_out_delay()
            if numpy.all(good_area1 > good_area0):
                logl1('New solutions with extra latency are better')
                in_delays = in_delays1
                out_delay = out_step1
                extra_clk = True
            else:
                logl1('Original solution without extra latency was better')

        logl1('Using in delays: {}'.format(in_delays))
        self._apply_calibration(in_delays=in_delays,
                                out_delays=[out_delay] * QDR_WORD_WIDTH,
                                clk_delay=out_delay,
                                extra_clk=extra_clk)

        cal, failure_pattern = self.qdr_cal_check()
        self._enable_fabric()
        if (not cal) and fail_hard:
            raise RuntimeError('QDR %s calibration failed.' % self.name)
        return cal, failure_pattern

# end
