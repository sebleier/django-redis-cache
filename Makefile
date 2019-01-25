SHELL := /bin/bash

PACKAGE_NAME=redis_cache
DJANGO_VERSION?=>=1.11,<3.0

.PHONY: install_requirements
install_requirements: requirements*.txt
	pip install -r requirements.txt
	pip install -r requirements-dev.txt
	pip install 'Django$(DJANGO_VERSION)'

.PHONY: clean
clean:
	python setup.py clean
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg*/
	rm -rf __pycache__/
	rm -f MANIFEST
	rm -f test.db

.PHONY: test
test: install_requirements
	PYTHONPATH=$(PYTHONPATH): django-admin.py test --settings=tests.settings -s

.PHONY: shell
shell:
	PYTHONPATH=$(PYTHONPATH): django-admin.py shell --settings=tests.settings
