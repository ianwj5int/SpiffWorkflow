from SpiffWorkflow.bpmn.specs.BpmnSpecMixin import BpmnSpecMixin
from SpiffWorkflow.specs.Simple import Simple

__author__ = 'matth'

class UserTask(Simple, BpmnSpecMixin):

    def is_engine_task(self):
        return False