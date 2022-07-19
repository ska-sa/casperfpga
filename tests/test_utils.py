import os
import pytest
from casperfpga import utils

from casperfpga import register
from casperfpga import sbram
from casperfpga import snap
from casperfpga import tengbe
from casperfpga import fortygbe
from casperfpga import qdr

def test_parse_example00(shared_datadir):
    """
    Test to ensure the data from snap_500.fpg is properly parsed.

    This function ensures that the two outputs of utils.parse_fpg are dictionary-like
    and return the expected meta and memory dictionary keys produced in python2.7. 
    A value from these sets is then verified.

    Parameters
    ----------
    shared_datadir : pathlib.Path object
        Injected variable that specifies the directory of where shared data is stored.
    """
    filename = str(shared_datadir / 'example00.fpg')
    meta_dictionary00, memorydict00 = utils.parse_fpg(filename)
    meta_keys_e00 = {
        'snapA',
        'snap_adc', 
        'snapA_ctrl', 
        'snapA_status', 
        'snapC_ctrl', 
        'snapC_status', 
        'snapC_bram', 
        'snapA_bram', 
        'snapB_ctrl', 
        'snapC', 
        'snapB', 
        'snapB_bram', 
        'snapB_status', 
        'SNAP', 
        '77777', 
        'eth_sw', 
        '77777_git',
    }
    meta_keys_o00 = set(meta_dictionary00.keys())
    mem_keys_e00 = {
        'adc16_use_synth',
        'snapC_ctrl',
        'snapA_status',
        'snapC_bram',
        'sys_scratchpad',
        'snapB_ctrl',
        'sys_rev_rcs',
        'snapC_status',
        'sys_board_id',
        'snapA_bram',
        'adc16_wb_ram0',
        'eth_sw',
        'adc16_wb_ram1',
        'lmx_ctrl',
        'adc16_wb_ram2',
        'snapA_ctrl',
        'adc16_controller',
        'sys_block',
        'snapB_status',
        'sys_rev',
        'snapB_bram',
        'sys_clkcounter'
    }
    mem_keys_o00 = set(memorydict00.keys())
    assert meta_keys_e00 == meta_keys_o00
    assert meta_dictionary00['77777']['system'] == 'snap_500'
    assert mem_keys_e00 == mem_keys_o00

def test_parse_example01(shared_datadir):
    """
    Test to ensure the data from snap_fengine.fpg is properly parsed.

    This function ensures that the two outputs of utils.parse_fpg are dictionary-like
    and return the expected meta and memory dictionary keys produced in python2.7. 
    A value from these sets is then verified.

    Parameters
    ----------
    shared_datadir : pathlib.Path object
        Injected variable that specifies the directory of where shared data is stored.
    """
    filename = str(shared_datadir / 'example01.fpg')
    meta_dictionary01, memorydict01 = utils.parse_fpg(filename)
    meta_keys_e01 = {
        'corr_0_acc_len', 
        'timebase_sync_period', 
        'adc_snap_adc', 
        'phase_switch_gpio_switch_offset', 
        'eq_core_clip_cnt', 
        'packetizer_chans', 
        'sync_period', 
        'phase_switch_gpio_switch_states', 
        'version_version', 
        'phase_switch_sw_switch_states', 
        'corr_0_input_sel', 'eq_core_coeffs', 
        '77777', 
        'input_snap_sel', 
        'phase_switch_enable_demod', 
        'packetizer_ants', 
        'chan_reorder_reorder3_map1', 
        'eth_sw', 
        'corr_0_dout', 
        'noise_seed_1', 
        'noise_seed_0', 
        'input_snapshot', 
        'input_snapshot_status', 
        'sync_sync_delay', 
        'pfb_status', 
        'packetizer_ips', 
        'input_snapshot_ctrl', 
        'input_snapshot_bram', 
        'input_source_sel', 
        'eth_ctrl', 
        'sync_count', 
        'phase_switch_enable_mod', 
        'pfb_ctrl', 
        'corr_0_acc_cnt', 
        'sync_uptime', 
        'delay_delays', 
        'SNAP', 
        'sync_arm',
    }
    meta_keys_o01 = set(meta_dictionary01.keys())
    mem_keys_e01 = { 
        'corr_0_acc_len',
        'timebase_sync_period',
        'corr_0_dout',
        'phase_switch_gpio_switch_offset',
        'eq_core_clip_cnt',
        'noise_seed_0',
        'sync_period',
        'phase_switch_gpio_switch_states',
        'version_version',
        'sys_rev_rcs',
        'delay_delays',
        'corr_0_input_sel',
        'eq_core_coeffs',
        'sys_board_id',
        'packetizer_chans', 
        'sys_block',
        'input_snap_sel',
        'phase_switch_enable_demod',
        'packetizer_ants',
        'chan_reorder_reorder3_map1',
        'eth_sw',
        'adc16_wb_ram1',
        'adc16_wb_ram0',
        'noise_seed_1',
        'adc16_wb_ram2',
        'input_snapshot_status',
        'sync_sync_delay',
        'i2c_ant2',
        'i2c_ant0',
        'i2c_ant1',
        'packetizer_ips',
        'input_snapshot_ctrl',
        'input_snapshot_bram',
        'adc16_use_synth',
        'lmx_ctrl',
        'input_source_sel',
        'sys_rev',
        'eth_ctrl',
        'sync_count',
        'sys_scratchpad',
        'phase_switch_enable_mod',
        'pfb_ctrl',
        'adc16_controller',
        'corr_0_acc_cnt',
        'sync_uptime',
        'pfb_status',
        'sys_clkcounter',
        'phase_switch_sw_switch_states',
        'sync_arm'
    }
    mem_keys_o01 = set(memorydict01.keys())
    assert meta_keys_e01 == meta_keys_o01
    assert meta_dictionary01['77777']['system'] == 'snap_fengine_git'
    assert mem_keys_e01 == mem_keys_o01

