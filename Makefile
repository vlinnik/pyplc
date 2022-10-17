MPY-CROSS?=~/.krax/mpy-cross
ODIR ?= $(shell pwd)/build
SOURCES = __init__.py modules.py prg.py utils.py server.py telnet.py netvar.py
INSTALL_DIR := pyplc
OBJS := $(patsubst %.py,$(ODIR)/$(INSTALL_DIR)/%.mpy,$(SOURCES))

clean:
	@find ./ -iname __pycache__  | xargs rm -rf

upload: clean
	@cd src && upydev dsync pyplc && upydev dsync kx

all: dirs $(OBJS)

dirs:
	@mkdir -p $(ODIR)/$(INSTALL_DIR)

$(ODIR)/$(INSTALL_DIR)/%.mpy: %.py
	@echo Compiling $<
	@$(MPY-CROSS) $< -o $@

.PHONY: dirs