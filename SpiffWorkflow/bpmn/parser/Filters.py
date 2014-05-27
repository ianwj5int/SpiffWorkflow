__author__ = 'matth'

from SpiffWorkflow.bpmn.parser.util import *
from SpiffWorkflow.bpmn.parser.ValidationException import ValidationException

SIGNAVIO_NS='http://www.signavio.com'

class Filter(object):
    def filter(self, bpmn, filename):
        """
        Do some kind of processing of the BPMN content and (if need be) raise a ValidationException
        """

class CheckForDisconnectedBoundaryEvents(Filter):

    def filter(self, bpmn, filename):
        #signavio sometimes disconnects a BoundaryEvent from it's owning task
        #They then show up as intermediateCatchEvents without any incoming sequence flows
        xpath = xpath_eval(bpmn)
        for catch_event in xpath('.//bpmn:intermediateCatchEvent'):
            incoming = xpath('.//bpmn:sequenceFlow[@targetRef="%s"]' % catch_event.get('id'))
            if not incoming:
                raise ValidationException('Intermediate Catch Event has no incoming sequences. This might be a Boundary Event that has been disconnected.',
                node=catch_event, filename=filename)

class SignavioFixCallActivities(Filter):

    def __init__(self, processes_ids_and_names):
        """
        processes_ids_and_names is a list of tuples - (idref, name)
        """
        self.processes_ids_and_names = processes_ids_and_names

    def filter(self, bpmn, filename):
        """
        Signavio produces slightly invalid BPMN for call activity nodes... It is supposed to put a reference to the id of the called process
        in to the calledElement attribute. Instead it stores a string (which is the name of the process - not its ID, in our interpretation)
        in an extension tag.

        This code gets the name of the 'subprocess reference', finds a process with a matching name, and sets the calledElement attribute
        to the id of the process.

        """
        for node in xpath_eval(bpmn)(".//bpmn:callActivity"):
            calledElement = node.get('calledElement', None)
            if not calledElement:
                signavioMetaData = xpath_eval(node, extra_ns={'signavio':SIGNAVIO_NS})('.//signavio:signavioMetaData[@metaKey="entry"]')
                if not signavioMetaData:
                    raise ValidationException('No Signavio "Subprocess reference" specified.', node=node, filename=filename)
                subprocess_reference = one(signavioMetaData).get('metaValue')
                matches = []
                for idref, name in self.processes_ids_and_names:
                    if (name or idref) == subprocess_reference:
                        matches.append(idref)
                if not matches:
                    raise ValidationException("No matching process definition found for '%s'." % subprocess_reference, node=node, filename=filename)
                if len(matches) != 1:
                    raise ValidationException("More than one matching process definition found for '%s'." % subprocess_reference, node=node, filename=filename)

                node.set('calledElement', matches[0])