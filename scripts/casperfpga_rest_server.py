#!/usr/bin/env python
import logging

from flask import Flask, request, make_response, send_file
from werkzeug.utils import secure_filename
from flask_restful import Resource, Api, reqparse

from io import StringIO
import re
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

def LOG_INFO(str):
    LOGGER.info(str)
    print(str)

class TransportTarget(object):
    def __init__(self, target, instance_id = 0, cfpga = None):
        self.target = target
        self.instance_id = instance_id
        self.cfpga = cfpga
        self.fpgfile_path = None

        if self.cfpga is None:
            LOG_INFO('Connecting to "{}"'.format(target))
            self.cfpga = casperfpga.CasperFpga(
                        host=target,
                        instance_id=instance_id,
                        transport=casperfpga.LocalPcieTransport,
                )
    
    def __del__(self):
        if self.cfpga is not None:
            self.cfpga.disconnect()
    
    def _setFpgfile_path(self, fpgfile_path):
        LOG_INFO('"{}" is programmed with "{}"'.format(self.target, fpgfile_path))
        self.fpgfile_path = fpgfile_path
        self.cfpga.get_system_information(self.fpgfile_path)
    
    def upload_to_ram_and_program(self, fpgfile_path):
        if fpgfile_path != self.fpgfile_path:
            if (self.fpgfile_path is not None and
                os.path.exists(self.fpgfile_path) and
                self.fpgfile_path.startswith(app.config['UPLOAD_FOLDER'])
            ):

                LOG_INFO('Removing previously uploaded fpg file for "{}": "{}"'.format(self.target, fpgfile_path))
                os.remove(self.fpgfile_path)
            
            LOG_INFO('Programming "{}" with "{}"'.format(self.target, fpgfile_path))
            self.cfpga.transport.upload_to_ram_and_program(fpgfile_path)
            self._setFpgfile_path(fpgfile_path)
        return True
    
    def is_connected(self, timeout=None, retries=None):
        return self.cfpga.transport.is_connected(timeout, retries)

def getTransportTarget(target, instance_id=0):
    target_id = '{}.{}'.format(target, instance_id)
    if target_id not in TRANSPORT_TARGET_DICT:
        TRANSPORT_TARGET_DICT[target_id] = TransportTarget(target, instance_id)
    return TRANSPORT_TARGET_DICT[target_id]

def getInstanceIdFromRequestArgs(args):
    pci_id = args.get('pci_id', default = None, type = str)
    if pci_id is not None:
        if pci_id not in XDMA_PCIE_DICT:
            raise RuntimeError('pci_id "{}" not recognised:\n{}'.format(pci_id, XDMA_PCIE_DICT))
        return XDMA_PCIE_DICT[pci_id]
    return args.get('instance_id', default = 0, type = int)

class RestTransport_Device(Resource):
    def get(self, target, device_name):
        size = request.args.get('size', type = int)
        offset = request.args.get('offset', default = 0, type = int)

        instance_id = getInstanceIdFromRequestArgs(request.args)        
        transportTarget = getTransportTarget(target, instance_id)

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

        instance_id = getInstanceIdFromRequestArgs(request.args)        
        transportTarget = getTransportTarget(target, instance_id)
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

        instance_id = getInstanceIdFromRequestArgs(request.args)        
        transportTarget = getTransportTarget(target, instance_id)

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
        instance_id = getInstanceIdFromRequestArgs(request.args)        
        transportTarget = getTransportTarget(target, instance_id)

        try:
            send_file(transportTarget.fpgfile_path)
        except:
            response = {
                'response':  'Failed to send fpgafile: {}'.format(transportTarget.fpgfile_path)
            }
            code = 500
        return response, code


    def put(self, target):
        filepath = None
        instance_id = getInstanceIdFromRequestArgs(request.args)        
        transportTarget = getTransportTarget(target, instance_id)

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

            transportTarget.upload_to_ram_and_program(filepath)
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

        instance_id = getInstanceIdFromRequestArgs(request.args)        
        transportTarget = getTransportTarget(target, instance_id)

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
        instance_id = getInstanceIdFromRequestArgs(request.args)        
        transportTarget = getTransportTarget(target, instance_id)

        response = {
            'response':  transportTarget.fpgfile_path is not None
        }
        code = 200
        return response, code

class RestTransport_PciXdmaMap(Resource):
    def get(self):
        return {
            'pci_xdma_id_map': XDMA_PCIE_DICT
        }, 200

class RestTransport_Version(Resource):
    def get(self):
        return {
            'response': '1.1.0'
        }, 200

api.add_resource(RestTransport_Device, '/<string:target>/device/<string:device_name>')
api.add_resource(RestTransport_DeviceList, '/<string:target>/device')
api.add_resource(RestTransport_FpgFile, '/<string:target>/fpgfile')
api.add_resource(RestTransport_IsConnected, '/<string:target>/connected')
api.add_resource(RestTransport_IsProgrammed, '/<string:target>/programmed')
api.add_resource(RestTransport_PciXdmaMap, '/PciXdmaMap')
api.add_resource(RestTransport_Version, '/version')

def get_xdma_pcie_map():
    pcie_xdma_regex = r'/sys/bus/pci/drivers/xdma/\d+:(?P<pci_id>.*?):.*?/xdma/xdma(?P<xdma_id>\d+)_user'
    xdma_dev_filepaths = glob.glob('/sys/bus/pci/drivers/xdma/*/xdma/xdma*_user')
    ret = {}
    for fp in xdma_dev_filepaths:
        match = re.match(pcie_xdma_regex, fp)
        ret[match.group('pci_id')] = int(match.group('xdma_id'))
    return ret

if __name__ == '__main__':
    XDMA_PCIE_DICT = get_xdma_pcie_map()
    app.run(host='0.0.0.0', port=5000, debug=False)  # run our Flask app
    # TODO disconnect instances when closing
    # for (target, cfpga) in TARGET_CFPGA_DICT.items():
    #     print('Disconnecting from "{}"'.format(target))
    #     cfpga.disconnect()
