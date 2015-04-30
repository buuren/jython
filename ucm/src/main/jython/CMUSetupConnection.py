# RIDC java libs:
from oracle.stellent.ridc import IdcClientManager, IdcContext, IdcClientException
from oracle.stellent.ridc.model import DataBinder, DataObject, DataResultSet, TransferFile
from oracle.stellent.ridc.protocol import ServiceResponse, ServiceException, ProtocolException
from oracle.stellent.ridc.protocol.http import HttpProtocolException
from oracle.stellent.ridc import *

from CMUConfigParser import CMUConfigParser
from CMULogger import log4j

from java.lang import System

class SetupUCMConnection:
	""" 
	Object: SetupUCMConnection
	Requires: path to configuration file, type of server (source/target or whatever is defined in JSON)
	returns: list of objects [client, userContext, serverInfo, instanceName]
	cleint = clientManager to server
	userContext = username/password
	serverInfo = hostname / username / password
	instanceName = content server name
	"""
	SetupUCMConnectionLogger = log4j("SetupUCMConnection")

	def __init__(self, pathToJSON, serverType):
		try:
			clientManager = IdcClientManager()
			idcConnectionURL = "idc://%s:4444" % CMUConfigParser(pathToJSON).returnObject(serverType, "hostname").split(":")[0]
			instanceName = CMUConfigParser(pathToJSON).returnObject(serverType, "instance")
			Username = CMUConfigParser(pathToJSON).returnObject(serverType, "username")
			Password = CMUConfigParser(pathToJSON).returnObject(serverType, "password")
		except Exception, err:
			self.SetupUCMConnectionLogger.infoMessage('__init__', 'Unable to read config file: %s' % err)
			System.exit(1)

		client = clientManager.createClient(idcConnectionURL)
		userContext = IdcContext(Username, Password) 
		serverInfo = "Hostname: %s, user name: %s, password: %s" % (idcConnectionURL, Username, Password)

		try:
			dataBinder = client.createBinder()
			dataBinder.putLocal("IdcService", "PING_SERVER")
			serverResponse = client.sendRequest(userContext, dataBinder)
			responseData = serverResponse.getResponseAsBinder()
		except ProtocolException, err:
			self.SetupUCMConnectionLogger.infoMessage('__init__', 'Unable to initialize socket connection to Content Server. %s [%s]' % (serverInfo, err))
			for stackTrace in err.getStackTrace():
				print stackTrace
			#print dir(err)
			System.exit(1)
		except ServiceException, err:
			self.SetupUCMConnectionLogger.infoMessage('__init__', 'Permission to run RIDC on %s is denied. [%s]' % (serverInfo, err))
			System.exit(1)
		except Exception, err:
			self.SetupUCMConnectionLogger.infoMessage('__init__', 'General exception occured. %s [%s]' % (serverInfo, err))
			System.exit(1)
		else:
			#idcConnectionURL = "http://%s" % CMUConfigParser(pathToJSON).returnObject(serverType, "hostname")

			client = clientManager.createClient(idcConnectionURL)
			
			dataBinder = client.createBinder()
			dataBinder.putLocal("IdcService", "CHECK_USER_CREDENTIALS")
			dataBinder.putLocal("userName", Username)
			dataBinder.putLocal("authenticateUser", "0")
			dataBinder.putLocal("userPassword", Password)
			dataBinder.putLocal("getUserInfo", "1")
			dataBinder.putLocal("userExtendedInfo", "1")
			
			try:
				serverResponse = client.sendRequest(userContext, dataBinder)
			except ProtocolException, err:
				self.SetupUCMConnectionLogger.infoMessage('__init__', 'Unable to validate user credentials. Check user name/password. %s [%s]' % (err, serverInfo))
				System.exit(1)
			else:
				responseData = serverResponse.getResponseAsBinder()
				userRoles = responseData.getLocal("roles")
				
				if userRoles and 'admin' in userRoles:
					idcConnectionURL = "idc://%s:4444" % CMUConfigParser(pathToJSON).returnObject(serverType, "hostname").split(":")[0]
					client = clientManager.createClient(idcConnectionURL)
					client.getConfig().setSocketTimeout(300000)
					dataBinder = client.createBinder()
					self.outData = [client, userContext, serverInfo, instanceName]
				else:
					self.SetupUCMConnectionLogger.infoMessage('__init__', 'User name %s: must have admin role. Current roles: %s [%s]' % (Username, userRoles, serverInfo))
					System.exit(1)