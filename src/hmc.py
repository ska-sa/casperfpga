
from memory import Memory

class Hmc(Memory):
    """
    General HMC memory on the FPGA.
    """
    def __init__(self, parent, device_name, address, length_bytes, mezzanine_site, device_info=None):
        super(Hmc, self).__init__(name=device_name, width_bits=256, address=address, length_bytes=length_bytes)
        self.parent = parent
        self.logger = parent.logger
        self.device_info = device_info
        self.device_name = device_name
        self.mezz_site = mezzanine_site
        self.reg_map = {# HMC Status Registers (LINK2)
                        'HMC_STAT_GEN_LOW_LINK2': 0x00,
                        'HMC_STAT_GEN_HIGH_LINK2': 0x04,
                        'HMC_STAT_INIT_LOW_LINK2': 0x08,
                        'HMC_STAT_INIT_HIGH_LINK2': 0x0C,
                        'HMC_CTRL_LOW_LINK2': 0x10,
                        'HMC_CTRL_HIGH_LINK2': 0x14,
                        'HMC_SENT_P_LOW_LINK2': 0x18,
                        'HMC_SENT_P_HIGH_LINK2': 0x1C,
                        'HMC_SENT_NP_LOW_LINK2': 0x20,
                        'HMC_SENT_NP_HIGH_LINK2': 0x24,
                        'HMC_SENT_R_LOW_LINK2': 0x28,
                        'HMC_SENT_R_HIGH_LINK2': 0x2C,
                        'HMC_POISONED_PACKET_LOW_LINK2': 0x30,
                        'HMC_POISONED_PACKET_HIGH_LINK2': 0x34,
                        'HMC_RCVD_RESP_LOW_LINK2': 0x38,
                        'HMC_RCVD_RESP_HIGH_LINK2': 0x3C,
                        'HMC_TX_LINK_RETRIES_LOW_LINK2': 0x40,
                        'HMC_TX_LINK_RETRIES_HIGH_LINK2': 0x44,
                        'HMC_ERR_ON_RX_LOW_LINK2': 0x48,
                        'HMC_ERR_ON_RX_HIGH_LINK2': 0x4C,
                        'HMC_RUN_LNGTH_BITFLIP_LOW_LINK2': 0x50,
                        'HMC_RUN_LNGTH_BITFLIP_HIGH_LINK2': 0x54,
                        'HMC_ERR_ABORT_NOT_CLEAR_LOW_LINK2': 0x58,
                        'HMC_ERR_ABORT_NOT_CLEAR_HIGH_LINK2': 0x5C,
                        'HMC_ERR_RSP_PACKET_LINK2': 0x60,
                        'HMC_ERRSTAT_LINK2': 0x64,
                        'HMC_CRC_ERR_CNT_LINK2': 0x68,
                        # HMC Status Registers (LINK3)
                        'HMC_STAT_GEN_LOW_LINK3': 0x6C,
                        'HMC_STAT_GEN_HIGH_LINK3': 0x70,
                        'HMC_STAT_INIT_LOW_LINK3': 0x74,
                        'HMC_STAT_INIT_HIGH_LINK3': 0x78,
                        'HMC_CTRL_LOW_LINK3': 0x7C,
                        'HMC_CTRL_HIGH_LINK3': 0x80,
                        'HMC_SENT_P_LOW_LINK3': 0x84,
                        'HMC_SENT_P_HIGH_LINK3': 0x88,
                        'HMC_SENT_NP_LOW_LINK3': 0x8C,
                        'HMC_SENT_NP_HIGH_LINK3': 0x90,
                        'HMC_SENT_R_LOW_LINK3': 0x94,
                        'HMC_SENT_R_HIGH_LINK3': 0x98,
                        'HMC_POISONED_PACKET_LOW_LINK3': 0x9C,
                        'HMC_POISONED_PACKET_HIGH_LINK3': 0xA0,
                        'HMC_RCVD_RESP_LOW_LINK3': 0xA4,
                        'HMC_RCVD_RESP_HIGH_LINK3': 0xA8,
                        'HMC_TX_LINK_RETRIES_LOW_LINK3': 0xAC,
                        'HMC_TX_LINK_RETRIES_HIGH_LINK3': 0xB0,
                        'HMC_ERR_ON_RX_LOW_LINK3': 0xB4,
                        'HMC_ERR_ON_RX_HIGH_LINK3': 0xB8,
                        'HMC_RUN_LNGTH_BITFLIP_LOW_LINK3': 0xBC,
                        'HMC_RUN_LNGTH_BITFLIP_HIGH_LINK3': 0xC0,
                        'HMC_ERR_ABORT_NOT_CLEAR_LOW_LINK3': 0xC4,
                        'HMC_ERR_ABORT_NOT_CLEAR_HIGH_LINK3': 0xC8,
                        'HMC_ERR_RSP_PACKET_LINK3': 0xCC,
                        'HMC_ERRSTAT_LINK3': 0xD0,
                        'HMC_CRC_ERR_CNT_LINK3': 0xD4,
                        'HMC_STATUS': 0xD8}
        # dictionary holding all HMC status information
        self.hmc_status_list = {}
        #dictionary holding all HMC revision information
        self.hmc_revision_list = {}
        self.logger.debug('New Hmc: %s' % self.device_name)

    @classmethod
    def from_device_info(cls, parent, device_name, device_info, memorymap_dict):
        """
        Process device info and the memory map to get all necessary info
        and return a Hmc instance.
        :param parent: the CasperFpga that hosts this HMC
        :param device_name: the unique device name
        :param device_info: information about this device
        :param memorymap_dict: a dictionary containing the device memory map
        :return: a Hmc object
        """
        address, length_bytes = -1, -1
        for mem_name in memorymap_dict.keys():
            if mem_name == device_name:
                address = memorymap_dict[mem_name]['address']
                length_bytes = memorymap_dict[mem_name]['bytes']
                try:
                    mezzanine_site = int(device_info['mez'])
                except KeyError:
                    mezzanine_site = 0
                break

        if address == -1 or length_bytes == -1:
            raise RuntimeError('Could not find address or length for ''Hmc %s' % device_name)
        return cls(parent, device_name, address, length_bytes, mezzanine_site,
                   device_info)

    def __repr__(self):
        return '%s:%s' % (self.__class__.__name__, self.name)


    def _wbone_rd(self, addr):
        """

        :param addr:
        :return:
        """
        return self.parent.transport.read_wishbone(addr)

    def _wbone_wr(self, addr, val):
        """

        :param addr:
        :param val:
        :return:
        """
        return self.parent.transport.write_wishbone(addr, val)

    def get_hmc_status(self):
        """
        Read HMC status
        :param
        :return: self.hmc_status_list - this is a dictionary containing all the HMC status information
        """

        # HMC Status Registers (LINK2)
        self.hmc_status_list['hmc_stat_gen_link2'] = (self._wbone_rd(self.address + self.reg_map['HMC_STAT_GEN_LOW_LINK2']) +
                                                      (self._wbone_rd(self.address + self.reg_map['HMC_STAT_GEN_HIGH_LINK2']) << 32))

        self.hmc_status_list['hmc_stat_init_link2'] = (self._wbone_rd(self.address + self.reg_map['HMC_STAT_INIT_LOW_LINK2']) +
                                                      (self._wbone_rd(self.address + self.reg_map['HMC_STAT_INIT_HIGH_LINK2']) << 32))

        self.hmc_status_list['hmc_ctrl_link2'] = (self._wbone_rd(self.address +
                                                 self.reg_map['HMC_CTRL_LOW_LINK2']) +
                                                 (self._wbone_rd(self.address +
                                                 self.reg_map['HMC_CTRL_HIGH_LINK2']) << 32))

        self.hmc_status_list['hmc_sent_p_link2'] = (self._wbone_rd(self.address +
                                                   self.reg_map['HMC_SENT_P_LOW_LINK2']) +
                                                   (self._wbone_rd(self.address +
                                                   self.reg_map['HMC_SENT_P_HIGH_LINK2']) << 32))

        self.hmc_status_list['hmc_sent_np_link2'] = (self._wbone_rd(self.address +
                                                    self.reg_map['HMC_SENT_NP_LOW_LINK2']) +
                                                    (self._wbone_rd(self.address +
                                                    self.reg_map['HMC_SENT_NP_HIGH_LINK2']) << 32))

        self.hmc_status_list['hmc_sent_r_link2'] = (self._wbone_rd(self.address +
                                                   self.reg_map['HMC_SENT_R_LOW_LINK2']) +
                                                   (self._wbone_rd(self.address +
                                                   self.reg_map['HMC_SENT_R_HIGH_LINK2']) << 32))

        self.hmc_status_list['hmc_poisoned_packet_link2'] = (self._wbone_rd(self.address +
                                                            self.reg_map['HMC_POISONED_PACKET_LOW_LINK2']) +
                                                            (self._wbone_rd(self.address +
                                                            self.reg_map['HMC_POISONED_PACKET_HIGH_LINK2']) << 32))

        self.hmc_status_list['hmc_rcvd_resp_link2'] = (self._wbone_rd(self.address +
                                                      self.reg_map['HMC_RCVD_RESP_LOW_LINK2']) +
                                                      (self._wbone_rd(self.address +
                                                      self.reg_map['HMC_RCVD_RESP_HIGH_LINK2']) << 32))

        self.hmc_status_list['hmc_tx_link_retries_link2'] = (self._wbone_rd(self.address +
                                                            self.reg_map['HMC_TX_LINK_RETRIES_LOW_LINK2']) +
                                                            (self._wbone_rd(self.address +
                                                            self.reg_map['HMC_TX_LINK_RETRIES_HIGH_LINK2']) << 32))

        self.hmc_status_list['hmc_err_on_rx_link2'] = (self._wbone_rd(self.address +
                                                      self.reg_map['HMC_ERR_ON_RX_LOW_LINK2']) +
                                                      (self._wbone_rd(self.address +
                                                      self.reg_map['HMC_ERR_ON_RX_HIGH_LINK2']) << 32))

        self.hmc_status_list['hmc_run_lngth_bitflip_link2'] = (self._wbone_rd(self.address +
                                                              self.reg_map['HMC_RUN_LNGTH_BITFLIP_LOW_LINK2']) +
                                                              (self._wbone_rd(self.address +
                                                              self.reg_map['HMC_RUN_LNGTH_BITFLIP_HIGH_LINK2']) << 32))

        self.hmc_status_list['hmc_err_abort_not_clr_link2'] = (self._wbone_rd(self.address +
                                                              self.reg_map['HMC_ERR_ABORT_NOT_CLEAR_LOW_LINK2']) +
                                                              (self._wbone_rd(self.address +
                                                              self.reg_map['HMC_ERR_ABORT_NOT_CLEAR_HIGH_LINK2']) << 32))

        self.hmc_status_list['hmc_err_rsp_packet_link2'] = (self._wbone_rd(self.address +
                                                           self.reg_map['HMC_ERR_RSP_PACKET_LINK2']))

        self.hmc_status_list['hmc_errstat_link2'] = (self._wbone_rd(self.address + self.reg_map['HMC_ERRSTAT_LINK2']))

        self.hmc_status_list['hmc_crc_err_count_link2'] = (self._wbone_rd(self.address +
                                                          self.reg_map['HMC_CRC_ERR_CNT_LINK2']))

        # HMC Status Registers (LINK3)
        self.hmc_status_list['hmc_stat_gen_link3'] = (self._wbone_rd(self.address +
                                                     self.reg_map['HMC_STAT_GEN_LOW_LINK3']) +
                                                     (self._wbone_rd(self.address +
                                                     self.reg_map['HMC_STAT_GEN_HIGH_LINK3']) << 32))

        self.hmc_status_list['hmc_stat_init_link3'] = (self._wbone_rd(self.address +
                                                      self.reg_map['HMC_STAT_INIT_LOW_LINK3']) +
                                                      (self._wbone_rd(self.address +
                                                      self.reg_map['HMC_STAT_INIT_HIGH_LINK3']) << 32))

        self.hmc_status_list['hmc_ctrl_link3'] = (self._wbone_rd(self.address +
                                                 self.reg_map['HMC_CTRL_LOW_LINK3']) +
                                                 (self._wbone_rd(self.address +
                                                 self.reg_map['HMC_CTRL_HIGH_LINK3']) << 32))

        self.hmc_status_list['hmc_sent_p_link3'] = (self._wbone_rd(self.address +
                                                   self.reg_map['HMC_SENT_P_LOW_LINK3']) +
                                                   (self._wbone_rd(self.address +
                                                   self.reg_map['HMC_SENT_P_HIGH_LINK3']) << 32))

        self.hmc_status_list['hmc_sent_np_link3'] = (self._wbone_rd(self.address +
                                                    self.reg_map['HMC_SENT_NP_LOW_LINK3']) +
                                                    (self._wbone_rd(self.address +
                                                    self.reg_map['HMC_SENT_NP_HIGH_LINK3']) << 32))

        self.hmc_status_list['hmc_sent_r_link3'] = (self._wbone_rd(self.address +
                                                   self.reg_map['HMC_SENT_R_LOW_LINK3']) +
                                                   (self._wbone_rd(self.address +
                                                   self.reg_map['HMC_SENT_R_HIGH_LINK3']) << 32))

        self.hmc_status_list['hmc_poisoned_packet_link3'] = (self._wbone_rd(self.address +
                                                            self.reg_map['HMC_POISONED_PACKET_LOW_LINK3']) +
                                                            (self._wbone_rd(self.address +
                                                            self.reg_map['HMC_POISONED_PACKET_HIGH_LINK3']) << 32))

        self.hmc_status_list['hmc_rcvd_resp_link3'] = (self._wbone_rd(self.address +
                                                      self.reg_map['HMC_RCVD_RESP_LOW_LINK3']) +
                                                      (self._wbone_rd(self.address +
                                                      self.reg_map['HMC_RCVD_RESP_HIGH_LINK3']) << 32))

        self.hmc_status_list['hmc_tx_link_retries_link3'] = (self._wbone_rd(self.address +
                                                            self.reg_map['HMC_TX_LINK_RETRIES_LOW_LINK3']) +
                                                            (self._wbone_rd(self.address +
                                                            self.reg_map['HMC_TX_LINK_RETRIES_HIGH_LINK3']) << 32))

        self.hmc_status_list['hmc_err_on_rx_link3'] = (self._wbone_rd(self.address +
                                                      self.reg_map['HMC_ERR_ON_RX_LOW_LINK3']) +
                                                      (self._wbone_rd(self.address +
                                                      self.reg_map['HMC_ERR_ON_RX_HIGH_LINK3']) << 32))

        self.hmc_status_list['hmc_run_lngth_bitflip_link3'] = (self._wbone_rd(self.address +
                                                              self.reg_map['HMC_RUN_LNGTH_BITFLIP_LOW_LINK3']) +
                                                              (self._wbone_rd(self.address +
                                                              self.reg_map['HMC_RUN_LNGTH_BITFLIP_HIGH_LINK3']) << 32))

        self.hmc_status_list['hmc_err_abort_not_clr_link3'] = (self._wbone_rd(self.address +
                                                              self.reg_map['HMC_ERR_ABORT_NOT_CLEAR_LOW_LINK3']) +
                                                              (self._wbone_rd(self.address +
                                                              self.reg_map['HMC_ERR_ABORT_NOT_CLEAR_HIGH_LINK3']) << 32))

        self.hmc_status_list['hmc_err_rsp_packet_link3'] = (self._wbone_rd(self.address +
                                                           self.reg_map['HMC_ERR_RSP_PACKET_LINK3']))

        self.hmc_status_list['hmc_errstat_link3'] = (self._wbone_rd(self.address + self.reg_map['HMC_ERRSTAT_LINK3']))

        self.hmc_status_list['hmc_crc_err_count_link3'] = (self._wbone_rd(self.address +
                                                          self.reg_map['HMC_CRC_ERR_CNT_LINK3']))

        self.hmc_status_list['hmc_status'] = (self._wbone_rd(self.address + self.reg_map['HMC_STATUS']))

        return self.hmc_status_list

    def get_hmc_revision(self):
        """
        Read HMC revision.
        :param
        :return: self.hmc_revision_list - this is a dictionary containing HMC Vendor ID, HMC Product Revision,
                                          HMC Protocol Revision and HMC Phy Revision
        """
        mezz_site = self.mezz_site + 1
        # Reads back the Revisions and Vendor ID (Register Address: 0x2C0004) - Refer to page 4 of the Micron HMC
        # Register Addendum data sheet for field mapping
        hmc_revision = self.parent.transport.read_hmc_i2c(interface = mezz_site,
                                                          slave_address = 0x10, read_address = 0x2C0004)
        self.hmc_revision_list['hmc_vendor_id'] = hex(hmc_revision & 0x000000FF)
        self.hmc_revision_list['hmc_product_rev'] = hex((hmc_revision & 0x0000FF00) >> 8)
        self.hmc_revision_list['hmc_protocol_rev'] = hex((hmc_revision & 0x00FF0000) >> 16)
        self.hmc_revision_list['hmc_phy_rev'] = hex((hmc_revision & 0xFF000000) >> 24)

        return self.hmc_revision_list



# end
