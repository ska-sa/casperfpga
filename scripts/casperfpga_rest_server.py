#!/usr/bin/env python
import logging

from flask import Flask, request, make_response, send_file
from werkzeug.utils import secure_filename
from flask_restful import Resource, Api, reqparse

from io import StringIO
import re
import argparse
import glob
import os
import base64
import casperfpga
from casperfpga.transport_localpcie import LocalPcieTransport
from casperfpga.utils import parse_fpg
from datetime import datetime

__author__ = 'radonnachie'
__date__ = 'Feb 2022'

LOGGER = logging.getLogger(__name__)
# Set log format to INFO  level
logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s",
        level=logging.INFO)

UPLOAD_FOLDER = '/tmp'
ALLOWED_EXTENSIONS = {'fpg'}
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

app = Flask(__name__)
api = Api(app)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

TRANSPORT_TARGET_DICT = {}
XDMA_PCIE_DICT = None
PCIE_XDMA_DICT = None

class TransportTarget(object):
    def __init__(self, xdma_id, cfpga = None, **kwargs):
        self.target = 'pcie%s'%XDMA_PCIE_DICT[xdma_id]
        self.instance_id = int(xdma_id)
        self.cfpga = cfpga
        self.fpgfile_path = None
        self.fpg_template = None

        if self.cfpga is None:
            LOGGER.info('Connecting to "{}"'.format(self.target))
            self.cfpga = casperfpga.CasperFpga(
                        host=self.target,
                        instance_id=self.instance_id,
                        transport=casperfpga.LocalPcieTransport,
                        **kwargs
                )
    
    def __del__(self):
        if self.cfpga is not None:
            self.cfpga.disconnect()
    
    def _setFpgfile_path(self, fpgfile_path):
        LOGGER.info('"{}" is programmed with "{}"'.format(self.target, fpgfile_path))
        self.fpgfile_path = fpgfile_path
        self.cfpga.get_system_information(self.fpgfile_path)
    
    def upload_to_ram_and_program(self, fpgfile_path):
        if fpgfile_path != self.fpgfile_path:            
            if (self.fpgfile_path is not None and
                os.path.exists(self.fpgfile_path) and
                self.fpgfile_path.startswith(app.config['UPLOAD_FOLDER'])
            ):
                LOGGER.info('Removing previously uploaded fpg file for "{}": "{}"'.format(self.target, fpgfile_path))
                os.remove(self.fpgfile_path)
            
            LOGGER.info('Programming "{}" with "{}"'.format(self.target, fpgfile_path))
            try:
                self.cfpga.transport.upload_to_ram_and_program(fpgfile_path)
            except RuntimeError as r:
                print(r)
                return False
            self._setFpgfile_path(fpgfile_path)
        return True
    
    def is_connected(self, timeout=None, retries=None):
        return self.cfpga.transport.is_connected(timeout, retries)

def getXdmaIdFromTarget(target):
    if target.startswith('pcie'):
        pci_id = target[4:]
        if pci_id not in PCIE_XDMA_DICT:
            raise RuntimeError(
                'pci_id "{}" not recognised:\n{}'.format(
                    pci_id, PCIE_XDMA_DICT
                )
            )
        return PCIE_XDMA_DICT[pci_id]
    
    if target.startswith('xdma'):
        return target[4:]

    raise RuntimeError((
        'Specified target "{}" not recognised:\nmust begin with either "pcie"'
        ' or "xdma" or be an exact XDMA ID ({}).').format(target,
        XDMA_PCIE_DICT.keys()
    ))

def getTransportTarget(target, **kwargs):
    xdma_id = getXdmaIdFromTarget(target) if target not in XDMA_PCIE_DICT.keys() else target
    if xdma_id not in TRANSPORT_TARGET_DICT:
        TRANSPORT_TARGET_DICT[xdma_id] = TransportTarget(xdma_id, **kwargs)
    return TRANSPORT_TARGET_DICT[xdma_id]

class RestTransport_Device(Resource):
    def get(self, target, device_name):
        size = request.args.get('size', type = int)
        offset = request.args.get('offset', default = 0, type = int)
      
        transportTarget = getTransportTarget(target)

        try:
            bytes_read = transportTarget.cfpga.transport.read(device_name, size, offset)
            response = make_response(bytes_read, 200,
                {
                    'Content-Type': 'application/octet-stream',
                    'Content-Length': str(size)
                }
            )
        except:
            response = make_response({
                'response': 'Failed to read. Confirm device_name \'{}\'.'.format(device_name),
            }, 404)
        return response#, code
    
    def put(self, target, device_name):
        offset = request.args.get('offset', default = 0, type = int)

        transportTarget = getTransportTarget(target)
        data = request.data

        try:
            transportTarget.cfpga.transport.blindwrite(device_name, data, offset)
            bytes_read = transportTarget.cfpga.transport.read(device_name, len(data), offset)

            response = make_response(bytes_read, 200,
                {
                    'Content-Type': 'application/octet-stream',
                    'Content-Length': str(len(data))
                }
            )
        except:
            response = make_response({
                'response': 'Unknown device_name \'{}\''.format(device_name),
                'device_names': list(transportTarget.cfpga.listdev()),
            }, 404)
        return response

