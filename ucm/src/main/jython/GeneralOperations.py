# -*- coding: utf-8 -*-
# coding=utf-8
'''
Created on 09.10.2014
@author: p998sqb
'''

#local classes
from CMULogger import log4j
from CMUConfigParser import CMUConfigParser
from CMUSetupConnection import SetupUCMConnection
#from com.google.common.difflib import *

#Java libs
from java.lang import System
from java.io import File 
from java.util import Scanner
from oracle.stellent.ridc.protocol import ServiceException
import java.io.FileOutputStream as FileOutputStream
import java.io.FileInputStream as FileInputStream
import java.nio.channels.FileChannel as FileChannel

#python libs
import time
import re
import os


class GeneralOperations(SetupUCMConnection):
	
	GeneralHandlerLogger = log4j("GeneralOperations")
	
	def __init__(self, pathToJSON):
		self.pathToJSON = pathToJSON
	
		try:
			print "================================"
			sourceServerData = SetupUCMConnection(self.pathToJSON, 'sourceServer')
			self.sourceClient = sourceServerData.outData[0]
			self.sourceUserContext = sourceServerData.outData[1]
			self.sourceServerInfo = sourceServerData.outData[2]
		except Exception, err:
			self.GeneralHandlerLogger.infoMessage('__init__', 'Unable to get information about source server: %s' % err)
			System.exit(1)
		
		try:
			targetServerData = SetupUCMConnection(self.pathToJSON, 'targetServer')
			targetClient = targetServerData.outData[0]
			targetUserContext = targetServerData.outData[1]
			targetServerInfo = targetServerData.outData[2]
		except Exception, err:
			self.GeneralHandlerLogger.infoMessage('__init__', 'Unable to get information about target server: %s' % err)
			System.exit(1)
			
	def checkAssetExists(self, WebAssetList, serverData, noSkip = True):
		if noSkip:
			self.GeneralHandlerLogger.infoMessage('checkAssetExists', 'Starting checkAssetExists method with params: [WebAssetList: %s] [noSkip: %s]' % (WebAssetList, noSkip))
		
		safeItemList = []

		checkClient = serverData[0]
		checkUserContext = serverData[1]
		checkServerInfo = serverData[2]
		checkServerInstance = serverData[3]

		for eachWebAsset in WebAssetList.split(','):
			if "|" in eachWebAsset:
				webAssetName = eachWebAsset.split('|')[0]
				webAssetRevision = eachWebAsset.split('|')[1]

				try:
					checkDataBinder = checkClient.createBinder()
					checkDataBinder.putLocal('IdcService', 'DOC_INFO_SIMPLE_BYREV')
					checkDataBinder.putLocal('dDocName', webAssetName)
					checkDataBinder.putLocal('dRevLabel', webAssetRevision)

					serverResponse = checkClient.sendRequest(checkUserContext, checkDataBinder)
					responseData = serverResponse.getResponseAsBinder()

					for eachDocRow in responseData.getResultSet("DOC_INFO").getRows():
						if eachDocRow.get('dDocName'):
							safeItemList.append('%s|%s' % (webAssetName, webAssetRevision))

				except ServiceException, err:
					if noSkip:
						self.GeneralHandlerLogger.infoMessage('checkAssetExists', 'Unable to get information about document %s with revision %s. Check document name spelling. Error: [%s]' % (webAssetName, webAssetRevision, err))
				except Exception, err:
					self.GeneralHandlerLogger.infoMessage('checkAssetExists', 'Unable to get information about document %s. Error: [%s]' % (webAssetName, err))
					System.exit(1)
				else:
					self.GeneralHandlerLogger.infoMessage('checkAssetExists', 'Found %s. With revision %s.' % (webAssetName, webAssetRevision))
			else:
				webAssetName = eachWebAsset

				try:
					checkDataBinder = checkClient.createBinder()
					checkDataBinder.putLocal('IdcService', 'DOC_INFO_BY_NAME')
					checkDataBinder.putLocal('dDocName', webAssetName)
					checkDataBinder.putLocal('RevisionSelectionMethod', 'Latest')
					serverResponse = checkClient.sendRequest(checkUserContext, checkDataBinder)
					responseData = serverResponse.getResponseAsBinder()

					for eachDocRow in responseData.getResultSet("DOC_INFO").getRows():
						if eachDocRow.get('dRevisionID'):
							webAssetRevision = eachDocRow.get('dRevisionID')
							safeItemList.append('%s|%s' % (webAssetName, webAssetRevision))

				except ServiceException, err:
					if noSkip:
						self.GeneralHandlerLogger.infoMessage('checkAssetExists', 'Unable to get information about document %s. Check document name spelling. Error: [%s]' % (webAssetName, err))
				except Exception, err:
					self.GeneralHandlerLogger.infoMessage('checkAssetExists', 'Unable to get information about document %s. Error: [%s]' % (webAssetName, err))
					System.exit(1)

		return safeItemList
	
	def checkTableExists(self, tableList, serverData, noSkip = True):
		if noSkip:
			self.GeneralHandlerLogger.infoMessage('checkTableExists', 'Starting checkTableExists method with params: [tableList: %s]' % tableList)

		safeTableList = []

		checkClient = serverData[0]
		checkUserContext = serverData[1]
		checkServerInfo = serverData[2]
		checkServerInstance = serverData[3]

		for eachTableName in tableList.split(','):
			if noSkip:
				self.GeneralHandlerLogger.infoMessage('checkTableExists', 'Checking table: %s' % eachTableName)
			try:
				checkDataBinder = checkClient.createBinder()
				checkDataBinder.putLocal('IdcService', 'GET_TABLE')
				checkDataBinder.putLocal('tableName', eachTableName)
				serverResponse = checkClient.sendRequest(checkUserContext, checkDataBinder)
				responseData = serverResponse.getResponseAsBinder()
			except ServiceException, err:
				if noSkip:
					self.GeneralHandlerLogger.infoMessage('checkTableExists', 'Unable to find table: %s. Check table name' % eachTableName)
			else:
				if noSkip:
					self.GeneralHandlerLogger.infoMessage('checkTableExists', 'Found table: %s. Adding table to safe list' % eachTableName)
				safeTableList.append(eachTableName)

		if len(safeTableList) == 0:
			self.GeneralHandlerLogger.infoMessage('checkTableExists', 'None of table in the list exist.')
		
		return safeTableList

	def returnTableList(self, serverData):

		tableListClient = serverData[0]
		tableListContext = serverData[1]
		tableListInfo = serverData[2]
		tableListInstance = serverData[3]

		fullTableList = []

		try:
			tableListClientBinder = tableListClient.createBinder()
			tableListClientBinder.putLocal('IdcService', 'GET_SCHEMA_TABLES')
			tableListServerResponse = tableListClient.sendRequest(tableListContext, tableListClientBinder)
			tableListResponseData = tableListServerResponse.getResponseAsBinder()
		except ServiceException, err:
			self.GeneralHandlerLogger.infoMessage('returnTableList', 'Unable to find table: %s. Check table name' % eachTableName)
		else:
			for eachResultSet in tableListResponseData.getResultSet('SchemaConfigData').getRows():
				fullTableList.append(eachResultSet.get('schObjectName'))

		return fullTableList

	def outputExternalHttpList(self):

		mainDataBinder = self.sourceClient.createBinder()
		mainDataBinder.putLocal('IdcService', 'SS_GET_SITE_REPORT')
		mainDataBinder.putLocal('siteId', 'kanal1')
		mainDataBinder.putLocal('sitesList', '7')
		serverResponse = self.sourceClient.sendRequest(self.sourceUserContext, mainDataBinder)
		responseData = serverResponse.getResponseAsBinder()

		webPathList = []
		for serverComp in responseData.getResultSet("SiteHierarchy").getRows():
			webPathList.append(serverComp.get("namePath"))
			print serverComp.get("namePath")

		System.exit(1)


		websiteItemList = []
		for serverComp in responseData.getResultSet("WebsiteDocs").getRows():
			websiteItemList.append(serverComp.get("dDocName").encode('ascii', 'ignore'))

		externalHttpList = {}
		for serverComp in responseData.getResultSet("NodeInfo").getRows():
			if 'http' in serverComp.get("primaryUrl"):
				externalHttpList[serverComp.get("primaryUrl")] = serverComp.get("nodeId").encode('ascii', 'ignore')

		for key, value in externalHttpList.items():
			for serverComp in responseData.getResultSet("SiteHierarchy").getRows():
				if serverComp.get("nodeId") == value:
					externalHttpList[key] = 'http://www.swedbank.com/%s' % serverComp.get("namePath")
					break

		for key, value in externalHttpList.items():
			print "%s -> %s" % (value, key)

		for eachWebFile in websiteItemList:
			
			mainDataBinder = self.sourceClient.createBinder()
			mainDataBinder.putLocal('IdcService', 'DOC_INFO_BY_NAME')
			mainDataBinder.putLocal('dDocName', eachWebFile)
			serverResponse = self.sourceClient.sendRequest(self.sourceUserContext, mainDataBinder)
			responseData = serverResponse.getResponseAsBinder()

			for serverComp in responseData.getResultSet("DOC_INFO").getRows():
				fileExtension = serverComp.get("dExtension").lower()
				fileObjectType = serverComp.get("xWebsiteObjectType").lower()
				
				if fileExtension == "xml" or fileExtension == "hcsp":
					if fileObjectType != "native document":

						fileGroup = serverComp.get("dSecurityGroup").lower()
						fileObjectType = "documents"
						fileDocType = serverComp.get("dDocType").lower()
						fileName = serverComp.get("dDocName").lower()

						if len((serverComp.get("dDocAccount").lower()).split('/')) > 1:
							fileAccount = '@' + '/@'.join((serverComp.get("dDocAccount").lower()).split('/'))
							filePath = "/sb/sys/ucm/shared/contrib/weblayout/groups/%s/%s/%s/%s/%s.%s" % (
								fileGroup, fileAccount, fileObjectType, fileDocType, fileName, fileExtension)
						else:
							filePath = "/sb/sys/ucm/shared/contrib/weblayout/groups/%s/%s/%s/%s.%s" % (
								fileGroup, fileObjectType, fileDocType, fileName, fileExtension)

						if not File(filePath).exists():
							print '============> DOES NOT EXIST: ', filePath
						else:

							openFile = open(filePath, 'r')
							iframeURLS = []

							for eachLine in openFile:	
								if 'iframe' in eachLine:
									#dataFileContent = open(filePath, 'r').read().encode('ascii', 'ignore')
									#iframeRegex = re.compile(r'src=(.*?)>\|^', re.IGNORECASE)
									

									#for eachFoundRegex in re.findall(iframeRegex, dataFileContent):
									iframeURLS.append(eachLine)

									if len(iframeURLS) > 0:
										print 'Found IFRAMES in file %s: ' % eachWebFile
										print iframeURLS
									
								#if 'http' in eachLine:
								#	dataFileContent = open(filePath, 'r').read().encode('ascii', 'ignore')
								#	iframeRegex = re.compile(r'http://(.+?)(?=(\"|<))', re.IGNORECASE)
								#	for eachFoundRegex in re.findall(iframeRegex, dataFileContent):
								#		if eachFoundRegex[0] not in ["www.stellent.com", "www.w3.org", "www.oracle.com"]:
								#				print "%s: HTTP link -> %s" % (fileName, eachFoundRegex[0])

	def projectFileCompare(self):
		while True:
			mainDataBinder = self.sourceClient.createBinder()
			mainDataBinder.putLocal('IdcService', 'GET_SEARCH_RESULTS')
			mainDataBinder.putLocal('QueryText', 'xWebsiteObjectType <matches> `Project` <AND> xxArchived <matches> `0`')
			mainDataBinder.putLocal('ResultCount', '1000')

			serverResponse = self.sourceClient.sendRequest(self.sourceUserContext, mainDataBinder)
			responseData = serverResponse.getResponseAsBinder()

			try: 
				projectDictionary.values()
			except NameError:
				projectDictionary = {}
				for serverComp in responseData.getResultSet('SearchResults').getRows():
					dDocName = serverComp.get('dDocName')
					dRevLabel = serverComp.get('dRevLabel')
					dID = serverComp.get('dID')

					projectDictionary[dDocName] = [dRevLabel, dID]
			else:
				for serverComp in responseData.getResultSet('SearchResults').getRows():
					filePath = '/sb/sys/ucm/shared/contrib/weblayout%s' % (serverComp.get('URL').replace('/idc', ''))
					dDocName = serverComp.get('dDocName')
					dRevLabel = serverComp.get('dRevLabel')
					dID = serverComp.get('dID')

					for siteid, revision in projectDictionary.iteritems():
						if siteid == dDocName:
							if dRevLabel != revision[0]:
								print 'Site %s was changed. Old revision was - %s[%s], new revision - %s[%s]' % (siteid, revision[0], revision[1], dRevLabel, dID)
								projectFilePaths = []
								for projectFile in [[siteid, revision[1]], [dDocName, dID]]:
									mainDataBinder = self.sourceClient.createBinder()
									mainDataBinder.putLocal('IdcService', 'DOC_INFO')
									mainDataBinder.putLocal('dDocName', projectFile[0])
									mainDataBinder.putLocal('dID', projectFile[1])

									serverResponse = self.sourceClient.sendRequest(self.sourceUserContext, mainDataBinder)
									responseData = serverResponse.getResponseAsBinder()
									projectFilePaths.append('/sb/sys/ucm/shared/contrib/weblayout%s' % responseData.getLocalData().get('DocUrl').replace('http://wcm.swedbank.net/idc', ''))

								os.system("diff -c %s %s" % (projectFilePaths[0], projectFilePaths[1]))

							continue

					"""
					inputChannel  = None
					outputChannel = None

					sourceFilePath = filePath
					destinationFilePath = "/export/home/p998sqb/projectfiles/%s/%s_%s.xml" % (dDocName, dDocName, dRevLabel)

					try:
						inputChannel = FileInputStream(sourceFilePath).getChannel()
						outputChannel = FileOutputStream(destinationFilePath).getChannel()
						outputChannel.transferFrom(inputChannel, 0, inputChannel.size())
					except Exception, ex:
						print "Unable to copy file: %s" % filePath
						print ex
						System.exit(1)
					finally:
						inputChannel.close()
						outputChannel.close()
					"""

		time.sleep(60)

	def main(self):
		print 'No service'
		#self.outputExternalHttpList()