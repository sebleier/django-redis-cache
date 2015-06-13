SHELL := /bin/bash
PACKAGE_NAME=redis_cache

VENV_DIR?=.venv
VENV_ACTIVATE=$(VENV_DIR)/bin/activate
WITH_VENV=. $(VENV_ACTIVATE);
DJANGO_VERSION?=1.7

default:
	python setup.py check build

$(VENV_ACTIVATE): requirements*.txt
	test -f $@ || virtualenv --python=python2.7 --system-site-packages $(VENV_DIR)
	touch $@

.PHONY: install_requirements
install_requirements: requirements*.txt
	$(WITH_VENV) pip install --no-deps -r requirements.txt
	$(WITH_VENV) pip install --no-deps -r requirements-dev.txt
	$(WITH_VENV) pip install Django==$(DJANGO_VERSION)

.PHONY: venv
venv: $(VENV_ACTIVATE)

.PHONY: setup
setup: venv

.PHONY: redis_servers
redis_servers:
	test -d redis || git clone https://github.com/antirez/redis
	git -C redis checkout 2.6
	make -C redis
	for i in 1 2 3; do \
    	./redis/src/redis-server \
    		--pidfile /tmp/redis`echo $$i`.pid \
    		--requirepass yadayada \
    		--daemonize yes \
    		--port `echo 638$$i` ; \
    	done

	for i in 4 5 6; do \
    	./redis/src/redis-server \
    		--pidfile /tmp/redis`echo $$i`.pid \
    		--requirepass yadayada \
    		--daemonize yes \
    		--port 0 \
    		--unixsocket /tmp/redis`echo $$i`.sock \
    		--unixsocketperm 755 ; \
    	done

.PHONY: clean
clean:
	python setup.py clean
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg*/
	rm -rf __pycache__/
	rm -f MANIFEST
	rm -f test.db
	find $(PACKAGE_NAME) -type f -name '*.pyc' -delete

.PHONY: teardown
teardown:
	rm -rf $(VENV_DIR)/

.PHONY: test
test: venv install_requirements redis_servers
	$(WITH_VENV) PYTHONPATH=$(PYTHONPATH): django-admin.py test --settings=tests.settings -s
	for i in 1 2 3 4 5 6; do kill `cat /tmp/redis$$i.pid`; done;

.PHONY: shell
shell: venv
	$(WITH_VENV) PYTHONPATH=$(PYTHONPATH): django-admin.py shell --settings=tests.settings

