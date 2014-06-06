# -*- coding: utf-8 -*-
from __future__ import division
# Copyright (C) 2012 Matthew Hampton
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

import os
import glob
from SpiffWorkflow.bpmn.BpmnWorkflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser.ValidationException import ValidationException
from SpiffWorkflow.bpmn.specs.BoundaryEvent import BoundaryEvent
from SpiffWorkflow.bpmn.specs.CallActivity import CallActivity
from SpiffWorkflow.bpmn.specs.ExclusiveGateway import ExclusiveGateway
from SpiffWorkflow.bpmn.specs.InclusiveGateway import InclusiveGateway
from SpiffWorkflow.bpmn.specs.IntermediateCatchEvent import IntermediateCatchEvent
from SpiffWorkflow.bpmn.specs.ManualTask import ManualTask
from SpiffWorkflow.bpmn.specs.NoneTask import NoneTask
from SpiffWorkflow.bpmn.specs.ParallelGateway import ParallelGateway
from SpiffWorkflow.bpmn.specs.ScriptTask import ScriptTask
from SpiffWorkflow.bpmn.specs.StartEvent import StartEvent
from SpiffWorkflow.bpmn.specs.UserTask import UserTask
from SpiffWorkflow.bpmn.specs.EndEvent import EndEvent
from SpiffWorkflow.bpmn.parser.ProcessParser import ProcessParser
from SpiffWorkflow.bpmn.parser.util import *
from SpiffWorkflow.bpmn.parser.task_parsers import *
from SpiffWorkflow.bpmn.parser.GlobalTaskResolver import GlobalTaskParser
import xml.etree.ElementTree as ET

