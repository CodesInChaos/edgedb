
from typing import *

from ..data import data_ops as e

from ..data.data_ops import (
    AnyTp, BoolTp, BoolVal, BuiltinFuncDef, CardOne, FunArgRetType,
    FunType, IntTp, IntVal, Val, ParamOptional, ParamSetOf,
    ParamSingleton, RefVal, SomeTp, StrVal, CardAny, ArrVal, StrTp, ArrTp)
from .errors import FunCallErr
from .built_ins import *
import operator
add_tp = FunType(args_ret_types=[FunArgRetType(
                    args_mod=[ParamSingleton(), ParamSingleton()],
                    args_tp=[IntTp(), IntTp()],
                    ret_tp=e.ResultTp(IntTp(), CardOne))]
                 )


def add_impl(arg: Sequence[Sequence[Val]]) -> Sequence[Val]:
    match arg:
        case [[e.ScalarVal(t1, v1)], [e.ScalarVal(t2, v2)]]:
            assert t1 == t2
            return [e.ScalarVal(t1, v1 + v2)]
    raise FunCallErr()


subtract_tp = FunType(
    args_ret_types=[FunArgRetType(
        args_tp=[IntTp(), IntTp()],
        args_mod=[ParamSingleton(), ParamSingleton()],
        ret_tp=e.ResultTp(IntTp(), CardOne))]
                      )


def subtract_impl(arg: Sequence[Sequence[Val]]) -> Sequence[Val]:
    match arg:
        case [[e.ScalarVal(t1, v1)], [e.ScalarVal(t2, v2)]]:
            assert t1 == t2
            return [e.ScalarVal(t1, v1 - v2)]
    raise FunCallErr()

multiply_tp = FunType(
    args_ret_types=[FunArgRetType(
        args_mod=[ParamSingleton(), ParamSingleton()],
        args_tp=[IntTp(), IntTp()],
        ret_tp=e.ResultTp(IntTp(), CardOne))]
                      )


multiply_impl = lift_binary_scalar_op(operator.mul)



mod_tp = FunType(
    args_ret_types=[FunArgRetType(
        args_mod=[ParamSingleton(), ParamSingleton()],
        args_tp=[IntTp(), IntTp()],
        ret_tp=e.ResultTp(IntTp(), CardOne))]
                 )


mod_impl = lift_binary_scalar_op(operator.mod)


eq_tp = FunType(
    args_ret_types=[FunArgRetType(
        args_tp=[SomeTp(0), SomeTp(0)],
        args_mod=[ParamSingleton(), ParamSingleton()], 
        ret_tp=e.ResultTp(BoolTp(), CardOne))])


def eq_impl(arg: Sequence[Sequence[Val]]) -> Sequence[Val]:
    match arg:
        case [[
            e.ScalarVal(t1, v1)], [
            e.ScalarVal(t2, v2)]]:
            assert t1 == t2
            return [BoolVal(v1 == v2)]
    raise FunCallErr(arg)


not_eq_tp = FunType(
    args_ret_types=[FunArgRetType(
        args_mod=[ParamSingleton(), ParamSingleton()],
        args_tp=[SomeTp(0), SomeTp(0)],
        ret_tp=e.ResultTp(BoolTp(), CardOne))])


def not_eq_impl(arg: Sequence[Sequence[Val]]) -> Sequence[Val]:
    match arg:
        case [[e.ScalarVal(t1, v1)], [e.ScalarVal(t2, v2)]]:
            assert t1 == t2
            return [BoolVal(v1 != v2)]
        case [[RefVal(_) as r1], [RefVal(_) as r2]]:
            return [BoolVal(r1 != r2)]
    raise FunCallErr(arg)


opt_eq_tp = FunType(
    args_ret_types=[FunArgRetType(
        args_mod=[ParamOptional(), ParamOptional()],
        args_tp=[SomeTp(0), SomeTp(0)],
        ret_tp=e.ResultTp(BoolTp(), CardOne))])


def opt_eq_impl(arg: Sequence[Sequence[Val]]) -> Sequence[Val]:
    match arg:
        case [[], []]:
            return [BoolVal(True)]
        case [l1, l2]:
            if len(l1) == 0 or len(l2) == 0:
                return [BoolVal(False)]
            else:
                return eq_impl(arg)
    raise FunCallErr()


opt_not_eq_tp = FunType(
    args_ret_types=[FunArgRetType(
        args_mod=[ParamOptional(), ParamOptional()],
        args_tp=[SomeTp(0), SomeTp(0)],
        ret_tp=e.ResultTp(BoolTp(), CardOne))])


def opt_not_eq_impl(arg: Sequence[Sequence[Val]]) -> Sequence[Val]:
    match arg:
        case [[], []]:
            return [BoolVal(False)]
        case [l1, l2]:
            if len(l1) == 0 or len(l2) == 0:
                return [BoolVal(True)]
            else:
                return not_eq_impl(arg)
    raise FunCallErr()


