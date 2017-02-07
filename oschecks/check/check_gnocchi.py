# -*- coding: utf-8 -*-

from gnocchiclient import client as gnocchi_client
from gnocchiclient import exceptions as gnocchi_exceptions

import oschecks.openstack as openstack
import oschecks.common as common


class GnocchiCommand(openstack.OpenstackCommand):
    '''Base class for Gnocchi checks.'''

    def get_parser(self, prog_name):
        parser = super(GnocchiCommand, self).get_parser(prog_name)
        if not hasattr(self, 'arg_group'):
            self.arg_group = parser.add_argument_group(
                'Time Series Database API Options'
            )
            self.arg_group.add_argument('--os-tdb-api-version', default='1')
        return parser

    def take_action(self, args):
        super(GnocchiCommand, self).take_action(args)
        try:
            self.gnocchi = gnocchi_client.Client(
                args.os_tdb_api_version,
                session=self.auth.sess)
        except gnocchi_exceptions.ClientException as exc:
            raise common.ExitCritical(
                    'Failed to create Gnocchi client: {}'.format(exc))


class CheckAPI(GnocchiCommand):
    def take_action(self, args):
        '''Check if the Gnocchi API is responding.'''
        super(CheckAPI, self).take_action(args)
        try:
            with common.Timer() as t:
                status = self.gnocchi.status.get()
        except gnocchi_exceptions.ClientException as exc:
            rc = common.RET_CRIT
            msg = 'Failed to get DB status: {}'.format(exc)
        else:
            rc = common.RET_OKAY
            msg = (
                'Time series DB status: '
                'Found {0[storage][summary][metrics]} metrics '
                'and {0[storage][summary][measures]} measures'.format(status)
            )
        return (rc, msg, t)


class CheckResourceTypeExists(GnocchiCommand):
    def get_parser(self, prog_name):
        parser = super(CheckResourceTypeExists, self).get_parser(prog_name)
        self.arg_group.add_argument('--resource-type', default='generic')
        return parser

    def take_action(self, args):
        '''Check if the named Gnocchi metric exists.'''
        super(CheckResourceTypeExists, self).take_action(args)

        try:
            with common.Timer() as t:
                resource_type = self.gnocchi.resource_type.get(
                    args.resource_type)
        except gnocchi_exceptions.NotFound:
            rc = common.RET_CRIT
            msg = 'Failed to get resource type: {}'.format(args.resource_type)
        except gnocchi_exceptions.ClientException as exc:
            rc = common.RET_CRIT
            msg = 'Unknown error appeared: {}'.format(exc)
        else:
            rc = common.RET_OKAY
            msg = (
                'Found resource type "{0[name]}" - state: {0[state]}, '
                'attributes: {0[attributes]}'.format(resource_type)
            )
        return (rc, msg, t)
