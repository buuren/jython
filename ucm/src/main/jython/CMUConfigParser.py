import java.io.File as File
import java.io.FileReader as FileReader

import os

from java.lang import System
from java.lang.System import exit

from org.json.simple.parser import JSONParser
from CMULogger import log4j

class CMUConfigParser:
	CMUConfigParserLogger = log4j("CMUConfigParser")
	
	def __init__(self, jsonFilePath):   
		
		self.filePath = jsonFilePath
		checkFile = File(self.filePath)
		
		if not checkFile.isFile():
			self.CMUConfigParserLogger.infoMessage('__init__', 'Unable to find file: %s' % jsonFilePath)
			System.exit(1)
		
	def returnObject(self, objectStructure, objectType, objectParams=False, noSkip=True):
		reader = FileReader(self.filePath)
		jsonParser = JSONParser()
		jsonObject = jsonParser.parse(reader)

		try:
			structure = jsonObject.get(objectStructure)
			if not structure:
				raise Exception
		except:
			self.CMUConfigParserLogger.infoMessage('returnObject', "Unable to find structure: %s in JSON file." % objectStructure)
			System.exit(1)

		try:
			returnObject = structure.get(objectType)
		except:
			self.CMUConfigParserLogger.infoMessage('returnObject', "Unable to find value %s in structure %s" % (objectStructure, objectType))
		else:
			if objectParams:
				try:
					returnObjectParam = returnObject.get(objectParams)
				except:
					self.CMUConfigParserLogger.infoMessage('returnObject', "Unable to find param %s in value %s in structure %s" % (objectParams, objectStructure, objectType), noSkip)
				else:
					return returnObjectParam
			else:
				return returnObject