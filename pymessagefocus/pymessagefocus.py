import xmlrpclib
import version
import re

class MessageFocusClient(object):
    version = version.version

    ERROR_CODES = {# MessageFocus undeclared / unpublished fault codes:
                   '200': 'Request could not be processed. %s.',
                   # MessageFocus declared / published fault codes: (reserves the range 100-400)
                   '101': ("System temporarily unavailable."
                           "You may wish to repeat your request again later."),
                   '102': 'The system is currently disabled.',
                   '201': 'Request was malformed or not understood.',
                   '202': 'The namespace you called a method on does not exist.',
                   '203': 'The method you called does not exist.',
                   '204': ("Argument invalid or of incorrect type, e.g. you "
                           "have passed a String where a Struct is expected."),
                   '205': ("Operation cannot be performed on this field, "
                           "e.g. you are trying to update an object ID"),
                   '206': ("Unknown or invalid option, e.g. incorrect "
                           "pagination parameters."),
                   '207': 'Object not found. %s.',
                   '208': ("Permission denied for object. The object may exist "
                           "but cannot be accessed by the API user."),
                   '209': 'No user found with that email address',
                   '210': ("The character encoding for your import data is not "
                           "recognised by MessageFocus."),
                   '211': 'A core table field name is not valid.',
                   '301': 'You must be authenticated to use this resource.',
                   '302': 'You are not authorised to perform that operation.',
                   '303': 'Your account is over quota.',
                   '304': 'Your account is making requests too frequently.',
                   '305': 'Your account is currently disabled.',
                   # XML-RPC defined error codes: (reserves the range -32768 -> -32000)
                   '-32700': 'Parse error. Not well formed.',
                   '-32701': 'Parse error. Unsupported encoding.',
                   '-32702': 'Parse error. Invalid character for encoding.',
                   '-32600': 'Server error. Invalid XML-RPC. Not conforming to specification.',
                   '-32601': 'Server error. Requested method not found.',
                   '-32602': 'Server error. Invalid method parameters.',
                   '-32603': 'Server error. Internal XML-RPC error.',
                   '-32500': 'Application error.',
                   '-32400': 'System error.',
                   '-32300': 'Transport error.',
                   # MessageFocusClient fault codes: (reserves the range 4096-8192)
                   '4096': 'Unknown error. Did not recognise fault code or error message. %s.',
                       # Type errors 4100+
                   '4101': 'Invalid input syntax for integer. %s.',
                       # SQL errors 4200+
                   '4201': 'Column does not exist. %s.',
                       # Missing required fields 4300+
                   '4301': 'Missing email field. %s.',
                       # Invalid input parameters and field values 4400+
                   '4401': 'Invalid core table id. %s.',
                   '4402': 'Invalid list id. %s.',
                   '4403': 'Invalid contact id. %s.',
                   '4404': 'Invalid email address. %s.',
                   '4405': 'Invalid ftp address. %s.',
                   '4499': 'Missing necessary input parameters. %s.',
                       # Action required in MessageFocus
                   '4501': 'Campaign has not been published. %s.',
                       # xmlrpclib errors
                   '5101': 'Not authenticated. %s.',
                   '5102': 'Cannot pass None values unless enabled in xmlrpclib.'}

    class Filters:
        TABLE_FILTER = {'name': True, 'id': True}

    class ErrorParsing:
        EXPECTED_INTEGER = re.compile('invalid input syntax for integer: ([^\[]*)')
        COLUMN_DOES_NOT_EXIST = re.compile('column ([^.]+\.[^\s]+) does not exist')
        PERMISSION_OBJECT_ID = re.compile('object_id=([0-9]+)')
        CAMPAIGN_ID_FROM_ADDITIONAL = re.compile('campaign id: ([^,]+),')

    def __init__(self, organisation, username, password):
        self._organisation = organisation
        self._username = username
        self._password = password

        self._url = 'https://%s.%s:%s@app.adestra.com/api/xmlrpc'
        self._api = xmlrpclib.ServerProxy(self._url % (organisation, username, password))
        return

    def error_dictionary(self, error_code, additional_information=None):
        """
        MessageFocusClient.error_dictionary
        ------------------------------------------------
        Given an error code and optionally additional
        information about the error, generate a full error
        dictionary that may be returned as an item in the
        results list of one of our helper functions.
        ------------------------------------------------
        @param  error_code               int
        @param  [additional_information] tuple or str
        @return                          dict {
            'message': str,
            'code':    int
        }
        """
        error_string = MessageFocusClient.ERROR_CODES[str(error_code)]
        if additional_information and '%s' in error_string:
            error_string = error_string % additional_information
        return {'message': error_string, 'code': error_code}

    def parse_exception(self, exception, additional_information=None):
        """
        MessageFocusClient.parse_exception
        ------------------------------------------------
        Attempt to parse the contents of an exception
        thrown from the API call in order to produce a
        more useful cut back error message in dictionary
        form.
        ------------------------------------------------
        @param  exception                Exception
        @param  [additional_information] tuple or str
        @return                          dict {
            'message': str,
            'code':    int
        }
        """
        if isinstance(exception, xmlrpclib.ProtocolError):
            error = {'code': 5101}
            additional_information = 'Organisation: %s, username: %s, password: %s' % (self._organisation,
                                                                                       self._username,
                                                                                       self._password)
            pass
        else:
            error = {'code': exception.__dict__.get('faultCode')}
            error_string = exception.__dict__.get('faultString', exception.message)
            pass


        # Additional information for the error message
        # in the format of a tuple or string to %
        additional_information = additional_information

        # Fault code 200 is undocumented by MessageFocus but frequently
        # used and could mean many things. The full fault string often
        # includes specifics about failed SQL queries and perl modules.
        # This information is rarely useful and should not be visible to
        # begin with for security reasons.
        #
        # Below we attempt to rewrite these errors into shorter more
        # useful error messages using MessageFocusClient.ErrorParsing
        # regular expressions, the MessageFocusClient.ERROR_CODES
        # dictionary and the additional_information variable from above.
        if error['code'] == 200:
            if 'invalid input syntax for integer' in error_string:
                # An example case where this might crop up is if you manage
                # to insert a string value where an integer is expected.
                error['code'] = 4101
                matches = MessageFocusClient.ErrorParsing.EXPECTED_INTEGER.search(error_string)
                if matches:
                    additional_information = ('Input value: %s' % matches.group(1).rstrip(' '))
                    pass
                pass
            elif ('column' in error_string) and ('does not exist' in error_string):
                # This is a SQL error where an invalid table name has somehow
                # made its way in to the query.
                #
                # There are likely many ways of achieving this failure,
                # I have put in place safeguards for some. E.g. attempting to
                # use a non-empty dictionary instead of an integer for the
                # core_table_id.
                error['code'] = 4201
                matches = MessageFocusClient.ErrorParsing.COLUMN_DOES_NOT_EXIST.search(error_string)
                if matches:
                    additional_information = ('Column name: %s' % matches.group(1))
                    pass
                pass
            elif 'Campaign has not been published' in error_string:
                error['code'] = 4501
                # additional information should be set by parameter when this error is possible
                # e.g. MessageFocusClient.transactional
                matches = MessageFocusClient.ErrorParsing.CAMPAIGN_ID_FROM_ADDITIONAL.search(additional_information)
                if matches:
                    additional_information = ('Campaign id: %s' % matches.group(1))
                    pass
                pass
            # If we failed to better identify the error, simply dump the
            # longform fault string into the additional information variable.
            if not additional_information:
                additional_information = (error_string)
                pass
            pass


        if error['code'] == 208:
            # It would appear MessageFocus throws different faultCodes for
            # essentially the same error depending on the parameter.
            # Let's convert 208 to 207 when object_name=campaign.
            if 'object_name=campaign' in error_string:
                error['code'] = 207

                matches = MessageFocusClient.ErrorParsing.CAMPAIGN_ID_FROM_ADDITIONAL.search(additional_information)
                if matches:
                    additional_information = ('Campaign id: %s' % matches.group(1))
                    pass
                pass
            pass

        # If there was no error code in the exception it is possible it
        # came from xmlrpclib, below we attempt to handle as many of
        # those as possible, falling back to the code for an entirely
        # unknown error (4096).
        if not error['code']:
            if 'cannot marshal None' in exception.message:
                error['code'] = 5102
                pass
            else:
                error['code'] = 4096
                pass
            pass

        error['message'] = MessageFocusClient.ERROR_CODES[str(error['code'])]

        if error['code'] in [200, 4096]:
            additional_information = (error_string)
            pass

        if additional_information and '%s' in error['message']:
            error['message'] = error['message'] % additional_information
            pass

        return error

    def filter_results(self, results, filter_dictionary):
        """
        MessageFocusClient.filter_results
        ------------------------------------------------
        Filter a dictionary by a second dictionary which
        ultimately maps desired keys to a boolean value.
        ------------------------------------------------
        @param  results           dict
        @param  filter_dictionary dict
        @return                   dict
        """
        def do_filter(f, k, v, o):
            if not f:
                return o
            if isinstance(f, bool):
                # truthy bool -> keep v
                o[k] = v
            elif isinstance(f, dict):
                # filter keys individually
                o[k] = filter_each(v, f, {})
            return o

        def filter_each(r, f, o):
            if isinstance(r, list):
                o = [filter_each(r[i], f, {}) for i in xrange(len(r))]
            elif isinstance(r, dict):
                for k, v in r.iteritems():
                    do_filter(f.get(k), k, v, o)
            return o or r

        return filter_each(results, filter_dictionary, None)

    def _add_contact_to_core_table(self, core_table_id, contact_data):
        """
        MessageFocusClient._add_contact_to_core_table
        ------------------------------------------------
        Add contact to core table and optionally data tables.
        To provide data for data tables, prefix the field
        name with the data table id, e.g. "2.field_name".
        If successful this method returns a dict s.t. {
            'success': True,
            'results': [{'message': 'Added',
                         'contact_id': contact_id}]
        }
        If an error was encountered it returns a dict s.t. {
            'success': False,
            'results': [@see(MessageFocusClient.parse_exception,
                             MessageFocusClient.error_dictionary)]
        }
        ------------------------------------------------
        @param  core_table_id int
        @param  contact_data  dict
        @return               dict {
            'success': bool,
            'results': list
        }
        """
        if not 'email' in contact_data:
            additional_information = 'Saw fields: %s' % contact_data.keys()
            return {'success': False,
                    'results': [self.error_dictionary(4301, additional_information=additional_information)]}

        email = contact_data['email']
        if (not isinstance(email, basestring)) or (not '@' in email) or (not '.' in email):
            additional_information = 'Field value: %s %s' % (email, type(email))
            return  {'success': False,
                     'results': [self.error_dictionary(4404, additional_information=additional_information)]}

        if not isinstance(core_table_id, int):
            additional_information = 'Input value: %s %s' % (core_table_id, type(core_table_id))
            return {'success': False,
                    'results': [self.error_dictionary(4401, additional_information=additional_information)]}
        try:
            return {'success': True, 'results': [{'message': 'Added', 'contact_id': self._api.contact.create(core_table_id, contact_data)}]}
        except Exception as e:
            additional_information = 'Core table id: %s, contact data: %s' % (core_table_id, contact_data)
            result = self.parse_exception(e, additional_information=additional_information)
            return {'success': False, 'results': [result]}
        pass

    def _associate_contact_with_list(self, contact_id, list_id):
        """
        MessageFocusClient._associate_contact_with_list
        ------------------------------------------------
        Associate a contact_id that is already in the
        system (with core table data) with a list_id for
        marketing (both campaign and transactional sends)
        purposes.
        If successful this method returns a dict s.t. {
            'success': True,
            'results': [{'message':  'Successfully associated' or 'Already associated',
                         'contact_id': contact_id}]
        }
        ------------------------------------------------
        @param  contact_id int
        @param  list_id    int
        @return            dict {
            'success': bool,
            'results': list
        }
        """
        if not isinstance(list_id, int):
            additional_information = 'Input value: %s %s' % (list_id, type(list_id))
            return {'success': False,
                    'results': [self.error_dictionary(4402, additional_information=additional_information)]}
        try:
            # The below call should return 0 or 1 for success
            # and raise an exception otherwise.
            # Any other return value is an unexpected error.
            result = self._api.contact.addList(contact_id, list_id)
            if result in [0, 1]:
                if not result:
                    result = {'message': 'Already associated', 'contact_id': contact_id}
                    pass
                else:
                    result = {'message': 'Successfully associated', 'contact_id': contact_id}
                    pass
                return {'success': True, 'results': [result]}
            else:
                # Unknown error (4096) supply the unrecognised result
                # as additional information to the error message.
                return {'success': False,
                        'results': [self.error_dictionary(4096, additional_information=result)]}
        except Exception as e:
            additional_information = 'Contact id: %s, list id: %s' % (contact_id, list_id)
            result = self.parse_exception(e, additional_information=additional_information)
            return {'success': False, 'results': [result]}
        pass

    def add_contact_to_list(self, core_table_id, list_id, contact_data):
        """
        MessageFocusClient.add_contact_to_list
        ------------------------------------------------
        Add contact to core table if not already there,
        once added make sure the contact id is associated
        with the given list id as well.
        For returned dictionary @see(MessageFocusClient._add_contact_to_core_table,
                                     MessageFocusClient._associate_contact_with_list)
        ------------------------------------------------
        @param  core_table_id int
        @param  list_id       int
        @param  contact_data  dict
        @return               dict {
            'success': bool,
            'results': list
        }
        """
        # The below call will return success with existing contact id in a
        # format identical to a new add if there is an existing contact with
        # the given email address. E.g. {'success': True, 'results': [23]}
        core_table_result = self._add_contact_to_core_table(core_table_id, contact_data)

        if core_table_result.get('success') and len(core_table_result.get('results', [])):
            # The below call will return success with different string values in the
            # results list depending on if there already was an association or if a
            # new one was added. @see(MessageFocusClient._associate_contact_with_list)
            return self._associate_contact_with_list(core_table_result.get('results')[0].get('contact_id'), list_id)
        return core_table_result

    def add_contacts_to_list(self, core_table_id, list_id, data_file_url, csv_column_map, notification_email_address=None):
        """
        MessageFocusClient.add_contacts_to_list
        ------------------------------------------------
        Request an ftp batched contact upload by passing
        a data file url and a field mapping dictionary.
        On success returns a dict like {
            'success': True,
            'results': [{'message': 'Import request received.',
                         'value': 1}]
        }
        If an error was encountered it returns a dict s.t. {
            'success': False,
            'results': [@see(MessageFocusClient.parse_exception,
                             MessageFocusClient.error_dictionary)]
        }
        ------------------------------------------------
        @param  core_table_id              int
        @param  list_id                    int
        @param  data_file_url              str
        @param  csv_column_map             dict
        @param  notification_email_address str
        @return                            dict {
            'success': bool,
            'results': list
        }
        """

        if not isinstance(core_table_id, int):
            additional_information = 'Input value: %s %s' % (core_table_id, type(core_table_id))
            return {'success': False,
                    'results': [self.error_dictionary(4401, additional_information=additional_information)]}

        if not isinstance(list_id, int):
            additional_information = 'Input value: %s %s' % (list_id, type(list_id))
            return {'success': False,
                    'results': [self.error_dictionary(4402, additional_information=additional_information)]}

        if not 'ftp' in data_file_url:
            additional_information = 'Input value: %s %s' % (data_file_url, type(data_file_url))
            return {'success': False,
                    'results': [self.error_dictionary(4405, additional_information=additional_information)]}

        options = {'list_id': list_id,
                   'dedupe_type': 'overwrite',
                   'field_map': csv_column_map,
                   'delete_after_import': False}

        if notification_email_address:
            options['notify_user'] = notification_email_address
            pass
        try:
            result = getattr(self._api.contact, 'import')(core_table_id, data_file_url, options)
            if result in [1]:
                return {'success': True,
                        'results': [{'message': 'Import request received.', 'value': result}]}
        except Exception as e:
            field_names = csv_column_map.keys()
            additional_information = 'Core table id: %s, list id: %s, data file url: %s, attempting to map fields: %s, notifying: %s'
            additional_information = additional_information % (core_table_id,
                                                               list_id,
                                                               data_file_url,
                                                               field_names,
                                                               notification_email_address)
            return {'success': False,
                    'results': [self.parse_exception(e, additional_information=additional_information)]}
        pass

    def get_core_data_for_contact_id(self, contact_id):
        """
        MessageFocusClient.get_core_data_for_contact_id
        ------------------------------------------------
        Search for a contact in the core tables by contact
        id and return a dictionary containing the information
        available in the core table about this contact id
        such as email address and first name.
        On success returns a dict like {
            'success': True,
            'results': [{'email': 'person@example.com',
                         'id': contact_id,
                         ..}]
        }
        If an error was encountered it returns a dict s.t. {
            'success': False,
            'results': [@see(MessageFocusClient.parse_exception,
                             MessageFocusClient.error_dictionary)]
        }
        ------------------------------------------------
        @param  contact_id int
        @return            dict {
            'success': bool,
            'results': list
        }
        """
        if not isinstance(contact_id, int):
            additional_information = 'Input value: %s %s' % (contact_id, type(contact_id))
            return {'success': False,
                    'results': [self.error_dictionary(4403, additional_information=additional_information)]}
        try:
            return {'success': True, 'results': [self._api.contact.get(contact_id)]}
        except Exception as e:
            additional_information = 'Contact id: %s' % contact_id
            return {'success': False,
                    'results': [self.parse_exception(e, additional_information=additional_information)]}
        pass

    def get_core_data_for_email_address(self, core_table_id, email_address):
        """
        MessageFocusClient.get_core_data_for_email_address
        ------------------------------------------------
        Search for a contact in the core tables by email
        address and return a dictionary containing the
        information available in the core table about this
        email address such as contact id and first name.
        On success returns a dict like {
            'success': True,
            'results': [{'email': 'person@example.com',
                         'id': contact_id,
                         ..}]
        }
        If an error was encountered it returns a dict s.t. {
            'success': False,
            'results': [@see(MessageFocusClient.parse_exception,
                             MessageFocusClient.error_dictionary)]
        }
        ------------------------------------------------
        @param  core_table_id int
        @param  email_address str
        @return               dict {
            'success': bool,
            'results': list
        }
        """
        if not isinstance(core_table_id, int):
            additional_information = 'Input value: %s %s' % (core_table_id, type(core_table_id))
            return {'success': False,
                    'results': [self.error_dictionary(4401, additional_information=additional_information)]}

        if not isinstance(email_address, basestring) or (not '@' in email_address) or (not '.' in email_address):
            additional_information = 'Input value: %s %s' % (email_address, type(email_address))
            return {'success': False,
                    'results': [self.error_dictionary(4404, additional_information=additional_information)]}

        try:
            result = self._api.contact.search(core_table_id, {'email': email_address})
            if not len(result):
                additional_information = 'Email address: %s' % email_address
                return {'success': False,
                        'results': [self.error_dictionary(207, additional_information=additional_information)]}
            return {'success': True, 'results': result}
        except Exception as e:
            additional_information = 'Core table id: %s, email address: %s' % (core_table_id, email_address)
            return {'success': False,
                    'results': [self.parse_exception(e, additional_information=additional_information)]}
        pass

    def get_core_tables(self):
        """
        MessageFocusClient.get_core_tables
        ------------------------------------------------
        Get a list of core tables for a return value like {
            'success': True,
            'results': [{'id': int,
                         'name': str}]
        }
        Or if an error was encountered {
            'success': False,
            'results': [@see(MessageFocusClient.parse_exception)]
        }
        ------------------------------------------------
        @return dict {
            'success': bool,
            'results': list
        }
        """
        try:
            return {'success': True,
                    'results': self.filter_results(self._api.coreTable.all(),
                                                   MessageFocusClient.Filters.TABLE_FILTER)}
        except Exception as e:
            return {'success': False, 'results': [self.parse_exception(e)]}
        pass

    def get_data_tables(self):
        """
        MessageFocusClient.get_data_tables
        ------------------------------------------------
        Get a list of data tables for a return value like {
            'success': True,
            'results': [{'id': int,
                         'name': str}]
        }
        Or if an error was encountered {
            'success': False,
            'results': [@see(MessageFocusClient.parse_exception)]
        }
        ------------------------------------------------
        @return dict {
            'success': bool,
            'results': list
        }
        """
        try:
            return {'success': True,
                    'results': self.filter_results(self._api.dataTable.all(),
                                                   MessageFocusClient.Filters.TABLE_FILTER)}
        except Exception as e:
            return {'success': False, 'results': [self.parse_exception(e)]}
        pass

    def get_lists(self):
        """
        MessageFocusClient.get_lists
        ------------------------------------------------
        Get a list of contact lists for a return value like {
            'success': True,
            'results': [{'id': int,
                         'name': str}]
        }
        Or if an error was encountered {
            'success': False,
            'results': [@see(MessageFocusClient.parse_exception)]
        }
        ------------------------------------------------
        @return dict {
            'success': bool,
            'results': list
        }
        """
        try:
            return {'success': True,
                    'results': self.filter_results(self._api.list.all(),
                                                   MessageFocusClient.Filters.TABLE_FILTER)}
        except Exception as e:
            return {'success': False, 'results': [self.parse_exception(e)]}
        pass

    def transactional(self, core_table_id, campaign_id, contact_id=None, email_address=None, transaction_data={}):
        """
        MessageFocusClient.transactional
        ------------------------------------------------
        Send a transactional email (campaign to a single
        email address).
        If successful returns a dictionary like {
            'success': True,
            'results': {
                [{'message': 'Sent',
                  'value': 1}]
            }
        }
        Or if an error was encountered {
            'success': False,
            'results': [@see(MessageFocusClient.parse_exception,
                             MessageFocusClient.get_core_data_for_email_address)]
        }
        ------------------------------------------------
        @param  core_table_id      int
        @param  campaign_id        int
        @param  [contact_id]       int
        @param  [email_address]    str
        @param  [transaction_data] dict
        @return                    dict {
            'success': bool,
            'results': list
        }
        """
        if (not contact_id) and (not email_address):
            additional_information = 'Input values: contact id %s %s, email_address %s %s - must provide one'
            additional_information = additional_information % (contact_id,
                                                               type(contact_id),
                                                               email_address,
                                                               type(email_address))
            return {'success': False,
                    'results': [self.error_dictionary(4499, additional_information=additional_information)]}

        if email_address and (not contact_id):
            core_data = self.get_core_data_for_email_address(core_table_id, email_address)
            if not core_data.get('success'):
                return core_data
            contact_id = core_data.get('results')[0].get('id')

        if not isinstance(contact_id, int):
            additional_information = 'Input value: %s %s' % (contact_id, type(contact_id))
            return {'success': False,
                    'results': [self.error_dictionary(4403, additional_information=additional_information)]}
        try:
            return {'success': True,
                    'results': [{'message': 'Sent',
                                 'value': self._api.contact.transactional(contact_id,
                                                                          campaign_id,
                                                                          transaction_data)}]}
        except Exception as e:
            additional_information = 'Core table id: %s, campaign id: %s, email_address: %s, transaction data: %s'
            additional_information = additional_information % (core_table_id,
                                                               campaign_id,
                                                               email_address,
                                                               transaction_data)
            return {'success': False,
                    'results': [self.parse_exception(e, additional_information=additional_information)]}
        pass
    pass