gt_tp = FunType(
    args_ret_types=[FunArgRetType(
        args_mod=[ParamSingleton(), ParamSingleton()],
        args_tp=[SomeTp(0), SomeTp(0)],
        ret_tp=e.ResultTp(BoolTp(), CardOne))])


def gt_impl(arg: Sequence[Sequence[Val]]) -> Sequence[Val]:
    match arg:
        case [[IntVal(i1)], [IntVal(i2)]]:
            return [BoolVal(i1 > i2)]
    raise FunCallErr()


concatenate_tp = FunType(
    args_ret_types=[
        FunArgRetType(
            args_mod=[ParamSingleton(),
                    ParamSingleton()],
            args_tp=[StrTp(),
                     StrTp()],
            ret_tp=e.ResultTp(StrTp(), CardOne)),
        FunArgRetType(
            args_mod=[ParamSingleton(),
                    ParamSingleton()],
            args_tp=[e.ArrTp(SomeTp(0)),
                     e.ArrTp(SomeTp(0))],
            ret_tp=e.ResultTp(e.ArrTp(SomeTp(0)), CardOne))])


def concatenate_impl(arg: Sequence[Sequence[Val]]) -> Sequence[Val]:
    match arg:
        case [[e.ScalarVal(_, s1)], [e.ScalarVal(_, s2)]]:
            return [StrVal(s1 + s2)]
        case [[ArrVal(arr1)], [ArrVal(arr2)]]:
            return [ArrVal([*arr1, *arr2])]
    raise FunCallErr()


coalescing_tp = FunType(
    args_ret_types=[FunArgRetType(
        args_mod=[ParamOptional(), ParamSetOf()],
        args_tp=[SomeTp(0), SomeTp(0)],
        ret_tp=e.ResultTp(SomeTp(0), CardAny))])


def coalescing_impl(arg: Sequence[Sequence[Val]]) -> Sequence[Val]:
    match arg:
        case [[], default]:
            return default
        case [[non_empty], _]:
            return [non_empty]
    raise FunCallErr()


in_tp = FunType(
    args_ret_types=[FunArgRetType(
        args_mod=[ParamSingleton(), ParamSetOf()],
        args_tp=[SomeTp(0), SomeTp(0)],
        ret_tp=e.ResultTp(BoolTp(), CardOne))])


def in_impl(arg: Sequence[Sequence[Val]]) -> Sequence[Val]:
    match arg:
        case [[singleton], l]:
            return [BoolVal(singleton in l)]
    raise FunCallErr()


exists_tp = FunType(
    args_ret_types=[FunArgRetType(
        args_mod=[ParamSetOf()], 
        args_tp=[AnyTp()],
        ret_tp=e.ResultTp(BoolTp(), CardOne))])


def exists_impl(arg: Sequence[Sequence[Val]]) -> Sequence[Val]:
    match arg:
        case [[]]:
            return [BoolVal(False)]
        case [_]:
            return [BoolVal(True)]
    raise FunCallErr()


or_tp = FunType(
    args_ret_types=[FunArgRetType(
        args_mod=[ParamSingleton(), ParamSingleton()],
        args_tp=[BoolTp(), BoolTp()],
        ret_tp=e.ResultTp(BoolTp(), CardOne))])


def or_impl(arg: Sequence[Sequence[Val]]) -> Sequence[Val]:
    match arg:
        case [[e.ScalarVal(_, b1)], [e.ScalarVal(_, b2)]]:
            return [e.BoolVal(b1 or b2)]
        case [_]:
            return [BoolVal(True)]
    raise FunCallErr()


all_builtin_ops: Dict[str, BuiltinFuncDef] = {
    "+": BuiltinFuncDef(tp=add_tp, impl=add_impl),
    "-": BuiltinFuncDef(tp=subtract_tp, impl=subtract_impl),
    "*": BuiltinFuncDef(tp=multiply_tp, impl=multiply_impl),
    "%": BuiltinFuncDef(tp=mod_tp, impl=mod_impl),
    "=": BuiltinFuncDef(tp=eq_tp, impl=eq_impl),
    "!=": BuiltinFuncDef(tp=not_eq_tp, impl=not_eq_impl),
    "?=": BuiltinFuncDef(tp=opt_eq_tp, impl=opt_eq_impl),
    "?!=": BuiltinFuncDef(tp=opt_not_eq_tp, impl=opt_not_eq_impl),
    ">": BuiltinFuncDef(tp=gt_tp, impl=gt_impl),
    "++": BuiltinFuncDef(tp=concatenate_tp, impl=concatenate_impl),
    "??": BuiltinFuncDef(tp=coalescing_tp, impl=coalescing_impl),
    "IN": BuiltinFuncDef(tp=in_tp, impl=in_impl),
    "EXISTS": BuiltinFuncDef(tp=exists_tp, impl=exists_impl),
    "OR": BuiltinFuncDef(tp=or_tp, impl=or_impl),
}
