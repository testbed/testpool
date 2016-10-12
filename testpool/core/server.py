# (c) 2015 Mark Hamilton, <mark.lee.hamilton@gmail.com>
#
# This file is part of testpool
#
# Testbed is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Testbed is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Testdb.  If not, see <http://www.gnu.org/licenses/>.
""" Test pool Server.

Server algorithm. VMs, given a current state, can be assigned an action
and when the action should fire.

STATE    ACTION    SUCCESS   STATE    FAILURE
PENDING  destroy   clone  PENDING  N attempts then mark BAD
PENDING  clone     attr   PENDING  N attempst then mark BAD
PENDING  attr      ready  READY    N attempst then mark BAD
RESERVED destroy   clone  PENDING  N attempts then mark BAD
"""
import datetime
import unittest
import time
import logging
import testpool.core.ext
import testpool.core.algo
import testpool.core.logger
from testpool.core import commands
from testpool.core import profile
from testpooldb import models

FOREVER = None
LOGGER = logging.getLogger(__name__)
logging.getLogger("django.db.backends").setLevel(logging.CRITICAL)


def args_process(args):
    """ Process any generic parameters. """

    testpool.core.logger.args_process(LOGGER, args)


def argparser():
    """Create server arg parser. """

    parser = commands.argparser("testpool")
    parser.add_argument('--count', type=int, default=FOREVER,
                        help="The numnber events to process and then quit."
                        "Used for debugging.")
    parser.add_argument('--sleep-time', type=int, default=60,
                        help="Time between checking for changes.")
    return parser


def adapt(exts):
    """ Check to see if the pools should change. """

    LOGGER.info("testpool adapt started")

    for profile1 in models.Profile.objects.all():
        ext = exts[profile1.hv.product]
        vmpool = ext.vmpool_get(profile1)
        testpool.core.algo.adapt(vmpool, profile1)

    LOGGER.info("testpool adapt ended")


def action_destroy(exts, vm1):
    """ Reclaim any VMs released. """

    LOGGER.info("testpool destroy started")

    LOGGER.info("loading %s %s %s", vm1.profile.hv.hostname,
                vm1.profile.hv.product, vm1.name)
    ext = exts[vm1.profile.hv.product]
    vmpool = ext.vmpool_get(vm1.profile)

    testpool.core.algo.vm_destroy(vmpool, vm1)


def action_clone(exts, vm1):
    """ Clone a new VM. """

    LOGGER.info("testpool action_clone started")

    LOGGER.info("loading %s %s %s", vm1.profile.hv.hostname,
                vm1.profile.hv.product, vm1.name)
    ext = exts[vm1.profile.hv.product]
    vmpool = ext.vmpool_get(vm1.profile)
    testpool.core.algo.vm_clone(vmpool, vm1)


def action_reclaim(exts, vm1):
    """ Reclaim a VM onces it has been reserved. """
    ##
    #  If VM expires reclaim it.
    for vm1 in models.VM.objects.filter(status=models.VM.RESERVED,
                                        reserved__lt=datetime.datetime.now()):
        LOGGER.info("vm expires %s %s %s", vm1.profile.hv.hostname,
                    vm1.profile.hv.product, vm1.name)
        ext = exts[vm1.profile.hv.product]
        vmpool = ext.vmpool_get(vm1.profile)
        testpool.core.algo.reclaim(vmpool, vm1)
        vm1.status = models.VM.PENDING
        vm1.save()
    ##
    LOGGER.info("testpool reclaim ended")


def setup(exts):
    """ Run the setup of each hypervisor.

    VMs are reset to pending with the action to destroy them.
    """

    LOGGER.info("testpool setup started")
    for profile1 in models.Profile.objects.all():
        LOGGER.info("setup %s %s %s", profile1.name, profile1.template_name,
                    profile1.vm_max)
        ##
        # Quickly go through all of the VMs to reclaim them by transitioning.
        # them to PENDING and action destroy
        for vm1 in profile1.vm_set.all():
            vm1.transition(models.VM.RESERVED,
                           testpool.core.algo.ACTION_DESTROY, 1)
        ##
    LOGGER.info("testpool setup ended")


def action_attr(exts):
    """ Retrieve attributes. """

    LOGGER.info("pending_to_ready started")
    ##
    #  If VM expires reclaim it.
    for vm1 in models.VM.objects.filter(status=models.VM.PENDING):
        ext = exts[vm1.profile.hv.product]
        vmpool = ext.vmpool_get(vm1.profile)
        vm1.ip_addr = vmpool.ip_get(vm1.name)
        if vm1.ip_addr:
            LOGGER.info("%s: VM %s discovered ip addr %s", vm1.profile.name,
                        vm1.name, vm1.ip_addr)
            vm1.transition(models.VM.READY, testpool.core.algo.ACTION_NONE, 1)
        else:
            LOGGER.info("%s: VM %s waiting for ip addr", vm1.profile.name,
                        vm1.name)
    ##
    LOGGER.info("pending_to_ready ended")


