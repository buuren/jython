#Python libs:
import time, datetime

#from sys import exit
#local classes
from CMULogger import log4j
from CMUConfigParser import CMUConfigParser
from CMUSetupConnection import SetupUCMConnection
from GeneralOperations import GeneralOperations

from oracle.stellent.ridc.protocol import ServiceException
from oracle.stellent.ridc.model.impl import DataResultSetImpl
from oracle.stellent.ridc.model import DataResultSet

#Java libs
from java.text import MessageFormat
from java.lang import System
from java.util import Arrays

def get_methods(input_text):
	for each_method in dir(input_text):
		print each_method
	System.exit(1)


class ArchiverHandler(SetupUCMConnection):
	ArchiverHandlerLogger = log4j("ArchiverHandler")

	"""
	How to create provider:

	1) Source server - outgoing provider
	2) Destionation server: make sure SystemSocket is enabled (port 4444)
	
	"""

	def __init__(self, pathToJSON):
		self.pathToJSON = pathToJSON
		self.ArchiverHandlerLogger.infoMessage('__init__', 'Starting archiver handler...')

		try:
			setupSourceServerData = SetupUCMConnection(self.pathToJSON, 'sourceServer')
			self.sourceClient = setupSourceServerData.outData[0]
			self.sourceUserContext = setupSourceServerData.outData[1]
			self.sourceServerInfo = setupSourceServerData.outData[2]
		except Exception, err:
			self.ArchiverHandlerLogger.infoMessage('__init__', 'Unable to get information about source server: %s' % err)
			System.exit(1) 
		
		try:
			setupTargetServerData = SetupUCMConnection(self.pathToJSON, 'targetServer')
			self.targetClient = setupTargetServerData.outData[0]
			self.targetUserContext = setupTargetServerData.outData[1]
			self.targetServerInfo = setupTargetServerData.outData[2]
		except Exception, err:
			self.ArchiverHandlerLogger.infoMessage('__init__', 'Unable to get information about target server: %s' % err)
			System.exit(1)
		
	def backupTables(self, bTableList, skipCheck = False):
		if skipCheck:
			backupTableList = bTableList
			lenBackupTableList = len(backupTableList)
		else:
			backupTableList = GeneralOperations(self.pathToJSON).checkTableExists(','.join(bTableList), self.targetServerData, noSkip = False)
			lenBackupTableList = len(backupTableList)

		if lenBackupTableList == 0:
			self.ArchiverHandlerLogger.infoMessage('backupTables', 'Backup table list is empty - nothing to backup.')
		else:
			self.ArchiverHandlerLogger.infoMessage('backupTables', 'Found tables in JSON. Backing up existing table...')
			self.ArchiverHandlerLogger.infoMessage('backupTables', 'Creating backup archiver "backup_%s" for tables on target server.' % self.archiverName )
			
			try:
				self.targetDataBinder = self.targetClient.createBinder()
				self.targetDataBinder.putLocal('IdcService', 'ADD_ARCHIVE')
				self.targetDataBinder.putLocal('IDC_Name', self.targetInstanceName)
				self.targetDataBinder.putLocal('aArchiveName', 'backup_%s' % self.archiverName)
				self.targetDataBinder.putLocal('aArchiveDescription', 'Description goes here')
				self.targetClient.sendRequest(self.targetUserContext, self.targetDataBinder)
			except Exception, err:
				self.ArchiverHandlerLogger.infoMessage('backupTables', 'Unable to create archiver on target server. [%s]' % err)
				System.exit(1)
			else:
				self.ArchiverHandlerLogger.infoMessage('backupTables', 'Checking job is created...')
				self.verifyArchiverNameExists(self.targetServerData, 'backup_%s' % self.archiverName)
				self.ArchiverHandlerLogger.infoMessage('backupTables', 'Backup archiver job is found. Adding tables to archiver data...')
				self.backupEditArchiverData(backupTableList)

	def backupEditArchiverData(self, bTableList):
		customQuery="Revisions.dDocName%=%'LIKWXXXXTFOMG'"
		try:
			self.ArchiverHandlerLogger.infoMessage('backupEditArchiverData', 'Modifying backup archive data...')
			self.targetDataBinder = self.targetClient.createBinder()
			self.targetDataBinder.putLocal('IdcService', 'EDIT_ARCHIVEDATA')
			self.targetDataBinder.putLocal('IDC_Name', self.targetInstanceName)
			self.targetDataBinder.putLocal('aArchiveName', 'backup_%s' % self.archiverName)
			
			editItems = 'aExportQuery'
			for eachTableName in bTableList:
				self.ArchiverHandlerLogger.infoMessage('backupEditArchiverData', 'Adding table %s to export query...' % eachTableName)
				editItems += ',aExportTable%s' % eachTableName
			editItems += ',aExportTables'
			self.targetDataBinder.putLocal('EditItems', editItems)

			self.targetDataBinder.putLocal('aExportQuery', 'Standard Query\tUseExportDate 0\tAllowExportPublished 0\tAllRevisions 1\tLatestRevisions 0\tNotLatestRevisions 0\tMostRecentMatching 0\tCurrentIndex -1\tClauses \tCustomQuery %s\tIsCustom 1' % customQuery)

			for eachTableName in bTableList:
				aExportTable = 'aExportTable%s' % eachTableName
				dataBinderValue = '\taTableName %s\t aCreateTimeStamp \t aModifiedTimeStamp \t aUsetargetID 0\t aIsCreateNewField 0\t aParentTables \t aTableRelations \t aIsReplicateDeletedRows 0\t aUseParentTS 0\t aRemoveExistingChildren 0\t aDeleteParentOnlyWhenNoChild 0\t aAllowDeleteParentRows 0\t Clauses \t CustomQuery \t IsCustom 0' % eachTableName
				self.targetDataBinder.putLocal(aExportTable, dataBinderValue)

			if len(bTableList) > 1:
				hdaTableList = ','.join(bTableList)
			else:
				hdaTableList = bTableList[0]
			self.targetDataBinder.putLocal('aExportTables', '%s' % hdaTableList)

			self.targetClient.sendRequest(self.targetUserContext, self.targetDataBinder)
		except Exception, err:
			self.ArchiverHandlerLogger.infoMessage('backupEditArchiverData', 'Unable to modify backup archiver data [%s]' % err)
			System.exit(1)
		else:
			self.ArchiverHandlerLogger.infoMessage('backupEditArchiverData', 'Succesfully modified backup archiver data. Exporting backup template...')
			self.exportArchiver('backup_%s' % self.archiverName, self.targetServerData, bTableList)

	def createArchiverJobs(self):
		self.ArchiverHandlerLogger.infoMessage('backupTables', 'Creating archiver %s on source server.' % self.archiverName)
		try:
			self.sourceDataBinder = self.sourceClient.createBinder()
			self.sourceDataBinder.putLocal('IdcService', 'ADD_ARCHIVE')
			self.sourceDataBinder.putLocal('IDC_Name', self.sourceInstanceName)
			self.sourceDataBinder.putLocal('aArchiveName', self.archiverName)
			self.sourceDataBinder.putLocal('aArchiveDescription', 'to %s' % self.targetInstanceName)
			self.sourceClient.sendRequest(self.sourceUserContext, self.sourceDataBinder)
		except Exception, err:
			self.ArchiverHandlerLogger.infoMessage('createArchiverJobs', 'Unable to create archiver on source server. [%s]' % err)
			System.exit(1)
		else:
			self.ArchiverHandlerLogger.infoMessage('createArchiverJobs', 'Checking job is created...')
			self.verifyArchiverNameExists(self.sourceServerData, self.archiverName)
		
		self.ArchiverHandlerLogger.infoMessage('createArchiverJobs', 'Creating archiver %s on target server.' % self.archiverName )
		try:
			self.targetDataBinder = self.targetClient.createBinder()
			self.targetDataBinder.putLocal('IdcService', 'ADD_ARCHIVE')
			self.targetDataBinder.putLocal('IDC_Name', self.targetInstanceName)
			self.targetDataBinder.putLocal('aArchiveName', self.archiverName)
			self.targetDataBinder.putLocal('aArchiveDescription', 'from %s' % self.sourceInstanceName)
			self.targetClient.sendRequest(self.targetUserContext, self.targetDataBinder)
		except Exception, err:
			self.ArchiverHandlerLogger.infoMessage('createArchiverJobs', 'Unable to create archiver on target server. [%s]' % err)
			System.exit(1)
		else:
			self.ArchiverHandlerLogger.infoMessage('createArchiverJobs', 'Checking job is created...')
			self.verifyArchiverNameExists(self.targetServerData, self.archiverName)

	def verifyArchiverNameExists(self, serverData, vArchiverName):
		try:
			verifyClient = serverData[0]
			verifyUserContext = serverData[1]
			verifyServerInfo = serverData[2]
			verifyServerInstance = serverData[3]

			verifyClientDataBinder = verifyClient.createBinder()
			verifyClientDataBinder.putLocal('IdcService', 'GET_ARCHIVES')
			verifyClientDataBinder.putLocal('IDC_Name', verifyServerInstance)
			serverResponse = verifyClient.sendRequest(verifyUserContext, verifyClientDataBinder)

			responseData = serverResponse.getResponseAsBinder()

			jobIsFound = False
			attempts = 0

			while True:
				for eachResult in responseData.getResultSet('ArchiveData').getRows():
					if vArchiverName == eachResult.get('aArchiveName'):
						jobIsFound = True

				if jobIsFound:
					self.ArchiverHandlerLogger.infoMessage('verifyArchiverNameExists', 'Success: archiver job exist in on %s server' % verifyServerInstance)
					break
				else:
					if attempts == 3:
						self.ArchiverHandlerLogger.infoMessage('verifyArchiverNameExists', 'Fail: Was unable to find archiver name %s on server after 3 attempts' % vArchiverName)
						System.exit(1)
					else:
						self.ArchiverHandlerLogger.infoMessage('verifyArchiverNameExists', 'Fail: unable to find archiver name %s on server. Trying again in 10 seconds' % vArchiverName)
						attempts += 1
						time.sleep(10)

		except Exception, err:
			self.ArchiverHandlerLogger.infoMessage('createArchiverJobs', 'Unable to create archiver on source server. [%s]' % err)
			System.exit(1)

	def editArchiverData(self, webAssetList = False, tableList = False, CMUClone = False):
		
		if webAssetList:
			self.ArchiverHandlerLogger.infoMessage('editArchiverData', 'Adding Web assets: %s to archive...' % (webAssetList))

			self.ArchiverHandlerLogger.infoMessage('editArchiverData', 'Checking Web Assets exit exists...')
			self.safeWebAssetList = GeneralOperations(self.pathToJSON).checkAssetExists(','.join(webAssetList), self.sourceServerData)
			self.lenSafeWebAssetList = len(self.safeWebAssetList)

			if self.lenSafeWebAssetList > 0:
				customQuery = ''
				
				for eachWebAsset in self.safeWebAssetList:
					webAssetName = eachWebAsset.split('|')[0]
					webAssetRev = eachWebAsset.split('|')[1]

					if len(customQuery) == 0:
						customQuery += MessageFormat.format("(Revisions.dDocName%=%''{0}''%AND%Revisions.dRevLabel%=%''{1}'')", webAssetName, webAssetRev)
					else:
						customQuery += MessageFormat.format("\r\nOR%(Revisions.dDocName%=%''{0}''%AND%Revisions.dRevLabel%=%''{1}'')", webAssetName, webAssetRev)
			else:
				customQuery="Revisions.dDocName%=%'LIKWXXXXTFOMG'"
		else:
			customQuery="Revisions.dDocName%=%'LIKWXXXXTFOMG'"
			self.safeWebAssetList = False
			self.lenSafeWebAssetList = 0

		if tableList:
			self.ArchiverHandlerLogger.infoMessage('editArchiverData', 'Adding Tables %s: to archive...' % (tableList))

			if CMUClone:
				self.safeTableList = tableList
			else:
				self.safeTableList = GeneralOperations(self.pathToJSON).checkTableExists(','.join(tableList), self.sourceServerData)

			if self.lenSafeTableList == 0:
				self.safeTableList = False
		else:
			self.safeTableList = False
			self.lenSafeTableList = 0

		try:
			self.ArchiverHandlerLogger.infoMessage('editArchiverData', 'Modifying archive data...')
			self.sourceDataBinder = self.sourceClient.createBinder()
			self.sourceDataBinder.putLocal('IdcService', 'EDIT_ARCHIVEDATA')
			self.sourceDataBinder.putLocal('IDC_Name', self.sourceInstanceName)
			self.sourceDataBinder.putLocal('aArchiveName', self.archiverName)
			#1: Query for content items
			editItems = 'aExportQuery'

			if self.safeTableList:
				for eachTableName in self.safeTableList:
					self.ArchiverHandlerLogger.infoMessage('editArchiverData', 'Adding table %s to export query...' % eachTableName)
					#2: Query for each table
					editItems += ',aExportTable%s' % eachTableName
				#3: All tables
				editItems += ',aExportTables'
			self.sourceDataBinder.putLocal('EditItems', editItems)

			self.sourceDataBinder.putLocal('aExportQuery', 'Standard Query\tUseExportDate 0\tAllowExportPublished 0\tAllRevisions 1\tLatestRevisions 0\tNotLatestRevisions 0\tMostRecentMatching 0\tCurrentIndex -1\tClauses \tCustomQuery %s\tIsCustom 1' % customQuery)

			if self.safeTableList:
				for eachTableName in self.safeTableList:
					aExportTable = 'aExportTable%s' % eachTableName
					if eachTableName == "FolderFolders":
						tableCustomQuery = "FolderFolders.fFolderGUID%NOT%LIKE%'FLD_TRASH#%'%AND\nFolderFolders.fFolderGUID%NOT%LIKE%'FLD_USER#%'"
						dataBinderValue = '\taTableName %s\taCreateTimeStamp \taModifiedTimeStamp \taUseSourceID 0\taIsCreateNewField 0\taParentTables \taTableRelations \taIsReplicateDeletedRows 0\taUseParentTS 0\taRemoveExistingChildren 0\taDeleteParentOnlyWhenNoChild 0\taAllowDeleteParentRows 0\tClauses \tCustomQuery \tIsCustom 0\tCurrentIndex -1\tClauses \tCustomQuery %s\tIsCustom 1' % (eachTableName, tableCustomQuery)
					else:
						dataBinderValue = '\taTableName %s\t aCreateTimeStamp \t aModifiedTimeStamp \t aUseSourceID 0\t aIsCreateNewField 0\t aParentTables \t aTableRelations \t aIsReplicateDeletedRows 0\t aUseParentTS 0\t aRemoveExistingChildren 0\t aDeleteParentOnlyWhenNoChild 0\t aAllowDeleteParentRows 0\t Clauses \t CustomQuery \t IsCustom 0' % eachTableName
					self.sourceDataBinder.putLocal(aExportTable, dataBinderValue)

				if len(self.safeTableList) > 1:
					hdaTableList = ','.join(self.safeTableList)
				else:
					hdaTableList = self.safeTableList[0]

				self.sourceDataBinder.putLocal('aExportTables', '%s' % hdaTableList)
				
			self.sourceClient.sendRequest(self.sourceUserContext, self.sourceDataBinder)
		except Exception, err:
			self.ArchiverHandlerLogger.infoMessage('editArchiverData', 'Unable to modify archiver data [%s]' % err)
			System.exit(1)
		else:
			self.ArchiverHandlerLogger.infoMessage('editArchiverData', 'Succesfully modified archiver data.')

	def editTransferOptions(self):
		self.ArchiverHandlerLogger.infoMessage('editTransferOptions', 'Changing transfer settings on source server')
		try:
			self.sourceDataBinder = self.sourceClient.createBinder()
			self.sourceDataBinder.putLocal('IdcService', 'EDIT_ARCHIVEDATA')
			self.sourceDataBinder.putLocal('IDC_Name', self.sourceInstanceName)
			self.sourceDataBinder.putLocal('aArchiveName', self.archiverName)
			self.sourceDataBinder.putLocal('EditItems', 'aTransferOwner,aTargetArchive')
			self.sourceDataBinder.putLocal('aTransferOwner', self.sourceInstanceName)
			self.sourceDataBinder.putLocal('aTargetArchive', '%s/%s' % (self.targetInstanceName, self.archiverName))
			self.sourceClient.sendRequest(self.sourceUserContext, self.sourceDataBinder)
		except Exception, err:
			self.ArchiverHandlerLogger.infoMessage('editTransferOptions', 'Unable to change transfer settings on source server [%s]' % err)
			System.exit(1)
		else:
			self.ArchiverHandlerLogger.infoMessage('editTransferOptions', 'Succesfully modified transfer settings on source server.')

		self.ArchiverHandlerLogger.infoMessage('editTransferOptions', 'Changing transfer settings on target server')
		try:
			self.targetDataBinder = self.targetClient.createBinder()
			self.targetDataBinder.putLocal('IdcService', 'EDIT_ARCHIVEDATA')
			self.targetDataBinder.putLocal('IDC_Name', self.targetInstanceName)
			self.targetDataBinder.putLocal('aArchiveName', self.archiverName)
			self.targetDataBinder.putLocal('EditItems', 'aIsTargetable,aIsAutomatedTransfer')
			self.targetDataBinder.putLocal('aIsTargetable', '1')
			self.targetDataBinder.putLocal('aIsAutomatedTransfer', '0')
			self.targetClient.sendRequest(self.targetUserContext, self.targetDataBinder)
		except Exception, err:
			self.ArchiverHandlerLogger.infoMessage('editTransferOptions', 'Unable to change transfer settings on target server [%s]' % err)
			System.exit(1)
		else:
			self.ArchiverHandlerLogger.infoMessage('editTransferOptions', 'Succesfully modified transfer settings on target server.')

	def exportArchiver(self, eArchiverName, serverData, bTableList = False):

		exportArchiverClient = serverData[0]
		exportArchiverUserContext = serverData[1]
		exportArchiverServerInfo = serverData[2]
		exportArchiverServerInstance = serverData[3]

		self.ArchiverHandlerLogger.infoMessage('exportArchiver', 'Exporting archive name %s on server: %s...' % (eArchiverName, exportArchiverServerInstance))

		try:
			exportArchiverDataBinder = exportArchiverClient.createBinder()
			exportArchiverDataBinder.putLocal('IdcService', 'EXPORT_ARCHIVE')
			exportArchiverDataBinder.putLocal('aArchiveName', eArchiverName)
			exportArchiverDataBinder.putLocal('IDC_Name', exportArchiverServerInstance)
			exportArchiverDataBinder.putLocal('dataSource', 'RevisionIDs')
			exportArchiverDataBinder.putLocal('aDoDelete', '0')
			exportArchiverClient.sendRequest(exportArchiverUserContext, exportArchiverDataBinder)
			time.sleep(15)
		except Exception, err:
			self.ArchiverHandlerLogger.infoMessage('exportArchiver', 'Unable to export archiver [%s] on server [%s]' % (err, exportArchiverServerInfo))
			System.exit(1)
		else:
			self.ArchiverHandlerLogger.infoMessage('exportArchiver', 'Succesfully exported archive')
			self.ArchiverHandlerLogger.infoMessage('exportArchiver', 'Verifying batch file...')
			self.verifyBatchFile(serverData, eArchiverName, bTableList)

	def verifyBatchFile(self, serverData, vArchiverName, bTableList = False):
		"""
		After export or transfered is finished, verify batch file contents to make sure all defined objects are there.
		The method uses server in serverData and goes to archive to parse batch file data.
		"""
		self.ArchiverHandlerLogger.infoMessage('verifyBatchFile', 'Running with params: serverData=%s; vArchiverName=%s; bTableList=%s' % (
			serverData, vArchiverName, bTableList)) 

		batchClient = serverData[0]
		batchUserContext = serverData[1]
		batchServerInfo = serverData[2]
		batchServerInstance = serverData[3]

		if self.safeWebAssetList:
			if len(self.safeWebAssetList) > 0:
				try:
					attempts = 0
					verifyDone = False
					while True:
						if verifyDone:
							break
						queryFileCount = len(self.safeWebAssetList)
						self.ArchiverHandlerLogger.infoMessage('verifyBatchFile', 'Verifying web assets: %s on server: %s' % (self.safeWebAssetList, batchServerInstance)) 

						batchClientDataBinder = batchClient.createBinder()
						batchClientDataBinder.putLocal('IdcService', 'GET_BATCHFILES')
						batchClientDataBinder.putLocal('IDC_Name', batchServerInstance)
						batchClientDataBinder.putLocal('aArchiveName', vArchiverName)
						serverResponse = batchClient.sendRequest(batchUserContext, batchClientDataBinder)
						responseData = serverResponse.getResponseAsBinder()

						for batchResult in responseData.getResultSet('BatchFiles').getRows():
							if int(batchResult.get('aIsTableBatch')) == 0:

								batchName = batchResult.get('aBatchFile')
								batchClientDataBinder = batchClient.createBinder()
								batchClientDataBinder.putLocal('IdcService', 'GET_BATCH_FILE_DOCUMENTS')
								batchClientDataBinder.putLocal('IDC_Name', batchServerInstance)
								batchClientDataBinder.putLocal('aArchiveName', vArchiverName)
								batchClientDataBinder.putLocal('aBatchFile', batchName)
								serverResponse = batchClient.sendRequest(batchUserContext, batchClientDataBinder)
								responseData = serverResponse.getResponseAsBinder()

								if int(queryFileCount) == int(batchResult.get('aNumDocuments')):
									self.ArchiverHandlerLogger.infoMessage('verifyBatchFile', 'All content items exist in batch file [%s]' % batchServerInstance)
									verifyDone = True
									break
								else:
									self.ArchiverHandlerLogger.infoMessage('verifyBatchFile', 'Found only [%s] content items (should have been [%s]) in batch file.' 
										% (batchResult.get('aNumDocuments'), queryFileCount))

									exportedItems = []
									for serverComp in responseData.getResultSet('ExportResults').getRows():
										exportedItems.append((serverComp.get('webViewableFile:name').split('~')[0]).lower())

									self.ArchiverHandlerLogger.infoMessage('verifyBatchFile', 'Exported items: %s. Checking which content items failed to export...' % exportedItems)

									for eachItemToExport in self.safeWebAssetList:
										if eachItemToExport.split('|')[0].lower() not in exportedItems:
											self.ArchiverHandlerLogger.infoMessage('verifyBatchFile', 'Failed to find in batch file: %s' % eachItemToExport.split('|')[0])

									self.ArchiverHandlerLogger.infoMessage('verifyBatchFile', 'Will try to search again in 10 seconds...')

									if attempts == 3:
										self.ArchiverHandlerLogger.infoMessage('verifyBatchFile', '3 attempts: Exit.')
										System.exit(1)

									attempts += 1
									time.sleep(10)
				except Exception, err:
					self.ArchiverHandlerLogger.infoMessage('verifyBatchFile', 'Unable to retrieve batch file [%s]' % err)
					System.exit(1)

		vsafeTableList = False

		if self.safeTableList:
			if len(self.safeTableList) > 0:
				vsafeTableList = self.safeTableList

		if bTableList:
			vsafeTableList = bTableList
			self.ArchiverHandlerLogger.infoMessage('verifyBatchFile', 'Found backup table list. Scanning Tables: %s. Len %s' % (vsafeTableList, len(vsafeTableList)))
			
		if vsafeTableList:
			attempts = 0
			verifyDone = False
			while True:
				if verifyDone:
					break

				try:
					queryTableCount = len(vsafeTableList)
					if queryTableCount > 0:

						self.ArchiverHandlerLogger.infoMessage('verifyBatchFile', 'Verifying tables: %s on %s' % (vsafeTableList, batchServerInstance)) 
						
						batchClientDataBinder = batchClient.createBinder()
						batchClientDataBinder.putLocal('IdcService', 'GET_BATCHFILES')
						batchClientDataBinder.putLocal('IDC_Name', batchServerInstance)
						batchClientDataBinder.putLocal('aArchiveName', vArchiverName)
						serverResponse = batchClient.sendRequest(batchUserContext, batchClientDataBinder)
						responseData = serverResponse.getResponseAsBinder()

						batchFileCount = 0

						exportedTables = []
						for batchResult in responseData.getResultSet('BatchFiles').getRows():
							if int(batchResult.get('aIsTableBatch')) == 1:
								exportedTables.append(batchResult.get('aBatchFile'))

						if len(exportedTables) == queryTableCount:
							self.ArchiverHandlerLogger.infoMessage('verifyBatchFile', 'All tables exist in batch file on %s' % batchServerInstance) 
							verifyDone = True
						else:
							self.ArchiverHandlerLogger.infoMessage('verifyBatchFile', 'Not all tables exist in batch file. Should be %s tables, but got only %s' % (queryTableCount, len(exportedTables)))
							self.ArchiverHandlerLogger.infoMessage('verifyBatchFile', 'Checking which tables failed to export...')
							for eachShouldBeTable in vsafeTableList:
								if eachShouldBeTable not in exportedTables:
									self.ArchiverHandlerLogger.infoMessage('verifyBatchFile', 'Missing table: %s' % eachShouldBeTable) 
							self.ArchiverHandlerLogger.infoMessage('verifyBatchFile', 'Trying again in 10 seconds...')
							attempts += 1
							time.sleep(10)
					else:
						self.ArchiverHandlerLogger.infoMessage('verifyBatchFile', 'Safe table list is empty')
				except Exception, err:
					self.ArchiverHandlerLogger.infoMessage('verifyBatchFile', 'Exception occured while scanning table data. [%s]' % err)
					attempts += 1
					self.ArchiverHandlerLogger.infoMessage('verifyBatchFile', 'Trying again in 10 seconds...')
					time.sleep(10)

		else:
			self.ArchiverHandlerLogger.infoMessage('verifyBatchFile', 'Safe table list is empty [%s]. Nothing to scan.' % vsafeTableList)

	def transferArchiveJob(self):
		self.ArchiverHandlerLogger.infoMessage('transferArchiveJob', 'Starting to transfer archive...')
		try:
			self.sourceDataBinder = self.sourceClient.createBinder()
			self.sourceDataBinder.putLocal('IdcService', 'TRANSFER_ARCHIVE')
			self.sourceDataBinder.putLocal('IDC_Name', self.sourceInstanceName)
			self.sourceDataBinder.putLocal('aArchiveName', self.archiverName)
			self.sourceDataBinder.putLocal('aTransferOwner', self.sourceInstanceName)
			self.sourceDataBinder.putLocal('aTargetArchive', '%s/%s' % (self.targetInstanceName, self.archiverName))
			self.sourceClient.sendRequest(self.sourceUserContext, self.sourceDataBinder)
		except Exception, err:
			self.ArchiverHandlerLogger.infoMessage('transferArchiveJob', 'Unable to transfer archive [%s]' % err)
			System.exit(1)
		else:
			self.ArchiverHandlerLogger.infoMessage('transferArchiveJob', 'Finished transfering archive.')
			self.ArchiverHandlerLogger.infoMessage('transferArchiveJob', 'Scanning transfer data batch file...')
			time.sleep(5 + self.lenSafeTableList * 0.5 + self.lenSafeTableList * 5)
			self.verifyBatchFile(self.targetServerData, self.archiverName)

	def returnBatchFile(self):
		"""
		Return batchfiles result set
		"""
		try:
			self.targetDataBinder = self.targetClient.createBinder()
			self.targetDataBinder.putLocal('IdcService', 'GET_BATCHFILES')
			self.targetDataBinder.putLocal('IDC_Name', self.targetInstanceName)
			self.targetDataBinder.putLocal('aArchiveName', self.archiverName)
			serverResponse = self.targetClient.sendRequest(self.targetUserContext, self.targetDataBinder)

			responseData = serverResponse.getResponseAsBinder()
			return responseData.getResultSet('BatchFiles')
			
		except Exception, err:
			self.ArchiverHandlerLogger.infoMessage('returnBatchFile', 'Unable to retrieve batch file [%s]' % err)
			System.exit(1)

	def importArchiveJob(self, batchFileResultSet):
		try:
			self.targetDataBinder = self.targetClient.createBinder()
			self.targetDataBinder.putLocal('IdcService', 'GET_BATCHFILES')
			self.targetDataBinder.putLocal('IDC_Name', self.targetInstanceName)
			self.targetDataBinder.putLocal('aArchiveName', self.archiverName)
			serverResponse = self.targetClient.sendRequest(self.targetUserContext, self.targetDataBinder)

			responseData = serverResponse.getResponseAsBinder()
			batchFileResultSet = responseData.getResultSet("BatchFiles")

			self.targetDataBinder = self.targetClient.createBinder()
			self.targetDataBinder.putLocal('IdcService', 'IMPORT_BATCHFILE')
			self.targetDataBinder.putLocal('IDC_Name', self.targetInstanceName)
			self.targetDataBinder.putLocal('aArchiveName', self.archiverName)

			for serverComp in batchFileResultSet.getRows():
				eachDataResultSet = DataResultSetImpl()
				
				eachDataResultSet.addField(DataResultSet.Field("aBatchFile"), "")
				eachDataResultSet.addField(DataResultSet.Field("aState"), "")
				eachDataResultSet.addField(DataResultSet.Field("IDC_Name"), "")
				eachDataResultSet.addField(DataResultSet.Field("aIsTableBatch"), "")
				eachDataResultSet.addField(DataResultSet.Field("aNumDocuments"), "")
				
				eachDataResultSet.addRow(Arrays.asList(
					serverComp.get("aBatchFile"),
					"NEW",
					serverComp.get("IDC_Name"),
					serverComp.get("aIsTableBatch"),
					serverComp.get("aNumDocuments"))
				)
				self.ArchiverHandlerLogger.infoMessage('importArchiveJob', 'Importing Table: %s' % serverComp.get("aBatchFile"))

				self.targetDataBinder.addResultSet("BatchFile", eachDataResultSet)

				self.targetClient.sendRequest(self.targetUserContext, self.targetDataBinder)

		except Exception, err:
			self.ArchiverHandlerLogger.infoMessage('importArchiveJob', 'Unable to import archive [%s]' % err)
			System.exit(1)
		else:
			self.ArchiverHandlerLogger.infoMessage('importArchiveJob', 'Import is finished, checking imported items...')
			#time.sleep(5 + self.lenSafeTableList * 0.5 + self.lenSafeTableList * 2)

	def checkImportedItems(self):
		self.ArchiverHandlerLogger.infoMessage('checkImportedItems', 'Starting to check imported items...')
		if self.safeWebAssetList:
			if len(self.safeWebAssetList) > 0:
				self.ArchiverHandlerLogger.infoMessage('checkImportedItems', 'Checking web asset list: %s' % self.safeWebAssetList)
				GeneralOperations(self.pathToJSON).checkAssetExists(','.join(self.safeWebAssetList), self.targetServerData)
		
		if self.safeTableList:
			if len(self.safeTableList) > 0:
				self.ArchiverHandlerLogger.infoMessage('checkImportedItems', 'Checking table list: %s' % self.safeTableList)
				GeneralOperations(self.pathToJSON).checkTableExists(','.join(self.safeTableList), self.targetServerData)

	def main(self, jobName, CMUClone = False, cloneTableList = False, CMUsourceServerData = False, CMUtargetServerData = False):
		self.sourceInstanceName = CMUConfigParser(self.pathToJSON).returnObject("sourceServer", "instance")
		self.targetInstanceName = CMUConfigParser(self.pathToJSON).returnObject("targetServer", "instance")

		if CMUClone:
			self.ArchiverHandlerLogger.infoMessage('main', 'Calling ArchiverOperations from CMUOpearations... ')
			self.archiverName = jobName

			self.sourceServerData = []
			self.sourceServerData.append(CMUsourceServerData[0])
			self.sourceServerData.append(CMUsourceServerData[1])
			self.sourceServerData.append(CMUsourceServerData[2])
			self.sourceServerData.append(CMUsourceServerData[3])

			self.targetServerData = []
			self.targetServerData.append(CMUtargetServerData[0])
			self.targetServerData.append(CMUtargetServerData[1])
			self.targetServerData.append(CMUtargetServerData[2])
			self.targetServerData.append(CMUtargetServerData[3])

			self.tableList = cloneTableList
			self.safeTableList = cloneTableList
			self.lenSafeTableList = len(self.safeTableList)
			self.safeWebAssetList = []
			
			if len(self.tableList) > 0:
				self.backupTables(self.tableList, skipCheck = True)

			self.ArchiverHandlerLogger.infoMessage('main', 'Starting to create archive jobs with name: %s' % self.archiverName)
			self.createArchiverJobs()

			self.ArchiverHandlerLogger.infoMessage('main', 'Exporting only tables')
			self.editArchiverData(tableList = self.tableList, CMUClone = True)

			self.ArchiverHandlerLogger.infoMessage('main', 'Editing transfer options...')
			self.editTransferOptions()

			self.ArchiverHandlerLogger.infoMessage('main', 'Exporting archiver job...')
			self.exportArchiver(self.archiverName, self.sourceServerData)

			self.ArchiverHandlerLogger.infoMessage('main', 'Transfering archive to target server..')
			self.transferArchiveJob()
			
			self.ArchiverHandlerLogger.infoMessage('main', 'Importing archive on target server...')
			self.importArchiveJob(self.returnBatchFile())

			self.checkImportedItems()

		else:
			self.archiverName = jobName

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

			webAssetList = CMUConfigParser(self.pathToJSON).returnObject("ArchiverOperations", "WebAssets", "List")
			tableList = CMUConfigParser(self.pathToJSON).returnObject("ArchiverOperations", "WebAssets", "Tables")

			self.webAssetList = list(webAssetList)
			self.tableList = list(tableList)

			self.safeWebAssetList = []
			self.safeTableList = []

			if len(self.tableList) > 0:
				self.backupTables(self.tableList)

			self.ArchiverHandlerLogger.infoMessage('main', 'Starting to create archive jobs with name: %s' % self.archiverName)
			self.createArchiverJobs()

			if len(self.webAssetList) > 0 and len(self.tableList) > 0:
				self.ArchiverHandlerLogger.infoMessage('main', 'Exporting Assets and Tables...')
				self.editArchiverData(webAssetList = self.webAssetList, tableList = self.tableList)
			elif len(self.webAssetList) > 0 and len(self.tableList) == 0:
				self.ArchiverHandlerLogger.infoMessage('main', 'Exporting only assets')
				self.editArchiverData(webAssetList = self.webAssetList)
			elif len(self.webAssetList) == 0 and len(self.tableList) > 0:
				self.ArchiverHandlerLogger.infoMessage('main', 'Exporting only tables')
				self.editArchiverData(tableList = self.tableList)
			else:
				self.ArchiverHandlerLogger.infoMessage('main', 'Web asset [%s] and Table list [%s] are empty - nothing to export. Exit' % (self.webAssetList, self.tableList))
				System.exit(1)

			self.ArchiverHandlerLogger.infoMessage('main', 'Editing transfer options...')
			self.editTransferOptions()

			self.ArchiverHandlerLogger.infoMessage('main', 'Exporting archiver job...')
			self.exportArchiver(self.archiverName, self.sourceServerData)

			self.ArchiverHandlerLogger.infoMessage('main', 'Transfering archive to target server..')
			self.transferArchiveJob()

			self.ArchiverHandlerLogger.infoMessage('main', 'Importing archive on target server...')
			self.importArchiveJob(self.returnBatchFile())

			self.checkImportedItems()