class BaseBpmnParser(object):
    """
    The BpmnParser class hierarchy is a set of pluggable base classes that manage the parsing of a set of BPMN files.
    It is intended that one of the classes will be selected and overriden by an application that implements a BPMN engine.

    Extension points:
    OVERRIDE_PARSER_CLASSES provides a map from full BPMN tag name to a TaskParser and Task class.
    PROCESS_PARSER_CLASS provides a subclass of ProcessParser
    WORKFLOW_CLASS provides a subclass of BpmnWorkflow

    """

    PARSER_CLASSES = {
        full_tag('startEvent')          : (StartEventParser, StartEvent),
        full_tag('endEvent')            : (EndEventParser, EndEvent),
        full_tag('userTask')            : (UserTaskParser, UserTask),
        full_tag('task')                : (NoneTaskParser, NoneTask),
        full_tag('manualTask')          : (ManualTaskParser, ManualTask),
        full_tag('exclusiveGateway')    : (ExclusiveGatewayParser, ExclusiveGateway),
        full_tag('parallelGateway')     : (ParallelGatewayParser, ParallelGateway),
        full_tag('inclusiveGateway')     : (InclusiveGatewayParser, InclusiveGateway),
        full_tag('callActivity')        : (CallActivityParser, CallActivity),
        full_tag('scriptTask')                  : (ScriptTaskParser, ScriptTask),
        full_tag('intermediateCatchEvent')      : (IntermediateCatchEventParser, IntermediateCatchEvent),
        full_tag('boundaryEvent')               : (BoundaryEventParser, BoundaryEvent),
        }

    OVERRIDE_PARSER_CLASSES = {}

    PROCESS_PARSER_CLASS = ProcessParser
    GLOBAL_TASK_PARSER_CLASS = GlobalTaskParser
    WORKFLOW_CLASS = BpmnWorkflow
    _DYNAMICALLY_LOAD_SUB_PROCESSES = None

    def __init__(self):
        """
        Constructor.
        """

    def _get_parser_class(self, tag):
        if tag in self.OVERRIDE_PARSER_CLASSES:
            return self.OVERRIDE_PARSER_CLASSES[tag]
        elif tag in self.PARSER_CLASSES:
            return self.PARSER_CLASSES[tag]
        return None, None

    def create_process_parsers_from_bpmn(self, bpmn, svg=None, filename=None, absolute_global_file_id=None):
        """
        Create process parser objects based on bpmn content.

        :param svg: Optionally, provide the text data for the SVG of the BPMN file
        :param filename: Optionally, provide the source filename.
        """
        xpath = xpath_eval(bpmn)

        processes = xpath('.//bpmn:process')
        for process in processes:
            process_parser = self.PROCESS_PARSER_CLASS(self, process, svg, filename=filename, doc_xpath=xpath,
                                                       absolute_global_task_id=absolute_global_file_id+":"+process.get('id') if absolute_global_file_id else None)
            yield process_parser

    def create_global_task_parsers_from_bpmn(self, bpmn, filename=None):
        """
        Create global task parser objects based on bpmn content.

        :param filename: Optionally, provide the source filename.
        """
        xpath = xpath_eval(bpmn)

        global_tasks = xpath('.//bpmn:globalTask')
        for global_task in global_tasks:
            global_task_parser = self.GLOBAL_TASK_PARSER_CLASS(self, global_task, filename=filename)
            yield global_task_parser

    def _parse_condition(self, outgoing_task, outgoing_task_node, sequence_flow_node, task_parser=None):
        xpath = xpath_eval(sequence_flow_node)
        condition_expression_node = conditionExpression = first(xpath('.//bpmn:conditionExpression'))
        if conditionExpression is not None:
            conditionExpression = conditionExpression.text
        return self.parse_condition(conditionExpression, outgoing_task, outgoing_task_node, sequence_flow_node, condition_expression_node, task_parser)

    def parse_condition(self, condition_expression, outgoing_task, outgoing_task_node, sequence_flow_node, condition_expression_node, task_parser):
        """
        Pre-parse the given condition expression, and return the parsed version. The returned version will be passed to the Script Engine
        for evaluation.
        """
        return condition_expression

    def _parse_documentation(self, node, task_parser=None, xpath=None):
        xpath = xpath or xpath_eval(node)
        documentation_node = first(xpath('.//bpmn:documentation'))
        return self.parse_documentation(documentation_node, node, xpath, task_parser=task_parser)

    def parse_documentation(self, documentation_node, node, node_xpath, task_parser=None):
        """
        Pre-parse the documentation node for the given node and return the text.
        """
        return None if documentation_node is None else documentation_node.text

    def parse_file(self, file):

        events = "start", "start-ns", "end-ns"

        root = None
        ns_map = []

        for event, elem in ET.iterparse(file, events):
            if event == "start-ns":
                ns_map.append(elem)
            elif event == "end-ns":
                ns_map.pop()
            elif event == "start":
                if root is None:
                    root = elem
                elem.ns_map = dict(ns_map)

        return ET.ElementTree(root)

    def filter(self, bpmn, filename):
        for f in self.get_filters():
            f.filter(bpmn, filename)

    def get_filters(self):
        return []

