import unittest

from django.test import TestCase
from django.http import HttpRequest
from django.core.urlresolvers import reverse


from django.test import TestCase
import settings

try:
    import json
except ImportError:
    import simplejson as json

def print_resp(resp):
   if not resp.content:
       return
   try:
       deserialized = json.loads(resp.content)
       if 'error_message' in deserialized.keys():
           print "ERROR: ", deserialized.get('error_message', '')
           print "TRACEBACK: ", deserialized.get('traceback', '')
       print json.dumps(deserialized, indent=4)
   except:
       print "resp is not json: ", resp
############################################
# LISTS
############################################
class ListFieldTest(TestCase):
    # fixtures = ['list_field_test.json', 'dict_field_test.json']

    def setUp(self):
        from django.conf import settings; settings.DEBUG = True 
        from models import ListFieldTest, DictFieldTest
        l = ListFieldTest.objects.create(
                                         list=[1,2,3],
                                         intlist=[1,2,3],
                                        )
        l = ListFieldTest.objects.create(
                                         list=[1.0,2.0,3.0],
                                         intlist=[1.0,2.0,3.0],
                                        )
        l = ListFieldTest.objects.create(
                                         list=[1,2,3],
                                         intlist=['1','2','3'],
                                        )

    def test_get(self):
        resp = self.client.get('/api/v1/listfieldtest/',
                               content_type='application/json') 
        self.assertEqual(resp.status_code, 200)
        deserialized = json.loads(resp.content)

        os = deserialized['objects']
        self.assertEqual(len(os), 3)
        
        self.assertEqual(os[0]['intlist'], [1,2,3])
        self.assertEqual(os[0]['list'], ['1','2','3'])

        # Objects get transformed to the underlying type of the list
        self.assertEqual(os[1]['intlist'], [1,2,3])
        

    def test_post(self):
        post_data = '{"list":["1", "2"], "intlist":[1,2]}'
        resp = self.client.post('/api/v1/listfieldtest/',
                                data = post_data,
                                content_type = 'application/json'
                               )

        self.assertEqual(resp.status_code, 201)

        resp = self.client.get('/api/v1/listfieldtest/', 
                               content_type='application/json') 
        self.assertEqual(resp.status_code, 200)

        deserialized = json.loads(resp.content)
        os = deserialized['objects']
        self.assertEqual(len(os), 4)
        self.assertEqual(os[3]['intlist'], [1,2])
        self.assertEqual(os[3]['list'], ['1','2'])

    def test_put(self):
        resp = self.client.get('/api/v1/listfieldtest/',
                               content_type='application/json') 
        self.assertEqual(resp.status_code, 200) 
        
        deserialized = json.loads(resp.content)
        os = deserialized['objects']
        l = os[0]
        l['list'] = [4,5]
        location = l['resource_uri']
        put_data = json.dumps(l)

        resp = self.client.put(location,
                               data=put_data,
                               content_type='application/json')
        self.assertEqual(resp.status_code, 204) 
        
        # make sure the update happened
        resp = self.client.get('/api/v1/listfieldtest/',
                               content_type='application/json') 
        self.assertEqual(resp.status_code, 200) 

        deserialized = json.loads(resp.content)
        l = deserialized['objects'][0]
        # the list is of Charfield
        self.assertEquals(l['list'], ['4','5'])
        
        resp = self.client.get(location,
                               content_type='application/json')
         
        deserialized = json.loads(resp.content)
        self.assertEqual(deserialized['list'], ['4', '5'])

    def test_delete(self):
        resp = self.client.get('/api/v1/listfieldtest/',
                               content_type='application/json') 
        self.assertEqual(resp.status_code, 200) 
        
        deserialized = json.loads(resp.content)
        os = deserialized['objects']
        old_len = len(os)
        location = os[0]['resource_uri']

        resp = self.client.delete(location,
                                  content_type='application/json')

        self.assertEquals(resp.status_code, 204)

        # make sure it's gone
        resp = self.client.get('/api/v1/listfieldtest/',
                               content_type='application/json') 
        self.assertEqual(resp.status_code, 200) 
        deserialized = json.loads(resp.content)
        os = deserialized['objects']  
        self.assertEquals(len(os), old_len - 1)
        
############################################
# EMBEDDED LISTS
############################################
        
