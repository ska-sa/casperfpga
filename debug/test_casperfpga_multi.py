import sys
import logging
from multiprocessing import Process, Queue


import casperfpga

logging.getLogger().setLevel(logging.INFO)

LOOP_LIMIT = 10000
FILE = '/srv/bofs/xeng/s_b16a4x64f_2018-01-11_1629.fpg'
SKARAB = 'skarab02030E-01'

f = casperfpga.CasperFpga(SKARAB)

# this will 'leak' sockets and you will run out of file descriptors
for loop in range(LOOP_LIMIT):
    print('Loop {}'.format(loop))
    sys.stdout.flush()
    f.upload_to_ram_and_program(FILE)
    # f.get_system_information(FILE)


def check_fpga_thing(result_queue, fpga):
    fpga.upload_to_ram_and_program(FILE)
    result_queue.put(True)


# this won't
results = Queue()
for loop in range(LOOP_LIMIT):
    print('Loop {}'.format(loop))
    sys.stdout.flush()
    p = Process(target=check_fpga_thing, args=(results, f))
    p.start()
    p.join(timeout=30)
    result = results.get()
    print result
    sys.stdout.flush()

# end
