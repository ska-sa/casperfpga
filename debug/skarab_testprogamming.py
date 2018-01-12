#!/usr/bin/env python

"""
Go through the SKARABs in dnsmasq and try to program them many times.
Collect stats about which could and could not be programmed.
"""
from __future__ import print_function
import time
import logging
import socket
from threading import Lock
import random

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

from corr2 import utils as corr2utils

import casperfpga
sd = casperfpga.skarab_definitions

dnsmasq = ''
hosts, lease_filename = corr2utils.hosts_from_dhcp_leases(host_pref='')
print('Found %i roaches in %s.' % (len(hosts), lease_filename))
# for ctr, host in enumerate(hosts):
#     print('\t%03i: %s' % (ctr, host))
results = {host: [0, 0] for host in hosts}
results_details = {host: [] for host in hosts}
loops = 10
loopctr = 0

# strip out hosts on leaf 16
newhosts = []
for idx, h in enumerate(hosts):
    ip = socket.gethostbyname(h)
    octet = ip[ip.index('.') + 1:]
    octet = octet[octet.index('.') + 1:]
    octet = octet[0:octet.index('.')]
    if octet != '16':
        # print('adding', ip, octet)
        newhosts.append(h)
    else:
        # print('excluding', ip, octet)
        pass
hosts = newhosts


def tic():
    global tictoctictoc
    try:
        len(tictoctictoc)
    except (TypeError, NameError):
        tictoctictoc = []
    tictoctictoc.append(time.time())


def toc():
    global tictoctictoc
    try:
        etime = time.time()
        stime = tictoctictoc.pop()
        return etime - stime
    except (TypeError, IndexError):
        return -1


# tic()
# fpgas = casperfpga.utils.threaded_create_fpgas_from_hosts(hosts[-10:-1], best_effort=True)
# print('%i: ' % len(fpgas), toc())
#
# tic()
# fpgas = casperfpga.utils.threaded_create_fpgas_from_hosts(hosts[0:20], best_effort=True)
# print('%i: ' % len(fpgas), toc())
#
# tic()
# fpgas = casperfpga.utils.threaded_create_fpgas_from_hosts(hosts[0:50], best_effort=True)
# print('%i: ' % len(fpgas), toc())
#
# tic()
# fpgas = casperfpga.utils.threaded_create_fpgas_from_hosts(hosts[0:100], best_effort=True)
# print('%i: ' % len(fpgas), toc())

tic()
fpgas = casperfpga.utils.threaded_create_fpgas_from_hosts(
    hosts, timeout=2, best_effort=True)
print('%i: ' % len(fpgas), toc())

tic()
casperfpga.skarab_fileops.progska(fpgas, '/home/paulp/bofs/feng_ct_2017-12-16_0716.fpg')
print(toc())
raise RuntimeError