class EmbeddedListFieldTest(TestCase):
    # fixtures = ['list_field_test.json', 'dict_field_test.json']

    def setUp(self):
        from django.conf import settings; settings.DEBUG = True
        from models import EmbeddedListFieldTest, PersonTest
        p       = PersonTest(name="andres")
        p1      = PersonTest(name="arman")
        self.l       = EmbeddedListFieldTest.objects.create()
        self.l.list.append(p)
        self.l.save()
        self.l.list.append(p1)
        self.l.save()

    def test_get(self):
        resp = self.client.get('/api/v1/embeddedlistfieldtest/',
                               content_type='application/json') 

        self.assertEqual(resp.status_code, 200)
        deserialized = json.loads(resp.content)
        os = deserialized['objects']
        self.assertEqual(len(os), 1)
        self.assertEqual(os[0]['list'][0]['name'], 'andres')
    
    def test_get_nested(self):
        """
            This test try to access only a child resource of a parent resource
        """
        resp = self.client.get('/api/v1/embeddedlistfieldtest/'+self.l.id+'/list/', content_type='application/json')
        deserialized = json.loads(resp.content)
        os = deserialized['objects']
        
        self.assertEqual(len(os), 2)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(os[0]['name'], 'andres')
        self.assertEqual(os[1]['name'], 'arman')

    def test_post(self):
        post_data = '{"list":[{"name":"evan"}, {"name":"ethan"}]}'
        resp = self.client.post('/api/v1/embeddedlistfieldtest/',
                                data = post_data,
                                content_type = 'application/json'
                               )
        self.assertEqual(resp.status_code, 201)
        
        location = resp['location']

        resp = self.client.get('/api/v1/embeddedlistfieldtest/',
                               content_type='application/json')
        self.assertEqual(resp.status_code, 200)

        deserialized = json.loads(resp.content)
        os = deserialized['objects']
        self.assertEqual(len(os), 2)
        self.assertEqual(os[1]['list'][0]['name'], 'evan')

    def test_post_nested(self):
        """
            Try to post a new resource nested inside the main object
        """
        post_data = '{"name":"Francois"}'
        resp = self.client.post('/api/v1/embeddedlistfieldtest/'+self.l.id+'/list/',
                       data=post_data,
                       content_type='application/json',
                       )
        self.assertEqual(resp.status_code, 201)
        
        #make sure it's there
        resp = self.client.get('/api/v1/embeddedlistfieldtest/'+self.l.id+'/list/',
                       content_type='application/json',
                       )
        self.assertEqual(resp.status_code, 200)
        deserialized = json.loads(resp.content)
        os = deserialized['objects']
        self.assertEqual(len(os), 3)
        self.assertEqual(os[0]['name'], 'andres')
        self.assertEqual(os[1]['name'], 'arman')
        self.assertEqual(os[2]['name'], 'Francois')
            

    def test_put(self):
        resp = self.client.get('/api/v1/embeddedlistfieldtest/',
                               content_type='application/json',
                               )

        deserialized = json.loads(resp.content)
        p = deserialized['objects'][0]
        p['list'][0]['name'] = "philip"
        location = p['resource_uri']
        # submit completely new data
        put_data = '{"list":[{"name":"evan"}, {"name":"ethan"}]}'

        resp = self.client.put(location,
                               data=put_data,
                               content_type='application/json',
                              )
        self.assertEquals(resp.status_code, 204)

        resp = self.client.get(location,
                               content_type='application/json',
                               )
        deserialized = json.loads(resp.content)

        self.assertEqual(len(deserialized['list']), 2)
        self.assertEqual(deserialized['list'][0]['name'], 'evan')
        self.assertEqual(deserialized['list'][1]['name'], 'ethan')
        

    def test_delete(self):
        resp = self.client.get('/api/v1/embeddedlistfieldtest/',
                               content_type='application/json',
                               )

        deserialized = json.loads(resp.content)
        location = deserialized['objects'][0]['resource_uri'] 
        resp = self.client.delete(location,
                                  content_type='application/json')
        self.assertEqual(resp.status_code, 204)
        # make sure it's actually gone
        resp = self.client.get('/api/v1/embeddedlistfieldtest/',
                               content_type='application/json',
                               )
        deserialized = json.loads(resp.content)
        # boom
        self.assertEqual(len(deserialized['objects']), 0)
        
        
