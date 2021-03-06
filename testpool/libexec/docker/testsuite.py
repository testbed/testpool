# Copyright (c) 2015-2018 Mark Hamilton, All rights reserved
"""
Test docker API

Install python binding to docker.
  - sudo -H pip install docker
"""

import time
import unittest
import logging
import docker
from testpooldb import models
from testpool.core import server
from testpool.core import ext
from testpool.core import algo
from testpool.libexec.docker import api

CONNECTION = "http://127.0.0.1"
TEST_POOL = "test.docker.pool"
##
# Used nginx because it does not terminate.
TEMPLATE = "nginx:1.13"
##

PRODUCT = "docker"


class Testsuite(unittest.TestCase):
    """ tests various aspects of cloning a container. """

    def setUp(self):
        """ Create docker pool. """

        (host1, _) = models.Host.objects.get_or_create(
            connection=CONNECTION, product=PRODUCT)
        defaults = {"resource_max": 3, "template_name": TEMPLATE}
        models.Pool.objects.update_or_create(name=TEST_POOL, host=host1,
                                             defaults=defaults)

        pool = api.Pool(CONNECTION, "test")
        try:
            pool.check()
        except Exception as arg:  # pylint: disable=broad-except
            assert False, arg

    def tearDown(self):
        """ Remove any previous test pools1. """
        logging.debug("tearDown")

        try:
            pool1 = models.Pool.objects.get(name=TEST_POOL)
            for rsrc1 in models.Resource.objects.filter(pool=pool1):
                rsrc1.delete()
            pool1.delete()
        except models.Pool.DoesNotExist:
            pass

        try:
            host1 = models.Host.objects.get(connection=CONNECTION,
                                            product=PRODUCT)
            host1.delete()
        except models.Host.DoesNotExist:
            pass

    def test_clone(self):
        """ test creating a container given an image. """

        count = 3

        host1 = docker.from_env()
        self.assertTrue(host1)

        pool = api.Pool(CONNECTION, "test")
        self.assertIsNotNone(pool)
        for item in range(count):
            name = pool.new_name_get(TEMPLATE, item)
            pool.destroy(name)

        names = [item for item in pool.conn.containers.list()]
        for item in range(count):
            name = pool.new_name_get(TEMPLATE, item)
            if name not in names:
                logging.debug("cloning %s to %s", TEMPLATE, name)
                pool.clone(TEMPLATE, name)
                pool.start(name)

        for item in range(count):
            name = TEMPLATE + ".%d" % item
            pool.destroy(name)

    def test_destroy_missing(self):
        """ test_destroy_missing. """

        pool1 = models.Pool.objects.get(name=TEST_POOL)

        host1 = api.pool_get(pool1)
        self.assertTrue(host1)

        name = "%s.destroy" % TEMPLATE
        host1.destroy(name)


# pylint: disable=R0903
class FakeArgs(object):
    """ Used in testing to pass values to server.main. """
    def __init__(self):
        self.count = 40
        self.sleep_time = 1
        self.max_sleep_time = 60
        self.min_sleep_time = 1
        self.setup = True
        self.verbose = 3
        self.cfg_file = ""