def test_create_memdev_00(shared_datadir):

    filepath = str(shared_datadir / 'example00.fpg')
    device_dict00, memorymap_dict00 = utils.parse_fpg(filepath)
    CASPER_MEMORY_DEVICES = {
        'xps:bram':         {'class': sbram.Sbram,       'container': 'sbrams'},
        'xps:qdr':          {'class': qdr.Qdr,           'container': 'qdrs'},
        'xps:sw_reg':       {'class': register.Register, 'container': 'registers'},
        #'xps:tengbe_v2':    {'class': tengbe.TenGbe,     'container': 'gbes'},
        #'xps:ten_gbe':      {'class': tengbe.TenGbe,     'container': 'gbes'},
        'xps:forty_gbe':    {'class': fortygbe.FortyGbe, 'container': 'gbes'},
        'casper:snapshot':  {'class': snap.Snap,         'container': 'snapshots'},
    }
    memory_devices00 = {}

    for device_name, device_info in device_dict00.items():
            if device_name == '':
                raise NameError('There\'s a problem somewhere, got a blank '
                                'device name?')
            if device_name in memory_devices00.keys():
                raise NameError('Memory device %s already exists' % device_name)
            # get the class from the known devices, if it exists there
            tag = device_info['tag']
            try:
                known_device_class = CASPER_MEMORY_DEVICES[tag]['class']
                known_device_container = CASPER_MEMORY_DEVICES[tag]['container']
            except KeyError:
                pass
            else:
                if not callable(known_device_class):
                    raise TypeError('%s is not a callable Memory class - '
                                    'that\'s a problem.' % known_device_class)
                new_device = known_device_class.from_device_info(
                    known_device_class, device_name, device_info, memorymap_dict00)
                #if new_device.name in known_device_class.memory_devices.keys():
                #    raise NameError(
                #        'Device called %s of type %s already exists in '
                #        'devices list.' % (new_device.name, type(new_device)))
                #known_device_class.devices[device_name] = new_device
                #known_device_class.memory_devices[device_name] = new_device
                #container = getattr(known_device_class, known_device_container)
                #setattr(container, device_name, new_device)
                #assert id(getattr(container, device_name)) == id(new_device)
                #assert id(new_device) == id(known_device_class.memory_devices[device_name])

def test_create_memdev_01(shared_datadir):

    filepath = str(shared_datadir / 'example01.fpg')
    device_dict01, memorymap_dict01 = utils.parse_fpg(filepath)
    CASPER_MEMORY_DEVICES = {
        'xps:bram':         {'class': sbram.Sbram,       'container': 'sbrams'},
        'xps:qdr':          {'class': qdr.Qdr,           'container': 'qdrs'},
        'xps:sw_reg':       {'class': register.Register, 'container': 'registers'},
        #'xps:tengbe_v2':    {'class': tengbe.TenGbe,     'container': 'gbes'},
        #'xps:ten_gbe':      {'class': tengbe.TenGbe,     'container': 'gbes'},
        'xps:forty_gbe':    {'class': fortygbe.FortyGbe, 'container': 'gbes'},
        'casper:snapshot':  {'class': snap.Snap,         'container': 'snapshots'},
    }
    memory_devices01 = {}

    for device_name, device_info in device_dict01.items():
            if device_name == '':
                raise NameError('There\'s a problem somewhere, got a blank '
                                'device name?')
            if device_name in memory_devices01.keys():
                raise NameError('Memory device %s already exists' % device_name)
            # get the class from the known devices, if it exists there
            tag = device_info['tag']
            try:
                known_device_class = CASPER_MEMORY_DEVICES[tag]['class']
                known_device_container = CASPER_MEMORY_DEVICES[tag]['container']
            except KeyError:
                pass
            else:
                if not callable(known_device_class):
                    raise TypeError('%s is not a callable Memory class - '
                                    'that\'s a problem.' % known_device_class)
                new_device = known_device_class.from_device_info(
                    known_device_class, device_name, device_info, memorymap_dict01)
                #if new_device.name in known_device_class.memory_devices.keys():
                #    raise NameError(
                #        'Device called %s of type %s already exists in '
                #        'devices list.' % (new_device.name, type(new_device)))
                #known_device_class.devices[device_name] = new_device
                #known_device_class.memory_devices[device_name] = new_device
                #container = getattr(known_device_class, known_device_container)
                #setattr(container, device_name, new_device)
                #assert id(getattr(container, device_name)) == id(new_device)
                #assert id(new_device) == id(known_device_class.memory_devices[device_name])
