__author__ = 'matth'

class GlobalTaskParser(object):

    def __init__(self, parser, node, filename=None):
        self.parser = parser
        self.node = node
        self.filename = filename

    def get_id(self):
        """
        Returns the process ID
        """
        return self.node.get('id')

    def get_name(self):
        """
        Returns the process name (or ID, if no name is included in the file)
        """
        return self.node.get('name', default=self.get_id())

    def parse_node(self):
        """
        Parse any extension elements
        """


class GlobalTaskResolver(object):

    def get_location_and_idref_for_global_task(self, global_task_parser, my_call_activity_task):
        """
        Return the location and idref for the specified global_task_parser based on the runtime state in my_call_activity_task
        """

    def get_absolute_global_file_id(self, filename):
        """
        Return an absolute identifier for the BPMN file that can be used to save the state of a running workflow instance
        """

    def get_location_and_idref_from_absolute_id(self, absolute_global_task_id):
        """
        Use a previously provided absolute id to locate a global task spec
        """