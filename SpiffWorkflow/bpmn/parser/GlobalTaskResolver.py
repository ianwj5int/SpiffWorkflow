__author__ = 'matth'

class GlobalTaskResolver(object):

    def get_task_spec(self, global_task_name, global_task_node, calling_process_parser):
        """
        Return the task spec for the specified global task.

        Currently, only subworkflow's are supported - i.e. return an instance of BpmnProcessSpec

        The calling_process_parser is provided so that relative names can be supported.
        """