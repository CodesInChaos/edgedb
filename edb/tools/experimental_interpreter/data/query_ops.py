

from enum import Enum
from typing import Callable, Optional, Sequence

from . import data_ops as e
from .data_ops import (ArrExpr, BackLinkExpr, BindingExpr, BoolVal,
                       BoundVarExpr, DBSchema, DetachedExpr, Expr,
                       FilterOrderExpr, ForExpr, FreeVarExpr, FunAppExpr,
                       InsertExpr, IntVal, LinkPropProjExpr, MultiSetExpr,
                       NamedTupleExpr,  ObjectProjExpr,
                       OffsetLimitExpr, OptionalForExpr, ParamOptional,
                       ParamSetOf, ParamSingleton, ShapedExprExpr, ShapeExpr,
                       StrVal, SubqueryExpr, TpIntersectExpr, TypeCastExpr,
                       UnionExpr, UnnamedTupleExpr, UpdateExpr, WithExpr)

from . import module_ops as mops
class QueryLevel(Enum):
    TOP_LEVEL = 1
    SEMI_SUBQUERY = 2
    SUBQUERY = 3


def enter_semi_subquery(level: QueryLevel) -> QueryLevel:
    match level:
        case QueryLevel.TOP_LEVEL:
            return QueryLevel.SEMI_SUBQUERY
        case QueryLevel.SEMI_SUBQUERY:
            return QueryLevel.SEMI_SUBQUERY
        case QueryLevel.SUBQUERY:
            return QueryLevel.SUBQUERY


def enter_sub_query(level: QueryLevel) -> QueryLevel:
    return QueryLevel.SUBQUERY


