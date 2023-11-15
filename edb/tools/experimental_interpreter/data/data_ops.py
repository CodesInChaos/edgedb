from __future__ import annotations
from typing import Dict, NamedTuple, Sequence, Tuple, Optional, Callable

from dataclasses import dataclass

from enum import Enum

# to use when we move to 3.11
# and https://peps.python.org/pep-0681/ is implemented in mypy
# https://github.com/python/mypy/issues/14293
# @dataclass_transformer
# def data(f):
#     return dataclass(f, frozen=True)


# LABELS

@dataclass(frozen=True)
class StrLabel:
    label: str


@dataclass(frozen=True)
class LinkPropLabel:
    label: str


Label = StrLabel | LinkPropLabel

# DEFINE TYPES


@dataclass(frozen=True)
class ObjectTp:
    """ Object Type encapsulating val: Dict[str, ResultTp] """
    val: Dict[str, ResultTp]


@dataclass(frozen=True)
class StrTp:
    pass


@dataclass(frozen=True)
class BoolTp:
    pass


@dataclass(frozen=True)
class IntTp:
    pass


@dataclass(frozen=True)
class IntInfTp:
    pass


@dataclass(frozen=True)
class DateTimeTp:
    pass


@dataclass(frozen=True)
class JsonTp:
    pass

@dataclass(frozen=True)
class UuidTp:
    pass


PrimTp = StrTp | IntTp | IntInfTp | BoolTp | DateTimeTp | JsonTp | UuidTp


@dataclass(frozen=True)
class VarTp:
    name: str


@dataclass(frozen=True)
class NamedTupleTp:
    val: Dict[str, Tp]


@dataclass(frozen=True)
class UnnamedTupleTp:
    val: Sequence[Tp]


@dataclass(frozen=True)
class ArrTp:
    tp: Tp


@dataclass(frozen=True)
class UnionTp:
    left: Tp
    right: Tp


@dataclass(frozen=True)
class IntersectTp:
    left: Tp
    right: Tp

@dataclass(frozen=True)
class NamedNominalLinkTp:
    name: str
    linkprop: ObjectTp

@dataclass(frozen=True)
class NominalLinkTp:
    subject: ObjectTp
    name : str
    linkprop: ObjectTp


@dataclass(frozen=True)
class ComputableTp:
    expr: BindingExpr
    tp: Tp


# Computable Tp Pending Type Inference
@dataclass(frozen=True)
class UncheckedComputableTp:
    expr: BindingExpr


@dataclass(frozen=True)
class DefaultTp:
    expr: BindingExpr
    tp: Tp


@dataclass(frozen=True)
class AnyTp:
    pass


@dataclass(frozen=True)
class SomeTp:
    index: int


# implementation trick for synthesizing the empty type
@dataclass
class UnifiableTp:
    id: int
    resolution: Optional[Tp] = None


Tp = (ObjectTp | PrimTp | VarTp | NamedNominalLinkTp  | NominalLinkTp
      | NamedTupleTp | UnnamedTupleTp
      | ArrTp | AnyTp | SomeTp | UnionTp | IntersectTp | UnifiableTp
      | ComputableTp | DefaultTp | UncheckedComputableTp)


@dataclass(frozen=True)
class Visible:
    pass


@dataclass(frozen=True)
class Invisible:
    pass


Marker = Visible | Invisible


# DEFINE CARDINALITIES


@dataclass(frozen=True)
class ZeroCardinal:
    def __add__(self, other):
        return other

    def __mul__(self, other: Cardinal):
        assert not isinstance(other, InfiniteCardinal), "Cannot multiply zero by inf"
        return self

    def __le__(self, other: Cardinal):
        return True


@dataclass(frozen=True)
class OneCardinal:
    def __add__(self, other: Cardinal):
        match other:
            case ZeroCardinal():
                return OneCardinal()
            case OneCardinal():
                return InfiniteCardinal()
            case InfiniteCardinal():
                return InfiniteCardinal()
        raise ValueError()

    def __mul__(self, other: Cardinal):
        return other

    def __le__(self, other: Cardinal):
        match other:
            case ZeroCardinal():
                return False
            case OneCardinal():
                return True
            case InfiniteCardinal():
                return True
        raise ValueError()

@dataclass(frozen=True)
class InfiniteCardinal:
    def __add__(self, other: Cardinal):
        return InfiniteCardinal()

    def __mul__(self, other: Cardinal):
        assert not isinstance(other, ZeroCardinal), "cannot multiply zero by inf"
        return InfiniteCardinal()

    def __le__(self, other: Cardinal):
        match other:
            case InfiniteCardinal():
                return True
            case OneCardinal():
                return False
            case ZeroCardinal():
                return False
        raise ValueError()


Cardinal = ZeroCardinal | OneCardinal | InfiniteCardinal
LowerCardinal = ZeroCardinal | OneCardinal
UpperCardinal = OneCardinal | InfiniteCardinal

CardNumZero = ZeroCardinal()
CardNumOne = OneCardinal()
CardNumInf = InfiniteCardinal()


