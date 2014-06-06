import unittest
import datetime
import time
from SpiffWorkflow.Task import Task
from tests.SpiffWorkflow.bpmn.BpmnWorkflowTestCase import DynamicallyLoadedSubWorkflowTestCase
from tests.SpiffWorkflow.bpmn.BpmnLoaderForTests import GlobalTaskResolverForTests, TestWorkflow



class DynamicLoadingOfSubWorkflowsTest(DynamicallyLoadedSubWorkflowTestCase):

    def setup_spec_base_level(self):
        self.resolver = GlobalTaskResolverForTests({
            'process-01': [
                'Dynamic-Loading-Workflows/base-package/process-01'],
        })
        self.spec = self.resolver.get_main_process_by_name('process-01')

    def setup_spec_sub_level(self):
        self.resolver = GlobalTaskResolverForTests({
            'process-01': [
                'Dynamic-Loading-Workflows/base-package/process-01',
                'Dynamic-Loading-Workflows/sub-package/process-01'],
        })
        self.spec = self.resolver.get_main_process_by_name('process-01')

    def setup_spec_user_content_level(self):
        self.resolver = GlobalTaskResolverForTests({
            'process-01': [
                'Dynamic-Loading-Workflows/base-package/process-01',
                'Dynamic-Loading-Workflows/sub-package/process-01',
                'Dynamic-Loading-Workflows/user-content/process-01'],
        })
        self.spec = self.resolver.get_main_process_by_name('process-01')

    def testRunThroughBaseLevel(self):
        self.setup_spec_base_level()
        self.workflow = TestWorkflow(self.spec)
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

    def testRunThroughSubLevel(self):
        self.setup_spec_sub_level()
        self.workflow = TestWorkflow(self.spec)
        self.do_next_named_step('User Task 02-A')
        self.workflow.do_engine_steps()
        self.save_restore()
        self.assertEquals(1, len(self.workflow.get_tasks(Task.READY)))
        self.do_next_named_step('User Task 03-A')
        self.workflow.do_engine_steps()
        self.save_restore()
        self.assertEquals(1, len(self.workflow.get_tasks(Task.READY)))
        self.do_next_named_step('User Task 02-B-Sub')
        self.workflow.do_engine_steps()
        self.save_restore()
        self.do_next_named_step('User Task 02-B')
        self.workflow.do_engine_steps()
        self.save_restore()
        self.assertEquals(0, len(self.workflow.get_tasks(Task.READY | Task.WAITING)))

    def testRunThroughUserLevel(self):
        self.setup_spec_user_content_level()
        self.workflow = TestWorkflow(self.spec)
        self.do_next_named_step('User Task Main User')
        self.workflow.do_engine_steps()
        self.save_restore()
        self.do_next_named_step('User Task 02-A')
        self.workflow.do_engine_steps()
        self.save_restore()
        self.assertEquals(1, len(self.workflow.get_tasks(Task.READY)))
        self.do_next_named_step('User Task 03-A')
        self.workflow.do_engine_steps()
        self.save_restore()
        self.assertEquals(1, len(self.workflow.get_tasks(Task.READY)))
        self.do_next_named_step('User Task 02-B-Sub')
        self.workflow.do_engine_steps()
        self.save_restore()
        self.do_next_named_step('User Task 02-B')
        self.workflow.do_engine_steps()
        self.save_restore()
        self.assertEquals(0, len(self.workflow.get_tasks(Task.READY | Task.WAITING)))

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(DynamicLoadingOfSubWorkflowsTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())