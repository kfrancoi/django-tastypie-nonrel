from django.conf.urls.defaults import url
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.core.urlresolvers import reverse, get_script_prefix, Resolver404, resolve
from tastypie.resources import ModelResource
from tastypie.http import *
from tastypie.utils import trailing_slash, dict_strip_unicode_keys
from tastypie.exceptions import ImmediateHttpResponse, NotFound
from tastypie.bundle import Bundle
from fields import EmbeddedCollection, ForeignKeyList, EmbeddedModelField, EmbeddedListField

#import logging
#logging.basicConfig(filename='debugAPI.log',level=logging.DEBUG)
#logging.debug('#############################')

class MongoResource(ModelResource):
    """Minor enhancements to the stock ModelResource to allow subresources."""
    
    def remove_api_resource_names(self, url_dict):
        kwargs_subset = url_dict.copy()

        for key in ['api_name', 'resource_name', 'subresource', 'attribute', 'request_type']:
            try:
                del(kwargs_subset[key])
            except KeyError:
                pass
        
        return kwargs_subset
    
    def dispatch_subresource(self, request, subresource_name, **kwargs):
        field = self.fields[subresource_name]
        resource = field.to_class()

        request_type = kwargs.pop('request_type')
        
        kwargs['id'] = kwargs['pk']
        kwargs['attribute'] = subresource_name
        kwargs['subresource'] = resource

        return self.dispatch(request_type, request, **kwargs)

    def get_detail(self, request, **kwargs):
        """
        Returns a single serialized resource.

        Calls ``cached_obj_get/obj_get`` to provide the data, then handles that result
        set and serializes it.

        Should return a HttpResponse (200 OK).
        """
        try:
            obj = self.cached_obj_get(request=request, **self.remove_api_resource_names(kwargs))
        except ObjectDoesNotExist:
            return HttpNotFound()
        except MultipleObjectsReturned:
            return HttpMultipleChoices("More than one resource is found at this URI.")

        bundle = self.build_bundle(obj=obj, request=request)
        bundle = self.full_dehydrate(bundle)
        bundle = self.alter_detail_data_to_serialize(request, bundle)
        
        #Hack to filter down the result of only a part of the object is asked 
        if 'attribute' in kwargs:
            bundle.data = dict({'objects' : bundle.data[kwargs['attribute']]})
        
        return self.create_response(request, bundle.data)
    
    def post_detail(self, request, **kwargs):
        """
        Creates a new subcollection of the resource under a resource.

        This is not implemented by default because most people's data models
        aren't self-referential.

        If a new resource is created, return ``HttpCreated`` (201 Created).
        """
        
        #1) Get the main resource object
        try:
            obj = self.cached_obj_get(request=request, **self.remove_api_resource_names(kwargs))
        except ObjectDoesNotExist:
            return HttpNotFound()
        except MultipleObjectsReturned:
            return HttpMultipleChoices("More than one resource is found at this URI.")
        
        #2) Create or get the subobject with the data in the bundle
        deserialized = self.deserialize(request, request.raw_post_data, format=request.META.get('CONTENT_TYPE', 'application/json'))
        deserialized = self.alter_deserialized_detail_data(request, deserialized)
        ## TO FIX: Choice here!  either we create a new object based on the POST request data or we try to get an existing object???
        ## --> by default, we create a new object!
        bundle = self.build_bundle(data=dict_strip_unicode_keys(deserialized), request=request)
        kwargs.pop('id')
        kwargs.pop('pk')
        updated_bundle = kwargs['subresource'].obj_create(bundle, request=request, **self.remove_api_resource_names(kwargs)) #TO FIX : Tend to create an object with the parent ID
        location = kwargs['subresource'].get_resource_uri(updated_bundle)
        
        #3) Add subobject or subobject ID to the main object
        if isinstance(self.fields[kwargs['attribute']], ForeignKeyList):
            getattr(obj, kwargs['attribute']).append(updated_bundle.obj.id)
        else :
            getattr(obj, kwargs['attribute']).append(updated_bundle.obj)
        obj.save()
        
        
        if not self._meta.always_return_data:
            return HttpCreated(location=location)
        else:
            updated_bundle = self.full_dehydrate(updated_bundle)
            updated_bundle = self.alter_detail_data_to_serialize(request, updated_bundle)
            return self.create_response(request, updated_bundle, response_class=http.HttpCreated, location=location)
    
    def base_urls(self):
        base = super(MongoResource, self).base_urls()

        embedded = ((name, obj) for name, obj in self.fields.items() if isinstance(obj, (EmbeddedCollection, EmbeddedListField, EmbeddedModelField, ForeignKeyList)))
        
        embedded_urls = []

        for name, obj in embedded:
            embedded_urls.extend([
                url(r"^(?P<resource_name>%s)/(?P<pk>\w[\w-]*)/(?P<subresource_name>%s)%s$" %
                    (self._meta.resource_name, name, trailing_slash()), self.wrap_view('dispatch_subresource'),
                    {'request_type': 'detail'},
                    name='api_dispatch_subresource_list'),

#                url(r"^(?P<resource_name>%s)/(?P<pk>\w[\w-]*)/(?P<subresource_name>%s)/(?P<index>\w[\w-]*)%s$" %
#                    (self._meta.resource_name, name, trailing_slash()),
#                    self.wrap_view('dispatch_subresource'),
#                    {'request_type': 'detail'},
#                    name='api_dispatch_subresource_detail')
                ])
        
        return embedded_urls + base
    
    def get_via_uri(self, uri, request=None):
        """
        This pulls apart the salient bits of the URI and populates the
        resource via a ``obj_get``.

        Optionally accepts a ``request``.

        If you need custom behavior based on other portions of the URI,
        simply override this method.
        """
        prefix = get_script_prefix()
        
        chomped_uri = uri

        if prefix and chomped_uri.startswith(prefix):
            chomped_uri = chomped_uri[len(prefix)-1:]

        try:
            view, args, kwargs = resolve(chomped_uri)
        except Resolver404:
            raise NotFound("The URL provided '%s' was not a link to a valid resource." % uri)

        return self.obj_get(request=request, **self.remove_api_resource_names(kwargs))


