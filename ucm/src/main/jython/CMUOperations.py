# -*- coding: utf-8 -*-
# coding=utf-8
'''
Created on 09.10.2014
@author: Vladimir Kolesnik
'''

#Python libs:
import time, re, datetime

# RIDC java libs:
from oracle.stellent.ridc.model import TransferFile
from oracle.stellent.ridc.protocol import ServiceResponse, ServiceException

#local classes
from CMULogger import log4j
from CMUConfigParser import CMUConfigParser
from CMUSetupConnection import SetupUCMConnection
from GeneralOperations import GeneralOperations
from ArchiverOperations import ArchiverHandler

#Java libs
from java.lang import Exception, SecurityException
import java.io.FileOutputStream as FileOutputStream
import java.io.ByteArrayOutputStream as ByteArrayOutputStream
import java.io.ObjectOutputStream as ObjectOutputStream
import java.util.ArrayList as ArrayList
import java.io.File as File
import java.io.FilePermission as FilePermission
import java.security.AccessController as AccessController
from java.lang import System
from java.lang.System import exit

def get_methods(input_text):
	for each_method in dir(input_text):
		print each_method
	System.exit(1)

class CMUHandler(SetupUCMConnection):
	"""
	Class to transfer CMU data between servers
	Requires: 
		1) pathToJSON: Main config JSON file. Passed as argument when calling jar
		2) bundleLocation: location to store bundles (zip file which contains CMU data)
	To call: CMUHandler().main(pathToJSON="", bundleLocation="")

	"""
	CMUHandlerLogger = log4j("CMUHandler")

	def __init__(self, pathToJSON):
		self.pathToJSON = pathToJSON
		self.bundleLocation = CMUConfigParser(self.pathToJSON).returnObject("CMUOperations", "bundleStoreLocation")
		
		try:
			self.CMUHandlerLogger.infoMessage('__init__', 'Connecting to server: sourceServer...')
			setupSourceServerData = SetupUCMConnection(self.pathToJSON, 'sourceServer')
			self.sourceClient = setupSourceServerData.outData[0]
			self.sourceUserContext = setupSourceServerData.outData[1]
			self.sourceServerInfo = setupSourceServerData.outData[2]
		except Exception, err:
			self.CMUHandlerLogger.infoMessage('__init__', 'Unable to get information about source server: %s' % err)
			System.exit(1)
		
		try:
			self.CMUHandlerLogger.infoMessage('__init__', 'Connecting to server: targetServer...')
			setupTargetServerData = SetupUCMConnection(self.pathToJSON, 'targetServer')
			self.targetClient = setupTargetServerData.outData[0]
			self.targetUserContext = setupTargetServerData.outData[1]
			self.targetServerInfo = setupTargetServerData.outData[2]
		except Exception, err:
			self.CMUHandlerLogger.infoMessage('__init__', 'Unable to get information about target server: %s' % err)
			System.exit(1)

	def resultSetParser(self):
		self.sourceDataBinder = self.sourceClient.createBinder()
		self.sourceDataBinder.putLocal('IdcService', 'GET_SCHEMA_TABLES')
		serverResponse = self.sourceClient.sendRequest(self.sourceUserContext, self.sourceDataBinder)
		responseData = serverResponse.getResponseAsBinder()

		for eachResultSet in responseData.getResultSetNames():
			for serverComp in responseData.getResultSet(eachResultSet).getRows():
				for eachKey in serverComp.keySet():
					print 'Result set: %s | Key: %s | Value: %s' % (eachResultSet, eachKey, serverComp.get(eachKey))

	def createBackupTemplate(self, continueOnError, addDependencies, ignoreDependencies, CMUClone = False, CMUBackup = False):
		self.CMUHandlerLogger.infoMessage('createBackupTemplate', 'Calling method: BackupTemplate method with params:')
		self.CMUHandlerLogger.infoMessage('createBackupTemplate', '\t[continueOnError=%s; addDependencies=%s; ignoreDependencies=%s; CMUClone=%s; CMUBackup=%s]' % (
			continueOnError, addDependencies, ignoreDependencies, CMUClone, CMUBackup))

		if CMUClone:
			self.CMUHandlerLogger.infoMessage('createBackupTemplate', 'Doing clone operation...')
			customActionName = "clone_backup_%s" % self.bundleName
		elif CMUBackup:
			self.CMUHandlerLogger.infoMessage('createBackupTemplate', 'Doing full backup operation...')
			customActionName = "full_backup_%s" % self.bundleName
		else:
			self.CMUHandlerLogger.infoMessage('createBackupTemplate', 'Doing regular backup operation...')
			customActionName = "backup_%s" % self.bundleName

		try:
			self.targetDataBinder = self.targetClient.createBinder()
			self.targetDataBinder.putLocal("IdcService", "UPDATE_TASK_SECTION")
			self.targetDataBinder.putLocal("isContinueOnError", continueOnError)
			self.targetDataBinder.putLocal("emailResults", "")

			self.targetDataBinder.putLocal("addDependencies", addDependencies)
			if addDependencies == "1":
				self.CMUHandlerLogger.infoMessage('createBackupTemplate', 'Adding dependencies to template')
				self.targetDataBinder.putLocal("cb_addDependencies", addDependencies)
			
			self.targetDataBinder.putLocal("ignoreDependencies", ignoreDependencies)
			if ignoreDependencies == "1":
				self.CMUHandlerLogger.infoMessage('createBackupTemplate', 'Ignoring dependencies to template')
				self.targetDataBinder.putLocal("cb_ignoreDependencies", ignoreDependencies)

			self.targetDataBinder.putLocal("customActionName", customActionName)
			self.targetDataBinder.putLocal("sectionItemList", "")
			self.targetDataBinder.putLocal("TaskName", "")
			self.targetDataBinder.putLocal("idcToken", "")
			self.targetDataBinder.putLocal("taskModified", "1")
			serverResponse = self.targetClient.sendRequest(self.targetUserContext, self.targetDataBinder)
			responseString = serverResponse.getResponseAsString()
			self.findTaskSession = re.findall(re.compile(r'TaskSession=(\w+)', re.IGNORECASE), responseString)[0]
		except Exception, err:
			self.CMUHandlerLogger.infoMessage('createBackupTemplate', 'Unable to get create template on target server: %s' % err)
			System.exit(1)

	def createTemplate(self, templateName, continueOnError, addDependencies, ignoreDependencies):
		self.CMUHandlerLogger.infoMessage('createTemplate', 'Calling method: createTemplate method with params:')
		self.CMUHandlerLogger.infoMessage('createTemplate', '\t[templateName=%s; continueOnError=%s; addDependencies=%s; ignoreDependencies=%s]' % (
			templateName, continueOnError, addDependencies, ignoreDependencies))

		try:
			self.sourceDataBinder = self.sourceClient.createBinder()
			self.sourceDataBinder.putLocal("IdcService", "UPDATE_TASK_SECTION")
			self.sourceDataBinder.putLocal("isContinueOnError", continueOnError)
			self.sourceDataBinder.putLocal("emailResults", "")

			self.targetDataBinder.putLocal("addDependencies", addDependencies)
			if addDependencies == "1":
				self.CMUHandlerLogger.infoMessage('createTemplate', 'Adding dependencies to template')
				self.targetDataBinder.putLocal("cb_addDependencies", addDependencies)

			self.targetDataBinder.putLocal("ignoreDependencies", ignoreDependencies)
			if ignoreDependencies == "1":
				self.CMUHandlerLogger.infoMessage('createTemplate', 'Ignoring dependencies to template')
				self.targetDataBinder.putLocal("cb_ignoreDependencies", ignoreDependencies)

			self.sourceDataBinder.putLocal("customActionName", templateName)
			self.sourceDataBinder.putLocal("sectionItemList", "")
			self.sourceDataBinder.putLocal("TaskName", "")
			self.sourceDataBinder.putLocal("idcToken", "")
			self.sourceDataBinder.putLocal("taskModified", "1")
			serverResponse = self.sourceClient.sendRequest(self.sourceUserContext, self.sourceDataBinder)
			responseString = serverResponse.getResponseAsString()
			self.findTaskSession = re.findall(re.compile(r'TaskSession=(\w+)', re.IGNORECASE), responseString)[0]

		except Exception, err:
			self.CMUHandlerLogger.infoMessage('createTemplate', 'Unable to get create template on source server: %s' % err)
			System.exit(1)

	def backupFunctionWithDeps(self, itemList, sectionID, eachObjectType, isContinueOnError, addDependencies, ignoreDependencies, CMUClone = False):
		self.CMUHandlerLogger.infoMessage('backupFunctionWithDeps', 'Calling method: backupFunctionWithDeps with params:') 
		self.CMUHandlerLogger.infoMessage('backupFunctionWithDeps', '\t[itemList=%s; sectionID=%s; eachObjectType=%s; isContinueOnError=%s; addDependencies=%s, ignoreDependencies=%s, CMUClone=%s]' % (
			itemList, sectionID, eachObjectType, isContinueOnError, addDependencies, ignoreDependencies, CMUClone))

		if CMUClone:
			self.CMUHandlerLogger.infoMessage('backupFunctionWithDeps', 'Cloning...') 
			try:
				self.targetDataBinder.putLocal('IdcService', 'CMU_SELECT_ALL_SECTION_ITEMS')
				self.targetDataBinder.putLocal("sectionItemList", itemList)

				self.targetDataBinder.putLocal("%s.addDependencies" % sectionID, "")
				if addDependencies == "1":
					self.CMUHandlerLogger.infoMessage('backupFunctionWithDeps', 'Adding dependencies for %s' % eachObjectType) 
					self.targetDataBinder.putLocal("cb_%s.addDependencies" % sectionID, addDependencies)
				
				self.targetDataBinder.putLocal("%s.ignoreDependencies" % sectionID, ignoreDependencies)
				if ignoreDependencies == "1":
					self.CMUHandlerLogger.infoMessage('backupFunctionWithDeps', 'Ignoring dependencies for %s' % eachObjectType) 
					self.targetDataBinder.putLocal("cb_%s.ignoreDependencies" % sectionID, ignoreDependencies)

				self.targetDataBinder.putLocal("%s.isContinueOnError" % sectionID, isContinueOnError)
				self.targetDataBinder.putLocal("SectionID", sectionID)
				self.targetDataBinder.putLocal("TaskSession", self.findTaskSession)
				self.targetDataBinder.putLocal("TaskName", "")
				self.targetDataBinder.putLocal('idcToken', '')
				self.targetDataBinder.putLocal("taskModified", "1")
				self.targetClient.sendRequest(self.targetUserContext, self.targetDataBinder)
			except Exception, err:
				self.CMUHandlerLogger.infoMessage('backupFunctionWithDeps', 'Unable to add %s into template [%s]' % (eachObjectType, err))
				System.exit(1)
			else:
				self.CMUHandlerLogger.infoMessage('backupFunctionWithDeps', 'Succesfully added %s to template...' % eachObjectType)
		else:
			try:
				self.targetDataBinder.putLocal('IdcService', 'UPDATE_TASK_SECTION')

				for eachItem in ['cb_item_' + itemName for itemName in itemList.split(',')]:
					self.targetDataBinder.putLocal(eachItem, 'on')
				self.targetDataBinder.putLocal("sectionItemList", itemList)

				self.targetDataBinder.putLocal("%s.addDependencies" % sectionID, "")
				if addDependencies == "1":
					self.CMUHandlerLogger.infoMessage('backupFunctionWithDeps', 'Adding dependencies for %s' % eachObjectType) 
					self.targetDataBinder.putLocal("cb_%s.addDependencies" % sectionID, addDependencies)
				
				self.targetDataBinder.putLocal("%s.ignoreDependencies" % sectionID, ignoreDependencies)
				if ignoreDependencies == "1":
					self.CMUHandlerLogger.infoMessage('backupFunctionWithDeps', 'Ignoring dependencies for %s' % eachObjectType) 
					self.targetDataBinder.putLocal("cb_%s.ignoreDependencies" % sectionID, ignoreDependencies)

				self.targetDataBinder.putLocal("SectionID", sectionID)
				self.targetDataBinder.putLocal("TaskSession", self.findTaskSession)
				self.targetDataBinder.putLocal("TaskName", "")
				self.targetDataBinder.putLocal('idcToken', '')
				self.targetDataBinder.putLocal("taskModified", "1")
				self.targetClient.sendRequest(self.targetUserContext, self.targetDataBinder)
			except Exception, err:
				self.CMUHandlerLogger.infoMessage('backupFunctionWithDeps', 'Unable to add %s into template [%s]' % (eachObjectType, err))
				System.exit(1)
			else:
				self.CMUHandlerLogger.infoMessage('backupFunctionWithDeps', 'Succesfully added %s to template...' % eachObjectType)

	def backupFunctionWithoutDeps(self, itemList, sectionID, eachObjectType, isContinueOnError, CMUClone = False):
		self.CMUHandlerLogger.infoMessage('backupFunctionWithoutDeps', 'Calling method: backupFunctionWithoutDeps with params:') 
		self.CMUHandlerLogger.infoMessage('backupFunctionWithoutDeps', '\t[itemList=%s; eachObjectType=%s; sectionID=%s; isContinueOnError=%s, CMUClone=%s]' % (
			itemList, sectionID, eachObjectType, isContinueOnError, CMUClone))

		if CMUClone:
			self.CMUHandlerLogger.infoMessage('backupFunctionWithoutDeps', 'Cloning...')
			try:
				self.targetDataBinder.putLocal("IdcService", "CMU_SELECT_ALL_SECTION_ITEMS")
				self.targetDataBinder.putLocal("sectionItemList", itemList)
				self.targetDataBinder.putLocal("%s.isContinueOnError" % sectionID, isContinueOnError)
				self.targetDataBinder.putLocal("SectionID", sectionID)
				self.targetDataBinder.putLocal("TaskSession", self.findTaskSession)
				self.targetDataBinder.putLocal("TaskName", "")
				self.targetDataBinder.putLocal('idcToken', '')
				self.targetDataBinder.putLocal("taskModified", "1")

				if eachObjectType == "Components":
					self.targetDataBinder.putLocal("cb_%s.cmuBuildComponents" % sectionID, "1")
					self.targetDataBinder.putLocal("%s.cmuBuildComponents" % sectionID, "")

				self.targetClient.sendRequest(self.targetUserContext, self.targetDataBinder)

			except Exception, err:
				self.CMUHandlerLogger.infoMessage('backupFunctionWithoutDeps', 'Unable to add %s into template: %s' % (eachObjectType, err))
				System.exit(1)
			else:
				self.CMUHandlerLogger.infoMessage('backupFunctionWithoutDeps', 'Successfully added %s to template' % itemList)
		else:
			try:
				self.targetDataBinder.putLocal("IdcService", "UPDATE_TASK_SECTION")
				
				for eachItem in ['cb_item_' + itemName for itemName in itemList.split(',')]:
					self.targetDataBinder.putLocal(eachItem, 'on')
					
				self.targetDataBinder.putLocal("sectionItemList", itemList)
				self.targetDataBinder.putLocal("%s.isContinueOnError" % sectionID, isContinueOnError)
				self.targetDataBinder.putLocal("SectionID", sectionID)
				self.targetDataBinder.putLocal("TaskSession", self.findTaskSession)
				self.targetDataBinder.putLocal("TaskName", "")
				self.targetDataBinder.putLocal('idcToken', '')
				self.targetDataBinder.putLocal("taskModified", "1")

				if eachObjectType == "Components":
					self.targetDataBinder.putLocal("cb_%s.cmuBuildComponents" % sectionID, "1")
					self.targetDataBinder.putLocal("%s.cmuBuildComponents" % sectionID, "")

				self.targetClient.sendRequest(self.targetUserContext, self.targetDataBinder)
			except Exception, err:
				self.CMUHandlerLogger.infoMessage('backupFunctionWithoutDeps', 'Unable to add %s into template: %s' % (eachObjectType, err))
				System.exit(1)
			else:
				self.CMUHandlerLogger.infoMessage('backupFunctionWithoutDeps', 'Successfully added %s to template' % itemList)

	def functionWithDeps(self, itemList, sectionID, eachObjectType, isContinueOnError, addDependencies, ignoreDependencies, CMUClone = False):

		self.CMUHandlerLogger.infoMessage('functionWithDeps', 'Calling method: functionWithDeps with params:') 
		self.CMUHandlerLogger.infoMessage('functionWithDeps', '\t[itemList=%s; sectionID=%s; eachObjectType=%s; isContinueOnError=%s; addDependencies=%s, ignoreDependencies=%s, CMUClone=%s]' % (
				itemList, sectionID, eachObjectType, isContinueOnError, addDependencies, ignoreDependencies, CMUClone))

		if CMUClone:
			self.CMUHandlerLogger.infoMessage('functionWithDeps', 'Cloning...')
			try:
				self.sourceDataBinder.putLocal('IdcService', 'CMU_SELECT_ALL_SECTION_ITEMS')
				self.sourceDataBinder.putLocal("sectionItemList", itemList)
				
				self.sourceDataBinder.putLocal("%s.addDependencies" % sectionID, addDependencies)
				if addDependencies == "1":
					self.CMUHandlerLogger.infoMessage('functionWithDeps', 'Adding dependencies for %s' % eachObjectType) 
					self.sourceDataBinder.putLocal("cb_%s.addDependencies" % sectionID, addDependencies)
				
				self.sourceDataBinder.putLocal("%s.ignoreDependencies" % sectionID, ignoreDependencies)
				if ignoreDependencies == "1":
					self.CMUHandlerLogger.infoMessage('functionWithDeps', 'Ignoring dependencies for %s' % eachObjectType) 
					self.sourceDataBinder.putLocal("cb_%s.ignoreDependencies" % sectionID, ignoreDependencies)

				self.sourceDataBinder.putLocal("SectionID", sectionID)
				self.sourceDataBinder.putLocal("TaskSession", self.findTaskSession)
				self.sourceDataBinder.putLocal("TaskName", "")
				self.sourceDataBinder.putLocal('idcToken', '')
				self.sourceDataBinder.putLocal("taskModified", "1")
				self.sourceClient.sendRequest(self.sourceUserContext, self.sourceDataBinder)
			except Exception, err:
				self.CMUHandlerLogger.infoMessage('functionWithDeps', 'Unable to add %s into template [%s]' % (eachObjectType, err))
				System.exit(1)
			else:
				self.CMUHandlerLogger.infoMessage('functionWithDeps', 'Succesfully added %s to template...' % eachObjectType)
		else:
			try:
				self.sourceDataBinder.putLocal('IdcService', 'UPDATE_TASK_SECTION')
				self.sourceDataBinder.putLocal("sectionItemList", itemList)

				for eachItem in ['cb_item_' + itemName for itemName in itemList.split(',')]:
					self.sourceDataBinder.putLocal(eachItem, 'on')

				self.sourceDataBinder.putLocal("%s.addDependencies" % sectionID, addDependencies)
				if addDependencies == "1":
					self.CMUHandlerLogger.infoMessage('functionWithDeps', 'Adding dependencies for %s' % eachObjectType) 
					self.sourceDataBinder.putLocal("cb_%s.addDependencies" % sectionID, addDependencies)
				
				self.sourceDataBinder.putLocal("%s.ignoreDependencies" % sectionID, ignoreDependencies)
				if ignoreDependencies == "1":
					self.CMUHandlerLogger.infoMessage('functionWithDeps', 'Ignoring dependencies for %s' % eachObjectType) 
					self.sourceDataBinder.putLocal("cb_%s.ignoreDependencies" % sectionID, ignoreDependencies)

				self.sourceDataBinder.putLocal("SectionID", sectionID)
				self.sourceDataBinder.putLocal("TaskSession", self.findTaskSession)
				self.sourceDataBinder.putLocal("TaskName", "")
				self.sourceDataBinder.putLocal('idcToken', '')
				self.sourceDataBinder.putLocal("taskModified", "1")
				self.sourceClient.sendRequest(self.sourceUserContext, self.sourceDataBinder)
			except Exception, err:
				self.CMUHandlerLogger.infoMessage('functionWithDeps', 'Unable to add %s into template [%s]' % (eachObjectType, err))
				System.exit(1)
			else:
				self.CMUHandlerLogger.infoMessage('functionWithDeps', 'Succesfully added %s to template...' % eachObjectType)

	def functionWithoutDeps(self, itemList, sectionID, eachObjectType, isContinueOnError, CMUClone = False):
		self.CMUHandlerLogger.infoMessage('functionWithoutDeps', 'Calling method: functionWithoutDeps with params:') 
		self.CMUHandlerLogger.infoMessage('functionWithoutDeps', '\t[itemList=%s; eachObjectType=%s; sectionID=%s; isContinueOnError=%s, CMUClone=%s]' % (
			itemList, sectionID, eachObjectType, isContinueOnError, CMUClone))

		if CMUClone:
			self.CMUHandlerLogger.infoMessage('functionWithoutDeps', 'Cloning...') 
			try:
				self.sourceDataBinder.putLocal("IdcService", "CMU_SELECT_ALL_SECTION_ITEMS")
				self.sourceDataBinder.putLocal("sectionItemList", itemList)
				self.sourceDataBinder.putLocal("%s.isContinueOnError" % sectionID, isContinueOnError)
				self.sourceDataBinder.putLocal("SectionID", sectionID)
				self.sourceDataBinder.putLocal("TaskSession", self.findTaskSession)
				self.sourceDataBinder.putLocal("TaskName", "")
				self.sourceDataBinder.putLocal('idcToken', '')
				self.sourceDataBinder.putLocal("taskModified", "1")

				if eachObjectType == "Components":

					itemGet = self.returnCMUSectionAndItem(eachObjectType)[0]
					sectionName = self.returnCMUSectionAndItem(eachObjectType)[1]  
					itemList = self.generateItemList(self.sourceServerData, sectionName, itemGet)

					self.componentsToEnable = []
					self.sourceDataBinder.putLocal("cb_%s.cmuBuildComponents" % sectionID, "1")
					self.sourceDataBinder.putLocal("%s.cmuBuildComponents" % sectionID, "")

					for compListName in itemList:
						self.componentsToEnable.append(compListName)

				self.sourceClient.sendRequest(self.sourceUserContext, self.sourceDataBinder)

			except Exception, err:
				self.CMUHandlerLogger.infoMessage('functionWithoutDeps', 'Unable to add %s into template: %s' % (eachObjectType, err))
				System.exit(1)
			else:
				self.CMUHandlerLogger.infoMessage('functionWithoutDeps', 'Successfully added %s to template' % itemList)
		else:
			try:
				self.sourceDataBinder.putLocal("IdcService", "UPDATE_TASK_SECTION")
				
				for eachItem in ['cb_item_' + itemName for itemName in itemList.split(',')]:
					self.sourceDataBinder.putLocal(eachItem, 'on')
					
				self.sourceDataBinder.putLocal("sectionItemList", itemList)
				self.sourceDataBinder.putLocal("%s.isContinueOnError" % sectionID, isContinueOnError)
				self.sourceDataBinder.putLocal("SectionID", sectionID)
				self.sourceDataBinder.putLocal("TaskSession", self.findTaskSession)
				self.sourceDataBinder.putLocal("TaskName", "")
				self.sourceDataBinder.putLocal('idcToken', '')
				self.sourceDataBinder.putLocal("taskModified", "1")

				if eachObjectType == "Components":
					self.componentsToEnable = []
					self.sourceDataBinder.putLocal("cb_%s.cmuBuildComponents" % sectionID, "1")
					self.sourceDataBinder.putLocal("%s.cmuBuildComponents" % sectionID, "")
					for compListName in itemList.split(','):
						self.componentsToEnable.append(compListName)

				self.sourceClient.sendRequest(self.sourceUserContext, self.sourceDataBinder)

			except Exception, err:
				self.CMUHandlerLogger.infoMessage('functionWithoutDeps', 'Unable to add %s into template: %s' % (eachObjectType, err))
				System.exit(1)
			else:
				self.CMUHandlerLogger.infoMessage('functionWithoutDeps', 'Successfully added %s to template' % itemList)

	def exportBackupTemplate(self, continueOnError, addDependencies, ignoreDependencies):
		self.CMUHandlerLogger.infoMessage('exportBackupTemplate', 'Calling method: exportBackupTemplate method with params:')
		
		self.CMUHandlerLogger.infoMessage('exportBackupTemplate', '\t[continueOnError=%s; addDependencies=%s; ignoreDependencies=%s]' % (
			continueOnError, addDependencies, ignoreDependencies))

		try:
			self.targetDataBinder.putLocal("IdcService", "CMU_UPDATE_AND_CREATE_ACTION")
			self.targetDataBinder.putLocal("contentserver.isContinueOnError", continueOnError)

			self.targetDataBinder.putLocal("addDependencies", addDependencies)
			if addDependencies == "1":
				self.targetDataBinder.putLocal("cb_addDependencies", addDependencies)
			
			self.targetDataBinder.putLocal("ignoreDependencies", ignoreDependencies)
			if ignoreDependencies == "1":
				self.targetDataBinder.putLocal("cb_ignoreDependencies", ignoreDependencies)

			self.targetDataBinder.putLocal("sectionItemList", "")
			self.targetDataBinder.putLocal("TaskName", "")
			self.targetDataBinder.putLocal("idcToken", "")
			self.targetDataBinder.putLocal("TaskSession", self.findTaskSession)
			self.targetDataBinder.putLocal("SectionID", "contentserver")
			self.targetDataBinder.putLocal("taskModified", "1")
			self.targetClient.sendRequest(self.targetUserContext, self.targetDataBinder)
		except Exception, err:
			self.CMUHandlerLogger.infoMessage('exportBackupTemplate', 'Exception while exporting backup template. %s' % err)
		else:
			self.CMUHandlerLogger.infoMessage('exportBackupTemplate', 'Export is done. Verifying results...')
		time.sleep(2)

		errorList = []
		
		while True:
			try:
				readtargetDataBinder = self.targetClient.createBinder()
				readtargetDataBinder.putLocal("IdcService", "CMU_LIST_ACTIVE_ACTIONS")
				
				readServerResponse = self.targetClient.sendRequest(self.targetUserContext, readtargetDataBinder)
				readExportResponseBundle = readServerResponse.getResponseAsBinder()
			
				if readExportResponseBundle:
					for eachResult in readExportResponseBundle.getResultSet('ActiveCmuActions').getRows():
						if eachResult.get('ActionEventType') == "error":

							errorMessage = 'Item: %s, Time: %s, Message: %s, Section: %s, Type: %s' % (
								   eachResult.get('ActionEventItem'), eachResult.get('ActionEventTime'), 
								   eachResult.get('ActionEventMessage'), eachResult.get('ActionEventSection'), 
								   eachResult.get('ActionEventType'))

							if errorMessage not in errorList:
								self.CMUHandlerLogger.infoMessage('exportBackupTemplate', 'Found error while exporting backup template. Printing error trace:')
								errorList.append(errorMessage)
								self.CMUHandlerLogger.infoMessage('exportBackupTemplate', errorMessage)
								
							
						rowsLen = readExportResponseBundle.getResultSet('ActiveCmuActions').getRows().size()-1
						lastMessage = readExportResponseBundle.getResultSet('ActiveCmuActions').getRows()[rowsLen].get('ActionEventMessage')

				else:
					self.CMUHandlerLogger.infoMessage('exportBackupTemplate', 'Unable to read server response. Retry in 10 seconds')
					time.sleep(10)
					continue

				if lastMessage == "!csCmuAbortedWithErrors":
					self.CMUHandlerLogger.infoMessage('exportBackupTemplate', 'Backup template export has been aborted by the server. Exit script.')
					System.exit(1)

				if lastMessage == "!csCmuActionFinished":
					self.CMUHandlerLogger.infoMessage('exportBackupTemplate', 'Successfully exported backup template.')
					break

				self.CMUHandlerLogger.infoMessage('exportBackupTemplate', 'Last message was: %s' % lastMessage)

				time.sleep(10)
			except Exception, err:
				self.CMUHandlerLogger.infoMessage('exportBackupTemplate', 'Error occured during CMU_LIST_ACTIVE_ACTIONS. Exit.')
				System.exit(1)

	def exportTemplate(self, continueOnError, addDependencies, ignoreDependencies):
		self.CMUHandlerLogger.infoMessage('exportTemplate', 'Calling method: exportTemplate method with params:')
	
		print '\t[continueOnError=%s; addDependencies=%s; ignoreDependencies=%s]' % (
			continueOnError, addDependencies, ignoreDependencies)

		try:
			self.sourceDataBinder.putLocal("IdcService", "CMU_UPDATE_AND_CREATE_ACTION")
			self.sourceDataBinder.putLocal("contentserver.isContinueOnError", continueOnError)
			self.targetDataBinder.putLocal("addDependencies", addDependencies)

			if addDependencies == "1":
				self.CMUHandlerLogger.infoMessage('exportTemplate', 'Exporting with dependencies')
				self.targetDataBinder.putLocal("cb_addDependencies", addDependencies)
			
			self.targetDataBinder.putLocal("ignoreDependencies", ignoreDependencies)

			if ignoreDependencies == "1":
				self.CMUHandlerLogger.infoMessage('exportTemplate', 'Exporting with dependencies')
				self.targetDataBinder.putLocal("cb_ignoreDependencies", ignoreDependencies)

			self.sourceDataBinder.putLocal("sectionItemList", "")
			self.sourceDataBinder.putLocal("TaskName", "")
			self.sourceDataBinder.putLocal("idcToken", "")
			self.sourceDataBinder.putLocal("TaskSession", self.findTaskSession)
			self.sourceDataBinder.putLocal("SectionID", "contentserver")
			self.sourceDataBinder.putLocal("taskModified", "1")
			self.sourceClient.sendRequest(self.sourceUserContext, self.sourceDataBinder)
		except Exception, err:
			self.CMUHandlerLogger.infoMessage('exportTemplate', 'Exception while exporting template. %s' % err)
		else:
			self.CMUHandlerLogger.infoMessage('exportTemplate', 'Export is completed. Verifying results...')

		time.sleep(2)
		errorList = []
		
		while True:
			try:
				readSourceDataBinder = self.sourceClient.createBinder()
				readSourceDataBinder.putLocal("IdcService", "CMU_LIST_ACTIVE_ACTIONS")
				
				readServerResponse = self.sourceClient.sendRequest(self.sourceUserContext, readSourceDataBinder)
				readExportResponseBundle = readServerResponse.getResponseAsBinder()
			
				if readExportResponseBundle:
					for eachResult in readExportResponseBundle.getResultSet('ActiveCmuActions').getRows():
						if eachResult.get('ActionEventType') == "error":

							errorMessage = 'Item: %s, Time: %s, Message: %s, Section: %s, Type: %s' % (
								   eachResult.get('ActionEventItem'), eachResult.get('ActionEventTime'), 
								   eachResult.get('ActionEventMessage'), eachResult.get('ActionEventSection'), 
								   eachResult.get('ActionEventType'))

							if errorMessage not in errorList:
								self.CMUHandlerLogger.infoMessage('exportTemplate', 'Found error while exporting template. Printing error trace:')
								errorList.append(errorMessage)
								self.CMUHandlerLogger.infoMessage('exportTemplate', errorMessage)
							
						rowsLen = readExportResponseBundle.getResultSet('ActiveCmuActions').getRows().size()-1
						lastMessage = readExportResponseBundle.getResultSet('ActiveCmuActions').getRows()[rowsLen].get('ActionEventMessage')

				else:
					self.CMUHandlerLogger.infoMessage('exportTemplate', 'Unable to read server response. Retry in 10 seconds')
					time.sleep(10)
					continue

				if lastMessage == "!csCmuAbortedWithErrors":
					self.CMUHandlerLogger.infoMessage('exportTemplate', 'Bundle export has been aborted by the server. Exit script.')
					System.exit(1)

				if lastMessage == "!csCmuActionFinished":
					self.CMUHandlerLogger.infoMessage('exportTemplate', 'Successfully exported template. Proceeding to download bundle...')
					break

				self.CMUHandlerLogger.infoMessage('exportBackupTemplate', 'Last message was: %s' % lastMessage)
				time.sleep(10)
			except Exception, err:
				self.CMUHandlerLogger.infoMessage('exportTemplate', 'Error occured during CMU_LIST_ACTIVE_ACTIONS. Exit.')
				System.exit(1)

	def downloanBundle(self, downloadBundleName):
		bundleExists = False
		attempts = 0

		self.sourceDataBinder = self.sourceClient.createBinder()
		self.sourceDataBinder.putLocal("IdcService", "CMU_GET_ALL_IMPORT_BUNDLES")
		
		while True:
			try:
				serverResponse = self.sourceClient.sendRequest(self.sourceUserContext, self.sourceDataBinder)
				bundlesResultSet = serverResponse.getResponseAsBinder().getResultSet('CmuBundles')
	
				for eachBundle in bundlesResultSet.getRows():
					if downloadBundleName == eachBundle.get('TaskName'):
						bundleExists = True
			except Exception, err:
				self.CMUHandlerLogger.infoMessage('downloanBundle', 'Exception while finding bundle. %s' % err)
				System.exit(1)
			else:
				if bundleExists:
					break
			finally:
				if attempts == 3:
					self.CMUHandlerLogger.infoMessage('downloanBundle', 'Could not find bundle after 30 seconds. Exit.')
					System.exit(1)
				if not bundleExists:
					self.CMUHandlerLogger.infoMessage('downloanBundle', 'Bundle is not ready yet. Checking for errors and will attempt to download bundle again in 10 seconds')
					attempts += 1
					time.sleep(10)

		donwloadDataBinder = self.sourceClient.createBinder()
		donwloadDataBinder.putLocal("IdcService", "CMU_DOWNLOAD_BUNDLE")
		donwloadDataBinder.putLocal("TaskName", downloadBundleName)
		serverResponse = self.sourceClient.sendRequest(self.sourceUserContext, donwloadDataBinder)
		
		if (serverResponse.getResponseType().equals(ServiceResponse.ResponseType.STREAM)):
			fstream = serverResponse.getResponseStream()
			outFileName = "%s%s.zip" % (self.bundleLocation, downloadBundleName)
			outFilenameStream = FileOutputStream(outFileName)
			
			byteArrayList = ArrayList()
			byteArrayList.add(1024)
			ByteArrayOutStream = ByteArrayOutputStream()
			objectOutputStream = ObjectOutputStream(ByteArrayOutStream)
			objectOutputStream.writeObject(byteArrayList)
			objectOutputStream.close()
			byteArray = ByteArrayOutStream.toByteArray()
			
			cFileStream = fstream.read(byteArray, 0, len(byteArray))
			while (cFileStream> 0):
				outFilenameStream.write(byteArray, 0, cFileStream)
				outFilenameStream.flush()
				cFileStream = fstream.read(byteArray, 0, len(byteArray))
			outFilenameStream.close()
			self.CMUHandlerLogger.infoMessage('downloanBundle', "Download is completed")
			fstream.close()
		else:
			self.CMUHandlerLogger.infoMessage('downloanBundle', "Download response was not a stream. Unable to download bundle")
			System.exit(1)
		
		serverResponse.close()

	def transferBundle(self, downloadBundleName):
		bundleLocation = "%s%s.zip" % (self.bundleLocation, downloadBundleName)
		
		checkFile = File(bundleLocation)
		
		if not checkFile.isFile():
			self.CMUHandlerLogger.infoMessage('transferBundle', 'Unable to find file:', bundleLocation)
			System.exit(1)
		try:
			self.targetDataBinder = self.targetClient.createBinder()
			self.targetDataBinder.putLocal("IdcService", "CMU_UPLOAD_BUNDLE")
			self.targetDataBinder.addFile("bundleName", TransferFile(checkFile))
			self.targetDataBinder.putLocal("createExportTemplate", "")
			self.targetDataBinder.putLocal("forceBundleOverwrite", "1")
			self.targetClient.sendRequest(self.targetUserContext, self.targetDataBinder)
		except Exception, err:
			self.CMUHandlerLogger.infoMessage('transferBundle', 'Unable to transfer bundle: %s [%s]' % (bundleLocation, err))
		else:
			self.CMUHandlerLogger.infoMessage('transferBundle', 'Successfully transfered bundle')
			time.sleep(5)

	def importBundle(self, downloadBundleName, IsContinueOnError, AddDependencies, IgnoreDependencies):
		self.CMUHandlerLogger.infoMessage('importBundle', 'Checking if bundle %s exists...' % downloadBundleName)
		self.targetDataBinder = self.targetClient.createBinder()
		self.targetDataBinder.putLocal("IdcService", "CMU_GET_ALL_IMPORT_BUNDLES")
		attempts = 0
		bundleExists = False
		
		while True:
			try:
				serverResponse = self.targetClient.sendRequest(self.targetUserContext, self.targetDataBinder)
				bundlesResultSet = serverResponse.getResponseAsBinder().getResultSet('CmuBundles')
	
				for eachBundle in bundlesResultSet.getRows():
					if downloadBundleName == eachBundle.get('TaskName'):
						bundleExists = True
			except Exception, err:
				self.CMUHandlerLogger.infoMessage('importBundle', 'Exception while finding bundle. %s' % err)
				System.exit(1)
			else:
				if bundleExists:
					self.CMUHandlerLogger.infoMessage('importBundle', 'Bundle is found: %s. Proceeding to import...' % eachBundle.get('TaskName'))
					break
			finally:
				if attempts == 3:
					self.CMUHandlerLogger.infoMessage('importBundle', 'Could not find bundle after 30 seconds. Exit.')
					System.exit(1)
				if not bundleExists:
					self.CMUHandlerLogger.infoMessage('importBundle', 'Bundle is not ready yet. Will search again in 10 seconds')
					attempts += 1
					time.sleep(10)
		try:
			self.targetDataBinder = self.targetClient.createBinder()
			self.targetDataBinder.putLocal("IdcService", "CMU_UPDATE_AND_CREATE_ACTION")
			self.targetDataBinder.putLocal("isContinueOnError", IsContinueOnError)
			self.targetDataBinder.putLocal("emailResults", "")
			self.targetDataBinder.putLocal("cb_addDependencies", AddDependencies)
			self.targetDataBinder.putLocal("addDependencies", "")
			self.targetDataBinder.putLocal("ignoreDependencies", IgnoreDependencies)
			self.targetDataBinder.putLocal("cb_isOverwrite", "1")
			self.targetDataBinder.putLocal("isOverwrite", "1")
			self.targetDataBinder.putLocal("idcToken", "")
			self.targetDataBinder.putLocal("sectionItemList", "")
			self.targetDataBinder.putLocal("TaskName", downloadBundleName)
			self.targetDataBinder.putLocal("TaskSession", self.findTaskSession)
			self.targetDataBinder.putLocal("isImport", "1")
			self.targetDataBinder.putLocal("taskModified", '0')
			self.targetClient.sendRequest(self.targetUserContext, self.targetDataBinder)
		except Exception, err:
			self.CMUHandlerLogger.infoMessage('importBundle', 'Exception occured while importing bundle. [%s]' % err)
			System.exit(1)
		else:
			self.CMUHandlerLogger.infoMessage('importBundle', 'Import bundle is completed. Verifying results...')

		time.sleep(5)
		errorList = []

		while True:
			try:
				readtargetDataBinder = self.targetClient.createBinder()
				readtargetDataBinder.putLocal("IdcService", "CMU_LIST_ACTIVE_ACTIONS")
				
				readServerResponse = self.targetClient.sendRequest(self.targetUserContext, readtargetDataBinder)
				readExportResponseBundle = readServerResponse.getResponseAsBinder()
			
				if readExportResponseBundle:
					for eachResult in readExportResponseBundle.getResultSet('ActiveCmuActions').getRows():
						if eachResult.get('ActionEventType') == "error":

							errorMessage = 'Item: %s, Time: %s, Message: %s, Section: %s, Type: %s' % (
								   eachResult.get('ActionEventItem'), eachResult.get('ActionEventTime'), 
								   eachResult.get('ActionEventMessage'), eachResult.get('ActionEventSection'), 
								   eachResult.get('ActionEventType'))

							if errorMessage not in errorList:
								self.CMUHandlerLogger.infoMessage('importBundle', 'Found error while importing bundle. Printing error trace:')
								self.CMUHandlerLogger.infoMessage('importBundle', errorMessage)
								errorList.append(errorMessage)
							
						rowsLen = readExportResponseBundle.getResultSet('ActiveCmuActions').getRows().size()-1
						lastMessage = readExportResponseBundle.getResultSet('ActiveCmuActions').getRows()[rowsLen].get('ActionEventMessage')

				else:
					self.CMUHandlerLogger.infoMessage('importBundle', 'Unable to read server response. Retry in 10 seconds')
					time.sleep(10)
					continue

				if lastMessage == "!csCmuAbortedWithErrors":
					self.CMUHandlerLogger.infoMessage('importBundle', 'Import has been aborted by the server. Exit script.')
					System.exit(1)

				if lastMessage == "!csCmuActionFinished":
					self.CMUHandlerLogger.infoMessage('importBundle', 'Successfully imported bundle.')
					break

				self.CMUHandlerLogger.infoMessage('importBundle', 'Last message was: %s' % lastMessage)

				time.sleep(10)
			except Exception, err:
				self.CMUHandlerLogger.infoMessage('importBundle', 'Error occured during CMU_LIST_ACTIVE_ACTIONS. Exit.')
				System.exit(1)

		try:
			if len(self.componentsToEnable) > 0:
				self.enableComponents()
		except AttributeError:
			pass
		
	def enableComponents(self):
		self.CMUHandlerLogger.infoMessage('enableComponents', 'Verifying the components exist on target server')
		
		self.targetDataBinder = self.targetClient.createBinder()
		self.targetDataBinder.putLocal("IdcService", "CONFIG_INFO")
		serverResponse = self.targetClient.sendRequest(self.targetUserContext, self.targetDataBinder)
		responseData = serverResponse.getResponseAsBinder()

		for eachCompEnable in self.componentsToEnable:
			if eachCompEnable == "SelectivelyRefineAndIndex":
				self.componentsToEnable.remove("SelectivelyRefineAndIndex")
			else:
				if not eachCompEnable in [eachComp.get('name') for eachComp in responseData.getResultSet("DisabledComponents").getRows()]:
					self.CMUHandlerLogger.infoMessage('enableComponents', 'Unable to find component %s in disabled comp list at target server' % eachCompEnable)
					System.exit(1)
		
		compsListString = ",".join(eachCompName for eachCompName in self.componentsToEnable)
		self.CMUHandlerLogger.infoMessage('enableComponents', 'Enabling component: %s' % compsListString )
		try:
			self.targetDataBinder = self.targetClient.createBinder()
			self.targetDataBinder.putLocal("IdcService", "ADMIN_TOGGLE_COMPONENTS")
			self.targetDataBinder.putLocal("idcToken", "")
			self.targetDataBinder.putLocal("isEnable", "1")
			self.targetDataBinder.putLocal("IDC_Id",  CMUConfigParser(self.pathToJSON).returnObject("targetServer", "idc_id"))
			self.targetDataBinder.putLocal("ComponentNames", compsListString)
			self.targetDataBinder.putLocal("componentFilterGroup", "")
			self.targetDataBinder.putLocal("showOfficialComponents", "1")
			self.targetDataBinder.putLocal("showCustomComponents", "1")
			self.targetDataBinder.putLocal("showSystemComponents", "")
			self.targetDataBinder.putLocal("componentsTagsFilter", "")
			for eachEnableComp in self.componentsToEnable:
				self.targetDataBinder.putLocal("DisabledComponentList", eachEnableComp)
					
			self.targetClient.sendRequest(self.targetUserContext, self.targetDataBinder)
		except Exception, err:
			self.CMUHandlerLogger.infoMessage('enableComponents', 'Exception occured while enabling components. [%s]' % err)
		else:
			self.CMUHandlerLogger.infoMessage('enableComponents', 'Enable components is completed.')    

	def checkPreReq(self, sourceCompPath, targetCompPath, eachObjectType, sectionName, itemGet):
		"""
		Function to compare all CMU sections between source and target servers.
		"""
		self.sourceDataBinder = self.sourceClient.createBinder()
		self.sourceDataBinder.putLocal("IdcService", "CMU_LIST_TASK_SECTION")
		self.sourceDataBinder.putLocal("SectionID", sectionName)
		serverResponse = self.sourceClient.sendRequest(self.sourceUserContext, self.sourceDataBinder)
		
		try:
			responseData = serverResponse.getResponseAsBinder()
		except ServiceException, err:
			self.CMUHandlerLogger.infoMessage('checkPreReq', 'Unable to find the following server section %s [%s]' % (sectionName, err))
		
		sourceToAddIntoDict = []
		
		for eachCompName in responseData.getResultSet('SectionItems').getRows():
			sourceToAddIntoDict.append(eachCompName.get(itemGet))

		self.targetDataBinder = self.targetClient.createBinder()
		self.targetDataBinder.putLocal("IdcService", "CMU_LIST_TASK_SECTION")
		self.targetDataBinder.putLocal("SectionID", sectionName)
		serverResponse = self.targetClient.sendRequest(self.targetUserContext, self.targetDataBinder)
		
		try:
			responseData = serverResponse.getResponseAsBinder()
		except ServiceException, err:
			self.CMUHandlerLogger.infoMessage('checkPreReq', 'Unable to find the following server section %s [%s]' % (sectionName, err))
		
		targetToAddIntoDict = []
		
		for eachCompName in responseData.getResultSet('SectionItems').getRows():
			targetToAddIntoDict.append(eachCompName.get(itemGet))
		
		if eachObjectType == "Components":
			self.sourceDataBinder = self.sourceClient.createBinder()
			self.sourceDataBinder.putLocal("IdcService", "CONFIG_INFO")
			serverResponse = self.sourceClient.sendRequest(self.sourceUserContext, self.sourceDataBinder)
			responseData = serverResponse.getResponseAsBinder()
			
			for eachComp in responseData.getResultSet("EnabledComponents").getRows():
				if sourceCompPath in eachComp.get('location'):
					sourceCompName = eachComp.get('location').split('/')[-2]
					sourceToAddIntoDict.append(sourceCompName)
				
			self.targetDataBinder = self.targetClient.createBinder()
			self.targetDataBinder.putLocal("IdcService", "CONFIG_INFO")
			serverResponse = self.targetClient.sendRequest(self.targetUserContext, self.targetDataBinder)
			responseData = serverResponse.getResponseAsBinder()
			
			for eachComp in responseData.getResultSet("EnabledComponents").getRows():
				if targetCompPath in eachComp.get('location'): 
					targetCompName = eachComp.get('location').split('/')[-2]
					targetToAddIntoDict.append(targetCompName)
					
		self.sourceCMUData[eachObjectType] = sourceToAddIntoDict
		self.targetCMUData[eachObjectType] = targetToAddIntoDict

	def findContentServerSection(self, searchFilter, sectionName, itemGet, includeStandard=False):

		self.CMUHandlerLogger.infoMessage('findContentServerSection', 'Calling method: findContentServerSection method with params:')

		self.CMUHandlerLogger.infoMessage('findContentServerSection', '\t[searchFilter=%s; sectionName=%s; itemGet=%s, includeStandard=%s]' % (
			searchFilter, sectionName, itemGet, includeStandard))

		if "*" in searchFilter:
			searchFilter = searchFilter.replace("*", "(\w+)")
	
		dataToExport = []
		self.sourceDataBinder = self.sourceClient.createBinder()
		self.sourceDataBinder.putLocal("IdcService", "CMU_LIST_TASK_SECTION")
		self.sourceDataBinder.putLocal("SectionID", sectionName)
		serverResponse = self.sourceClient.sendRequest(self.sourceUserContext, self.sourceDataBinder)
		
		try:
			responseData = serverResponse.getResponseAsBinder()
		except ServiceException, err:
			self.CMUHandlerLogger.infoMessage('findContentServerSection', 'Unable to find the following server section %s [%s]' % (sectionName, err))

		for eachCompName in responseData.getResultSet('SectionItems').getRows():
			matchFilter = re.findall(re.compile(r'%s' % searchFilter, re.IGNORECASE), eachCompName.get(itemGet))
			if matchFilter:
				self.CMUHandlerLogger.infoMessage('findContentServerSection', 'Adding %s to itemList' % eachCompName.get(itemGet))
				dataToExport.append(eachCompName.get(itemGet))
		if includeStandard:
			"""
			TO DO
			"""
			pass
		
		return dataToExport

	def checkContentExist(self, serverData, eachObject, itemList, sectionName, itemGet, noFail = True):
		checkContentExistClient = serverData[0]
		checkContentExistUserContext = serverData[1]
		checkContentExistServerInfo = serverData[2]
		checkContentExistServerInstance = serverData[3]

		itemListToReturn = []

		failRequirements = False
		self.CMUHandlerLogger.infoMessage('checkContentExist', 'Checking requirements for itemList %s. sectionName [%s]. itemGet [%s] on server: %s' % (
			itemList, sectionName, itemGet, checkContentExistServerInstance))

		for eachItemName in itemList:
			if "*" in eachItemName:
				itemList.remove(eachItemName)
				for eachFoundItem in self.findContentServerSection(eachItemName, sectionName, itemGet):
					itemList.append(eachFoundItem)


		checkContentExistClientDataBinder = checkContentExistClient.createBinder()

		checkContentExistDataBinder = checkContentExistClient.createBinder()
		checkContentExistDataBinder.putLocal("IdcService", "CMU_LIST_TASK_SECTION")
		checkContentExistDataBinder.putLocal("SectionID", sectionName)
		serverResponse = checkContentExistClient.sendRequest(checkContentExistUserContext, checkContentExistDataBinder)
		
		try:
			responseData = serverResponse.getResponseAsBinder()
		except ServiceException:
			self.CMUHandlerLogger.infoMessage('checkContentExist', 'Unable to find the following server section %s' % (sectionName))

		getItemList = [getItem.get(itemGet) for getItem in responseData.getResultSet('SectionItems').getRows()]

		for eachItemInList in itemList:
			if eachItemInList not in getItemList:
				if noFail:
					self.CMUHandlerLogger.infoMessage('checkContentExist',  "%s: Could not find %s in %s. Abort CMU operation." %
					(eachObject, eachItemInList, getItemList))
					failRequirements = True
			else:
				if not noFail:
					self.CMUHandlerLogger.infoMessage('checkContentExist',  "%s: Adding %s to template." % (eachObject, eachItemInList))
					itemListToReturn.append(eachItemInList)

		if failRequirements:
			System.exit(1)
		else:
			if noFail:
				self.CMUHandlerLogger.infoMessage('checkContentExist',  "All %s in JSON lists are found." % eachObject)

		if not noFail:
			return itemListToReturn

	def generateItemList(self, serverData, sectionName, itemGet):

		generateItemListClient = serverData[0]
		generateItemListUserContext = serverData[1]
		generateItemListInfo = serverData[2]
		generateItemListServerInstance = serverData[3]

		generateItemListDataBinder = generateItemListClient.createBinder()
		generateItemListDataBinder.putLocal("IdcService", "CMU_LIST_TASK_SECTION")
		generateItemListDataBinder.putLocal("SectionID", sectionName)
		generateItemListServerResponse = generateItemListClient.sendRequest(generateItemListUserContext, generateItemListDataBinder)
		generateItemListReturn = []
		
		try:
			responseData = generateItemListServerResponse.getResponseAsBinder()
			for eachCompName in responseData.getResultSet('SectionItems').getRows():
				generateItemListReturn.append(eachCompName.get(itemGet))
		except ServiceException, err:
			self.CMUHandlerLogger.infoMessage('checkPreReq', 'Unable to find the following server section %s [%s]' % (sectionName, err))

		return generateItemListReturn

	def returnCMUSectionAndItem(self, eachObjectType):

		CMUSectionDictionary = {
			"Components": ['name', 'components', 'noDeps'],
			"Content Metadata": ['dName', 'docmetadef', 'hasDeps'],
			"Content Types": ['dDocType', 'doctypes', 'noDeps'],
			"Content Formats": ['dFormat', 'docformats', 'hasDeps'],
			"File Extensions": ['dExtension', 'fileextensions', 'noDeps'],
			"User Metadata": ['umdName', 'usermetadef', 'noDeps'],
			"Aliases": ['dAlias', 'aliases', 'noDeps'],
			"Security Groups": ['dGroupName', 'securitygroups', 'noDeps'],
			"Roles": ['dRoleName', 'roles', 'hasDeps'],
			"Predefined Accounts": ['dDocAccount', 'predefinedaccounts', 'noDeps'],
			"Subscription Types": ['scpType', 'subscriptiontypes', 'noDeps'],
			"Schema Views": ['schViewName', 'schemaview', 'hasDeps'],
			"Schema Tables": ['schTableName', 'schematables', 'hasDeps'],
			"Schema Relations": ['schRelationName', 'schemarelations', 'hasDeps'],
			"Application Fields": ['schFieldName', 'applicationfields', 'noDeps'],
			"Workflows": ['dWfName', 'workflows', 'hasDeps'],
			"Workflow Templates": ['dWfTemplateName', 'workflowtemplates', 'hasDeps'],
			"Workflow Tokens": ['wfTokenName', 'workflowtokens', 'hasDeps'],
			"Workflow Scripts": ['wfScriptName', 'workflowscripts', 'hasDeps'],
			"Content Profiles": ['dpName', 'contentprofiles', 'hasDeps'],
			"Content Profile Rules": ['dpRuleName', 'contentprofilerules', 'hasDeps'],
			"Subscriptions": ['dSubscriptionAlias', 'subscriptions', 'hasDeps'],
			"Pages": ['PageName', 'pages', 'hasDeps'],
			"Archive Definitions": ['aArchiveName', 'archives', 'noDeps'],
			"Personalization Data": ['dName', 'pne', 'noDeps'],
			"Targeted Quick Searches": ['tqsKey', 'admintargetedquicksearches', 'noDeps'],
			"Advanced Search Design": ['asdFieldName', 'advsearchdesign', 'hasDeps'],
			"Server Config": ['name', 'config', 'noDeps'],
			"Simple Profiles": ['dpName', 'simpleprofiles', 'hasDeps']
		}
		
		try:
			return CMUSectionDictionary[eachObjectType]
		except KeyError:
			self.CMUHandlerLogger.infoMessage('returnCMUSectionAndItem', 'No such content type: %s. CMU Abort.' % eachObjectType)
			System.exit(1)

	def CMUCheckPrinter(self, mainDict, messageOne, messageTwo):

		if len(mainDict) != 0:
			self.CMUHandlerLogger.infoMessage('CMUCheckPrinter', 'Requirements failed - servers are different. Generating JSON...')
			self.CMUHandlerLogger.infoMessage('CMUCheckPrinter', messageOne)
			self.CMUHandlerLogger.infoMessage('CMUCheckPrinter', '=================================================================================') 
			for eachKey, eachValue in mainDict.iteritems():

				if len(eachValue) != 0:
					if self.returnCMUSectionAndItem(eachKey)[2] == "hasDeps":
						print '"%s": {\n\t"List": ["%s"],\n\t"Continue on error": ""\n},\n' % (eachKey, '", "'.join(eachValue))
					else:
						print '"%s": {\n\t"List": ["%s"],\n\t"Continue on error": "",\n\t"Add dependencies": ""\n},\n' % (eachKey, '", "'.join(eachValue))
			self.CMUHandlerLogger.infoMessage('CMUCheckPrinter', '=================================================================================')
		else:
			self.CMUHandlerLogger.infoMessage('CMUCheckPrinter', messageTwo)

	def CMUGetServerInfo(self):
		config_dictionary = {}
		services_to_parse = ['CONFIG_INFO', 'GET_SYSTEM_AUDIT_INFO']
		binders_count = 2

		for each_config_service in services_to_parse:
			self.sourceDataBinder = self.sourceClient.createBinder()
			self.sourceDataBinder.putLocal("IdcService", "%s" % each_config_service)
			serverResponse = self.sourceClient.sendRequest(self.sourceUserContext, self.sourceDataBinder)
			sourceResponseData = serverResponse.getResponseAsBinder()

			self.targetDataBinder = self.targetClient.createBinder()
			self.targetDataBinder.putLocal("IdcService", "%s" % each_config_service)
			serverResponse = self.targetClient.sendRequest(self.targetUserContext, self.targetDataBinder)
			targetResponseData = serverResponse.getResponseAsBinder()
						
			for server_index, each_binder_result in enumerate([sourceResponseData, targetResponseData]):
				if each_config_service == 'CONFIG_INFO':
					config_dictionary['SERVER_%s_%s_OUTPUT' % (server_index, each_config_service)] = {}

					config_dictionary['SERVER_%s_%s_OUTPUT' % (server_index, each_config_service)]['JavaProperties_values'] = {}
					config_dictionary['SERVER_%s_%s_OUTPUT' % (server_index, each_config_service)]['Features_values'] = {}
					config_dictionary['SERVER_%s_%s_OUTPUT' % (server_index, each_config_service)]['EnabledComponents_values'] = {}
					idc_version = each_binder_result.getLocal('ProductVersion')

					for result_set_value in each_binder_result.getResultSet('JavaProperties').getRows():
						config_dictionary['SERVER_%s_%s_OUTPUT' % (server_index, each_config_service)]['JavaProperties_values'][result_set_value.get('name')] = result_set_value.get('value')

					for result_set_value in each_binder_result.getResultSet('EnabledComponents').getRows():
						config_dictionary['SERVER_%s_%s_OUTPUT' % (server_index, each_config_service)]['EnabledComponents_values'][result_set_value.get('name')] = result_set_value.get('version')

					for result_set_value in each_binder_result.getResultSet('Features').getRows():
						config_dictionary['SERVER_%s_%s_OUTPUT' % (server_index, each_config_service)]['Features_values'][result_set_value.get('idcFeatureName')] = result_set_value.get('idcFeatureVersion')

				elif each_config_service == 'GET_SYSTEM_AUDIT_INFO':
					config_dictionary['SERVER_%s_%s_OUTPUT' % (server_index, each_config_service)] = {}
					config_dictionary['SERVER_%s_%s_OUTPUT' % (server_index, each_config_service)]['EnvironmentKeyEvents'] = {}

					for result_set_value in each_binder_result.getResultSet('EnvironmentKeyEvents').getRows():
						config_dictionary['SERVER_%s_%s_OUTPUT' % (server_index, each_config_service)]['EnvironmentKeyEvents'][result_set_value.get('KeyName')] = result_set_value.get('CurrentValue')
				else:
					self.CMUHandlerLogger.infoMessage('CMUGetServerInfo', 'Unable to parse service [%s]: ' % each_config_service)
					System.exit(1)

		for each_config_service in services_to_parse:
			self.CMUHandlerLogger.infoMessage('CMUGetServerInfo', 'Parsing service result: %s' % each_config_service)
			for server_index in range(binders_count):
				service_output_keys = config_dictionary['SERVER_%s_%s_OUTPUT' % (server_index, each_config_service)].keys()
				for each_service_output_key in service_output_keys:
					each_server_output_key_keys = config_dictionary['SERVER_%s_%s_OUTPUT' % (server_index, each_config_service)][each_service_output_key].keys()
					for damn in each_server_output_key_keys:
						try:
							if config_dictionary['SERVER_%s_%s_OUTPUT' % (server_index, each_config_service)][each_service_output_key][damn] == config_dictionary['SERVER_%s_%s_OUTPUT' % ('1', each_config_service)][each_service_output_key][damn]:
								pass
							else:
								self.CMUHandlerLogger.infoMessage('CMUGetServerInfo', '[%s] %s: %s and %s dont match' % (each_service_output_key, damn, config_dictionary['SERVER_%s_%s_OUTPUT' % (server_index, each_config_service)][each_service_output_key][damn],
									config_dictionary['SERVER_%s_%s_OUTPUT' % ('1', each_config_service)][each_service_output_key][damn]))
						except KeyError:
							self.CMUHandlerLogger.infoMessage('CMUGetServerInfo', '[%s] Unable to find key %s in SERVER_1(target)' % (each_service_output_key, damn))

	def main(self, jobName):
		self.bundleName = jobName
		self.sourceCMUData = {}
		self.targetCMUData = {}
		self.sourceInstanceName = CMUConfigParser(self.pathToJSON).returnObject("sourceServer", "instance")
		self.targetInstanceName = CMUConfigParser(self.pathToJSON).returnObject("targetServer", "instance")

		self.sourceServerData = []
		self.sourceServerData.append(self.sourceClient)
		self.sourceServerData.append(self.sourceUserContext)
		self.sourceServerData.append(self.sourceServerInfo)
		self.sourceServerData.append(self.sourceInstanceName)

		self.targetServerData = []
		self.targetServerData.append(self.targetClient)
		self.targetServerData.append(self.targetUserContext)
		self.targetServerData.append(self.targetServerInfo)
		self.targetServerData.append(self.targetInstanceName)

		doCMUCheck = CMUConfigParser(self.pathToJSON).returnObject("CMUOperations", "doCMUCheck")
		doCMUClone = CMUConfigParser(self.pathToJSON).returnObject("CMUOperations", "doCMUClone")
		doCMUBackup = CMUConfigParser(self.pathToJSON).returnObject("CMUOperations", "doCMUBackup")

		listOfOBjectTypes = ["Content Types", "Components", "Content Metadata", "Content Formats", "File Extensions",
							 "User Metadata", "Aliases", "Security Groups", "Roles", "Predefined Accounts", 
							 "Schema Views", "Schema Tables", "Schema Relations", "Application Fields", "Workflows", 
							 "Workflow Templates", "Workflow Tokens", "Workflow Scripts", "Content Profiles", "Content Profile Rules",
							  "Pages", "Archive Definitions", "Targeted Quick Searches", "Subscription Types"]

		listOfOBjectTypesToSkip = ["Personalization Data", "Simple Profiles", "Subscriptions", "Advanced Search Design", "Server Config"]

		protectedCMUData = {
							"Content Metadata": ["xIdcProfile"],
							"User Metadata": ["uSupplementalMarkings"], ##Use RMA to migrate 
							"Schema Tables": ["RelatedTypes", "CpdLinks", "CpdArchivedLinks", "FolderFiles", "WebdavLock"] ##Table definiation is out of date
						}

		if doCMUCheck == "1":
			self.CMUGetServerInfo()
			
			sourcePathToSysComps = CMUConfigParser(self.pathToJSON).returnObject("sourceServer", "pathToSysComps")
			targetPathToSysComps = CMUConfigParser(self.pathToJSON).returnObject("targetServer", "pathToSysComps")
			
			self.CMUHandlerLogger.infoMessage('main', 'Checking pre-requirements...')
			for eachObjectType in listOfOBjectTypes:
				if not eachObjectType in listOfOBjectTypesToSkip:
					itemGet = self.returnCMUSectionAndItem(eachObjectType)[0]
					sectionName = self.returnCMUSectionAndItem(eachObjectType)[1]  
					self.checkPreReq(sourcePathToSysComps, targetPathToSysComps, eachObjectType, sectionName, itemGet)
					
			existsOnSourceButNotOnTarget = {}
			existsOnTargetButNotOnSource = {}
			existsOnSourceAndOnTarget = {}
			
			for eachObjectType in listOfOBjectTypes:
				if not eachObjectType in listOfOBjectTypesToSkip:
					
					existsOnSourceOnly = []
					existsOnTargetOnly = []
					existsEverywhere = []

					for eachKey in self.sourceCMUData[eachObjectType]:
						if eachKey in self.targetCMUData[eachObjectType]:
							existsEverywhere.append(eachKey)
						else:
							existsOnSourceOnly.append(eachKey)

					existsOnSourceButNotOnTarget[eachObjectType] = existsOnSourceOnly
					existsOnSourceAndOnTarget[eachObjectType] = existsEverywhere

					for eachKey in self.targetCMUData[eachObjectType]:
						if not eachKey in self.sourceCMUData[eachObjectType]:
							existsOnTargetOnly.append(eachKey)

					existsOnTargetButNotOnSource[eachObjectType] = existsOnTargetOnly

			self.CMUCheckPrinter(existsOnSourceButNotOnTarget, 'The following CMU data is missing on target server (%s): ' % self.targetServerInfo, 'All CMU Content on SOURCE exists on TARGET')
			self.CMUCheckPrinter(existsOnTargetButNotOnSource, 'The following CMU data is missing on source server (%s): ' % self.sourceServerInfo, 'All CMU Content on SOURCE exists on TARGET')
			self.CMUCheckPrinter(existsOnSourceAndOnTarget, 'The following CMU data exists on both servers', 'Was not able to find any similiar CMU data. Both servers are different')
			System.exit(1)

		templateIsContinueOnError = CMUConfigParser(self.pathToJSON).returnObject("CMUOperations", "Template settings", "Continue on error")
		templateAddDependencies = CMUConfigParser(self.pathToJSON).returnObject("CMUOperations", "Template settings", "Add dependencies")

		if templateIsContinueOnError != "1":
			templateIsContinueOnError = ""

		if templateAddDependencies != "1":
			templateAddDependencies = ""
			templateIgnoreDependencies = "1"
		else:
			templateAddDependencies = "1"
			templateIgnoreDependencies = ""

		if doCMUBackup == "1":
			self.CMUHandlerLogger.infoMessage('main', 'Making a full backup of CMU data on target server...')
			self.createBackupTemplate(templateIsContinueOnError, templateAddDependencies, templateIgnoreDependencies, CMUBackup= True)

			for eachObjectType in listOfOBjectTypes:
				itemGet = self.returnCMUSectionAndItem(eachObjectType)[0]
				sectionName = self.returnCMUSectionAndItem(eachObjectType)[1]
				methodType = self.returnCMUSectionAndItem(eachObjectType)[2]

				if methodType == "hasDeps":
					self.backupFunctionWithDeps("", sectionName, eachObjectType, templateIsContinueOnError, templateAddDependencies, templateIgnoreDependencies, CMUClone = True)
				else:
					self.backupFunctionWithoutDeps("", sectionName, eachObjectType, templateIsContinueOnError, CMUClone = True)

			self.CMUHandlerLogger.infoMessage('main', 'Full backup: Exporting backup template...')
			self.exportBackupTemplate(templateIsContinueOnError, templateAddDependencies, templateIgnoreDependencies)
			self.CMUHandlerLogger.infoMessage('main', 'Full backup is done. Exit.')
			System.exit(1)
		
		if doCMUClone == "1":
			
			self.CMUHandlerLogger.infoMessage('main', 'Cloning source to target...')
			self.CMUHandlerLogger.infoMessage('main', 'Clone: Backing up existing CMU data on target server...')
			
			self.createBackupTemplate(templateIsContinueOnError, templateAddDependencies, templateIgnoreDependencies, CMUClone = True)

			for eachObjectType in listOfOBjectTypes:
				itemGet = self.returnCMUSectionAndItem(eachObjectType)[0]
				sectionName = self.returnCMUSectionAndItem(eachObjectType)[1]
				methodType = self.returnCMUSectionAndItem(eachObjectType)[2]

				if methodType == "hasDeps":
					self.backupFunctionWithDeps("", sectionName, eachObjectType, templateIsContinueOnError, templateAddDependencies, templateIgnoreDependencies, CMUClone = True)
				else:
					self.backupFunctionWithoutDeps("", sectionName, eachObjectType, templateIsContinueOnError, CMUClone = True)

			self.CMUHandlerLogger.infoMessage('main', 'Clone: Exporting backup template...')
			self.exportBackupTemplate(templateIsContinueOnError, templateAddDependencies, templateIgnoreDependencies)

			self.CMUHandlerLogger.infoMessage('main', 'Clone: Backup is completed. Creating template on source server')
			self.createTemplate('clone_%s' % self.bundleName, templateIsContinueOnError, templateAddDependencies, templateIgnoreDependencies)

			self.CMUHandlerLogger.infoMessage('main', 'Clone: adding all source CMU data to template...')

			for eachObjectType in listOfOBjectTypes:
				itemGet = self.returnCMUSectionAndItem(eachObjectType)[0]
				sectionName = self.returnCMUSectionAndItem(eachObjectType)[1]
				methodType = self.returnCMUSectionAndItem(eachObjectType)[2]

				if eachObjectType in protectedCMUData.keys():

					generatedList = self.generateItemList(self.sourceServerData, sectionName, itemGet)

					for eachProtectedCMUData in protectedCMUData[eachObjectType]:
						generatedList.remove(eachProtectedCMUData)	

					if methodType == "hasDeps":
						self.functionWithDeps(','.join(generatedList), sectionName, eachObjectType, templateIsContinueOnError, templateAddDependencies, templateIgnoreDependencies)
					else:
						self.functionWithoutDeps(','.join(generatedList), sectionName, eachObjectType, templateIsContinueOnError)

				else:
					if methodType == "hasDeps":
						self.functionWithDeps("", sectionName, eachObjectType, templateIsContinueOnError, templateAddDependencies, templateIgnoreDependencies, CMUClone = True)
					else:
						self.functionWithoutDeps("", sectionName, eachObjectType, templateIsContinueOnError, CMUClone = True)

			self.CMUHandlerLogger.infoMessage('main', 'All content is added. Exporting clone template....')
			self.exportTemplate(templateIsContinueOnError, templateAddDependencies, templateIgnoreDependencies)

			System.exit(1)
			
			self.CMUHandlerLogger.infoMessage('main', 'Downloading clone template....')
			self.downloanBundle('clone_%s' % self.bundleName)



			self.CMUHandlerLogger.infoMessage('main', 'Transfering clone template....')
			self.transferBundle('clone_%s' % self.bundleName)

			self.CMUHandlerLogger.infoMessage('main', 'Importing clone template....')
			self.importBundle('clone_%s' % self.bundleName, templateIsContinueOnError, templateAddDependencies, templateIgnoreDependencies)
			
			self.CMUHandlerLogger.infoMessage('main', 'Starting to clone tables...')
			sourceServerTables = GeneralOperations(self.pathToJSON).returnTableList(self.sourceServerData)
			targetServerTables = GeneralOperations(self.pathToJSON).returnTableList(self.targetServerData)

			for eachSourceTable in sourceServerTables:
				if eachSourceTable not in targetServerTables:
					self.CMUHandlerLogger.infoMessage('main', 'Unable to migrate table: %s - table does not exist in Target Table list' % eachSourceTable)
					sourceServerTables.remove(eachSourceTable)

			skipCloneTables = ["Users", "FrameworkFoldersHistory", "FolderFiles", "ExtendedConfigProperties", "FolderMigrationUndo", "OriginatingOrg", "TaskLock"
			"WebdavLock", "FolderMetaDefaults", "RecordFormatList", "CpdLinks", "FolderMigrationExcludeIds", "CpdArchivedLinks", "CpdBasketLinks",
			"WebdavLockAssociation", "MediaTypeList", "FileCache", "FolderMigrationLegacyMappings", "FileStorage", "CpdChangeHistory", "LastTrashHistory",
			"ZRMJobs", "FolderMigrationStatus", "DocFormats", "FrameworkFoldersHistory", "QFL_Retention", "AuditPeriodList"] 
			
			for eachSkipCloneTable in sourceServerTables:
				if eachSkipCloneTable in skipCloneTables:
					self.CMUHandlerLogger.infoMessage('main', 'Removing table %s from Table List' % eachSkipCloneTable)
					sourceServerTables.remove(eachSkipCloneTable)

			ArchiverHandler(self.pathToJSON).main('clone_%s' % self.bundleName, CMUClone = True, cloneTableList = sourceServerTables, CMUsourceServerData = self.sourceServerData, CMUtargetServerData = self.targetServerData)

			self.CMUHandlerLogger.infoMessage('main', 'Clone opearation is done. Exit.')
			System.exit(1)

		#====================================================================================================================================#
		#====================================================================================================================================#
		#====================================================================================================================================#

		self.CMUHandlerLogger.infoMessage('main', 'Checking if all defined content in JSON exist on source server')

		for eachObjectType in listOfOBjectTypes:
			itemList = CMUConfigParser(self.pathToJSON).returnObject("CMUOperations", eachObjectType, "List", noSkip = False)
			if itemList:
				self.CMUHandlerLogger.infoMessage('main', ' > Working with object type: %s <' % eachObjectType)
				if len(itemList) == 0:
					self.CMUHandlerLogger.infoMessage('main', 'List of object type [%s] is empty. Check JSON file.' % eachObjectType)
				else:
					itemGet = self.returnCMUSectionAndItem(eachObjectType)[0]
					sectionName = self.returnCMUSectionAndItem(eachObjectType)[1]
					itemList = list(itemList)
					self.checkContentExist(self.sourceServerData, eachObjectType, itemList, sectionName, itemGet)

		self.CMUHandlerLogger.infoMessage('main', 'All content is found.')
		self.CMUHandlerLogger.infoMessage('main', 'Backing up old CMU content on target server')
		self.createBackupTemplate(templateIsContinueOnError, templateAddDependencies, templateIgnoreDependencies)

		for eachObjectType in listOfOBjectTypes:
			itemList = CMUConfigParser(self.pathToJSON).returnObject("CMUOperations", eachObjectType, "List", noSkip = False)
			if itemList:
				if len(itemList) == 0:
					self.CMUHandlerLogger.infoMessage('main', 'List of object type [%s] is empty. Check JSON file.' % eachObjectType)
				else:
					itemList = list(itemList)
		
					itemGet = self.returnCMUSectionAndItem(eachObjectType)[0]
					sectionName = self.returnCMUSectionAndItem(eachObjectType)[1]
					methodType = self.returnCMUSectionAndItem(eachObjectType)[2]

					for eachItemName in itemList:
						if "*" in eachItemName:
							itemList.remove(eachItemName)
							for eachFoundItem in self.findContentServerSection(eachItemName, sectionName, itemGet):
								itemList.append(eachFoundItem)

					fixedList = self.checkContentExist(self.targetServerData, eachObjectType, itemList, sectionName, itemGet, noFail = False)
					listIsContinueOnError = CMUConfigParser(self.pathToJSON).returnObject("CMUOperations", eachObjectType, "Continue on error")

					if len(fixedList) > 0:

						if methodType == "hasDeps":
							addDependencies = CMUConfigParser(self.pathToJSON).returnObject("CMUOperations", eachObjectType, "Add dependencies")

							if listIsContinueOnError != "1":
								listIsContinueOnError = ""

							if addDependencies != "1":
								addDependencies = ""
								ignoreDependencies = "1"
							else:
								ignoreDependencies = ""

							callMethod = "self.backupFunctionWithDeps(','.join(fixedList), '%s', '%s', '%s', '%s', '%s')" % (
								sectionName, eachObjectType, listIsContinueOnError, addDependencies, ignoreDependencies)

						else:
							if listIsContinueOnError != "1":
								listIsContinueOnError = ""

							callMethod = "self.backupFunctionWithoutDeps(','.join(fixedList), '%s', '%s', '%s')" % (
								sectionName, eachObjectType, listIsContinueOnError)

						self.CMUHandlerLogger.infoMessage('main', 'Executing: %s' % callMethod)
						
						exec callMethod

					else:
						self.CMUHandlerLogger.infoMessage('main', 'fixedList is empty - nothing to add to template')

		self.CMUHandlerLogger.infoMessage('main', 'Exporting backup template...')
		self.exportBackupTemplate(templateIsContinueOnError, templateAddDependencies, templateIgnoreDependencies)

		self.CMUHandlerLogger.infoMessage('main', 'Reading template settings and creating exporte template...')
		self.createTemplate(self.bundleName, templateIsContinueOnError, templateAddDependencies, templateIgnoreDependencies)

		for eachObjectType in listOfOBjectTypes:
			itemList = CMUConfigParser(self.pathToJSON).returnObject("CMUOperations", eachObjectType, "List", noSkip = False)
			if itemList:
				self.CMUHandlerLogger.infoMessage('main', ' > Working with object type: %s <' % eachObjectType)
				if len(itemList) == 0:
					self.CMUHandlerLogger.infoMessage('main', 'List of object type [%s] is empty. Check JSON file.' % eachObjectType)
				else:
					itemList = list(itemList)
		
					itemGet = self.returnCMUSectionAndItem(eachObjectType)[0]
					sectionName = self.returnCMUSectionAndItem(eachObjectType)[1]
					methodType = self.returnCMUSectionAndItem(eachObjectType)[2]

					for eachItemName in itemList:
						if "*" in eachItemName:
							itemList.remove(eachItemName)
							for eachFoundItem in self.findContentServerSection(eachItemName, sectionName, itemGet):
								itemList.append(eachFoundItem)

					isContinueOnError = CMUConfigParser(self.pathToJSON).returnObject("CMUOperations", eachObjectType, "Continue on error")

					if methodType == "hasDeps":

						addDependencies = CMUConfigParser(self.pathToJSON).returnObject("CMUOperations", eachObjectType, "Add dependencies")

						if isContinueOnError != "1":
							isContinueOnError = ""
						if addDependencies != "1":
							addDependencies = ""
							ignoreDependencies = "1"
						else:
							ignoreDependencies = ""

						callMethod = "self.functionWithDeps(','.join(itemList), '%s', '%s', '%s', '%s', '%s')" % (
							sectionName, eachObjectType, isContinueOnError, addDependencies, ignoreDependencies)
					else:
						if isContinueOnError != "1":
							isContinueOnError = ""

						callMethod = "self.functionWithoutDeps(','.join(itemList), '%s', '%s', '%s')" % (
							sectionName, eachObjectType, isContinueOnError)

					self.CMUHandlerLogger.infoMessage('main', 'Executing: %s' % callMethod)
				
					exec callMethod

		self.CMUHandlerLogger.infoMessage('main', 'Exporting template...')
		self.exportTemplate(templateIsContinueOnError, templateAddDependencies, templateIgnoreDependencies)
		
		self.CMUHandlerLogger.infoMessage('main', 'Downloading bundle...')
		self.downloanBundle(self.bundleName)

		self.CMUHandlerLogger.infoMessage('main', 'Transfering bundle...')
		self.transferBundle(self.bundleName)
		
		self.CMUHandlerLogger.infoMessage('main', 'Starting import bundle process...')
		self.importBundle(self.bundleName, templateIsContinueOnError, templateAddDependencies, templateIgnoreDependencies)