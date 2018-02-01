import sys
import time
import logging

import casperfpga

logging.getLogger().setLevel(logging.DEBUG)

LOOP_LIMIT = 10000
FILE = '/srv/bofs/xeng/s_b16a4x64f_2018-01-11_1629.fpg'
SKARAB = 'skarab02030E-01'

for loop in range(LOOP_LIMIT):
    try:
        print('Loop {}'.format(loop))
        sys.stdout.flush()
        f = casperfpga.CasperFpga(SKARAB)
        f.upload_to_ram_and_program(FILE)
        # f.get_system_information(FILE)
        time.sleep(5)
        f = None
    except KeyboardInterrupt:
        break
