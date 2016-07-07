include defs.mk

check::

.PHONY:
build: MANIFEST.in ./setup.py 
	python ./setup.py build sdist bdist_wheel

install: build
	sudo -H pip install --upgrade dist/testpool-*.tar.gz

uninstall:
	sudo -H pip uninstall testpool

clean::
	python ./setup.py clean
	rm -rf dist build testpool.egg-info
