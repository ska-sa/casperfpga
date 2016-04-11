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

QDR_WORD_WIDTH = 36

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


def find_cal_area(a):
    """

    :param a:
    :return:
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

        # set the 'verbosity' flag for the QDR
        self.verbosity = 0
        
        LOGGER.debug('New Qdr %s' % self)
        # TODO - Link QDR ctrl register to self.registers properly

    @classmethod
    def from_device_info(cls, parent, device_name, device_info, memorymap_dict):
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

        :return:
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
        :return: 
        """
        self.p_write_int(self.control_mem, value,
                         blindwrite=True, word_offset=offset)

    def qdr_reset(self):
        """
        Resets the QDR and the IO delays (sets all taps=0).
        """
        self._control_mem_write(1, 0)
        self._control_mem_write(0, 0)

    def qdr_delay_out_step(self, bitmask, step):
        """
        Steps all bits in bitmask by 'step' number of taps.
        :param bitmask:
        :param step:
        """
        if step == 0:
            return
        self._control_mem_write(0 if step < 0 else 0xffffffff, 7)
        for _ctr in range(abs(step)):
            self._control_mem_write(0, 6)
            self._control_mem_write(0, 5)
            self._control_mem_write(0xffffffff & bitmask, 6)
            self._control_mem_write((0xf & (bitmask >> 32)) << 4, 5)

    def qdr_delay_clk_step(self, step):
        """
        Steps the output clock by 'step' amount.
        :param step:
        """
        if step == 0:
            return
        self._control_mem_write(0 if step < 0 else 0xffffffff, 7)
        for _ctr in range(abs(step)):
            self._control_mem_write(0, 5)
            self._control_mem_write(1 << 8, 5)

    def qdr_delay_in_step(self, bitmask, step):
        """
        Steps all bits in bitmask by 'step' number of taps.
        :param bitmask:
        :param step:
        :return:
        """
        if step == 0:
            return
        self._control_mem_write(0 if step < 0 else 0xffffffff, 7)
        for _ctr in range(abs(step)):
            self._control_mem_write(0, 4)
            self._control_mem_write(0, 5)
            self._control_mem_write(0xffffffff & bitmask, 4)
            self._control_mem_write(0xf & (bitmask >> 32), 5)

    def qdr_delay_clk_get(self):
        """
        Gets the current value for the clk delay.
        :return:
        """
        raw = self.p_read_uint(self.control_mem, word_offset=8)
        if (raw & 0x1f) != ((raw & (0x1f << 5)) >> 5):
            raise RuntimeError('Counter values not the same -- logic error! '
                               'Got back %i.' % raw)
        return raw & 0x1f

    def qdr_cal_check(self):
        """
        Checks calibration on a qdr. Raises an exception if it failed.
        :return:
        """
        patfail = 0
        for pattern in CAL_DATA:
            data_format = '>%iL' % len(pattern)
            self.p_bwrite(
                self.memory, struct.pack(data_format, *pattern))
            curr_val = self.p_read(self.memory, len(pattern)*4)
            curr_val = struct.unpack(data_format, curr_val)
            for word_n, word in enumerate(pattern):
                patfail = patfail | (word ^ curr_val[word_n])
                if self.verbosity > 2:
                    print '{0:032b}'.format(word),
                    print '{0:032b}'.format(curr_val[word_n]),
                    print '{0:032b}'.format(patfail)
        if patfail > 0:
            # raise RuntimeError('Calibration of QDR%i failed: 0b%s.' % (
            #     qdr, '{0:032b}'.format(patfail)))
            return False
        else:
            return True

    def find_in_delays(self):
        """
        :return: 
        """
        n_steps = 32
        n_bits = 32
        fail = []
        bit_cal = []
        valid_steps = []
        for ctr in range(n_bits):
            bit_cal.append([])
            valid_steps.append([])
        for step in range(n_steps):
            patfail = 0
            for pattern in CAL_DATA:
                data_format = '>%iL' % len(pattern)
                self.p_bwrite(
                    self.memory, struct.pack(data_format, *pattern))
                curr_val = self.p_read(self.memory, len(pattern)*4)
                curr_val = struct.unpack(data_format, curr_val)
                for word_n, word in enumerate(pattern):
                    patfail |= word ^ curr_val[word_n]
                    if self.verbosity > 2:
                        print '\t %4i %4i' % (step, word_n),
                        print '{0:032b}'.format(word),
                        print '{0:032b}'.format(curr_val[word_n]),
                        print '{0:032b}'.format(patfail)
            fail.append(patfail)
            for bit in range(n_bits):
                bitval = 1 - 2 * ((fail[step] & (1 << bit)) >> bit)
                bit_cal[bit].append(bitval)
                # if bit_cal[bit][step]==True:
                #     valid_steps[bit].append(step)
            if self.verbosity > 2:
                print 'STEP input delays to %i!' % (step+1)
            self.qdr_delay_in_step(0xfffffffff, 1)

        if self.verbosity > 0:
            print 'Eye for QDR %s (0 is pass, 1 is fail):' % self.name
            for step in range(n_steps):
                print '\tTap step %2i: ' % step,
                print '{0:032b}'.format(fail[step])

        if self.verbosity > 3:
            for bit in range(n_bits):
                print 'Bit %2i: ' % bit,
                print bit_cal[bit]

        # find indices where calibration passed and failed:
        for bit in range(n_bits):
            try:
                bit_cal[bit].index(1)
            except ValueError:
                raise RuntimeError('Calibration failed for bit %i.' % bit)

        # if (self.verbosity > 0):
        #     print 'valid_steps for bit %i' % (bit), valid_steps[bit]

        # find the largest contiguous cal area
        cal_steps = numpy.zeros(n_bits + 4)
        for bit in range(n_bits):
            cal_area = find_cal_area(bit_cal[bit])
            if cal_area[0] < 4:
                raise RuntimeError('Could not find a robust calibration '
                                   'setting for QDR %s' % self.name)
            # original was 1/2
            # running on /4 for some months, but seems to be giving errors
            # with hot roaches
            cal_steps[bit] = sum(cal_area[1:3])/2
            # cal_steps[bit] = sum(cal_area[1:3])/3
            # cal_steps[bit] = sum(cal_area[1:3])/4
            if self.verbosity > 1:
                print 'Selected tap for bit %i: %i' % (bit, cal_steps[bit])

        # since we don't have access to bits 32-36, we guess the number of
        # taps required based on the other bits:
        # MEDIAN
        median_taps = numpy.median(cal_steps)
        if self.verbosity > 1:
            print 'Median taps: %i' % median_taps
        for bit in range(32, QDR_WORD_WIDTH):
            cal_steps[bit] = median_taps
            if self.verbosity > 1:
                print 'Selected tap for bit %i: %i' % (bit, cal_steps[bit])

        # # MEAN
        # mean_taps = numpy.mean(cal_steps)
        # if self.verbosity > 1:
        #     print 'Mean taps: %i' % mean_taps
        # for bit in range(32, QDR_WORD_WIDTH):
        #     cal_steps[bit] = mean_taps
        #     if self.verbosity > 1:
        #         print 'Selected tap for bit %i: %i' % (bit, cal_steps[bit])

        return cal_steps

    def apply_cals(self, in_delays, out_delays, clk_delay):
        """

        :param in_delays:
        :param out_delays:
        :param clk_delay:
        :return:
        """
        # reset all the taps to default (0)
        self.qdr_reset()
        assert len(in_delays) == QDR_WORD_WIDTH
        assert len(out_delays) == QDR_WORD_WIDTH

        self.qdr_delay_clk_step(clk_delay)

        for step in range(int(max(in_delays))):
            mask = 0
            for bit in range(len(in_delays)):
                mask += (1 << bit if (step < in_delays[bit]) else 0)
            if self.verbosity > 1:
                print 'Step %i' % step,
                print '{0:036b}'.format(mask)
            self.qdr_delay_in_step(mask, 1)

        for step in range(int(max(out_delays))):
            mask = 0
            for bit in range(len(out_delays)):
                mask += (1 << bit if (step < out_delays[bit]) else 0)
            if self.verbosity > 1:
                print 'Step out %i' % step,
                print '{0:036b}'.format(mask)
            self.qdr_delay_out_step(mask, 1)

    def qdr_cal(self, fail_hard=True):
        """
        Calibrates a QDR controller, stepping input delays and (if that fails)
        output delays. Returns True if calibrated, raises a runtime
        exception if it doesn't.
        :param fail_hard:
        :return:
        """
        cal = False
        out_step = 0
        while (not cal) and (out_step < 32):
            # reset all the in delays to zero, and the out delays to
            # this iteration.
            in_delays = [0] * QDR_WORD_WIDTH
            self.apply_cals(in_delays, out_delays=[out_step] * QDR_WORD_WIDTH,
                            clk_delay=out_step)
            if self.verbosity > 0:
                print '--- === Trying with OUT DELAYS to %i === ---' % out_step,
                print 'was: %i' % self.qdr_delay_clk_get()
            try:
                in_delays = self.find_in_delays()
            except AssertionError:
                in_delays = [0] * QDR_WORD_WIDTH
            except Exception as e:
                raise RuntimeError('Unknown exception in qdr_cal '
                                   '- %s' % e.message)
            self.apply_cals(in_delays, out_delays=[out_step] * QDR_WORD_WIDTH,
                            clk_delay=out_step)
            cal = self.qdr_cal_check()
            out_step += 1
        if self.qdr_cal_check():
            return True
        else:
            if fail_hard:
                raise RuntimeError('QDR %s calibration failed.' % self.name)
            else:
                return False

# end