# # stripe
# skfops = casperfpga.skarab_fileops
# image_chunks, local_checksum = skfops.gen_image_chunks(
#     '/home/paulp/bofs/feng_ct_2017-12-16_0716.fpg', True)
#
# print('%i chunks to TX.' % len(image_chunks))
#
#
# def send_image_chunk(seq_num, chunk_id, num_chunks, chunk_data):
#     rx_timeout = 1
#     request = sd.SdramProgramWishboneReq(
#         chunk_id, num_chunks, chunk_data)
#     request_payload = request.create_payload(seq_num)
#     # send the packet to all the boards
#     for fpga in fpgas:
#         fpga.transport.skarab_ctrl_sock.sendto(
#             request_payload, fpga.transport.skarab_eth_ctrl_port)
#     # # now check all the boards responses
#     # for fpga in fpgas:
#     #     rx_packet = None
#     #     while rx_packet is None:
#     #         rx_packet = casperfpga.SkarabTransport.receive_packet(
#     #             request, seq_num,
#     #             fpga.transport.skarab_ctrl_sock,
#     #             rx_timeout, fpga.host)
#     #     if not ((rx_packet.packet['chunk_id'] == chunk_id) and (rx_packet.packet['ack'] == 0)):
#     #         raise RuntimeError('RX fail from board %s' % fpga.host)
#     if chunk_id % 500 == 0:
#         print('Chunk %i done.' % chunk_id)
#
#
# def bump_seq(seq):
#     if seq >= 0xffff:
#         seq = 0
#     else:
#         seq += 1
#     return seq
#
#
# upload_start_time = time.time()
# num_chunks = len(image_chunks)
# LOGGER.debug('Number of chunks to send: %i' % num_chunks)
#
# seq_num = random.randint(0, 0xffff)
#
# tic()
#
# # send chunk zero - initialization chunk
# seq_num = bump_seq(seq_num)
# init_success = send_image_chunk(seq_num,
#     chunk_id=0, num_chunks=num_chunks,
#     chunk_data=image_chunks[0])
# # if not init_success:
# #     errmsg = 'Failed to transmit SDRAM programming initialization ' \
# #              'packet.'
# #     raise sd.SkarabProgrammingError(errmsg)
#
# # send other chunks
# for chunk_number in range(0, num_chunks):
#     LOGGER.debug('Sending chunk {}\n'.format(chunk_number))
#     seq_num = bump_seq(seq_num)
#     chunk_transmit_success = send_image_chunk(
#         seq_num,
#         chunk_id=chunk_number + 1,
#         num_chunks=num_chunks,
#         chunk_data=image_chunks[chunk_number])
#     # if not chunk_transmit_success:
#     #     errmsg = 'Transmission of chunk %d failed. Programming ' \
#     #              'failed.' % chunk_number
#     #     LOGGER.error(errmsg)
#     #     self.clear_sdram()
#     #     raise sd.SkarabProgrammingError(errmsg)
#
# # check if we sent the last chunk
# # all chunks sent ok!
# LOGGER.debug('All images chunks transmitted successfully!')
#
# print(toc())
#
# raise RuntimeError

# checksum_match = True
# if checksum:
#     # i.e. If the value is non-zero
#     spartan_checksum = self.get_spartan_checksum()
#     checksum_match = skfops.check_checksum(
#         spartan_checksum=spartan_checksum,
#         local_checksum=checksum)
# else:
#     debugmsg = 'Not verifying Spartan/upload checksum.'
#     LOGGER.debug(debugmsg)
#
# if checksum_match:
#     self._sdram_programmed = True
#     return True
# else:
#     errmsg = 'Checksum mismatch. Clearing SDRAM.'
#     LOGGER.error(errmsg)
#     self.clear_sdram()
#     raise sd.SkarabProgrammingError(errmsg)
#
#
# upload_time = time.time() - upload_start_time
# LOGGER.debug('Uploaded bitstream in %.1f seconds.' % upload_time)
# reboot_start_time = time.time()
# self.boot_from_sdram()
# try:
#     skip_wait = kwargs['skip_wait']
# except KeyError:
#     skip_wait = False
# if skip_wait:
#     return True
# # wait for board to come back up
# timeout = timeout + time.time()
# while timeout > time.time():
#     if self.is_connected(retries=1):
#         # # configure the mux back to user_date mode
#         # self.config_prog_mux(user_data=1)
#         [golden_image, multiboot, firmware_version] = \
#             self.get_virtex7_firmware_version()
#         if golden_image == 0 and multiboot == 0:
#             reboot_time = time.time() - reboot_start_time
#             LOGGER.info(
#                 '%s back up, in %.1f seconds (%.1f + %.1f) with FW ver '
#                 '%s' % (self.host, upload_time + reboot_time,
#                         upload_time, reboot_time, firmware_version))
#             return True
#         elif golden_image == 1 and multiboot == 0:
#             LOGGER.error(
#                 '%s back up, but fell back to golden image with '
#                 'firmware version %s' % (self.host, firmware_version))
#             return False
#         elif golden_image == 0 and multiboot == 1:
#             LOGGER.error(
#                 '%s back up, but fell back to multiboot image with '
#                 'firmware version %s' % (self.host, firmware_version))
#             return False
#         else:
#             LOGGER.error(
#                 '%s back up, but unknown image with firmware '
#                 'version number %s' % (self.host, firmware_version))
#             return False
#     time.sleep(0.1)
#
# LOGGER.error('%s has not come back!' % self.host)
# return False


