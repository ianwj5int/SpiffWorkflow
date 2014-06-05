import unittest
import datetime
import time
from SpiffWorkflow.Task import Task
from SpiffWorkflow.bpmn.BpmnWorkflow import BpmnWorkflow
from tests.SpiffWorkflow.bpmn.BpmnWorkflowTestCase import DynamicallyLoadedSubWorkflowTestCase


class NestedProcessesTest(DynamicallyLoadedSubWorkflowTestCase):
    def setUp(self):
        self.spec = self.load_spec()

    def load_spec(self):
        return self.load_workflow_spec('Dynamic-Loading-Workflows/base-package/workflow-source/process-01/level-01.bpmn', 'level-01')

    def testRunThroughHappy(self):

        self.workflow = BpmnWorkflow(self.spec)
        self.do_next_named_step('User Task 02-A')
        self.workflow.do_engine_steps()
        self.save_restore()
        self.assertEquals(1, len(self.workflow.get_tasks(Task.READY)))
        self.do_next_named_step('User Task 03-A')
        self.workflow.do_engine_steps()
        self.save_restore()
        self.assertEquals(1, len(self.workflow.get_tasks(Task.READY)))
        self.do_next_named_step('User Task 02-B')
        self.workflow.do_engine_steps()
        self.save_restore()
        self.assertEquals(0, len(self.workflow.get_tasks(Task.READY | Task.WAITING)))

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(NestedProcessesTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())