class RestTransport_DeviceList(Resource):
    def get(self, target):
        device_name = request.args.get('device_name', default = None, type = str)

        transportTarget = getTransportTarget(target)

        try:
            response_val = list(transportTarget.cfpga.listdev())
            if device_name is not None:
                response_val = device_name in response_val
            response = {
                'response': response_val,
            }
            code = 200
        except:
            response = {
                'response': 'Failed to listdev',
            }
            code = 500
        return response, code

class RestTransport_FpgFile(Resource):
    def get(self, target):
        transportTarget = getTransportTarget(target)

        try:
            return send_file(transportTarget.fpgfile_path)
        except:
            response = {
                'response':  'Failed to send fpgafile: {}'.format(transportTarget.fpgfile_path)
            }
            code = 500
            return response, code


    def put(self, target):
        filepath = None
        transportTarget = getTransportTarget(target)

        try:
            if 'fpga' in request.files:
                file = request.files['fpga']
                # If the user does not select a file, the browser submits an
                # empty file without a filename.
                assert file.filename != ''
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    filepath = os.path.join(
                        app.config['UPLOAD_FOLDER'],
                        '{}{}'.format(
                            datetime.now().strftime("%Y-%m-%d_%Hh%Mm%S_"),
                            filename
                        )
                    )
                    file.save(filepath)
            else:
                filepath = request.args.get('fpgfile_path')

            if not transportTarget.upload_to_ram_and_program(filepath):
                response = {
                    'response': ('Provided fpg file does not match '
                        '`pr_template`: "{}"'.format(transportTarget.fpg_template))
                }
                code = 500
            else:
                response = {
                    'response':  transportTarget.fpgfile_path
                }
                code = 200
        except:
            if filepath is not None:
                response = {
                    'response':  'Error programming with "{}".'.format(filepath)
                }
                code = 500
            else:
                response = {
                    'response':  'Either upload a file or provide a server-local fileos.path.'
                }
                code = 500

        return response, code

class RestTransport_IsConnected(Resource):
    def get(self, target):
        timeout = request.args.get('timeout', default = None, type = int)
        retries = request.args.get('retries', default = None, type = int)       

        transportTarget = getTransportTarget(target)

        try:
            response = {
                'response':  transportTarget.is_connected(timeout, retries)
            }
            code = 200
        except:
            response = {
                'response':  'TransportTarget not created'
            }
            code = 500
        return response, code

class RestTransport_IsProgrammed(Resource):
    def get(self, target):
        transportTarget = getTransportTarget(target)

        response = {
            'response':  transportTarget.fpgfile_path is not None
        }
        code = 200
        return response, code

class RestTransport_PciXdmaMap(Resource):
    def get(self):
        return {
            'pci_xdma_id_map': PCIE_XDMA_DICT
        }, 200

class RestTransport_Version(Resource):
    def get(self):
        return {
            'response': '1.2.0'
        }, 200

api.add_resource(RestTransport_Device, '/<string:target>/device/<string:device_name>')
api.add_resource(RestTransport_DeviceList, '/<string:target>/device')
api.add_resource(RestTransport_FpgFile, '/<string:target>/fpgfile')
api.add_resource(RestTransport_IsConnected, '/<string:target>/connected')
api.add_resource(RestTransport_IsProgrammed, '/<string:target>/programmed')
api.add_resource(RestTransport_PciXdmaMap, '/PciXdmaMap')
api.add_resource(RestTransport_Version, '/version')

def get_pcie_xdma_map():
    pcie_xdma_regex = r'/sys/bus/pci/drivers/xdma/\d+:(?P<pci_id>.*?):.*?/xdma/xdma(?P<xdma_id>\d+)_user'
    xdma_dev_filepaths = glob.glob('/sys/bus/pci/drivers/xdma/*/xdma/xdma*_user')
    ret = {}
    for fp in xdma_dev_filepaths:
        match = re.match(pcie_xdma_regex, fp)
        ret[match.group('pci_id')] = match.group('xdma_id')
    return ret

if __name__ == '__main__':    
    parser = argparse.ArgumentParser(
        description=('Initialize a REST server exposing localpcietransports as'
        'remote ones.')
    )
    parser.add_argument('fpgfile', type=str,
        # default='/home/cosmic/dev/vla-dev/pr_templates/adm_4x100g_pr_template_test/outputs/adm_4x100g_pr_template_test_2022-02-03_1951.fpg',
        help='Path to the initial fpg file that the PCI devices are programmed with.'
    )
    parser.add_argument('--program', '-p', action='store_true',
        help='Program the PCI devices with fpgfile.'
    )
    args = parser.parse_args()

    PCIE_XDMA_DICT = get_pcie_xdma_map()
    XDMA_PCIE_DICT = {}

    for (pci_id, xdma_id) in PCIE_XDMA_DICT.items():
        XDMA_PCIE_DICT[xdma_id] = pci_id
        localtransport = getTransportTarget(xdma_id, fpgfile=args.fpgfile)
        if args.program:
            print('Programmed "pcie{}" successfully: {}'.format(pci_id, localtransport.upload_to_ram_and_program(args.fpgfile)))
        else:
            localtransport._setFpgfile_path(args.fpgfile)


    app.run(host='0.0.0.0', port=5002, debug=False)  # run our Flask app
    # TODO disconnect instances when closing
    # for (target, cfpga) in TARGET_CFPGA_DICT.items():
    #     print('Disconnecting from "{}"'.format(target))
    #     cfpga.disconnect()
