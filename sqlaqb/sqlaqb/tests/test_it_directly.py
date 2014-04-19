# -*- coding:utf-8 -*-
import sqlalchemy as sa
import hashlib
from sqlaqb import (
    ModelCreation, 
    ModuleProvider, 
    attach_method, 
    InvalidContract, 
)

creation = ModelCreation()
_provider = ModuleProvider(creation)
create_models = _provider

@creation.register("Group")
def create_group(dispatch, bases, name, model_name):
    def on_tablename(attrs):
        attrs.update(
            id=sa.Column(sa.Integer, primary_key=True, nullable=False), 
            name=sa.Column(sa.String(255), nullable=False), 
        )
    attrs = dispatch.create_attrs(name, on_tablename=on_tablename)
    return type(model_name, bases, attrs) #use model_name (not name)

@creation.register("User", depends=["Group"])
def create_user(dispatch, bases, name, model_name):
    def on_tablename(attrs):
        group_table_name = dispatch.table_name_of("Group")
        attrs.update(
            id=sa.Column(sa.Integer, primary_key=True, nullable=False), 
            group_id=sa.Column(sa.Integer, sa.ForeignKey("{}.id".format(group_table_name)), nullable=True), 
            name=sa.Column(sa.String(255), nullable=False), 
        )
    attrs = dispatch.create_attrs(name, on_tablename=on_tablename)
    method = attach_method(attrs)

    @method
    def set_password(self, password, digest_impl=get_password_digest):
        self.password_digest = digest_impl(password)

    @method
    def verify_password(self, password):
        return self.password_digest == password

    return type(model_name, bases, attrs) #use model_name (not name)

def get_password_digest(password):
    return hashlib.sha1(password).hexdigest()


## test
import unittest
from sqlalchemy.ext.declarative import declarative_base

class Tests(unittest.TestCase):
    def _callFUT(self, *args, **kwargs):
        return create_models(*args, **kwargs)

    def test_missing(self):
        Base = declarative_base()
        with self.assertRaisesRegex(InvalidContract, "is empty"):
            self._callFUT(Base, {})

    def test_single(self):
        Base = declarative_base()
        contract = {"Group": {"table_name": "groups"}}
        models = self._callFUT(Base, contract)

        self.assertEqual(str(models.Group.__mapper__), "Mapper|Group|groups")
        self.assertTrue(issubclass(models.Group, Base))
        self.assertTrue(models.Group.name)
        self.assertTrue(models.Group.id)

    def test_single_with_mixin__has_field(self):
        Base = declarative_base()
        from datetime import datetime

        class TimeStampMixin(object):
            updated_at = sa.Column(sa.DateTime, onupdate=datetime.now)
            created_at = sa.Column(sa.DateTime, default=datetime.now, nullable=False)

        contract = {"Group": {"table_name": "groups"}}
        models = self._callFUT(Base, contract, parents=[TimeStampMixin])

        self.assertEqual(str(models.Group.__mapper__), "Mapper|Group|groups")
        self.assertTrue(models.Group.created_at)
        self.assertTrue(models.Group.updated_at)

    def test_same_base_twice__same(self):
        Base = declarative_base()
        contract = {"Group": {"table_name": "groups"}}
        models1 = self._callFUT(Base, contract)
        models2 = self._callFUT(Base, contract)
        self.assertEqual(models1, models2)

    def test_other_base_twice__different(self):
        Base = declarative_base()
        Base2 = declarative_base()
        contract = {"Group": {"table_name": "groups"}}
        models1 = self._callFUT(Base, contract)
        models2 = self._callFUT(Base2, contract)
        self.assertNotEqual(models1, models2)
        self.assertNotEqual(models1.Group, models2.Group)

    def test_single__with_model_name(self):
        Base = declarative_base()
        contract = {"Group": {"table_name": "groups", "model_name": "MyGroup"}}
        models = self._callFUT(Base, contract)

        self.assertEqual(str(models.MyGroup.__mapper__), "Mapper|MyGroup|groups")
        self.assertTrue(issubclass(models.MyGroup, Base))

    def test_single__missing_depends(self):
        Base = declarative_base()
        contract = {"User": {"table_name": "users"}}
        with self.assertRaisesRegex(InvalidContract, "Group is missing"):
            self._callFUT(Base, contract)

    def test_full(self):
        Base = declarative_base()
        contract = {"User": {"table_name": "users"}, 
                    "Group": {"table_name": "groups"}}
        models = self._callFUT(Base, contract)

        self.assertEqual(str(models.Group.__mapper__), "Mapper|Group|groups")
        self.assertEqual(str(models.User.__mapper__), "Mapper|User|users")
        #xxx:
        self.assertEqual(repr(list(models.User.group_id.foreign_keys)), 
                          "[ForeignKey('groups.id')]")

    def test_full__with_table(self):
        metadata = sa.MetaData()
        Base = declarative_base(metadata=metadata)
        group = sa.Table("groups", metadata, 
                         sa.Column("id", sa.Integer, primary_key=True, nullable=False),
                     )
        contract = {"User": {"table_name": "users"}, 
                    "Group": {"table": group}}
        models = self._callFUT(Base, contract)

        self.assertEqual(str(models.Group.__mapper__), "Mapper|Group|groups")
        self.assertEqual(str(models.User.__mapper__), "Mapper|User|users")
        #xxx:
        self.assertEqual(repr(list(models.User.group_id.foreign_keys)), 
                          "[ForeignKey('groups.id')]")


    def test_full__with_model(self):
        Base = declarative_base()
        class MyGroup(Base):
            id = sa.Column(sa.Integer, primary_key=True, nullable=False)
            special = sa.Column(sa.String("32"), doc="this is special")
            __tablename__ = "my_groups"

        contract = {"User": {"table_name": "users"}, 
                    "Group": {"model": MyGroup}}
        models = self._callFUT(Base, contract)

        self.assertEqual(str(models.Group.__mapper__), "Mapper|MyGroup|my_groups")
        self.assertEqual(str(models.User.__mapper__), "Mapper|User|users")
        #xxx:
        self.assertEqual(repr(list(models.User.group_id.foreign_keys)), 
                          "[ForeignKey('my_groups.id')]")

if __name__ == "__main__":
    unittest.main()
