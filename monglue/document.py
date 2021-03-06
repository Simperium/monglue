from bson.codec_options import CodecOptions

"""
Exceptions
"""
class DocumentError(Exception):
    """Generic Monglue Document exception"""


class ValidationError(DocumentError):
    """Document vaidation failed"""


"""
Validators
"""
def required(document, field_name):
    return field_name in document

def optional(document, field_name):
    return True

def _validate(klass, document):
    if hasattr(klass, '__collection_fields__'):
        validators = klass.__collection_fields__
        for key in [k for k in document if k != '_id']:
            if key not in validators:
                raise ValidationError('Unknown field: %s' % key)

        for key in validators:
            if not validators[key](document, key):
                raise ValidationError('Validation failed for: %s' % key)

def _strip_class(value):
    if isinstance(value, Document):
        return _strip_class(value.a)
    if type(value) is dict:
        for k, v in value.items():
            value[k] = _strip_class(v)
    elif type(value) is list:
        for i in range(len(value)):
            value[i] = _strip_class(value[i])
    return value

class Document(object):
    @classmethod
    def new(klass, document=None):
        if not document:
            document = {}
        _validate(klass, document)
        c = klass.__database__[klass.__collection_name__]
        _id = c.insert(document)
        return klass(document)

    def __setitem__(self, key, value):
        # pymongo.find as_class applies recursively to documents embedded in result
        self.a[key] = _strip_class(value)

    def __new__(klass, *a, **kw):
        indexes = getattr(klass, '__collection_indexes__', None)
        if indexes:
            for key, options in indexes:
                klass.ensure_index(key, **options)
        return object.__new__(klass)

    def __init__(self, document=None):
        self.a = document or {}
        # it's not intuitive that calling drop on an instance will actually
        # drop the entire collection
        self.drop = self.__drop

    def refresh(self):
        self.a = self.find_one(self.a['_id']).a

    @classmethod
    def find(klass, spec=None):
        return klass\
            .__database__[klass.__collection_name__]\
            .with_options(codec_options=CodecOptions(document_class=klass))\
            .find(spec)

    @classmethod
    def find_one(klass, spec=None):
        return klass\
            .__database__[klass.__collection_name__]\
            .with_options(codec_options=CodecOptions(document_class=klass))\
            .find_one(spec)

    def set(self, document):
        self.a.update(document)
        _validate(self, self.a)
        return self.__database__[self.__collection_name__].update(
            {'_id': self.a['_id']}, {'$set': document})

    def unset(self, document):
        self.a.update(document)
        _validate(self, self.a)
        return self.__database__[self.__collection_name__].update(
            {'_id': self.a['_id']}, {'$unset': document})

    def addToSet(self, document):
        # XXX - this could reuse the pymongo stub code
        for key in document:
            if key not in self.a:
                self.a[key] = []
            self.a[key] = list(set(self.a[key]) | set([document[key]]))
        _validate(self, self.a)
        return self.__database__[self.__collection_name__].update(
            {'_id': self.a['_id']}, {'$addToSet': document})

    def remove(self):
        return self.__database__[self.__collection_name__].remove(
            {'_id': self.a['_id']})

    @classmethod
    def drop(klass):
        return klass.__database__[klass.__collection_name__].drop()

    def __drop(self):
        raise AssertionError('can only be called on a class method')

    @classmethod
    def index_information(klass):
        return klass.__database__[klass.__collection_name__].index_information()

    @classmethod
    def ensure_index(klass, key, **options):
        return klass.__database__[klass.__collection_name__].ensure_index(
            key, **options)

    def __repr__(self):
        return repr(self.a)


class Bind(object):
    def __init__(self, database, *Klasses, **kw):
        self.store = kw.pop('store', self)
        self.__database__ = database
        for Klass in Klasses:
            setattr(self,
                Klass.__name__,
                type(Klass.__name__, (Klass,),
                    {'x': self.store, '__database__': database}))