############################################
# DICTS
############################################
class DictFieldTest(TestCase):

    def setUp(self):
        from django.conf import settings; settings.DEBUG = True
        from models import ListFieldTest, DictFieldTest
        self.location = '/api/v1/dictfieldtest/'
        l = DictFieldTest.objects.create(
                                         dict={"1":1, '2':'2',})
        l = DictFieldTest.objects.create(
                                         dict={"1":1, '2':'2', '3':[1,2,3]})
        l = DictFieldTest.objects.create(
                                         dict={"1":1, 
                                               '2':'2', 
                                               'latlon':[1.234, 2.3443],
                                               '3':[1,2,3],
                                               '4':{'1':1},
                                              },
                                        )
        l = DictFieldTest.objects.create(
                                         dict={"1":1,
                                               '2':'2',
                                              })

    def test_get(self):
        resp = self.client.get(self.location, 
                               content_type='application/json') 
        self.assertEqual(resp.status_code, 200)

    def test_post(self):
        post_data = '{"dict":{"1":1, "2":"2", "3":[1,2,3], "4":{"1":1}}}'
        resp = self.client.post(self.location,
                                data = post_data,
                                content_type = 'application/json'
                               )

        self.assertEqual(resp.status_code, 201)

        resp = self.client.get(self.location,
                               content_type='application/json') 
        self.assertEqual(resp.status_code, 200)

    def test_put(self):
        resp = self.client.get(self.location,
                               content_type='application/json') 
        self.assertEqual(resp.status_code, 200) 
        deserialized = json.loads(resp.content)
        l = deserialized['objects'][0]
        l['dict'] = {'1':'one', 'two':2}
        location = l['resource_uri']
        put_data = json.dumps(l)

        resp = self.client.put(location,
                               data=put_data,
                               content_type='application/json')
        self.assertEqual(resp.status_code, 204) 
        
        # make sure the update happened
        resp = self.client.get(self.location,
                               content_type='application/json') 
        self.assertEqual(resp.status_code, 200) 
        deserialized = json.loads(resp.content)
        # it's last, because when you delete an element in a list it gets pushed
        # to the back
        l = deserialized['objects'][3]
        self.assertEquals(l['dict'], {'1':'one', 'two':2})
 
    def test_delete(self):
        resp = self.client.get(self.location,
                               content_type='application/json',
                               )

        deserialized = json.loads(resp.content)
        os = deserialized['objects']
        location = os[0]['resource_uri'] 
        num_os = len(os)
        
        resp = self.client.delete(location,
                                  content_type='application/json')
        self.assertEqual(resp.status_code, 204)
        # make sure it's actually gone
        resp = self.client.get(self.location,
                               content_type='application/json',
                               )
        
        deserialized = json.loads(resp.content)
        # boom
        self.assertEqual(len(deserialized['objects']), num_os-1)


############################################
# EMBEDDED
############################################

