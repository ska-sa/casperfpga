#!/usr/bin/env python
import argparse
from casperfpga.transport_redis import RedisTapcpDaemon


parser = argparse.ArgumentParser(
    description='Start the redis tapcp daemon',
    formatter_class=argparse.ArgumentDefaultsHelpFormatter
)

parser.add_argument('-r', '--redishost', dest='redishost', type=str, default='redishost',
                    help='the hostname of the redis gateway')
args = parser.parse_args()

daemon = RedisTapcpDaemon(args.redishost)

daemon.run()
