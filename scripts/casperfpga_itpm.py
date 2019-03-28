import casperfpga

myfpga = casperfpga.CasperFpga(host='192.168.14.99', transport=casperfpga.ItpmTransport)
myfpga.set_log_level()
print "Loading Bitstream..."
myfpga.upload_to_ram_and_program('./bitstream/itpm_test_2018-08-01_1416.fpg')
print "Reading sys_scratchpad"
myfpga.read('sys_scratchpad', 1)
print hex(myfpga.read('sys_scratchpad', 1))
print "Writing sys_scratchpad"
## There is an issue with blindwrite=False
myfpga.write_int('sys_scratchpad', 0x12345678, blindwrite=True)
print "Reading sys_scratchpad"
print hex(myfpga.read('sys_scratchpad', 1))

wr_data_list = [k for k in range(0, 256)]
myfpga.read('mem4k', len(wr_data_list))
myfpga.write('mem4k', wr_data_list)
myfpga.read('mem4k', len(wr_data_list))

wr_data_list = [0 for k in range(0, 256)]
myfpga.write('mem4k', wr_data_list)
myfpga.read('mem4k', len(wr_data_list))