class TestsuiteServer(unittest.TestCase):
    """ Test model output. """

    def tearDown(self):
        """ Make sure pool is removed. """

        try:
            host1 = models.Host.objects.get(connection=CONNECTION,
                                            product=PRODUCT)
            pool1 = models.Pool.objects.get(name=TEST_POOL, host=host1)
            pool = api.pool_get(pool1)
            algo.destroy(pool, pool1)
            pool1.delete()
        except models.Host.DoesNotExist:
            pass
        except models.Pool.DoesNotExist:
            pass

        host1 = docker.from_env()
        pool = api.Pool(CONNECTION, "test")

    def test_setup(self):
        """ test_setup. """

        (host1, _) = models.Host.objects.get_or_create(connection=CONNECTION,
                                                       product=PRODUCT)

        defaults = {"resource_max": 1, "template_name": TEMPLATE}
        (pool1, _) = models.Pool.objects.update_or_create(
            name=TEST_POOL, host=host1, defaults=defaults)

        args = FakeArgs()
        server.args_process(args)
        self.assertEqual(server.main(args), 0)
        self.assertEqual(pool1.resource_set.all().count(), 1)

    def test_create_one(self):
        """ Create one container. """

        (host1, _) = models.Host.objects.get_or_create(connection=CONNECTION,
                                                       product=PRODUCT)
        defaults = {"resource_max": 1, "template_name": TEMPLATE}
        models.Pool.objects.update_or_create(name=TEST_POOL, host=host1,
                                             defaults=defaults)

        args = FakeArgs()
        server.args_process(args)
        self.assertEqual(server.main(args), 0)

    def test_create_two(self):
        """ Create one container. """

        (host1, _) = models.Host.objects.get_or_create(connection=CONNECTION,
                                                       product=PRODUCT)
        defaults = {"resource_max": 2, "template_name": TEMPLATE}
        models.Pool.objects.update_or_create(name=TEST_POOL, host=host1,
                                             defaults=defaults)

        args = FakeArgs()
        server.args_process(args)
        self.assertEqual(server.main(args), 0)

    def test_shrink(self):
        """ test_shrink. test when the pool shrinks. """

        (host1, _) = models.Host.objects.get_or_create(connection=CONNECTION,
                                                       product=PRODUCT)
        defaults = {"resource_max": 3, "template_name": TEMPLATE}
        (pool1, _) = models.Pool.objects.update_or_create(
            name=TEST_POOL, host=host1, defaults=defaults)

        args = FakeArgs()
        server.args_process(args)
        self.assertEqual(server.main(args), 0)

        ##
        # Now shrink the pool to two
        pool1.resource_max = 2
        pool1.save()
        ##

        args = FakeArgs()
        args.setup = False
        server.args_process(args)
        self.assertEqual(server.main(args), 0)
        exts = ext.api_ext_list()

        pool = exts[PRODUCT].pool_get(pool1)
        self.assertEqual(len(pool.list(pool1)), 2)

    def test_expand(self):
        """ test_expand. Check when pool increases. """

        (host1, _) = models.Host.objects.get_or_create(connection=CONNECTION,
                                                       product=PRODUCT)
        defaults = {"resource_max": 2, "template_name": TEMPLATE}
        (pool1, _) = models.Pool.objects.update_or_create(
            name=TEST_POOL, host=host1, defaults=defaults)

        ##
        #  Now expand to 3
        pool1.resource_max = 3
        pool1.save()
        ##

        args = FakeArgs()
        server.args_process(args)
        self.assertEqual(server.main(args), 0)

        exts = ext.api_ext_list()
        pool = exts[PRODUCT].pool_get(pool1)
        self.assertEqual(len(pool.list(pool1)), 3)

    def test_expiration(self):
        """ test_expiration. """

        resource_max = 3

        (host1, _) = models.Host.objects.get_or_create(connection=CONNECTION,
                                                       product=PRODUCT)
        defaults = {"resource_max": resource_max, "template_name": TEMPLATE}
        (pool1, _) = models.Pool.objects.update_or_create(
            name=TEST_POOL, host=host1, defaults=defaults)

        args = FakeArgs()
        server.args_process(args)
        self.assertEqual(server.main(args), 0)

        rsrcs = pool1.resource_set.filter(status=models.Resource.READY)
        self.assertEqual(len(rsrcs), resource_max)

        rsrc = rsrcs[0]

        ##
        # Acquire for 3 seconds.
        rsrc.transition(models.Resource.RESERVED, algo.ACTION_DESTROY, 3)
        time.sleep(5)
        args.setup = False
        args.count = 2
        args.sleep_time = 1
        args.max_sleep_time = 1
        args.min_sleep_time = 1
        server.args_process(args)
        self.assertEqual(server.main(args), 0)
        ##

        exts = ext.api_ext_list()
        server.adapt(exts)

        rsrcs = pool1.resource_set.filter(status=models.Resource.READY)

        ##
        # Check to see if the expiration happens.
        self.assertEqual(rsrcs.count(), 2)
        ##


if __name__ == "__main__":
    unittest.main()
