import os
import sys
import src.main.jython.hello

for root, dirs, files in os.walk("Libs"):
	for filename in files:
		if filename.endswith(".jar"):
			print 'Adding %s to sys.path' % filename
			sys.path.append("Libs/%s" % filename)

from org.apache.log4j import PropertyConfigurator
