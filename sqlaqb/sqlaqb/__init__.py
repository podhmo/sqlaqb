# -*- coding:utf-8 -*-
from collections import defaultdict
import copy
from .langhelpers import ClassTypes
import imp

class InvalidContract(Exception):
    pass
class InvalidDefinition(Exception):
    pass
class DefinitionNameConflict(InvalidDefinition):
    pass
class DefinitionNotFound(InvalidDefinition):
    pass
class WalkerNotFound(Exception):
    pass

class NamePool(object):
    def register(self, *args):
        for k in args:
            setattr(self, k, k)
        return self

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
       
    def has_table_name(self, target):
        return "table_name" in target
    def has_table(self, target):
        return "table" in target
    def has_model(self, target):
        return "model" in target

    def target_of(self, name):
        return  self.contract[name]        

    def table_name_of(self, name):
        target = self.target_of(name)
        if self.has_table_name(target):
            return target["table_name"]
        elif self.has_table(target):
            return target["table"].name
        elif self.has_model(target):
            return target["model"].__tablename__
        else:
            raise InvalidContract("contract[{name}] must be include 'table_name' or 'table' or 'model'".format(name=name))

    def create_attrs(self, name, on_table=None, on_tablename=None):
        target = self.target_of(name)
        if self.has_table_name(target):
            attrs = {"__tablename__": target["table_name"]}
            on_tablename and on_tablename(attrs)
            return attrs
        elif self.has_table(target):
            attrs = {"__table__":  target["table"]}
            on_table and on_table(attrs)
            return attrs
        else:
            raise InvalidContract("table name not found. contract[{name}]".format(name=name))

    def create_model(self, definition, name, model_name):
        target = self.target_of(name)
        if self.has_model(target):
            return target["model"]
        return definition(self, self.bases, name, model_name)

class ModelCreation(object):
    def __init__(self, module_name="models", dispatch_impl=Dispatch, strict=True):
        self.module_name = module_name
        self.depends = defaultdict(list) ##TODO: topological sorting
        self.definitions = {}
        self.dispatch_impl = dispatch_impl
        self.strict = strict

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
        def _register(target):
            if isinstance(target, ClassTypes):
                walker = get_walker(target)
                definition = walker.create_definition(self, target)
                self.add_definition(name, definition, depends=depends)
                return target
            else:
                definition = target
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

_walker_attr = "_walker"
def get_walker(target):
    try:
        return getattr(target, _walker_attr)
    except:
        fmt = "walker is not found in {taret!r}."
        raise WalkerNotFound(fmt.format(taret=target))

class Marker(object):
    def __init__(self, tag):
        self.tag = tag

    def mark(self, target):
        setattr(target, self.tag, True)
        return target

    def is_marked(self, target):
        return hasattr(target, self.tag)

DeferredAttributeMarker = Marker("___sqlqb_deffered")

class AttributesWalker(object): #todo:rename
    excludes=set(["__dict__", "__name__", "__doc__", "__module__", "__weakref__", "__new__"])
    def __init__(self, base_cls, excludes=excludes):
        self.base_cls = base_cls
        self.excludes = excludes

    def is_exclude_class(self, cls):
        return any(cls is k for k in [ModelSeed, object])

    def _iterate_attributes(self, cls, dispatch):
        D = {}

        for c in reversed(cls.__mro__):
            if self.is_exclude_class(c):
                continue

            for k, v in c.__dict__.items():
                if k in self.excludes:
                    continue
                if DeferredAttributeMarker.is_marked(v):
                    D[k] = v(cls, dispatch)
                elif callable(v):
                    D[k] = v
                else:
                    D[k] = copy.copy(v) ## for Column etc.

        for k in self.base_cls.__dict__:
            if k in D:
                del D[k]
        return D

    def create_definition(self, creation, cls):
        def definition(dispatch, bases, name, model_name):
            def on_tablename(attrs):
                attrs.update(self._iterate_attributes(cls, dispatch))
            attrs = dispatch.create_attrs(name, on_tablename=on_tablename)
            return type(model_name, bases, attrs) #use model_name (not name)
        return definition

def with_walker(walker):
    def _with_walker(cls):
        setattr(cls, _walker_attr, walker(cls))
        return cls
    return _with_walker

def with_tablename(keyname, marker=DeferredAttributeMarker):
    def _with_tablename(method):
        def __with_tablename(cls, dispatch):
            tablename = dispatch.table_name_of(keyname)
            return method(cls, tablename)
        marker.mark(__with_tablename)
        return __with_tablename
    return _with_tablename

def with_modelname(keyname, marker=DeferredAttributeMarker):
    def _with_modelname(method):
        def __with_modelname(cls, dispatch):
            modelname = dispatch.model_name_of(keyname)
            return method(cls, modelname)
        marker.mark(__with_modelname)
        return __with_modelname
    return _with_modelname

@with_walker(AttributesWalker)
class ModelSeed(object):
    pass