class EmbededModelFieldTest(TestCase):
    def setUp(self):
        from django.conf import settings; settings.DEBUG = True
        from models import PersonTest, EmbeddedModelFieldTest
        self.m = EmbeddedModelFieldTest.objects.create(
                           customer=PersonTest(name="andres"),
                                                 )
        ms = EmbeddedModelFieldTest.objects.all()

    def test_get(self):
        #request = HttpRequest()
        resp = self.client.get('/api/v1/embeddedmodelfieldtest/',
                               content_type='application/json',
                               )
        self.assertEqual(resp.status_code, 200)
        rj = json.loads(resp.content)
        self.assertEqual(rj['objects'][0]['customer']['name'], 'andres')

    def test_get_nested(self):
        """
            This test try to access only a child resource of a parent resource
        """
        resp = self.client.get('/api/v1/embeddedmodelfieldtest/'+self.m.id+'/customer/', content_type='application/json')
        deserialized = json.loads(resp.content)
        os = deserialized['objects']
        
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(os['name'], 'andres')

    def test_post(self):
        
        #request = HttpRequest()
        post_data = '{"customer":{"name":"san"}}'
        resp = self.client.post('/api/v1/embeddedmodelfieldtest/',
                               data=post_data,
                               content_type='application/json',
                               )
        self.assertEqual(resp.status_code, 201)
        # make sure it's there
        resp = self.client.get('/api/v1/embeddedmodelfieldtest/',
                               content_type='application/json',
                               )
        self.assertEqual(resp.status_code, 200)
        deserialized = json.loads(resp.content)
        self.assertEqual(len(deserialized['objects']), 2)
        self.assertEqual(deserialized['objects'][1]['customer']['name'], 'san')

    def test_put(self):
        resp = self.client.get('/api/v1/embeddedmodelfieldtest/',
                               content_type='application/json',
                               )
        
        logging.debug('[TEST PUT] Object init : %s'%resp.content)
        
        deserialized = json.loads(resp.content)
        p = deserialized['objects'][0]
        p['customer']['name'] = "philip"
        put_data = json.dumps(p)
        
        logging.debug('[TEST PUT] Put data : %s'%put_data)
        logging.debug('[TEST PUT] Location : %s'%p['resource_uri'])
        
        location = p['resource_uri']
        resp = self.client.put(location,
                               data=put_data,
                               content_type='application/json',
                              )
        self.assertEquals(resp.status_code, 204)
        
        resp = self.client.get(location,
                               content_type='application/json',
                               )
        
        logging.debug('[TEST PUT] GET PUTTED DATA : %s'%resp.content)
        logging.debug('[TEST PUT] GET PUTTED DATA (deserialized): %s'%json.loads(resp.content))
        logging.debug('[TEST PUT] p : %s'%p)
        deserialized = json.loads(resp.content)

        self.assertEqual(deserialized['customer']['name'],
                         p['customer']['name'])

        resp = self.client.get('/api/v1/embeddedmodelfieldtest/',
                               content_type='application/json',
                               )

        deserialized = json.loads(resp.content)
        self.assertEquals(len(deserialized['objects']), 1)
        p = deserialized['objects'][0]
        self.assertEquals(p['customer']['name'], "philip")

    def test_delete(self):
        resp = self.client.get('/api/v1/embeddedmodelfieldtest/',
                               content_type='application/json',
                               )

        deserialized = json.loads(resp.content)
        location = deserialized['objects'][0]['resource_uri'] 
        resp = self.client.delete(location,
                                  content_type='application/json')
        self.assertEqual(resp.status_code, 204)
        # make sure it's actually gone
        resp = self.client.get('/api/v1/embeddedmodelfieldtest/',
                               content_type='application/json',
                               )
        deserialized = json.loads(resp.content)
        # boom
        self.assertEqual(len(deserialized['objects']), 0)


############################
# EmbeddedCollections
############################

class EmbeddedCollectionFieldTestCase(TestCase):
    def setUp(self):
        from django.conf import settings; settings.DEBUG = True
        from models import PersonTest, EmbeddedCollectionFieldTest
        self.m = EmbeddedCollectionFieldTest.objects.create(
            list=[PersonTest(name="andres"),PersonTest(name="josh")]
            )
        
        ms = EmbeddedCollectionFieldTest.objects.all()

    @property
    def url(self):
        r = lambda name, *args, **kwargs: reverse(name, args=args, kwargs=kwargs)
        return r('api_dispatch_subresource_list',
                 api_name='v1',
                 resource_name='embeddedcollectionfieldtest',
                 pk=self.m.id,
                 subresource_name='list')
        

    def test_get(self):
        #request = HttpRequest()
        resp = self.client.get(self.url,
                               content_type='application/json',
                               )
        self.assertEqual(resp.status_code, 200)
        rj = json.loads(resp.content)
        self.assertEqual(len(rj['objects']), 2)
        self.assertEqual(rj['objects'][0]['name'], 'andres')
        

############################
# ForeignKeyList
############################
import logging
logging.basicConfig(filename='debugTestCases.log',level=logging.DEBUG)
logging.debug('#############################')

