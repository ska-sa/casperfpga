from matplotlib import pyplot as plt
import sys
import time

def make_wave(x):
    s = ""
    for n in range(len(x)):
        if n==0:
            if(x[n]):
                s += "-"
            else:
                s +="_"
            continue
        # now high was low
        if (x[n] and not(x[n-1])):
            s += "/"
        # remain high
        elif (x[n] and x[n-1]):
            s += "-"
        # remain low
        elif (int(not(x[n]) and not(x[n-1]))):
            s += "_"
        # now low was high
        elif (not(x[n]) and x[n-1]):
            s += "\\"
        else:
            print("I am impossible!")
    return s

def print_waveforms(sclk, mosi, cs):
    cs_str = "".join(["%d" % x for x in cs])
    mosi_str = make_wave(mosi)
    sclk_str = make_wave(sclk)
    print("SCLK: %s" % sclk_str)
    print("MOSI: %s" % mosi_str)
    print("CS  : %s" % cs_str)
            
   

class ADS5296():
    def print(self,x):
        if not self.quiet:
            print(x)

    def __init__(self, fpga):
        self.quiet = True
        self.fpga = fpga
        #self.ctrl_reg = "ads5296_controller%d" % board_id
    
    def set_spi_out(self, sclk, mosi, cs, fmc):
        #v = ((mosi & 1) << 4) + ((sclk & 1) << 3) + (cs & 0b111)
        # From Larry:
        #signal     spreadsheet     actual
        #cs[0] CSO  LA33_P          LA32_P
        #cs[1] CS1  LA33_N          LA32_N
        #MOSI = SDA LA32_P          LA33_P
        #SCLK = SCL LA32_N          LA33_N
        # register is based on spreadsheet values:
        # bit0 = cs0
        # bit1 = cs1
        # bit2 = cs2
        # bit3 = sclk
        # bit4 = mosi

        # Need to swap cs0 <-> MOSI; cs1 <-> SCLK
        # bit0 = mosi
        # bit1 = sclk
        # bit2 = cs2
        # bit3 = cs1
        # bit4 = cs0
        v = ((cs & 1) << 4) + (((cs >> 1) & 1) << 3) + (((cs >> 2) & 1) << 2) + ((sclk & 1) << 1) + (mosi & 1)
        self.fpga.write_int("ads5296_spi_out%d"%fmc, v)
        return sclk, mosi, cs

    def get_spi_in(self, fmc):
        return self.fpga.read_uint("ads5296_spi_in%d"%fmc)

    def assert_reset(self, fmc):
        self.fpga.write_int("ads5296_rst%d"%fmc, 1)

    def deassert_reset(self, fmc):
        self.fpga.write_int("ads5296_rst%d"%fmc, 0)

    def assert_sync(self, fmc):
        self.fpga.write_int("ads5296_sync%d"%fmc, 1)

    def deassert_sync(self, fmc):
        self.fpga.write_int("ads5296_sync%d"%fmc, 0)

    def send_spi(self, addr, val, cs, fmc, show_diagram=False):
        NBITS = 24
        # record SPI so we can plot
        spi = []
        data = ((addr & 0xff) << 16) + (val & 0xffff)
        # set clock high and cs to something we don't care about
        cs = cs & 0b111
        spi += self.set_spi_out(1, 0, (cs+1)&0b111, fmc)
        # lower cs
        spi+= self.set_spi_out(1, 0, cs, fmc)
        # set data and toggle clock
        dout = 0
        for i in range(NBITS):
            # lower clock
            spi += self.set_spi_out(0, 0, cs, fmc)
            # set data
            spi += self.set_spi_out(0, (data >> (NBITS - 1 - i)) & 1, cs, fmc)
            # assert clock
            spi += self.set_spi_out(1, (data >> (NBITS - 1 - i)) & 1, cs, fmc)
            # get miso bit
            dout += (self.get_spi_in(fmc) << (NBITS - 1 - i))
        # once we get to here we've sent / received all the data and the clock is still high
        # deassert cs
        spi += self.set_spi_out(1, (data & 1), (cs+1)&0b111, fmc)
        #print("SCLK: %s" % spi[0::3])
        #print("MOSI: %s" % spi[1::3])
        #print("CS  : %s" % spi[2::3])
        if show_diagram:
            print_waveforms(spi[0::3], spi[1::3], spi[2::3])
        #if plot:
        #    print("plotting")
        #    plt.figure()
        #    plt.subplot(1,3,1)
        #    plt.plot(spi[0::3], label="SCLK")
        #    plt.legend()
        #    plt.subplot(1,3,2)
        #    plt.plot(spi[1::3], label="MOSI")
        #    plt.legend()
        #    plt.subplot(1,3,3)
        #    plt.plot(spi[2::3], label="CS")
        #    plt.legend()
        #    plt.show()
        return dout

    def disable_readout(self, cs, fmc):
        self.send_spi(1, 0, cs, fmc)

    def enable_readout(self, cs, fmc):
        self.send_spi(1, 1, cs, fmc)

    def read_spi(self, addr, cs, fmc):
        # put everyone out of read mode
        for i in range(8):
            self.disable_readout(i, fmc)
        # put the chip we want to read in read mode
        self.enable_readout(cs, fmc)
        # read value
        d = self.send_spi(addr, 0, cs, fmc)
        # put the chip back in write mode
        self.disable_readout(cs, fmc)
        return d

    #def _write(self, data, offset=0):
    #    # Don't do a blind write. The successful readback will
    #    # verify that the SPI transaction completed, and was ack'd
    #    # by the wishbone core.
    #    self.print("WB writing 0x%x to offset 0x%x" % (data, offset))
    #    self.fpga.write_int(self.ctrl_reg, data, word_offset=offset)

    #def _read(self, offset=0):
    #    return self.fpga.read_uint(self.ctrl_reg, word_offset=offset)

    #def write_spi(self, addr, data, chip):
    #    addr = addr & 0xff
    #    data = data & 0xffff
    #    self.print("Writing 0x%x to address 0x%x, CS:0x%x" % (data, addr, chip))
    #    payload = (addr << 16) + data
    #    self._write(payload, 1)
    #    self._write(chip, 0)

    #def disable_readout(self, chip):
    #    self.print("Writing 0x%x to address 0x%x, CS:0x%x" % (0, 1, chip))
    #    self.write_spi(1, 0, chip)

    #def enable_readout(self, chip):
    #    # Disable readout for all chips
    #    for i in range(8):
    #        self.disable_readout(i)
    #    self.print("Writing 0x%x to address 0x%x, CS:0x%x" % (1, 1, chip))
    #    self.write_spi(1, 1, chip)
    #        
    #def read_spi(self, addr, chip):
    #    self.enable_readout(chip)
    #    self.write_spi(addr, 0xaabb, chip)
    #    x = self._read(offset=2)
    #    self.disable_readout(chip)
    #    return x
        
