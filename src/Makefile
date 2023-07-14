MPY-CROSS?=~/.krax/mpy-cross

clean:
	@find ./ -iname __pycache__  | xargs rm -rf

release: pyplc kx kx_bonjour.py
#	git commit -a
#	@echo PyPLC_VERSION = \"`git describe`\" >pyplc/consts.py
#	for x in $^; do echo upydev dsync $${x} -g; done

upload: clean
	for x in pyplc kx kx_bonjour.py ; do echo upydev dsync $${x} -g; done
# upydev dsync pyplc 
# upydev dsync kx