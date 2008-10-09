PYTHON ?= python
SETUP  := setup.py

build:
	$(PYTHON) $(SETUP) $@

install:
ifdef DESTDIR
	$(PYTHON) $(SETUP) $@ --root=$(DESTDIR)
else
	$(PYTHON) $(SETUP) $@
endif

clean:
	$(PYTHON) $(SETUP) $@
	rm -rf build

.PHONY: build install clean
