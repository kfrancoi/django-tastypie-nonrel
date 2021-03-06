from tastypie import fields
from tastypie.fields import (ApiField, 
                             ToOneField, 
                             ToManyField, 
                             ApiFieldError,
                             NOT_PROVIDED,)
from tastypie.bundle import Bundle
from tastypie.utils import dict_strip_unicode_keys

#import logging
#logging.basicConfig(filename='debugAPI.log',level=logging.DEBUG)
#logging.debug('#############################')


class ListField(ApiField):
    """
        Represents a list of simple items - strings, ints, bools, etc. For
        embedding objects use EmbeddedListField in combination with EmbeddedModelField
        instead.
    """
    dehydrated_type     =   'list'

    def dehydrate(self, obj):
        return self.convert(super(ListField, self).dehydrate(obj))

    def convert(self, value):
        if value is None:
            return None
        return value 

class EmbeddedListField(ToManyField):
    """
        Represents a list of embedded objects. It must be used in conjunction
        with EmbeddedModelField.
        Does not allow for manipulation (reordering) of List elements. Use
        EmbeddedCollection instead.
    """
    is_related = False
    is_m2m = False

    def __init__(self, of, attribute, related_name=None, default=NOT_PROVIDED, null=False, blank=False, readonly=False, full=False, unique=False, help_text=None):
        super(EmbeddedListField, self).__init__(to=of, 
                                                 attribute=attribute,
                                                 related_name=related_name,
                                                 # default=default, 
                                                 null=null, 
                                                 # blank=blank, 
                                                 # readonly=readonly, 
                                                 full=full, 
                                                 unique=unique, 
                                                 help_text=help_text)
    def dehydrate(self, bundle):
        if not bundle.obj or not bundle.obj.pk:
            if not self.null:
                raise ApiFieldError("The model '%r' does not have a primary key and can not be d in a ToMany context." % bundle.obj)
            return []
        if not getattr(bundle.obj, self.attribute):
            if not self.null:
                raise ApiFieldError("The model '%r' has an empty attribute '%s' and doesn't all a null value." % (bundle.obj, self.attribute))
            return []
        self.m2m_resources = []
        m2m_dehydrated = []
        # TODO: Also model-specific and leaky. Relies on there being a
        #       ``Manager`` there.
        # NOTE: only had to remove .all()
        for m2m in getattr(bundle.obj, self.attribute):
            m2m_resource = self.get_related_resource(m2m)
            m2m_bundle = Bundle(obj=m2m)
            self.m2m_resources.append(m2m_resource)
            m2m_dehydrated.append(self.dehydrate_related(m2m_bundle, m2m_resource))
        return m2m_dehydrated

    def hydrate(self, bundle):
        return [b.obj for b in self.hydrate_m2m(bundle)]

class DictField(ApiField):
    dehydrated_type     =   'dict'
    
    def dehydrate(self, obj):
        return self.convert(super(DictField, self).dehydrate(obj))

    def convert(self, value):
        if value is None:
            return None

        return value

class EmbeddedModelField(ToOneField):
    """
        Embeds a resource inside another resource just like you would in Mongo.
    """
    is_related = False
    dehydrated_type     =   'embedded'

    def __init__(self, embedded, attribute, null=False, help_text=None):
        '''
            The ``embedded`` argument should point to a ``Resource`` class, NOT
            to a ``Model``. Required.
        '''
        super(EmbeddedModelField, self).__init__(
                                                 to=embedded,
                                                 attribute=attribute,
                                                 null=null,
                                                 full=True,
                                                 help_text=help_text,
                                                )
    def dehydrate(self, obj):
        return super(EmbeddedModelField, self).dehydrate(obj).data

    def hydrate(self, bundle):
        value = super(ToOneField, self).hydrate(bundle)
        if value is None:
            return value

        return self.build_related_resource(value)

    def build_related_resource(self, value):
        """
        Used to ``hydrate`` the data provided. If just a URL is provided,
        the related resource is attempted to be loaded. If a
        dictionary-like structure is provided, a fresh resource is
        created.
        """
        self.fk_resource = self.to_class()
        
        # Try to hydrate the data provided.
        value = dict_strip_unicode_keys(value)
        
        self.fk_bundle = Bundle(data=value)
            
        return self.fk_resource.full_hydrate(self.fk_bundle).obj

