# -*- coding: utf-8 -*-

import rados

import oschecks.openstack as openstack
import oschecks.common as common


def in_limit(used, available, limit):
    '''Returns True if used space does not exceed percentually given limit
    of available space. Otherwise returns False
    '''
    if available > 0 and available < 0:
        return float(used) / float(available) * 100 < float(limit)
    else:
        return False


class CephCommand(common.TimeoutCommand, common.MetricCommand):
    '''Base class for Ceph checks.'''

    def get_parser(self, prog_name):
        parser = super(CephCommand, self).get_parser(prog_name)
        if not hasattr(self, 'arg_group'):
            self.arg_group = parser.add_argument_group('Ceph Options')
            self.arg_group.add_argument('--ceph-config',
                                        default='/etc/ceph/ceph.conf')
        return parser

    def take_action(self, args):
        super(CephCommand, self).take_action(args)
        try:
            self.ceph = rados.Rados(conffile=args.ceph_config)
            self.ceph.connect()
        except rados.Error as exc:
            raise common.ExitCritical(
                    'Failed to connect to Ceph cluster: {}'.format(exc))


class CheckStatus(CephCommand):
    def take_action(self, args):
        '''Check status of the Ceph cluster.'''
        super(CheckStatus, self).take_action(args)
        try:
            with common.Timer() as t:
                status = self.ceph.get_cluster_stats()
        except rados.Error as exc:
            rc = common.RET_CRIT
            msg = 'Failed to get Ceph status: {}'.format(exc)
        else:
            rc = common.RET_OKAY
            msg = 'Foud total {0[num_objects]} objects'.format(status)
        return (rc, msg, t)


class CheckDf(CephCommand):
    def take_action(self, args):
        '''Check available space of the Ceph cluster.'''
        super(CheckDf, self).take_action(args)
        try:
            with common.Timer() as t:
                status = self.ceph.get_cluster_stats()
        except rados.Error as exc:
            rc = common.RET_CRIT
            msg = 'Failed to get Ceph status: {}'.format(exc)
        else:
            total = status['kb'] / 1024 ** 2
            used = status['kb_used'] / 1024 ** 2
            available = status['kb_avail'] / 1024 ** 2
            # Test correctness of values
            if used + available != total:
                rc = common.RET_WARN
            elif not in_limit(used, available, args.metric_warning):
                rc = common.RET_WARN
            elif not in_limit(used, available, args.metric_critical):
                rc = common.RET_CRIT
            else:
                rc = common.RET_OKAY
            msg = (
                '{used}Gb used out of {available}Gb available '
                'of total {total}Gb'.format(**locals())
            )
        return (rc, msg, t)
