# -*- coding:utf-8 -*-
from collections import defaultdict
import imp

class InvalidContract(Exception):
    pass
class InvalidDefinition(Exception):
    pass
class DefinitionNameConflict(InvalidDefinition):
    pass
class DefinitionNotFound(InvalidDefinition):
    pass

class ModuleProvider(object):
    def __init__(self, creation, keyfn=id):
        self.cache = {}
        self.keyfn = keyfn
        self.creation = creation

    def needs(self, names):
        return self.creation.needs(names)

    def verify_contract(self, contract):
        ks = contract.keys()
        if not ks:
            raise InvalidContract("contract is empty")
        for k in self.needs(ks):
            if not k in contract:
                msg = "{k} is missing in contract({contract})".format(k=k, contract=contract)
                raise InvalidContract(msg)

    def __call__(self, base, contract, parents=None):
        self.verify_contract(contract)
        k = self.keyfn(base)
        try:
            return self.cache[k]
        except KeyError:
            if parents:
                bases = tuple(parents) + (base, )
            else:
                bases = (base, )
            module = self.cache[k] = self.create(bases, contract)
            return module

    def create(self, base, contract):
        return self.creation(base, contract)

class Dispatch(object):
    def __init__(self, bases, contract):
        self.bases = bases
        self.contract = contract

    def model_name_of(self, name):
        try:
            return self.contract[name]["model_name"]
        except KeyError:
            return name
       
    def is_table_name(self, target):
        return "table_name" in target
    def is_table(self, target):
        return "table" in target
    def is_model(self, target):
        return "model" in target

    def target_of(self, name):
        return  self.contract[name]        

    def table_name_of(self, name):
        target = self.target_of(name)
        if self.is_table_name(target):
            return target["table_name"]
        elif self.is_table(target):
            return target["table"].name
        elif self.is_model(target):
            return target["model"].__tablename__
        else:
            raise InvalidContract("contract[{name}] must be include 'table_name' or 'table' or 'model'".format(name=name))

    def create_attrs(self, name, on_table=None, on_tablename=None):
        target = self.target_of(name)
        if self.is_table_name(target):
            attrs = {"__tablename__": target["table_name"]}
            on_tablename and on_tablename(attrs)
            return attrs
        elif self.is_table(target):
            attrs = {"__table__":  target["table"]}
            on_table and on_table(attrs)
            return attrs
        else:
            raise InvalidContract("table name not found. contract[{name}]".format(name=name))

    def create_model(self, definition, name, model_name):
        target = self.target_of(name)
        if self.is_model(target):
            return target["model"]
        return definition(self, self.bases, name, model_name)

class ModelCreation(object):
    def __init__(self, module_name="models", dispatch_impl=Dispatch, strict=False):
        self.module_name = module_name
        self.depends = defaultdict(list) ##TODO: topological sorting
        self.definitions = {}
        self.dispatch_impl = dispatch_impl

    def needs(self, names):
        r = []
        history = {}
        for name in names:
            self._needs_rec(name, history, r)
        return r

    def _needs_rec(self, name, history, r):
        if not name in history:
            history[name] = 1
            for depend in self.depends[name]:
                self._needs_rec(depend, history, r)
            r.append(name)
        return r

    def add_definition(self, name, definition, depends=None):
        if name in self.definitions:
            if self.strict:
                raise DefinitionNameConflict("{name} is registered, already".format(name=name))
        self.depends[name] = depends or []
        self.definitions[name] = definition

    def register(self, name, depends=None):
        def _register(definition):
            self.add_definition(name, definition, depends=depends)
            return definition
        return _register
    
    def __call__(self, bases, contract):
        module = imp.new_module(self.module_name)
        dispatch = self.dispatch_impl(bases, contract)
        for k in contract.keys():
            try:
                definition = self.definitions[k]
                model_name = dispatch.model_name_of(k)
                model = dispatch.create_model(definition, k, model_name)
                setattr(module, model_name, model)
            except KeyError:
                raise DefinitionNotFound("{k} is not found in {definitions}".format(k=k, definitions=self.definitions))
        return module

def attach_method(D):
    def _attach_method(fn):
        D[fn.__name__] = fn
        return fn
    return _attach_method
