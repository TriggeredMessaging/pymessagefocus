pymessagefocus
==============

Import and create an instance of the API wrapper which is built around xmlrpclib. Note that authentication errors will not surface until calls are made.
```
>>> from pymessagefocus import *
>>> MessageFocusClient
<class 'pymessagefocus.pymessagefocus.MessageFocusClient'>
>>> messagefocus = MessageFocusClient('organisation', 'username', 'password')
>>> messagefocus
<pymessagefocus.pymessagefocus.MessageFocusClient object at 0x7f13cbfc2050>
>>>

```

Add contact with core and data table properties to list with id 2 and core table with id 1. The data table property is the one marked as 4.field where 4 is the data table id and field is the field name.
```
>>> messagefocus.add_contact_to_list(1,
                                     2, {'email': 'person@example.com',
                                         'title': 'Mr',
                                         '4.field': 'meh'})
{'sucess': True, 'results': [{'message': 'Successfully associated', 'contact_id': 45}]}
```

Retrieve data from the core table with the id 1 for person@example.com. Note that this does not include the data table fields.
```
>>> messagefocus.get_core_data_for_email_address(1, 'person@example.com')
{'results': [{'first_name': '',
              'surname': '',
              'title': 'Mr',
              'email': 'person@example.com',
              'id': 45,
              'job_title': ''}],
 'success': True}
```

Send a transactional email to a person (must exist in the core table specified by the core table id).
```
>>> messagefocus.transactional(1, 1, 'person@example.com', {})
{'results': [{'message': 'Sent', 'value': 1}], 'success': True}
```