def main(args):
    """ Main entry point for server. """

    count = args.count

    LOGGER.info("testpool server started")
    if count != FOREVER and count < 0:
        raise ValueError("count should be a positive number or FOREVER")

    ##
    # Restart the daemon if extensions change.
    exts = testpool.core.ext.api_ext_list()
    #
    setup(exts)

    while count == FOREVER or count > 0:
        adapt(exts)
        vm1 = models.VM.objects.filter(status!=models.VM.READY).order_by("action_time").first()
        if vm1:
            logging.info("%s: %s at %s", vm1.name, vm1.action, vm1.action_time)
            if vm1.action == testpool.core.algo.ACTION_DESTROY:
                action_destroy(exts, vm1)
            elif vm1.action == testpool.core.algo.ACTION_CLONE:
                action_clone(exts, vm1)
            elif vm1.action == testpool.core.algo.ACTION_ATTR:
                action_attr(exts)

        if args.sleep_time > 0:
            LOGGER.info("testpool sleeping %s (seconds)", args.sleep_time)
            time.sleep(args.sleep_time)

        if count != FOREVER:
            count -= 1

    LOGGER.info("testpool server stopped")
    return 0


# pylint: disable=R0903
class FakeArgs(object):
    """ Used in testing to pass values to server.main. """
    def __init__(self):
        self.count = 1
        self.sleep_time = 0


class ModelTestCase(unittest.TestCase):
    """ Test model output. """

    @staticmethod
    def fake_args():
        """ Return fake args to pass to main. """
        return FakeArgs()

    def test_setup(self):
        """ test_setup. """

        (hv1, _) = models.HV.objects.get_or_create(hostname="localhost",
                                                   product="fake")

        defaults = {"vm_max": 1, "template_name": "fake.template"}
        (profile1, _) = models.Profile.objects.update_or_create(
            name="fake.profile.1", hv=hv1, defaults=defaults)

        args = ModelTestCase.fake_args()
        self.assertEqual(main(args), 0)
        profile1.delete()

    def tearDown(self):
        profile.profile_remove("localhost", "fake.profile.1")

    def test_shrink(self):
        """ test_shrink. """

        product = "fake"
        profile_name = "fake.profile.2"
        hostname = "localhost"

        (hv1, _) = models.HV.objects.get_or_create(hostname=hostname,
                                                   product=product)
        defaults = {"vm_max": 10, "template_name": "fake.template"}
        (profile1, _) = models.Profile.objects.update_or_create(
            name="fake.profile.2", hv=hv1, defaults=defaults)

        args = ModelTestCase.fake_args()
        self.assertEqual(main(args), 0)
        exts = testpool.core.ext.api_ext_list()

        vmpool = exts[product].vmpool_get(hostname, profile_name)

        ##
        # Now shrink the pool to two
        profile1.vm_max = 2
        profile1.save()

        adapt(exts)

        vmpool = exts[product].vmpool_get(hostname, profile_name)
        self.assertEqual(len(vmpool.vm_list()), 2)

    def test_expand(self):
        """ test_expand. """

        product = "fake"
        hostname = "localhost"
        profile_name = "fake.profile.3"

        (hv1, _) = models.HV.objects.get_or_create(hostname=hostname,
                                                   product=product)
        defaults = {"vm_max": 3, "template_name": "fake.template"}
        (profile1, _) = models.Profile.objects.update_or_create(
            name=profile_name, hv=hv1, defaults=defaults)

        args = ModelTestCase.fake_args()
        self.assertEqual(main(args), 0)

        ##
        # Now shrink the pool to two
        profile1.vm_max = 12
        profile1.save()

        exts = testpool.core.ext.api_ext_list()
        adapt(exts)

        vmpool = exts[product].vmpool_get(hostname, profile_name)
        self.assertEqual(len(vmpool.vm_list()), 12)

    def test_expiration(self):
        """ test_expiration. """

        product = "fake"
        hostname = "localhost"
        profile_name = "fake.profile.4"

        (hv1, _) = models.HV.objects.get_or_create(hostname=hostname,
                                                   product=product)
        defaults = {"vm_max": 3, "template_name": "fake.template"}
        (profile1, _) = models.Profile.objects.update_or_create(
            name=profile_name, hv=hv1, defaults=defaults)

        args = ModelTestCase.fake_args()
        self.assertEqual(main(args), 0)

        vms = profile1.vm_set.filter(status=models.VM.PENDING)
        vm1 = vms[0]
        ##
        # Acquire for 3 seconds.
        vm1.acquire(3)
        ##
        time.sleep(5)

        exts = testpool.core.ext.api_ext_list()
        reclaim(exts)

        vms = profile1.vm_set.filter(status=models.VM.PENDING)

        ##
        # Check to see if the expiration happens.
        self.assertEqual(vms.count(), 3)
        ##