class MongoListResource(ModelResource):
    """An embedded MongoDB list acting as a collection. Used in conjunction with
       a EmbeddedCollection.
    """
    
    def __init__(self, parent=None, attribute=None, api_name=None):
        self.parent = parent
        self.attribute = attribute
        self.instance = None
        super(MongoListResource, self).__init__(api_name)


    def dispatch(self, request_type, request, **kwargs):
        self.instance = self.safe_get(request, **kwargs)
        return super(MongoListResource, self).dispatch(request_type, request, **kwargs)

    def safe_get(self, request, **kwargs):
        filters = self.remove_api_resource_names(kwargs)
        try:
            del(filters['index'])
        except KeyError:
            pass

        try:
            return self.parent.cached_obj_get(request=request, **filters)
        except ObjectDoesNotExist:
            raise ImmediateHttpResponse(response=HttpGone())
                                    

    def remove_api_resource_names(self, url_dict):
        kwargs_subset = url_dict.copy()

        for key in ['api_name', 'resource_name', 'subresource_name']:
            try:
                del(kwargs_subset[key])
            except KeyError:
                pass
        
        return kwargs_subset

    def get_object_list(self, request):
        if not self.instance:
            return []

        def add_index(index, obj):
            obj.pk = index
            return obj

        return [add_index(index, obj) for index, obj in enumerate(getattr(self.instance, self.attribute))]

    def obj_get_list(self, request=None, **kwargs):
        return self.get_object_list(request)

    def obj_get(self, request=None, **kwargs):
        index = int(kwargs['index'])
        try:
            return self.get_object_list(request)[index]
        except IndexError:
            raise ImmediateHttpResponse(response=HttpGone())

    def obj_create(self, bundle, request=None, **kwargs):
        bundle = self.full_hydrate(bundle)
        getattr(self.instance, self.attribute).append(bundle.obj)
        self.instance.save()
        return bundle

    def obj_update(self, bundle, request=None, **kwargs):
        index = int(kwargs['index'])
        try:
            bundle.obj = self.get_object_list(request)[index]
        except IndexError:
            raise NotFound("A model instance matching the provided arguments could not be found.")
        bundle = self.full_hydrate(bundle)
        new_index = int(bundle.data['id'])
        lst = getattr(self.instance, self.attribute)
        lst.pop(index)
        lst.insert(new_index, bundle.obj)
        self.instance.save()
        return bundle

    def obj_delete(self, request=None, **kwargs):
        index = int(kwargs['index'])
        self.obj_get(request, **kwargs)
        getattr(self.instance, self.attribute).pop(index)
        self.instance.save()

    def obj_delete_list(self, request=None, **kwargs):
        setattr(self.instance, self.attribute, [])
        self.instance.save()

    def put_detail(self, request, **kwargs):
        """
        Either updates an existing resource or creates a new one with the
        provided data.
        
        Calls ``obj_update`` with the provided data first, but falls back to
        ``obj_create`` if the object does not already exist.
        
        If a new resource is created, return ``HttpCreated`` (201 Created).
        If an existing resource is modified, return ``HttpAccepted`` (204 No Content).
        """
        deserialized = self.deserialize(request, request.raw_post_data, format=request.META.get('CONTENT_TYPE', 'application/json'))
        bundle = self.build_bundle(data=dict_strip_unicode_keys(deserialized))
        self.is_valid(bundle, request)
        
        try:
            updated_bundle = self.obj_update(bundle, request=request, **kwargs)
            return HttpAccepted()
        except:
            updated_bundle = self.obj_create(bundle, request=request, **kwargs)
            return HttpCreated(location=self.get_resource_uri(updated_bundle))


    def get_resource_uri(self, bundle_or_obj):
        if isinstance(bundle_or_obj, Bundle):
            obj = bundle_or_obj.obj
        else:
            obj = bundle_or_obj


        kwargs = {
            'resource_name': self.parent._meta.resource_name,
            'subresource_name': self.attribute
        }
        if self.instance:
            kwargs['pk'] = self.instance.pk


        kwargs['index'] = obj.pk


        if self._meta.api_name is not None:
            kwargs['api_name'] = self._meta.api_name

        ret = self._build_reverse_url('api_dispatch_subresource_detail',
                                       kwargs=kwargs)

        return ret
            
