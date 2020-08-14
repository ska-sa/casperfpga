"""
Try casperfpga transport_katcp in a loop
of creating snaps and then deleting them.
"""
import psutil

SNAP_NAMES = ['frb-snap1-pi', 'frb-snap2-pi',
              'frb-snap3-pi', 'frb-snap4-pi', 'frb-snap5-pi',
              'frb-snap6-pi', 'frb-snap8-pi']
NLOOPS = 10
SIMULATION = False

if SIMULATION:
    pass
else:
    import casperfpga

def count_ofds():
    of_list = psutil.Process().open_files()
    return len(of_list)

def disconnect_snaps(arg_counter, arg_snap_list, arg_snaps):
    """
    Disconnect and delete all members of a snaps array
    """
    ix = 0
    for snap in arg_snaps:
        snap_name = arg_snap_list[ix]
        print("disconnect_snaps: [{}] {}".format(arg_counter, snap_name))
        if SIMULATION:
            snap.close()
        else:
            snap.disconnect()
        del snap
        ix += 1

def init_snaps(arg_counter, arg_snap_list):
    """
    Initialize a snaps array
    """
    asnaps = []
    for snap_name in arg_snap_list:
        print("init_snaps: [{}] {}".format(arg_counter, snap_name))
        if SIMULATION:
            snap_instance = open("/etc/profile", "r")
        else:
            snap_instance = casperfpga.CasperFpga(snap_name, transport=casperfpga.KatcpTransport)
        asnaps.append(snap_instance)
    return asnaps

def main(nloops=NLOOPS):
	counter = 0
	if SIMULATION:
	    f = []
	print("main: Begin loops, initial count of open FDs:", count_ofds())
	while counter < nloops:
	    snaps = init_snaps(counter, SNAP_NAMES)
	    print("main: count of open FDs after init_snaps:", count_ofds())
	    disconnect_snaps(counter, SNAP_NAMES, snaps)
	    print("main: count of open FDs after disconnect_snaps:", count_ofds())
	    counter += 1
	print("main: All loops have completed")

main()
