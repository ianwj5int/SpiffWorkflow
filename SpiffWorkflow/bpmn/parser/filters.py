__author__ = 'matth'

from SpiffWorkflow.bpmn.parser.util import *
from SpiffWorkflow.bpmn.parser.ValidationException import ValidationException
import os

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

class EclipseConvertAnchorTypeCalledElementIdsToQNames(Filter):
    """
    This filter should be run before the EclipseConvertAbsolutePlatformImportsToRelativePaths one
    """

    def __init__(self):
        pass

    def filter(self, bpmn, filename):
        location_to_namespace_map = {}

        for bpmn_import in xpath_eval(bpmn)('.//bpmn:import[@importType="http://www.omg.org/spec/BPMN/20100524/MODEL"]'):
            location_to_namespace_map[bpmn_import.get('location')] = bpmn_import.get('namespace')

        for node in xpath_eval(bpmn)(".//bpmn:callActivity"):
            calledElement = node.get('calledElement', None)
            assert calledElement
            for location, namespace in location_to_namespace_map.iteritems():
                if calledElement.startswith(location+'#'):
                    rev_map = dict((value, key) for key, value in node.ns_map.iteritems())
                    assert namespace in rev_map
                    calledElement = "%s:%s" % (rev_map[namespace], calledElement[len(location)+1:])
                    node.set('calledElement', calledElement)
                    break

class EclipseConvertAbsolutePlatformImportsToRelativePaths(Filter):
    def __init__(self, platform_roots):
        """
        platform_roots is a dictionary mapping from platform root folders to matching local disk paths
        """
        self.platform_roots = platform_roots

    def filter(self, bpmn, filename):
        filename = os.path.abspath(filename)
        for bpmn_import in xpath_eval(bpmn)('.//bpmn:import'):
            location = bpmn_import.get('location')
            converted, location = self._convert_location(filename, location)
            bpmn_import.set('location', location)

    def _convert_location(self, filename, location):
        if location.startswith('platform:/resource/'):
            for root, local in self.platform_roots.iteritems():
                if location.startswith(root):
                    target = os.path.abspath(os.path.join(local, location[len(root)+1:]))
                    location = os.path.relpath(target, os.path.dirname(filename))
                    return True, location
        return False, location