import json
import logging
import os
import sys
import UserDict

import time

import cherrypy
import controllers.module as module
import splunk
import splunk.search
import splunk.util
import lib.util as util
import collections

from string import Template

logger = logging.getLogger("splunk")


class Node(object):
	def __init__(self, nid, moid, parent, name, addfields):
		self.nid = nid
		self.moid = moid
		self.parent = parent
		self.children = []
		self.name = name
		self.addfields = addfields
	def getLeaves (self):
		leavesSum = []
		if (len(self.children) == 0):
			return self
		else:
			for c in self.children:
				try:
					leavesSum.extend(c.getLeaves())
				except TypeError:
					leavesSum.append(c.getLeaves())
			logger.info("Length of leaves: %s",len(leavesSum))
			return leavesSum
	def getBranches (self):
		branchesSum = []
		if (len(self.children) > 0):
			try:
				branchesSum.extend(self)
			except TypeError:
				branchesSum.append(self)
			logger.info("Adding branch: %s",branchesSum)
			for c in self.children:
				try:
					branchesSum.extend(c.getBranches())
				except TypeError:
					branchesSum.append(c.getBranches())
		return branchesSum
		
class NodeDict(UserDict.UserDict):
	def addNodes(self, nodes):
		""" Add every node as a child to its parent by doing two passes."""
		for i in (1, 2):
			for node in nodes:
				self.data[node.nid] = node
				if node.parent in self.data.keys():
					if node.parent != "N/A" and node not in self.data[node.parent].children:
						self.data[node.parent].children.append(node)

class SOLNTreeNav(module.ModuleHandler):
	
	parentSnippet = Template('<div class="ui-tree-parent $metype-parent-div" id="$meid-parent"><div class="ui-tree-node-box $metype-node-box"><span class="noel-icon-plus noel-icon ui-icon-parent"></span><div class="ui-tree-node $metype-node" id="$meid" solndata=\'$medata\'>$name</div></div><div class="ui-tree-container $metype-container" style="display:none;">$content</div></div>')
	childSnippet = Template('<div class="ui-tree-node-box $metype-node-box"><div class="ui-tree-node ui-tree-node-leaf $metype-node" id="$meid" solndata=\'$medata\'>$name</div></div>')
	
	def getDataString(self, data):
		"""
		Create a json literal of the id_fields within data
		"""
		jsdata = {}
		for field in self.id_fields:
			jsdata[field] = data.get(field, "")
		return json.dumps(jsdata)
	
	def _getMarkupForNode(self, node):
		"""
		Recursively get markup for a node and all its children
		"""
		
		if (len(node.children) == 0):
			#AVAST GIMME MEdata there matey! P-)
			return self.childSnippet.substitute(name=node.name, meid=node.nid, metype=node.addfields["type"].lower(), medata=self.getDataString(node.addfields))
		else:
			childContent = []
			for child in node.children:
				childContent.append(self._getMarkupForNode(child))
			return self.parentSnippet.substitute(name=node.name, meid=node.nid, metype=node.addfields["type"].lower(), medata=self.getDataString(node.addfields), content=("".join(childContent)))
	
	def getResultID(self, result, id_fields):
		"""
		Create an ID from the result and configured id_fields
		#TODO: should probably escape ID's for selectors...
		RETURNS a string to be used as an ID
		"""
		compound_key = []
		for id_field in id_fields:
			compound_key.append(str(result.get(id_field, "NULL")))
		return "-".join(compound_key)
	
	def generateResults(self, **kwargs):
		"""
		Make the html output for an arbitrary hierarchy given by the upstream search
		"""
		sid = kwargs.get("sid", None)
		pp = kwargs.get("postProcess", '')
		self.id_fields = kwargs.get("idFields").split(",")
		self.parent_fields = kwargs.get("parentFields").split(",")
		self.type_field = kwargs.get("typeField")
		self.display_field = kwargs.get("displayField")
		self.root_type = kwargs.get("rootType")
		logger.info("Root type:" + self.root_type)
		job = splunk.search.getJob(sid)
		if pp:
			job.setFetchOption(search=pp)
		rs = getattr(job, 'results')
		nodes = []
		fieldNames = [self.type_field] + self.id_fields
		requiredFields = self.id_fields + self.parent_fields + [self.display_field]
		for i, result in enumerate(rs):
			resultId = self.getResultID(result, self.id_fields)
			resultParent = self.getResultID(result, self.parent_fields)
			logger.debug("Result data:" + str(result))
			resultName = str(result.get(self.display_field, "No Display Value"))
			resultAddFields = {}
			for field in fieldNames:
				fieldValues = result.get(field, None)
				if fieldValues:
					resultAddFields[field] = str(fieldValues)
			nodes.append(Node(resultId, resultId, resultParent, resultName, resultAddFields))
					
		nodeDict = NodeDict()
		nodeDict.addNodes(nodes)
		logger.debug("Node Dictionary:"+ str(nodeDict))
		rootNodes = [node for nid, node in nodeDict.items() if node.addfields[self.type_field] == self.root_type]
		logger.info("RootNodes: %s", rootNodes)
		data = []
		for rootNode in rootNodes:
			logger.info("RootNode: %s",rootNode.name)
			logger.info("Leaves: %s",rootNode.getLeaves())
			logger.info("Branches: %s", rootNode.getBranches())
			data.append(self._getMarkupForNode(rootNode))
		
		markup = "".join(data)
		return markup