class ADS5296fw():
    def print(self,x):
        if not self.quiet:
            print(x, file=sys.stderr)

    def __init__(self, fpga, fmc=0):
        self.quiet = True
        self.fpga = fpga
        self.fmc = fmc
        self.spi_ctrl_reg = "ads5296_spi_controller%d" % fmc

    def init(self, cs):
        self.reset(cs)
        print("CS:%d 0x0 (wrote 1) "%cs, hex(self.read_spi(0, cs)), file=sys.stderr)
        self.write_spi(0x0F, 0x0400, cs) # power down pin partial
        print("CS:%d 0x0f (wrote 0x0400)"%cs, hex(self.read_spi(0x0F, cs)), file=sys.stderr)
        self.write_spi(0x07, 0x0001, cs) # enable interleave
        print("CS:%d 0x07 (wrote 0x0001)"%cs, hex(self.read_spi(0x07, cs)), file=sys.stderr)
        #self.write_spi(0x42, 0x8000, cs) # DDR phase
        #print("CS:%d"%cs, hex(self.read_spi(0x42, cs)))
        self.write_spi(0x46, 0x8104, cs) # 10b serialization, LSB first, 2's complement, DDR
        #self.write_spi(0x46, 0x8100, cs) # 10b serialization, LSB first, offset binary, DDR
        print("CS:%d 0x46 (wrote 0x8104)"%cs, hex(self.read_spi(0x46, cs)), file=sys.stderr)
        self.write_spi(0x40, 0x8000, cs) # input selection
        print("CS:%d 0x40 (wrote 0x8000)"%cs, hex(self.read_spi(0x40, cs)), file=sys.stderr)
        self.write_spi(0x25, 0x8000, cs) # Enable external sync
        print("CS:%d 0x25 (wrote 0x8000)"%cs, hex(self.read_spi(0x25, cs)), file=sys.stderr)
        print("Enabling VTC on IDELAYs", file=sys.stderr)
        self.enable_vtc_data(range(8), cs)
        self.enable_vtc_fclk(cs)

    def get_fclk_err_cnt(self, board):
        return self._read_ctrl(7, board)

    def bitslip(self, channel, board):
        self._write_ctrl(0, 15, board)
        self._write_ctrl(1<<channel, 15, board)
        self._write_ctrl(0, 15, board)

    def set_clock_source(self, source, board):
        x = self._read_ctrl(9, board)
        reset_state = x & 0xff
        if source == board:
            clksel = 0
        else:
            clksel = 1
        self._write_ctrl((clksel << 8) + reset_state, 9, board)

    def calibrate_fclk(self, board, apply_to_fclk=True, apply_to_data=True):
        NTAPS = 512
        STEP_SIZE = 4
        NSTEPS = NTAPS // STEP_SIZE
        self.enable_rst_fclk(board*4)
        self.disable_rst_fclk(board*4)
        self.disable_vtc_fclk(board*4)
        errs = []
        for i in range(0, NTAPS, STEP_SIZE):
            self.load_delay_fclk(i, board * 4)
            c0 = self.get_fclk_err_cnt(board)
            c1 = self.get_fclk_err_cnt(board)
            if c1 < c0:
                print("!!!!!", c0, c1)
                c1 += 2**32
            errs += [c1 - c0]
            print("FCLK cal: %d: %d errs" % (i, errs[-1]), file=sys.stderr)
        slack = []
        for i in range(NSTEPS):
            #count number of zeros before this slot
            count_before = 0
            for j in range(i, 0, -1):
                if errs[j] == 0:
                    count_before += 1
                else:
                    break 
            #count number of zeros after this slot
            count_after= 0
            for j in range(i, NSTEPS, 1):
                if errs[j] == 0:
                    count_after += 1
                else:
                    break
            slack += [min(count_before, count_after)]
        delay = slack.index(max(slack)) * STEP_SIZE
        if apply_to_fclk:
            self.load_delay_fclk(delay, board*4)
        if apply_to_data:
            for cs in range(4*board, 4*(board+1)):
                self.enable_rst_data(range(8), cs)
                self.disable_rst_data(range(8), cs)
                self.disable_vtc_data(range(8), cs)
                self.load_delay_data(delay, range(8), cs)
                #self.load_delay_data(511, range(8), cs)
                self.enable_vtc_data(range(8), cs)
        self.enable_vtc_fclk(board*4)
        return delay, slack[delay // STEP_SIZE]

    def _write_ctrl(self, data, offset=0, board=0):
        #print("Writing 0x%8x to address %d of controller %d" % (data, offset, board))
        self.fpga.write_int("ads5296_controller%d_%d" % (self.fmc, board), data, word_offset=offset, blindwrite=True)

    def _read_ctrl(self, offset=0, board=0):
        return self.fpga.read_uint("ads5296_controller%d_%d" % (self.fmc, board), word_offset=offset)

    def reset_mmcm_assert(self, board):
        x = self._read_ctrl(offset=9, board=board)
        self._write_ctrl(x | 0b1, offset=9, board=board)

    def reset_mmcm_deassert(self, board):
        x = self._read_ctrl(offset=9, board=board)
        self._write_ctrl(x &~0b1, offset=9, board=board)

    def trigger_snapshot(self, board):
        self._write_ctrl(0, offset=16, board=board)
        self._write_ctrl(1, offset=16, board=board)
        self._write_ctrl(0, offset=16, board=board)

    def reset_mmcm(self, board):
        self.reset_mmcm_assert(board)
        self.reset_mmcm_deassert(board)

    def mmcm_get_lock(self, board):
        """
        Get a board's MMCM lock status.
        Return True if MMCM is locked, False if not. Or,
        return None if the MMCM doesn't exist for this board
        (because it is using another board's clocks)
        """
        x = self._read_ctrl(offset=9, board=board)
        master = bool(x & (1<<24))
        locked = bool(x & (1<<16))
        if master:
            return locked
        else:
            return None

    def reset_iserdes(self, board):
        self._write_ctrl(1, offset=8, board=board)
        self._write_ctrl(0, offset=8, board=board)

    def enable_vtc_data(self, pins, cs):
        board = cs // 4
        chip = cs % 4
        d = 0
        for pin in pins:
            d += (1 << pin)
        d = d << (8*chip)
        current = self._read_ctrl(offset=4, board=board)
        new = current | d
        self._write_ctrl(new, offset=4, board=board)

    def disable_vtc_data(self, pins, cs):
        board = cs // 4
        chip = cs % 4
        d = 2**32 - 1
        for pin in pins:
            d -= ((1 << pin) << (8*chip))
        current = self._read_ctrl(offset=4, board=board)
        new = current & d
        self._write_ctrl(new, offset=4, board=board)

    def enable_vtc_fclk(self, cs):
        board = cs // 4
        self._write_ctrl(1, offset=5, board=board)

    def disable_vtc_fclk(self, cs):
        board = cs // 4
        self._write_ctrl(0, offset=5, board=board)

    def enable_rst_data(self, pins, cs):
        board = cs // 4
        chip = cs % 4
        d = 0
        for pin in pins:
            d += (1 << pin)
        d = d << (8*chip)
        current = self._read_ctrl(offset=2, board=board)
        new = current | d
        self._write_ctrl(new, offset=2, board=board)

    def disable_rst_data(self, pins, cs):
        board = cs // 4
        chip = cs % 4
        d = 2**32 - 1
        for pin in pins:
            d -= ((1 << pin) << (8*chip))
        current = self._read_ctrl(offset=2, board=board)
        new = current & d
        self._write_ctrl(new, offset=2, board=board)

    def enable_rst_fclk(self, cs):
        board = cs // 4
        self._write_ctrl(1, offset=3, board=board)

    def disable_rst_fclk(self, cs):
        board = cs // 4
        self._write_ctrl(0, offset=3, board=board)

    def load_delay_data(self, delay, pins, cs):
        board = cs // 4
        chip = cs % 4
        d = 2**32 - 1
        #self.disable_vtc_data(pins, cs)
        # Disable all writes
        self._write_ctrl(0, offset=0, board=board)
        self._write_ctrl(0, offset=1, board=board)
        self._write_ctrl(delay, offset=6, board=board)
        d = 0
        for pin in pins:
            d += (1 << pin)
        d = d << (8*chip)
        #print("delaying %s of chip %d board %d by %d" % (str(pins), cs, board, delay))
        #print("%x" % d)
        self._write_ctrl(d, offset=0, board=board)
        self._write_ctrl(0, offset=0, board=board)
        #self.enable_vtc_data(pins, cs)

    def load_delay_fclk(self, delay, cs):
        board = cs // 4
        chip = cs % 4
        d = 2**32 - 1
        # Disable VTC
        #self.disable_vtc_fclk(cs)
        # Disable all writes
        self._write_ctrl(0, offset=0, board=board)
        self._write_ctrl(0, offset=1, board=board)
        self._write_ctrl(delay, offset=6, board=board)
        self._write_ctrl(1, offset=1, board=board)
        self._write_ctrl(0, offset=1, board=board)
        #self.enable_vtc_fclk(cs)

    def enable_test_pattern(self, mode, cs, val0=0x3ff, val1=0x000):
        if mode == "ramp":
            val = 0b100
        elif mode == "toggle":
            val = 0b010
        elif mode == "constant":
            val = 0b001
        elif mode == "data":
            val = 0b000
        else:
            print("Error, test mode not understood. Try 'ramp', 'toggle', 'data', or 'constant'")
        val0 = val0 << 2
        val1 = val1 << 2
        self.write_spi(0x26, (val0 & 0x3ff) << 6, cs)
        self.write_spi(0x27, (val1 & 0x3ff) << 6, cs)
        # set pattern selection
        # 1<<15 enables the external sync enable bit
        self.write_spi(0x25, (1<<15) + (val<<4) + ((val1 >> 10)<<2) + (val0 >> 10), cs)
    
    def reset(self, cs):
        self.write_spi(0, 1, cs, readback=False) # The reset register auto-clears

    def assert_sync(self, fmc):
        self.fpga.write_int("sync", 1)

    def deassert_sync(self, fmc):
        self.fpga.write_int("sync", 0)

    def disable_readout(self, cs):
        self.blindwrite_spi(1, 0, cs)

    def enable_readout(self, cs):
        self.blindwrite_spi(1, 1, cs)

    def read_spi(self, addr, cs):
        # put everyone out of read mode
        for i in range(8):
            self.disable_readout(i)
        # put the chip we want to read in read mode
        self.enable_readout(cs)
        # read value
        d = self.blindwrite_spi(addr, 0, cs, readback=True)
        # put the chip back in write mode
        self.disable_readout(cs)
        return d

    def _write(self, data, offset=0):
        # Don't do a blind write. The successful readback will
        # verify that the SPI transaction completed, and was ack'd
        # by the wishbone core.
        #self.print("WB writing 0x%x to offset 0x%x" % (data, offset))
        self.fpga.write_int(self.spi_ctrl_reg, data, word_offset=offset)

    def _read(self, offset=0):
        return self.fpga.read_uint(self.spi_ctrl_reg, word_offset=offset)

    def blindwrite_spi(self, addr, data, chip, readback=True):
        addr = addr & 0xff
        data = data & 0xffff
        #self.print("Writing 0x%x to address 0x%x, CS:0x%x" % (data, addr, chip))
        payload = (addr << 16) + data
        self._write(payload, 1)
        self._write((((chip+1)%8) << 8) +  chip, 0)
        if readback:
            readback = self._read(2) & 0xffff
            return readback

    def write_spi(self, addr, data, chip, readback=True):
        self.print("Writing 0x%x to address 0x%x, CS:0x%x" % (data, addr, chip))
        self.blindwrite_spi(addr, data, chip)
        readback_data = self.read_spi(addr, chip)
        self.print("readback: 0x%x" % readback_data)
        if readback and readback_data != data:
            print("WARNING >>>> SPI readback error (chip %d, addr 0x%x)" % (chip, addr))
        return readback_data

    def read_clk_rates(self, board):
        now = time.time()
        counts0 = [0 for _ in range(5)]
        counts1 = [0 for _ in range(5)]
        diffs = [0 for _ in range(5)]
        for i in range(5):
            counts0[i] = self._read_ctrl(offset=10+i, board=board)
        time.sleep(now + 1 - time.time())
        for i in range(5):
            counts1[i] = self._read_ctrl(offset=10+i, board=board)
        for i in range(5):
            if counts1[i] < counts0[i]:
                diffs[i] = counts1[i] - counts0[i] + 2**32
            else:
                diffs[i] = counts1[i] - counts0[i]
        return diffs
