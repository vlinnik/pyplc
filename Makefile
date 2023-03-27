MPY-CROSS?=~/.krax/mpy-cross
ODIR ?= $(shell pwd)/build
SOURCES = __init__.py modules.py prg.py utils.py server.py telnet.py netvar.py
INSTALL_DIR := pyplc
OBJS := $(patsubst %.py,$(ODIR)/$(INSTALL_DIR)/%.mpy,$(SOURCES))

clean:
	@find ./ -iname __pycache__  | xargs rm -rf

upload: clean
	@cd src && upydev dsync pyplc -g && upydev dsync kx -g && upydev dsync kx_bonjour.py -g 

all: dirs $(OBJS)

dirs:
	@mkdir -p $(ODIR)/$(INSTALL_DIR)

package:
	@echo PyPLC_VERSION = \"`git describe`\">src/pyplc/consts.py
	python -m build && pip install ./dist/pyplc-0.0.7-py3-none-any.whl --force-reinstall
	
$(ODIR)/$(INSTALL_DIR)/%.mpy: %.py
	@echo Compiling $<
	@$(MPY-CROSS) $< -o $@

.PHONY: dirs
