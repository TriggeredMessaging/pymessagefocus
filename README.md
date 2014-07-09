pymessagefocus
==============

Import and create an instance of the API wrapper which is built around xmlrpclib. Note that authentication errors will not surface until calls are made.
```python
>>> from pymessagefocus import *
>>> MessageFocusClient
<class 'pymessagefocus.pymessagefocus.MessageFocusClient'>
>>> messagefocus = MessageFocusClient('organisation', 'username', 'password')
>>> messagefocus
<pymessagefocus.pymessagefocus.MessageFocusClient object at 0x7f13cbfc2050>
```
==========

**Add contact to list**

Add contact with core and data table properties and associate it with a list. Data table fields are identified by putting the data table id in front of the field name.
```python
core_table_id = 1
list_id = 2
email_address = 'person@example.com'
contact_data = {'email': email_address,
                'title': 'Mr',
                '4.field': 'value'}

messagefocus.add_contact_to_list(core_table_id,
                                 list_id,
                                 contact_data)
```
==========

**Get contact**

Using either email address or contact id. Note that this does not include the data table fields.
```python
core_table_id = 1
email_address = 'person@example.com'
messagefocus.get_core_data_for_email_address(core_table_id,
                                             email_address)
```
```python
contact_id = 1
messagefocus.get_core_data_for_contact_id(contact_id)
```
==========

**Send transactional message**

The person identified by the email address must exist in the core table identified by core_table_id
```python
core_table_id = 1
campaign_id = 1
email_address = 'person@example.com'
transaction_data = {}
messagefocus.transactional(core_table_id,
                           campaign_id,
                           email_addres,
                           {})
```
==========

**Get lists and tables**
```python
messagefocus.get_lists()
```
```python
messagefocus.get_data_tables()
```
```python
messagefocus.get_core_tables()
```
