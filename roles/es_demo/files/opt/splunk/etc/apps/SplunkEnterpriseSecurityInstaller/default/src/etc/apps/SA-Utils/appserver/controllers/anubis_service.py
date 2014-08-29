import logging
import os
import sys

import cherrypy

from splunk import AuthorizationFailed as AuthorizationFailed
import splunk.appserver.mrsparkle.controllers as controllers
import splunk.appserver.mrsparkle.lib.util as util
import splunk.entity as en
import splunk.bundle as bundle

from splunk.util import normalizeBoolean as normBool
from splunk.appserver.mrsparkle.lib.decorators import expose_page
from splunk.appserver.mrsparkle.lib.routes import route

from splunk.appserver.mrsparkle.lib import viewconf
from string import Template

VIEW_ENTITY_CLASS = 'data/ui/views'
globalCounter = {}
htmlModuleHierarchySnippet = ""
globalModList = {}

parentSnippet = Template('<div class="ui-tree-parent $metype-parent-div" id="$meid-parent"><div class="ui-tree-node-box $metype-node-box"><span class="noel-icon-plus noel-icon ui-icon-parent"></span><div class="ui-tree-node $metype-node module-node" id="$meid">$name<span class="layoutPanel-Name">$panel</span></div></div><div class="ui-tree-container $metype-container" style="display:none;">$content</div></div>')
childSnippet = Template('<div class="ui-tree-node-box $metype-node-box"><div class="ui-tree-node ui-tree-node-leaf $metype-node module-node" id="$meid">$name<span class="layoutPanel-Name">$panel</span></div></div>')
		
		
logger = logging.getLogger('splunk')

class AnubisService(controllers.BaseController):
	'''Anubis Debugging Service Controller'''
 
	@route('/:app/:action=show')
	@expose_page(must_login=True, methods=['GET']) 
	def show(self, app, view, **kwargs):
		''' shows basic debug page '''

		form_content  = {}
		user = cherrypy.session['user']['name'] 
		
		#GET MODULE INFO HERE
		viewConfig = viewconf.loads(en.getEntity(VIEW_ENTITY_CLASS, view, namespace=app).get('eai:data'), view, isStorm=False)
		modules = self.processModuleHierarchy(viewConfig)
		moduleHierarchySnippet = []
		
		logger.debug(modules)
		
		for module in modules:
			moduleHierarchySnippet.append(self._getMarkupForNode(module))
		logger.debug(moduleHierarchySnippet)

		moduleHierarchySnippet = "".join(moduleHierarchySnippet)
		
		return self.render_template('/SA-Utils:/templates/anubis_debug_show.html', 
									dict(form_content=form_content, moduleHierarchySnippet=moduleHierarchySnippet))

	def _getMarkupForNode(self, node):
		"""
		Recursively get markup for a node and all its children
		"""
		if node.get('children') == None:
			return childSnippet.substitute(name=node.get('mid', 'Not Available'), meid=node.get('mid', 'Not Available'), panel=node.get('layoutPanel', ''), metype=node.get('className', 'I need to fix this'))
		else:
			childContent = []
			for child in node["children"]:
				childContent.append(self._getMarkupForNode(child))
			return parentSnippet.substitute(name=node.get('mid', 'Not Available'), meid=node.get('mid', 'Not Available'), panel=node.get('layoutPanel', ''), metype=node.get('className', 'I need to fix this'), content=("".join(childContent)))

	@route('/:app/:action=getAppServerConfiguration')
	@expose_page(must_login=True, methods=['GET'])
	def getAppServerConfiguration(self, app, action, targetApp, **kwargs):
		''' Returns configuration data '''

		logger.debug("Grabbing configuration info")
		sessionKey = cherrypy.session['sessionKey']

		# GET APP INFORMATION
		appConf = bundle.getConf("app",sessionKey=sessionKey, namespace=targetApp)
		# Determine version information of app
		try:
			appVersion = appConf["launcher"]["version"]
		except Exception:
			# Unable to locate the version
			appVersion = -1
		# Determine build information of app
		try:
			appBuild = appConf["install"]["build"]
		except Exception:
			# Unable to locate the build
			appBuild = -1
		
		# GET SPLUNK INFORMATION
		splunkInfo = en.getEntities(["server","info"], sessionKey=sessionKey)
		try:
			splunkVersion = splunkInfo["server-info"]["version"]
		except Exception:
			# Unable to get splunk version
			splunkVersion = -1

		try:
			splunkBuild = splunkInfo["server-info"]["build"]
		except Exception:
			# Unable to get splunk build
			splunkBuild = -1
		
		return self.render_json({
								 "appVersion" : appVersion,
								 "appBuild" : appBuild,
								 "splunkVersion" : splunkVersion,
								 "splunkBuild" : splunkBuild,
								})
								
	def _recurseModuleTree(self, data, depth=0):
		output = []
		
		for i, mod in enumerate(data):
			# assign a unique DOM ID to this module
			globalCounter.setdefault(mod['className'], -1)
			globalCounter[mod['className']] += 1
			
			mod["mid"] = '%s_%s_%s_%s' % (mod['className'],globalCounter[mod['className']], depth,i)
			
			if mod.get('children'):
				self._recurseModuleTree(mod['children'], depth=depth+1)
	
		return data
		
	def processModuleHierarchy(self, viewConfig):
		modules = viewConfig['modules']
		globalCounter.clear()
		return self._recurseModuleTree(modules)

	def _redirect(self, app, endpoint):
		''' convienience wrapper to make_url() '''

		return self.make_url(['custom', 'SA-Utils', 'anubis_service', app, endpoint])