class ForeignKeyListTestCase(TestCase):
    def setUp(self):
        from django.conf import settings;settings.DEBUG = True
        from models import PersonTest, ForeignKeyListFieldTest
        self.p1       = PersonTest.objects.create(name="Kevin")
        self.p2       = PersonTest.objects.create(name="Gwen")
        self.l        = ForeignKeyListFieldTest.objects.create()
        self.l.list.append(self.p1.id)
        self.l.save()
        self.l.list.append(self.p2.id)
        self.l.save()
        
        
    
    @property
    def url(self):
        r = lambda name, *args, **kwargs: reverse(name, args=args, kwargs=kwargs)
        return r('api_dispatch_subresource_list',
                 api_name='v1',
                 resource_name='foreignkeylistfieldtest',
                 pk=self.l.id,
                 subresource_name='list')
    
    def test_get(self):
        #request = HttpRequest()
        #logging.debug("URL : %s"%self.url)
        #resp = self.client.get(self.url, content_type='application/json')
        resp = self.client.get('/api/v1/foreignkeylistfieldtest/', content_type='application/json')
        
        deserialized = json.loads(resp.content)
        os = deserialized['objects']
        self.assertEqual(len(os), 1)
        
        self.assertEqual(resp.status_code, 200)
        logging.debug("resp Content : %s" %resp.content)
        rj = json.loads(resp.content)
        os = rj['objects'][0]
        self.assertEqual(len(os['list']),2)
        self.assertEqual(os['list'][0]['name'], 'Kevin')
    
    def test_get_nested(self):
        """
            This test try to access only a child resource of a parent resource
        """
        resp = self.client.get('/api/v1/foreignkeylistfieldtest/'+self.l.id+'/list/', content_type='application/json')
        deserialized = json.loads(resp.content)
        os = deserialized['objects']
        
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(os), 2)
        self.assertEqual(os[0]['name'], 'Kevin')
        self.assertEqual(os[1]['name'], 'Gwen')
    
    def test_post_new(self):
        logging.debug("Start POST test")
        #post_data = '{"list":["/api/v1/persontest/'+self.p1.id+'"]}'
        post_data = '{"list":[{"name":"nivek"},{"name":"newg"}]}'
        resp = self.client.post('/api/v1/foreignkeylistfieldtest/',
                               data=post_data,
                               content_type='application/json',
                               )
        logging.debug("Response from POST : %s"%resp)
        self.assertEqual(resp.status_code, 201)
        
        # make sure it's there
        #1) Get the newly create resource uri
        resp = self.client.get('/api/v1/foreignkeylistfieldtest/',
                               content_type='application/json',
                               )
        self.assertEqual(resp.status_code, 200)
        deserialized = json.loads(resp.content)
        self.assertEqual(len(deserialized['objects']), 2)
        new_uri = deserialized['objects'][1]['resource_uri']
        resp = self.client.get(new_uri,
                       content_type='application/json',
                       )
        self.assertEqual(resp.status_code, 200)
        #2) Check it correspond to the data added
        deserialized = json.loads(resp.content)
        self.assertEqual(deserialized['list'][0]['name'], 'nivek')
        self.assertEqual(deserialized['list'][1]['name'], 'newg')
    
    def test_post_existing(self):
        #Add related resource already existing somewhere in the db
        #TO FIX!
        post_data = '{"list":[{"name":"Kevin"},{"name":"Gwen"}]}'
        resp = self.client.post('/api/v1/foreignkeylistfieldtest/',
                               data=post_data,
                               content_type='application/json',
                               )
        self.assertEqual(resp.status_code, 201)
        
        # make sure it's there
        resp = self.client.get('/api/v1/foreignkeylistfieldtest/',
                               content_type='application/json',
                               )
        self.assertEqual(resp.status_code, 200)
        deserialized = json.loads(resp.content)
        self.assertEqual(len(deserialized['objects']), 2)
        self.assertEqual(deserialized['objects'][1]['list'][0], self.p1.id)
        self.assertEqual(deserialized['objects'][1]['list'][1], self.p2.id)
    
    def test_post_nested(self):
        """
            Try to post a new resource nested inside the main object
        """
        post_data = '{"name":"Francois"}'
        resp = self.client.post('/api/v1/foreignkeylistfieldtest/'+self.l.id+'/list/',
                       data=post_data,
                       content_type='application/json',
                       )
        self.assertEqual(resp.status_code, 201)
        
        #make sure it's there
        resp = self.client.get('/api/v1/foreignkeylistfieldtest/'+self.l.id+'/list/',
                       content_type='application/json',
                       )
        self.assertEqual(resp.status_code, 200)
        deserialized = json.loads(resp.content)
        os = deserialized['objects']
        self.assertEqual(len(os), 3)
        self.assertEqual(os[0]['name'], 'Kevin')
        self.assertEqual(os[1]['name'], 'Gwen')
        self.assertEqual(os[2]['name'], 'Francois')