class StaticFileSetBpmnParser(BaseBpmnParser):
    """
    The StaticFileSetBpmnParser class uses a static set of BPMN files as the source of it's workflow specifictions.
    It will load sub workflows eagerly (on parse)

    """

    _DYNAMICALLY_LOAD_SUB_PROCESSES = False


    def __init__(self):
        """
        Constructor.
        """
        super(StaticFileSetBpmnParser, self).__init__()
        self.process_parsers = {}
        self.process_parsers_by_name = {}

    def get_process_parser(self, process_id_or_name):
        """
        Returns the ProcessParser for the given process ID or name. It matches by name first.
        """
        if process_id_or_name in self.process_parsers_by_name:
            return self.process_parsers_by_name[process_id_or_name]
        else:
            return self.process_parsers[process_id_or_name]

    def get_spec(self, process_id_or_name):
        """
        Parses the required subset of the BPMN files, in order to provide an instance of BpmnProcessSpec (i.e. WorkflowSpec)
        for the given process ID or name. The Name is matched first.
        """
        return self.get_process_parser(process_id_or_name).get_spec()

    def add_bpmn_file(self, filename):
        """
        Add the given BPMN filename to the parser's set.
        """
        self.add_bpmn_files([filename])

    def add_bpmn_files_by_glob(self, g):
        """
        Add all filenames matching the provided pattern (e.g. *.bpmn) to the parser's set.
        """
        self.add_bpmn_files(glob.glob(g))

    def add_bpmn_files(self, filenames):
        """
        Add all filenames in the given list to the parser's set.
        """
        for filename in filenames:
            f = open(filename, 'r')
            try:
                self.add_bpmn_xml(self.parse_file(f), filename=filename)
            finally:
                f.close()

    def add_bpmn_xml(self, bpmn, svg=None, filename=None):
        """
        Add the given lxml representation of the BPMN file to the parser's set.

        :param svg: Optionally, provide the text data for the SVG of the BPMN file
        :param filename: Optionally, provide the source filename.
        """
        for process_parser in self.create_process_parsers_from_bpmn(bpmn, svg=svg, filename=filename):
            if process_parser.get_id() in self.process_parsers:
                raise ValidationException('Duplicate process ID', node=process_parser.node, filename=filename)
            if process_parser.get_name() in self.process_parsers_by_name:
                raise ValidationException('Duplicate process name', node=process_parser.node, filename=filename)
            self.process_parsers[process_parser.get_id()] = process_parser
            self.process_parsers_by_name[process_parser.get_name()] = process_parser

#For backwards compatibility:
class BpmnParser(StaticFileSetBpmnParser):
    """
    DEPRECATED: This class is only present in order to maintain backwards compatibility. Please use StaticFileSetBpmnParser or DynamicFileBasedBpmnParser
    """
    pass


class DynamicFileBasedBpmnParser(BaseBpmnParser):
    _DYNAMICALLY_LOAD_SUB_PROCESSES = True

    def __init__(self, global_task_resolver=None):
        """
        Constructor.
        """
        super(DynamicFileBasedBpmnParser, self).__init__()
        self.process_parsers_by_url_and_id = {}
        self.global_task_parsers_by_url_and_id = {}
        self.global_task_resolver = global_task_resolver

    def resolve_called_activity_spec(self, location, idref, my_call_activity_task=None, absolute_global_task_id=None):


        if absolute_global_task_id and self.global_task_resolver:
            location, idref = self.global_task_resolver.get_location_and_idref_from_absolute_id(absolute_global_task_id)
        else:
            filename = os.path.abspath(location)
            if (filename , idref) in self.global_task_parsers_by_url_and_id:
                location, idref = self.global_task_resolver.get_location_and_idref_for_global_task(
                    self.global_task_parsers_by_url_and_id[(filename, idref)], my_call_activity_task)

        filename = os.path.abspath(location)

        if (filename, idref) in self.process_parsers_by_url_and_id:
            return self.process_parsers_by_url_and_id[(filename, idref)].get_spec()

        f = open(filename, 'r')
        try:
            bpmn = self.parse_file(f)
            self.filter(bpmn, filename)
            absolute_global_file_id = self.global_task_resolver.get_absolute_global_file_id(filename) if self.global_task_resolver else None
            for process_parser in self.create_process_parsers_from_bpmn(bpmn, svg=None, filename=filename, absolute_global_file_id=absolute_global_file_id):
                self.process_parsers_by_url_and_id[(filename, process_parser.get_id())] = process_parser
            for global_task_parser in self.create_global_task_parsers_from_bpmn(bpmn, filename=filename):
                self.global_task_parsers_by_url_and_id[(filename, global_task_parser.get_id())] = global_task_parser
                global_task_parser.parse_node()
        finally:
            f.close()

        if (filename , idref) in self.global_task_parsers_by_url_and_id:
            return self.resolve_called_activity_spec(filename, idref)

        return self.process_parsers_by_url_and_id[(filename, idref)].get_spec()

    def _resolve_global_task(self, global_task_parser, my_call_activity_task):
        return self.global_task_resolver.get_task_spec(global_task_parser, my_call_activity_task)

    def get_spec(self, bpmn_file, process_idref):
        return self.resolve_called_activity_spec(bpmn_file, process_idref, None)