.. _DevelopmentAnchor:

Development
***********

Prior to developing in testpool:

  sudo -H make setup
  ./bin/tpl-db migrate

Additionally docker must be installed, tests and development rely on it.

Web Development
===============

To simplify web development, developers can avoid using an actual hypervisor.
Instead developers can create a fake pool.

Since testpool uses django, once the web server is running it will 
automatically restart when content changes. In one shell, run the testpool
web server::

  ./bin/tpl-db runserver

In a new shell start the testpool daemon.::

  ./bin/tpl-daemon -vv

In a new shell, create several pools. The following creates two pool .
The first pool uses template0 to generate two fake VMs. The second pool
creates three fake VMs from template1.::

  ./bin/tpl pool add localhost fake pool0 template0 2
  ./bin/tpl pool add localhost fake pool1 template1 3

The tpl-daemon will over time generate 5 VMs in the ready state. In other
words, fake VMs are transitioned from pending to reserved over a short
period of time. Testpool web content showing overall VM pool statistics can 
be found::

  http://127.0.0.1:8000/testpool/pool

To manipulate VM content, meaning reserve and release VMs, review the vm
command help::

  ./bin/tpl vm --help

Debian Packaging
================

Before debian packages can be created apt-file must be installed and updated
so that the python requirements.txt file can be mapped to equivalent 
debian package dependencies.::

  sudo apt-get install apt-file
  sudo apt-file update
  pip install pep8>=1.7.0 pylint>=1.5.4 pytest>=2.8.3

Make sure to set EMAIL before using dch
Also note that versions are incremented in the change log::

  dch -U

Build Testpool debian package and install::

  make deb.build
  sudo make install