def mangle_fpgas(fpgas):
    for f in fpgas:
        f.transport.mangle()

mangle_fpgas(fpgas)

# tic()
# res = fpgas[0].upload_to_ram_and_program(
#     '/home/paulp/bofs/feng_ct_2017-12-16_0716.fpg')
# print(res)
# print(toc())

import multiprocessing
import time

skfops = casperfpga.skarab_fileops
image_chunks, local_checksum = skfops.gen_image_chunks(
    '/home/paulp/bofs/feng_ct_2017-12-16_0716.fpg', True)

print('Transmitting %i chunks' % len(image_chunks))


class Consumer(multiprocessing.Process):

    def __init__(self, task_queue, result_queue):
        multiprocessing.Process.__init__(self)
        self.task_queue = task_queue
        self.result_queue = result_queue

    def run(self):
        proc_name = self.name
        while True:
            next_task = self.task_queue.get()
            if next_task is None:
                # Poison pill means shutdown
                print('%s: Exiting' % proc_name)
                self.task_queue.task_done()
                break
            print('%s: %s' % (proc_name, next_task))
            answer = next_task()
            self.task_queue.task_done()
            self.result_queue.put(answer)
        return


class Task(object):
    def __init__(self, fpga):
        self.fpga = fpga

    # def receive_packet(request_object, sequence_number,
    #                    skarab_socket, timeout, hostname):
    #     return

    def __call__(self):
        self.fpga.transport.unmangle()
        res = self.fpga.upload_to_ram_and_program(
            filename=None, image_chunks=image_chunks,
            image_checksum=local_checksum,
            skip_wait=True)
        return res

    def __str__(self):
        return '%s(%i)' % (self.fpga.host, id(self.fpga))


# Establish communication queues
tasks = multiprocessing.JoinableQueue()
results = multiprocessing.Queue()

# Start consumers
num_consumers = multiprocessing.cpu_count() * 2

num_consumers = 75

print('Creating %d consumers' % num_consumers)
consumers = [Consumer(tasks, results) for i in xrange(num_consumers)]
for w in consumers:
    w.start()

# Enqueue jobs
num_jobs = 150
for i in xrange(num_jobs):
    tasks.put(Task(fpgas[i]))

# Add a poison pill for each consumer
for i in xrange(num_consumers):
    tasks.put(None)

# Wait for all of the tasks to finish
tic()
tasks.join()
# Start printing results
while num_jobs:
    result = results.get()
    print('Result:', result)
    num_jobs -= 1
print(toc())

raise RuntimeError

tic()
fpgas[101].transport.unmangle()
fpgas[101].upload_to_ram_and_program(
    '/home/paulp/bofs/feng_ct_2017-12-16_0716.fpg')
print(toc())

fpga = fpgas[0]
print(fpga.host, fpga.transport.lock, id(fpga))

raise RuntimeError

while loopctr < loops:
    print('loop:%s' % loopctr)
    for host in hosts:
        print('\t%s' % host, end='')
        try:
            f = casperfpga.CasperFpga(host)
            print(f.transport.get_virtex7_firmware_version(), end=' ')
            print(f.transport.get_embedded_software_version(), end=' ')
            res = f.upload_to_ram_and_program(
                '/home/paulp/bofs/feng_ct_2017-12-16_0716.fpg')
            print(res)
            if not res:
                raise RuntimeError
            results[host][0] += 1
            print('pass')
        except Exception as e:
            results[host][1] += 1
            print('fail - %s' % e.message)
    loopctr += 1
print(results)

# end
