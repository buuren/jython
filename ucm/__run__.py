# -*- coding: utf-8 -*-
# coding=utf-8
'''
Created on 09.10.2014
@author: Vladimir Kolesnik
'''
import os, sys, datetime

#Local libs
from src.main.jython.CMULogger import log4j

#Java libs
from java.lang import System, Thread
from org.apache.log4j import PropertyConfigurator

currentDate = datetime.datetime.now()
jobName = currentDate.strftime("%Y-%m-%d_%H-%M-%S")

classLoader = Thread.currentThread().getContextClassLoader()
PropertyConfigurator.configure(classLoader.getResource("src/main/resources/log4j.properties")) 
							   
runLogger = log4j("runLogger")

if len(sys.argv) > 1:
	pathToJSON = sys.argv[1]
	runLogger.infoMessage('main', 'Using %s as a configuration file...' % pathToJSON)
else:
	runLogger.infoMessage('main', 'JAR requires at least 1 argument: path to JSON config file.')
	System.exit(1)

from src.main.jython.CMUConfigParser import CMUConfigParser

doCMUExport = CMUConfigParser(pathToJSON).returnObject("CMUOperations", "doCMUExport")
doArchiverExport = CMUConfigParser(pathToJSON).returnObject("ArchiverOperations", "doArchiverExport")
doGeneralOperations = CMUConfigParser(pathToJSON).returnObject("GeneralOperations", "doGeneralOperations")

if doCMUExport:
	runLogger.infoMessage('main', 'Calling CMUOpeartions...')
	from src.main.jython.CMUOperations import CMUHandler
	CMUHandler(pathToJSON).main(jobName)
else:
	runLogger.infoMessage('main', 'Do CMU export is empty - nothing to do.')
	
if doArchiverExport:
	runLogger.infoMessage('main', 'Calling Archiver Operations...')
	from src.main.jython.ArchiverOperations import ArchiverHandler
	ArchiverHandler(pathToJSON).main(jobName)
else:
	runLogger.infoMessage('main', 'Do Archiver Export is empty - nothing to do.')

if doGeneralOperations:
	runLogger.infoMessage('main', 'Calling General Operations...')
	from src.main.jython.GeneralOperations import GeneralOperations
	GeneralOperations(pathToJSON).main()
else:
	runLogger.infoMessage('main', 'Do Archiver Export is empty - nothing to do.')
