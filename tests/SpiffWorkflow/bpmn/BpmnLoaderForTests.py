# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import, division

from __future__ import division
from SpiffWorkflow.bpmn.parser.filters import EclipseConvertAbsolutePlatformImportsToRelativePaths, EclipseConvertAnchorTypeCalledElementIdsToQNames
from SpiffWorkflow.bpmn.specs.CallActivity import CallActivity
from SpiffWorkflow.bpmn.specs.EndEvent import EndEvent
from SpiffWorkflow.bpmn.specs.ExclusiveGateway import ExclusiveGateway
from SpiffWorkflow.bpmn.specs.UserTask import UserTask
from SpiffWorkflow.bpmn.parser.BpmnParser import BpmnParser, DynamicFileBasedBpmnParser
from SpiffWorkflow.bpmn.parser.task_parsers import UserTaskParser, EndEventParser, CallActivityParser
from SpiffWorkflow.bpmn.parser.util import full_tag
from SpiffWorkflow.bpmn.parser.GlobalTaskResolver import GlobalTaskResolver
from SpiffWorkflow.operators import Assign
import os

__author__ = 'matth'

#This provides some extensions to the BPMN parser that make it easier to implement testcases

class TestUserTask(UserTask):

    def get_user_choices(self):
        if not self.outputs:
            return []
        assert len(self.outputs) == 1
        next_node = self.outputs[0]
        if isinstance(next_node, ExclusiveGateway):
            return next_node.get_outgoing_sequence_names()
        return self.get_outgoing_sequence_names()

    def do_choice(self, task, choice):
        task.set_data(choice=choice)
        task.complete()

class TestEndEvent(EndEvent):

    def _on_complete_hook(self, my_task):
        my_task.set_data(end_event=self.description)
        super(TestEndEvent, self)._on_complete_hook(my_task)

class TestCallActivity(CallActivity):

    def __init__(self, parent, name, **kwargs):
        super(TestCallActivity, self).__init__(parent, name, out_assign=[Assign('choice', 'end_event')], **kwargs)

class TestBpmnParser(BpmnParser):
    OVERRIDE_PARSER_CLASSES = {
        full_tag('userTask')            : (UserTaskParser, TestUserTask),
        full_tag('endEvent')            : (EndEventParser, TestEndEvent),
        full_tag('callActivity')        : (CallActivityParser, TestCallActivity),
        }

    def parse_condition(self, condition_expression, outgoing_task, outgoing_task_node, sequence_flow_node, condition_expression_node, task_parser):
        cond = super(TestBpmnParser, self).parse_condition(condition_expression,outgoing_task, outgoing_task_node, sequence_flow_node, condition_expression_node, task_parser)
        if cond is not None:
            return cond
        return "choice == '%s'" % sequence_flow_node.get('name', None)

class DynamicallyLoadedSubWorkflowTestBpmnParser(DynamicFileBasedBpmnParser):

    OVERRIDE_PARSER_CLASSES = {
        full_tag('userTask')            : (UserTaskParser, TestUserTask),
        full_tag('endEvent')            : (EndEventParser, TestEndEvent),
        full_tag('callActivity')        : (CallActivityParser, TestCallActivity),
        }

    def parse_condition(self, condition_expression, outgoing_task, outgoing_task_node, sequence_flow_node, condition_expression_node, task_parser):
        cond = super(TestBpmnParser, self).parse_condition(condition_expression,outgoing_task, outgoing_task_node, sequence_flow_node, condition_expression_node, task_parser)
        if cond is not None:
            return cond
        return "choice == '%s'" % sequence_flow_node.get('name', None)

    def get_filters(self):
        return super(DynamicallyLoadedSubWorkflowTestBpmnParser, self).get_filters() + [
            EclipseConvertAnchorTypeCalledElementIdsToQNames(),
            EclipseConvertAbsolutePlatformImportsToRelativePaths({
                'platform:/resource/SpiffWorkflow' : os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))),
            })]

class GlobalTaskResolverForTests(GlobalTaskResolver):

    def __init__(self, processes):
        self.processes = processes
        self._parsed_processes = {}

    def get_main_process_by_name(self, name):
        return self._get_process_spec(name, 'main', 'main')

    def _get_process_spec(self, collection_name, bpmn_name, process_id):
        name = '%s.%s.%s' % (collection_name, bpmn_name, process_id)
        if name not in self._parsed_processes:
            f = 'file_not_found__'
            i = 1
            while not os.path.exists(f):
                f = os.path.join(os.path.dirname(__file__), 'data', self.processes[collection_name][-i], '%s.bpmn' % bpmn_name)
                i+= 1
            self._parsed_processes[name] = DynamicallyLoadedSubWorkflowTestBpmnParser(self).get_spec(f, process_id)

        return self._parsed_processes[name]

    def get_task_spec(self, global_task_parser):
        collection_name = os.path.basename(os.path.dirname(global_task_parser.filename))
        bpmn_name, process_id = global_task_parser.get_name().split(':')
        return self._get_process_spec(collection_name, bpmn_name, process_id)