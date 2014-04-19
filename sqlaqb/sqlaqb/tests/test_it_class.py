# -*- coding:utf-8 -*-
import sqlalchemy as sa
from sqlalchemy.orm import relationship
from sqlaqb import (
    ModelCreation, 
    ModuleProvider, 
    ModelSeed, 
    with_tablename, 
    with_modelname, 
)

creation = ModelCreation()
_provider = ModuleProvider(creation)
create_models = _provider

@creation.register("Group")
class Group(ModelSeed):
    id=sa.Column(sa.Integer, primary_key=True, nullable=False)
    name=sa.Column(sa.String(255), nullable=False)

@creation.register("User", depends=["Group"])
class User(ModelSeed):
    id=sa.Column(sa.Integer, primary_key=True, nullable=False)
    name=sa.Column(sa.String(255), nullable=False)

    @with_tablename("Group")
    def group_id(cls, group_table_name):
        return sa.Column(sa.Integer, sa.ForeignKey("{}.id".format(group_table_name)), nullable=True)

    @with_modelname("Group")
    def group(cls, name):
        return relationship(name)

    def set_password(self, password, digest_impl=lambda : "xxx"):
        self.password_digest = digest_impl(password)

    def verify_password(self, password):
        return self.password_digest == password

## test
import unittest
from sqlalchemy.ext.declarative import declarative_base

class Tests(unittest.TestCase):
    def _callFUT(self, *args, **kwargs):
        return create_models(*args, **kwargs)

    def test_single(self):
        Base = declarative_base()
        contract = {"Group": {"table_name": "groups"}}
        models = self._callFUT(Base, contract)

        self.assertEqual(str(models.Group.__mapper__), "Mapper|Group|groups")
        self.assertTrue(issubclass(models.Group, Base))
        self.assertTrue(models.Group.name)
        self.assertTrue(models.Group.id)

        ## user is not found
        with self.assertRaises(AttributeError):
            models.User

    def test_full(self):
        Base = declarative_base()
        contract = {"User": {"table_name": "users"}, 
                    "Group": {"table_name": "groups", "model_name": "_Group"}}
        models = self._callFUT(Base, contract)

        self.assertEqual(str(models._Group.__mapper__), "Mapper|_Group|groups")
        self.assertEqual(str(models.User.__mapper__), "Mapper|User|users")
        #xxx:
        self.assertEqual(repr(list(models.User.group_id.foreign_keys)), 
                          "[ForeignKey('groups.id')]")

    def test_missing_contract(self):
        from sqlaqb import InvalidContract
        Base = declarative_base()
        contract = {}
        with self.assertRaisesRegex(InvalidContract, "is empty"):
            self._callFUT(Base, contract)

    def test_invalid_contract(self):
        from sqlaqb import DefinitionNotFound
        Base = declarative_base()
        contract = {"Another": {"table_name": "another"}}
        with self.assertRaisesRegex(DefinitionNotFound, "Another is not found"):
            self._callFUT(Base, contract)

if __name__ == "__main__":
    unittest.main()