class EmbeddedCollection(ToManyField):
    """
        EmbeddedCollection allows for operating on the sub resources
        individually, through the index based collection.
    """
    is_related = False
    is_m2m = False

    def __init__(self, of, attribute, related_name=None, default=NOT_PROVIDED, null=False, blank=False, readonly=False, full=False, unique=False, help_text=None):
        super(EmbeddedCollection, self).__init__(to=of, 
                                                 attribute=attribute,
                                                 related_name=related_name,
                                                 # default=default, 
                                                 null=null, 
                                                 # blank=blank, 
                                                 # readonly=readonly, 
                                                 full=full, 
                                                 unique=unique, 
                                                 help_text=help_text)

    def dehydrate(self, bundle):
        if not bundle.obj or not bundle.obj.pk:
            if not self.null:
                raise ApiFieldError("The model '%r' does not have a primary key and can not be d in a ToMany context." % bundle.obj)
            return []
        if not getattr(bundle.obj, self.attribute):
            if not self.null:
                raise ApiFieldError("The model '%r' has an empty attribute '%s' and doesn't all a null value." % (bundle.obj, self.attribute))
            return []
        self.m2m_resources = []
        m2m_dehydrated = []
        # TODO: Also model-specific and leaky. Relies on there being a
        #       ``Manager`` there.
        # NOTE: only had to remove .all()
        for index, m2m in enumerate(getattr(bundle.obj, self.attribute)):
            m2m.pk = index
            m2m.parent = bundle.obj
            m2m_resource = self.get_related_resource(m2m)
            m2m_bundle = Bundle(obj=m2m)
            self.m2m_resources.append(m2m_resource)
            m2m_dehydrated.append(self.dehydrate_related(m2m_bundle, m2m_resource))
        return m2m_dehydrated

    def hydrate(self, bundle):
        return [b.obj for b in self.hydrate_m2m(bundle)]

    @property
    def to_class(self):
        base = super(EmbeddedCollection, self).to_class
        return lambda: base(self._resource(), self.instance_name)

class ForeignKeyList(ToManyField):
    """
    """
    is_related = False
    is_m2m = False
    
    def __init__(self, of, attribute, related_name=None, default=NOT_PROVIDED, null=False, blank=False, readonly=False, full=True, unique=False, help_text=None):
        super(ForeignKeyList, self).__init__(to=of, 
                                                 attribute=attribute,
                                                 related_name=related_name,
                                                 # default=default, 
                                                 null=null, 
                                                 # blank=blank, 
                                                 # readonly=readonly, 
                                                 full=full, 
                                                 unique=unique, 
                                                 help_text=help_text)
    
    def dehydrate_related(self, bundle, related_resource):
        return related_resource.full_dehydrate(bundle)
        
    def dehydrate(self, bundle):
        #1) Check limit cases
        if not bundle.obj or not bundle.obj.pk:
            if not self.null:
                raise ApiFieldError("The model '%r' does not have a primary key and can not be d in a ToMany context." % bundle.obj)
            return []
        if not getattr(bundle.obj, self.attribute, None):
            if not self.null:
                raise ApiFieldError("The model '%s' has an empty attribute '%s' and doesn't allow a null value." % (bundle.obj, self.attribute))
            return []
        
        self.foreign_resources = []
        foreign_dehydrated = []
        
        #2) Get foreign list
        foreignKeyList = getattr(bundle.obj, self.attribute)
        
        for index, foreign in enumerate(foreignKeyList):
            foreign_resource = self.get_related_resource(foreign)
            #TO FIX : Choose the right action depending on the Full attribute
            foreign_bundle = Bundle(obj=foreign_resource.obj_get(id=foreign_resource.instance), request=bundle.request)
            foreign_dehydrated.append(self.dehydrate_related(foreign_bundle, foreign_resource))
        
        return foreign_dehydrated
    
    def hydrate(self, bundle):
        hydrateList = []
        
        for b in self.hydrate_m2m(bundle):
            b.obj.save()
            hydrateList.append(b.obj.id)
        
        return hydrateList
    
    def build_related_resource(self, value, request=None, related_obj=None, related_name=None):
        """
        Used to ``hydrate`` the data provided. If just a URL is provided,
        the related resource is attempted to be loaded. If a
        dictionary-like structure is provided, a fresh resource is
        created.
        """
        self.fk_resource = self.to_class()
        
        # Try to hydrate the data provided.
        value = dict_strip_unicode_keys(value)
        
        self.fk_bundle = Bundle(data=value)
            
        return self.fk_resource.full_hydrate(self.fk_bundle)
