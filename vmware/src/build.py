import os


for root, dirs, files in os.walk("."):
	for file in files:
		if not file.endswith(".jar"):
			 os.system("jar -uf app.jar %s" % os.path.join(root, file)) 