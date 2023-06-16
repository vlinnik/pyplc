clean:
	@find ./ -iname __pycache__  | xargs rm -rf

upload: clean
	@cd src
	upydev dsync pyplc 
	upydev dsync kx