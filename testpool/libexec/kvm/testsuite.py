import unittest
import libvirt
import logging
from testpool.libexec import kvm
from xml.etree import ElementTree as ET

TEST_HOST="192.168.0.27"

def request_cred(credentials, user_data):
    for credential in credentials:
        if credential[0] == libvirt.VIR_CRED_AUTHNAME:
            credential[4] = "mhamilton"
        elif credential[0] == libvirt.VIR_CRED_PASSPHRASE:
            credential[4] = "password"
    return 0

class Testsuite(unittest.TestCase):

    def test_clone(self):
        """ test clone """

        fmt = "qemu+ssh://mhamilton@%s/system"
        connect = fmt % TEST_HOST
        hv1 = kvm.api.vmpool_get(connect)

        hndl = libvirt.open(connect)

        for item in range(3):
            vm_name = "pool.ubuntu1404.%d" % item
            try:
                hv1.destroy(vm_name)
            except libvirt.libvirtError:
                continue
            except Exception, arg:
                print "MARK: caught"
                logging.exception(arg)

        pool = [item for item in hv1.conn.listAllDomains()]
        pool = [item.name() for item in pool]
        pool = [item for item in pool if item.startswith("pool.ubuntu1404")]
        for item in range(3):
            vm_name = "pool.ubuntu1404.%d" % item
            if vm_name not in pool:
                logging.debug("creating %s", vm_name)
                hv1.clone("template.ubuntu1404", vm_name)
                hv1.start(vm_name)

    def test_info(self):
        """ test_info """
        fmt = "qemu+ssh://mhamilton@%s/system"
        cmd = fmt % TEST_HOST
        hndl = libvirt.open(cmd)
        self.assertTrue(hndl)

        self.assertTrue(hndl.getInfo())
        self.assertTrue(hndl.getHostname())

    def test_storage(self):
        """ test_storage """
        fmt = "qemu+ssh://mhamilton@%s/system"
        cmd = fmt % TEST_HOST
        hndl = libvirt.open(cmd)
        self.assertTrue(hndl)
        for item in hndl.listDefinedDomains():
            print "VM: defined", item

        for item in hndl.listDomainsID():
            dom = hndl.lookupByID(item)
            print "Active: Name: ", dom.name()
            print "Active: Info: ", dom.info()

    def old_test_auth(self):
        fmt = "qemu+tcp://%s/system"
        cmd = fmt % TEST_HOST
        auth = [[libvirt.VIR_CRED_AUTHNAME, libvirt.VIR_CRED_PASSPHRASE],
                request_cred, None]
        hndl = libvirt.openAuth(cmd, auth, 0)
        self.assertTrue(hndl)
        hndl.close()

    def test_destroy(self):
        """ test_destroy. """

        fmt = "qemu+ssh://mhamilton@%s/system"
        connect = fmt % TEST_HOST
        hv1 = kvm.api.vmpool_get(connect)

        hndl = libvirt.open(connect)

        try:
            vm_name = "pool.ubuntu1404.0"
            hv1.clone("template.ubuntu1404", vm_name)
            hv1.start(vm_name)
        except ValueError:
            pass

        hv1.destroy(vm_name)

    def test_create_idempotent(self):
        """ test_create_idempotent. """


        fmt = "qemu+ssh://mhamilton@%s/system"
        connect = fmt % TEST_HOST
        hv1 = kvm.api.vmpool_get(connect)

        hndl = libvirt.open(connect)

        vm_name = "pool.ubuntu1404.create"
        try:
            print "MARK: clone"
            logging.info("%s: cloning", vm_name)
            hv1.clone("template.ubuntu1404", vm_name)
            hv1.start(vm_name)
        except ValueError:
            pass

        try:
            print "MARK: clone"

            logging.info("%s: cloning", vm_name)
            hv1.clone("template.ubuntu1404", vm_name)
            hv1.start(vm_name)
        except ValueError:
            pass

        print "MARK: destroy"
        hv1.destroy(vm_name)

        try:
            hv1.clone("template.ubuntu1404", vm_name)
            hv1.start(vm_name)
        except ValueError:
            pass

        print "MARK: destroy"
        hv1.destroy(vm_name)

if __name__ == "__main__":
    unittest.main()
