import unittest

from monglue.test.test_mongo import PyMongoStub
from monglue.document import Document
from monglue.document import Bind
from monglue.document import required
from monglue.document import optional
from monglue.document import ValidationError


class User(Document):
    __collection_name__ = 'users'
    def truncate_name(self):
        return '%s %s.' % (self['first_name'], self['last_name'][0])


class UserStrict(User):
    __collection_fields__ = {
        'first_name': required,
        'last_name': required,
        'age': optional,
    }


class DoumentTest(unittest.TestCase):
    def _get_database(self):
        db = PyMongoStub()['foo']
        return Bind(db, User, UserStrict)

    def test_new(self):
        db = self._get_database()
        u = db.User.new({'first_name': 'Daniel', 'last_name': 'Hengeveld'})
        self.assertEqual(u.truncate_name(), 'Daniel H.')
        self.assertTrue('_id' in u)

    def test_a(self):
        db = self._get_database()
        data = {'first_name': 'Daniel', 'last_name': 'Hengeveld'}
        u = db.User.new(data)
        self.assertEqual(u.a, data)

    def test_AttributeError(self):
        db = self._get_database()
        data = {'first_name': 'Daniel', 'last_name': 'Hengeveld'}
        u = db.User.new(data)
        self.assertRaises(AttributeError, getattr, u, 'foo')
        try:
            u.foo
        except AttributeError, e:
            self.assertEqual(
                str(e),
                "exceptions.AttributeError: 'User' object has no attribute 'foo'")

    def test_find(self):
        db = self._get_database()
        db.User.new({'first_name': 'Daniel', 'last_name': 'Hengeveld'})
        db.User.new({'first_name': 'Andy', 'last_name': 'Gayton'})
        got = db.User.find()
        got.sort(lambda x,y: cmp(x['first_name'], y['first_name']))
        self.assertEqual(
            [u.truncate_name() for u in got], ['Andy G.', 'Daniel H.'])

    def test_find_one(self):
        db = self._get_database()
        db.User.new({'first_name': 'Daniel', 'last_name': 'Hengeveld'})
        db.User.new({'first_name': 'Andy', 'last_name': 'Gayton'})
        got = db.User.find_one({'first_name': 'Daniel'})
        self.assertEqual(got.truncate_name(), 'Daniel H.')

    def test_remove(self):
        db = self._get_database()
        u = db.User.new({'first_name': 'Ted', 'last_name': 'Burns'})
        u.remove()
        got = db.User.find()
        self.assertEqual(got, [])

    def test_set(self):
        db = self._get_database()
        u = db.User.new({'first_name': 'Ted', 'last_name': 'Burns'})
        _id = u['_id']
        u.set({'first_name': 'Ned'})
        self.assertEqual(
            u, {'_id': _id, 'first_name': 'Ned', 'last_name': 'Burns'})
        self.assertEqual(
            db.User.find(),
            [{'_id': _id, 'first_name': 'Ned', 'last_name': 'Burns'}])

    def test_addToSet(self):
        db = self._get_database()
        u = db.User.new({'first_name': 'Ted', 'last_name': 'Burns'})
        _id = u['_id']

        u.addToSet({'permissions': 'read'})
        self.assertEqual(u, {
                '_id': _id,
                'first_name': 'Ted',
                'last_name': 'Burns',
                'permissions': ['read']})

        u.addToSet({'permissions': 'write'})
        self.assertEqual(u, {
                '_id': _id,
                'first_name': 'Ted',
                'last_name': 'Burns',
                'permissions': ['read', 'write']})

        self.assertEqual(
            db.User.find(), [{
                '_id': _id,
                'first_name': 'Ted',
                'last_name': 'Burns',
                'permissions': ['read', 'write']}])

    def test_validation(self):
        db = self._get_database()
        u = db.UserStrict.new(
            {'first_name': 'Daniel', 'last_name': 'Hengeveld'})

    def test_validation_required(self):
        db = self._get_database()
        self.assertRaises(
            ValidationError,
            db.UserStrict.new, {'first_name': 'Daniel'})

    def test_validation_not_optional(self):
        db = self._get_database()
        self.assertRaises(
            ValidationError,
            db.UserStrict.new, {'address': '915 Hampshire St, San Francisco'})

    def test_validation_on_set(self):
        db = self._get_database()
        u = db.UserStrict.new(
            {'first_name': 'Daniel', 'last_name': 'Hengeveld'})
        self.assertRaises(
            ValidationError,
            u.set, {'address': '915 Hampshire St, San Francisco'})