def max_cardinal(a: Cardinal, b: Cardinal):
    if a <= b:
        return b
    else:
        return a


def min_cardinal(a: Cardinal, b: Cardinal):
    if a <= b:
        return a
    else:
        return b

@dataclass(frozen=True)
class CMMode:
    lower: LowerCardinal
    upper: UpperCardinal
    # multiplicity: Cardinal = None  # type: ignore

    # def __post_init__(self):
    #     if self.multiplicity is None:
    #         object.__setattr__(self, 'multiplicity', self.upper)

    def __add__(self, other: CMMode):
        new_lower = self.lower + other.lower
        return CMMode(new_lower if new_lower != CardNumInf else CardNumOne,
                      self.upper + other.upper)
                      

    def __mul__(self, other: CMMode):
        return CMMode(self.lower * other.lower,
                      self.upper * other.upper)


# CardZero = CMMode(CardNumZero, CardNumZero)
CardOne = CMMode(CardNumOne, CardNumOne)
CardAtMostOne = CMMode(CardNumZero, CardNumOne)
CardAtLeastOne = CMMode(CardNumOne, CardNumInf)
CardAny = CMMode(CardNumZero, CardNumInf)

# ResultTp = Tuple[Tp, CMMode]


class ResultTp(NamedTuple):
    tp: Tp
    mode: CMMode


# DEFINE PARAMETER MODIFIERS

@dataclass(frozen=True)
class ParamSingleton:
    pass


@dataclass(frozen=True)
class ParamOptional:
    pass


@dataclass(frozen=True)
class ParamSetOf:
    pass


ParamModifier = ParamSingleton | ParamOptional | ParamSetOf


@dataclass(frozen=True)
class FunArgRetType:
    args_tp: Sequence[Tp]
    ret_tp: ResultTp


@dataclass(frozen=True)
class FunType:
    # all (overloaded) args need to have the same modifier
    args_mod: Sequence[ParamModifier]
    args_ret_types: Sequence[FunArgRetType]
    effect_free: bool = False

# DEFINE PRIM VALUES


@dataclass(frozen=True, order=True)
class StrVal:
    val: str


@dataclass(frozen=True, order=True)
class IntVal:
    val: int


@dataclass(frozen=True)
class DateTimeVal:
    val: str


@dataclass(frozen=True)
class JsonVal:
    val: str


@dataclass(frozen=True)
class FunVal:
    fname: str


@dataclass(frozen=True)
class IntInfVal:
    """ the infinite integer, used as the default value for limit """
    pass


@dataclass(frozen=True)
class BoolVal:
    val: bool


PrimVal = (StrVal | IntVal | FunVal | IntInfVal | BoolVal
           | DateTimeVal | JsonVal)

# DEFINE EXPRESSIONS


@dataclass(frozen=True)
class UnionExpr:
    left: Expr
    right: Expr


@dataclass(frozen=True)
class MultiSetExpr:
    expr: Sequence[Expr]


@dataclass(frozen=True)
class TypeCastExpr:
    tp: Tp
    arg: Expr


@dataclass(frozen=True)
class FunAppExpr:
    fun: str
    overloading_index: Optional[int]
    args: Sequence[Expr]


# @dataclass(frozen=True)
# class ObjectExpr:
#     val: Dict[Label, Expr]

@dataclass(frozen=True)
class FreeObjectExpr:
    pass

@dataclass(frozen=True)
class ConditionalDedupExpr:
    expr: Expr


@dataclass(frozen=True)
class FreeVarExpr:
    var: str


@dataclass(frozen=True)
class BoundVarExpr:
    var: str


@dataclass(frozen=True)
class ObjectProjExpr:
    subject: Expr
    label: str


@dataclass(frozen=True)
class BackLinkExpr:
    subject: Expr
    label: str


@dataclass(frozen=True)
class TpIntersectExpr:
    subject: Expr
    tp: str


@dataclass(frozen=True)
class LinkPropProjExpr:
    subject: Expr
    linkprop: str


@dataclass(frozen=True)
class SubqueryExpr:  # select e in formalism
    expr: Expr


# @dataclass(frozen=True)
# class SingularExpr:  # select e in formalism
#     expr: Expr


@dataclass(frozen=True)
class DetachedExpr:
    expr: Expr


@dataclass(frozen=True)
class WithExpr:
    bound: Expr
    next: BindingExpr


@dataclass(frozen=True)
class ForExpr:
    bound: Expr
    next: BindingExpr


@dataclass(frozen=True)
class OptionalForExpr:
    bound: Expr
    next: BindingExpr

@dataclass(frozen=True)
class IfElseExpr:
    then_branch: Expr
    condition: Expr
    else_branch: Expr

@dataclass(frozen=True)
class FilterOrderExpr:
    subject: Expr
    filter: BindingExpr
    order: Dict[str, BindingExpr] # keys are order-specifying list


@dataclass(frozen=True)
class OffsetLimitExpr:
    subject: Expr
    offset: Expr
    limit: Expr


@dataclass(frozen=True)
class InsertExpr:
    name: str
    new: Dict[str, Expr]


@dataclass(frozen=True)
class UpdateExpr:
    subject: Expr
    shape: ShapeExpr