def map_query(f: Callable[[Expr, QueryLevel],
                          Optional[Expr]],
              expr: Expr, schema: e.TcCtx,
              level: QueryLevel = QueryLevel.TOP_LEVEL) -> Expr:
    """ maps a function over free variables and bound variables,
    and does not modify other nodes

    f : called with current expression and the current level,
        return a non-null value to cut off further exploration
    level : Indicates the current level, initially should be

    """
    tentative = f(expr, level)
    if tentative is not None:
        return tentative
    else:
        def recur(expr):
            return map_query(f, expr, schema, level)

        def semisub_recur(expr):
            return map_query(f, expr, schema, enter_semi_subquery(level))

        def sub_recur(expr):
            return map_query(f, expr, schema, enter_sub_query(level))
        match expr:
            case FreeVarExpr(_):
                return expr
            case BoundVarExpr(_):
                return expr
            case e.ScalarVal(_):
                return expr
            case BindingExpr(var=var, body=body):
                # type: ignore[has-type]
                return BindingExpr(var=var, body=recur(body))
            case UnnamedTupleExpr(val=val):
                return UnnamedTupleExpr(val=[recur(e) for e in val])
            case NamedTupleExpr(val=val):
                return NamedTupleExpr(
                    val={k: recur(e) for (k, e) in val.items()})
            case ObjectProjExpr(subject=subject, label=label):
                return ObjectProjExpr(subject=recur(subject), label=label)
            case LinkPropProjExpr(subject=subject, linkprop=linkprop):
                return LinkPropProjExpr(
                    subject=recur(subject),
                    linkprop=linkprop)
            case BackLinkExpr(subject=subject, label=label):
                return BackLinkExpr(subject=recur(subject), label=label)
            case TpIntersectExpr(subject=subject, tp=tp_name):
                return TpIntersectExpr(subject=recur(subject), tp=tp_name)
            case FunAppExpr(fun=fname, args=args, overloading_index=idx):
                mapped_args: Sequence[Expr] = []
                _, resolved_fun_def = mops.resolve_raw_name_and_func_def(schema, fname)
                args_mods = [resolved_fun_def[i].tp.args_mod 
                             for i in range(len(resolved_fun_def))
                             if len(resolved_fun_def[i].tp.args_mod) == len(args)]
                if len(args_mods) == 0:
                    # This is due to named only arguments, need some time to sort out
                    raise ValueError("Expecting fun_defs [TODO named args]")
                assert all([args_mods[0] == args_mod for args_mod in args_mods]), \
                    "Expecting all args_mods to be the same"
                params = resolved_fun_def[0].tp.args_mod
                for i in range(len(args)):
                    match params[i]:
                        case ParamSingleton():
                            mapped_args = [*mapped_args, recur(args[i])]
                        case ParamOptional():
                            mapped_args = [*mapped_args,
                                           semisub_recur(args[i])]
                        case ParamSetOf():
                            mapped_args = [
                                *mapped_args, sub_recur(args[i])]
                        case _:
                            raise ValueError
                return FunAppExpr(
                    fun=fname, args=mapped_args, overloading_index=idx)
            case FilterOrderExpr(subject=subject, filter=filter, order=order):
                return FilterOrderExpr(
                    subject=recur(subject),
                    filter=sub_recur(filter),
                    order={l : sub_recur(o) for (l,o) in order.items()})
            case ShapedExprExpr(expr=expr, shape=shape):
                return ShapedExprExpr(
                    expr=recur(expr),
                    shape=sub_recur(shape))
            case ShapeExpr(shape=shape):
                return ShapeExpr(
                    shape={k: sub_recur(e_1) for (k, e_1) in shape.items()})
            case TypeCastExpr(tp=tp, arg=arg):
                return TypeCastExpr(tp=tp, arg=recur(arg))
            case UnionExpr(left=left, right=right):
                return UnionExpr(
                    left=sub_recur(left),
                    right=sub_recur(right))
            case ArrExpr(elems=arr):
                return ArrExpr(elems=[recur(e) for e in arr])
            case MultiSetExpr(expr=arr):
                return MultiSetExpr(expr=[sub_recur(e) for e in arr])
            case OffsetLimitExpr(subject=subject, offset=offset, limit=limit):
                return OffsetLimitExpr(
                    subject=sub_recur(subject),
                    offset=sub_recur(offset),
                    limit=sub_recur(limit))
            case WithExpr(bound=bound, next=next):
                return WithExpr(
                    bound=sub_recur(bound),
                    next=sub_recur(next))
            case ForExpr(bound=bound, next=next):
                return ForExpr(
                    bound=sub_recur(bound),
                    next=sub_recur(next))
            case OptionalForExpr(bound=bound, next=next):
                return OptionalForExpr(
                    bound=sub_recur(bound),
                    next=sub_recur(next))
            case e.IfElseExpr(
                    then_branch=then_branch,
                    condition=condition,
                    else_branch=else_branch):
                return e.IfElseExpr(
                    then_branch=sub_recur(then_branch),
                    condition=recur(condition),
                    else_branch=sub_recur(else_branch))
            case InsertExpr(name=name, new=new):
                return InsertExpr(name=name, new=
                    {k: sub_recur(e) for (k, e) in new.items()})
            # case ObjectExpr(val=val):
            #     return ObjectExpr(
            #         val={label: sub_recur(item)
            #              for (label, item) in val.items()})
            case DetachedExpr(expr=expr):
                return DetachedExpr(expr=sub_recur(expr))
            case SubqueryExpr(expr=expr):
                return SubqueryExpr(expr=sub_recur(expr))
            case UpdateExpr(subject=subject, shape=shape):
                return UpdateExpr(
                    subject=recur(subject),
                    shape=sub_recur(shape))
            case e.DeleteExpr(subject=subject):
                return e.DeleteExpr(subject=recur(subject))

    raise ValueError("Not Implemented: map_query ", expr)


def map_sub_and_semisub_queries(
        f: Callable[[Expr],
                    Optional[Expr]],
        expr: Expr, schema: e.TcCtx) -> Expr:
    def map_fun(sub: Expr, level: QueryLevel) -> Optional[Expr]:
        if level == QueryLevel.SEMI_SUBQUERY or level == QueryLevel.SUBQUERY:
            return f(sub)
        else:
            return None
    return map_query(map_fun, expr, schema)