@dataclass(frozen=True)
class DeleteExpr:
    subject: Expr

# @dataclass(frozen=True)
# class RefIdExpr:
#     refid : int


@dataclass(frozen=True)
class ShapedExprExpr:
    expr: Expr
    shape: ShapeExpr


@dataclass(frozen=True)
class BindingExpr:
    var: str
    body: Expr


@dataclass(frozen=True)
class ShapeExpr:
    shape: Dict[Label, BindingExpr]


@dataclass(frozen=True)
class UnnamedTupleExpr:
    val: Sequence[Expr]


@dataclass(frozen=True)
class NamedTupleExpr:
    val: Dict[str, Expr]


@dataclass(frozen=True)
class ArrExpr:
    elems: Sequence[Expr]


# VALUES

# @dataclass(frozen=True)
# class BinProdVal:
#     label : str
#     marker : Marker
#     this : Val
#     next : DictVal

# @dataclass(frozen=True)
# class BinProdUnitVal:
#     pass


@dataclass(frozen=True)
class ObjectVal:
    val: Dict[Label, Tuple[Marker, MultiSetVal]]


# @dataclass(frozen=True)
# class FreeVal:
#     val: ObjectVal


@dataclass(frozen=True)
class RefVal:
    refid: int
    val: ObjectVal

# @dataclass(frozen=True)
# class RefLinkVal:
#     from_id : int
#     to_id : int
#     val : ObjectVal


# @dataclass(frozen=True)
# class LinkWithPropertyVal:
#     subject : Val
#     link_properties : Val

@dataclass(frozen=True)
class UnnamedTupleVal:
    val: Sequence[Val]


@dataclass(frozen=True)
class NamedTupleVal:
    val: Dict[str, Val]


@dataclass(frozen=True)
class ArrVal:
    val: Sequence[Val]


# @dataclass(frozen=True)
# class LinkPropVal:
#     refid: int
#     linkprop: ObjectVal


# TODO: Check the eval_order_by code to make sure 
# emptyfirst/emptylast is handled correctly
@dataclass(frozen=True, order=True)
class MultiSetVal:
    vals: Sequence[Val]
    # singleton: bool = False


Val = (PrimVal | RefVal | UnnamedTupleVal | NamedTupleVal | ArrVal )  

# MultiSetVal = Sequence[Val]

VarExpr = (FreeVarExpr | BoundVarExpr)

Expr = (
    PrimVal | TypeCastExpr | FunAppExpr | FreeVarExpr | BoundVarExpr |
    ObjectProjExpr | LinkPropProjExpr | WithExpr | ForExpr | OptionalForExpr |
    TpIntersectExpr | BackLinkExpr | FilterOrderExpr | OffsetLimitExpr |
    InsertExpr | UpdateExpr | MultiSetExpr | ShapedExprExpr | ShapeExpr |
    FreeObjectExpr | ConditionalDedupExpr |
    # ObjectExpr | 
    BindingExpr | Val | UnnamedTupleExpr | NamedTupleExpr |
    ArrExpr | Tp | UnionExpr | DetachedExpr | SubqueryExpr
    #   | SingularExpr
    | IfElseExpr | DeleteExpr)


@dataclass(frozen=True)
class DBEntry:
    tp: str
    data: Dict[str, MultiSetVal]


@dataclass(frozen=True)
class DB:
    dbdata: Dict[int, DBEntry]
    # subtp : Sequence[Tuple[TypeExpr, TypeExpr]]


@dataclass(frozen=True)
class BuiltinFuncDef():
    tp: FunType
    impl: Callable[[Sequence[Sequence[Val]]], Sequence[Val]]


@dataclass(frozen=True)
class DBSchema:
    val: Dict[str, ObjectTp]
    fun_defs: Dict[str, BuiltinFuncDef]

# RT Stands for Run Time


# @dataclass(frozen=True)
# class RTData:
#     cur_db: DB
#     read_snapshots: Sequence[DB]
#     schema: DBSchema
#     eval_only: bool  # a.k.a. no DML, no effect


class RTExpr(NamedTuple):
    cur_db: DB
    expr: Expr


class RTVal(NamedTuple):
    cur_db: DB
    val: MultiSetVal


@dataclass
class TcCtx:
    schema: DBSchema
    varctx: Dict[str, ResultTp]


class SubtypingMode(Enum):
    # Regular subtyping do not allow missing keys or additional keys
    Regular = 1
    # insert subtyping allow missing keys in subtypes of an object type
    Insert = 2
    # shape subtyping allow additional keys in subtypes of an object type
    Shape = 3


starting_id = 0


def next_id():
    global starting_id
    starting_id += 1
    return starting_id


def next_name(prefix: str = "n") -> str:
    return prefix + str(next_id())


def ref(id):
    return RefVal(id, {})


OrderLabelSep = "-"  # separates components of an order object label
OrderAscending = "ascending"
OrderDescending = "descending"


IndirectionIndexOp = "_[_]"
IndirectionSliceOp = "_[_:_]"
# IfElseOp = "std::IF:_if_else_"
