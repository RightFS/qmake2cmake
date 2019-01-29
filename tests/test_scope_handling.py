#!/usr/bin/env python3
#############################################################################
##
## Copyright (C) 2018 The Qt Company Ltd.
## Contact: https://www.qt.io/licensing/
##
## This file is part of the plugins of the Qt Toolkit.
##
## $QT_BEGIN_LICENSE:GPL-EXCEPT$
## Commercial License Usage
## Licensees holding valid commercial Qt licenses may use this file in
## accordance with the commercial license agreement provided with the
## Software or, alternatively, in accordance with the terms contained in
## a written agreement between you and The Qt Company. For licensing terms
## and conditions see https://www.qt.io/terms-conditions. For further
## information use the contact form at https://www.qt.io/contact-us.
##
## GNU General Public License Usage
## Alternatively, this file may be used under the terms of the GNU
## General Public License version 3 as published by the Free Software
## Foundation with exceptions as appearing in the file LICENSE.GPL3-EXCEPT
## included in the packaging of this file. Please review the following
## information to ensure the GNU General Public License requirements will
## be met: https://www.gnu.org/licenses/gpl-3.0.html.
##
## $QT_END_LICENSE$
##
#############################################################################

from pro2cmake import Scope, SetOperation, merge_scopes, recursive_evaluate_scope

import pytest
import typing

ScopeList = typing.List[Scope]

def _map_to_operation(**kwargs):
    result = {}  # type: typing.Mapping[str, typing.List[SetOperation]]
    for (key, value) in kwargs.items():
        result[key] = [SetOperation(value)]
    return result


def _new_scope(*, parent_scope=None, condition='', **kwargs) -> Scope:
    return Scope(parent_scope=parent_scope,
                 file='file1', condition=condition, operations=_map_to_operation(**kwargs))


def _evaluate_scopes(scopes: ScopeList) -> ScopeList:
    for s in scopes:
        if not s.parent:
            recursive_evaluate_scope(s)
    return scopes


def _validate(input_scopes: ScopeList, output_scopes: ScopeList):
    merged_scopes = merge_scopes(input_scopes)
    assert merged_scopes == output_scopes


def test_evaluate_one_scope():
    scope = _new_scope(condition='QT_FEATURE_foo', test1='bar')

    input_scope = scope
    recursive_evaluate_scope(scope)
    assert scope == input_scope


def test_evaluate_child_scope():
    scope = _new_scope(condition='QT_FEATURE_foo', test1='bar')
    _new_scope(parent_scope=scope, condition='QT_FEATURE_bar', test2='bar')

    input_scope = scope
    recursive_evaluate_scope(scope)

    assert scope.total_condition == 'QT_FEATURE_foo'
    assert len(scope.children) == 1
    assert scope.getString('test1') == 'bar'
    assert scope.getString('test2', 'not found') == 'not found'

    child = scope.children[0]
    assert child.total_condition == 'QT_FEATURE_bar AND QT_FEATURE_foo'
    assert child.getString('test1', 'not found') == 'not found'
    assert child.getString('test2') == 'bar'


def test_evaluate_two_child_scopes():
    scope = _new_scope(condition='QT_FEATURE_foo', test1='bar')
    _new_scope(parent_scope=scope, condition='QT_FEATURE_bar', test2='bar')
    _new_scope(parent_scope=scope, condition='QT_FEATURE_buz', test3='buz')

    input_scope = scope
    recursive_evaluate_scope(scope)

    assert scope.total_condition == 'QT_FEATURE_foo'
    assert len(scope.children) == 2
    assert scope.getString('test1') == 'bar'
    assert scope.getString('test2', 'not found') == 'not found'
    assert scope.getString('test3', 'not found') == 'not found'

    child1 = scope.children[0]
    assert child1.total_condition == 'QT_FEATURE_bar AND QT_FEATURE_foo'
    assert child1.getString('test1', 'not found') == 'not found'
    assert child1.getString('test2') == 'bar'
    assert child1.getString('test3', 'not found') == 'not found'

    child2 = scope.children[1]
    assert child2.total_condition == 'QT_FEATURE_buz AND QT_FEATURE_foo'
    assert child2.getString('test1', 'not found') == 'not found'
    assert child2.getString('test2') == ''
    assert child2.getString('test3', 'not found') == 'buz'


def test_evaluate_else_child_scopes():
    scope = _new_scope(condition='QT_FEATURE_foo', test1='bar')
    _new_scope(parent_scope=scope, condition='QT_FEATURE_bar', test2='bar')
    _new_scope(parent_scope=scope, condition='else', test3='buz')

    input_scope = scope
    recursive_evaluate_scope(scope)

    assert scope.total_condition == 'QT_FEATURE_foo'
    assert len(scope.children) == 2
    assert scope.getString('test1') == 'bar'
    assert scope.getString('test2', 'not found') == 'not found'
    assert scope.getString('test3', 'not found') == 'not found'

    child1 = scope.children[0]
    assert child1.total_condition == 'QT_FEATURE_bar AND QT_FEATURE_foo'
    assert child1.getString('test1', 'not found') == 'not found'
    assert child1.getString('test2') == 'bar'
    assert child1.getString('test3', 'not found') == 'not found'

    child2 = scope.children[1]
    assert child2.total_condition == 'QT_FEATURE_foo AND NOT QT_FEATURE_bar'
    assert child2.getString('test1', 'not found') == 'not found'
    assert child2.getString('test2') == ''
    assert child2.getString('test3', 'not found') == 'buz'


def test_evaluate_invalid_else_child_scopes():
    scope = _new_scope(condition='QT_FEATURE_foo', test1='bar')
    _new_scope(parent_scope=scope, condition='else', test3='buz')
    _new_scope(parent_scope=scope, condition='QT_FEATURE_bar', test2='bar')

    input_scope = scope
    with pytest.raises(AssertionError):
        recursive_evaluate_scope(scope)


def test_merge_empty_scope_list():
    _validate([], [])


def test_merge_one_scope():
    scopes = [_new_scope(test='foo')]

    recursive_evaluate_scope(scopes[0])

    _validate(scopes, scopes)


def test_merge_one_on_scope():
    scopes = [_new_scope(condition='ON', test='foo')]

    recursive_evaluate_scope(scopes[0])

    _validate(scopes, scopes)


def test_merge_one_off_scope():
    scopes = [_new_scope(condition='OFF', test='foo')]

    recursive_evaluate_scope(scopes[0])

    _validate(scopes, [])


def test_merge_one_conditioned_scope():
    scopes = [_new_scope(condition='QT_FEATURE_foo', test='foo')]

    recursive_evaluate_scope(scopes[0])

    _validate(scopes, scopes)


def test_merge_two_scopes_with_same_condition():
    scopes = [_new_scope(condition='QT_FEATURE_bar', test='foo'),
              _new_scope(condition='QT_FEATURE_bar', test2='bar')]

    recursive_evaluate_scope(scopes[0])
    recursive_evaluate_scope(scopes[1])

    result = merge_scopes(scopes)

    assert len(result) == 1
    r0 = result[0]
    assert r0.total_condition == 'QT_FEATURE_bar'
    assert r0.getString('test') == 'foo'
    assert r0.getString('test2') == 'bar'


def test_merge_three_scopes_two_with_same_condition():
    scopes = [_new_scope(condition='QT_FEATURE_bar', test='foo'),
              _new_scope(condition='QT_FEATURE_baz', test1='buz'),
              _new_scope(condition='QT_FEATURE_bar', test2='bar')]

    recursive_evaluate_scope(scopes[0])
    recursive_evaluate_scope(scopes[1])
    recursive_evaluate_scope(scopes[2])

    result = merge_scopes(scopes)

    assert len(result) == 2
    r0 = result[0]
    assert r0.total_condition == 'QT_FEATURE_bar'
    assert r0.getString('test') == 'foo'
    assert r0.getString('test2') == 'bar'

    assert result[1] == scopes[1]


def test_merge_two_unrelated_on_off_scopes():
    scopes = [_new_scope(condition='ON', test='foo'),
              _new_scope(condition='OFF', test2='bar')]

    recursive_evaluate_scope(scopes[0])
    recursive_evaluate_scope(scopes[1])

    _validate(scopes, [scopes[0]])


def test_merge_two_unrelated_on_off_scopes():
    scopes = [_new_scope(condition='OFF', test='foo'),
              _new_scope(condition='ON', test2='bar')]

    recursive_evaluate_scope(scopes[0])
    recursive_evaluate_scope(scopes[1])

    _validate(scopes, [scopes[1]])


def test_merge_parent_child_scopes_with_different_conditions():
    scope = _new_scope(condition='FOO', test1='parent')
    scopes = [scope, _new_scope(parent_scope=scope, condition='bar', test2='child')]

    recursive_evaluate_scope(scope)

    _validate(scopes, scopes)


def test_merge_parent_child_scopes_with_same_conditions():
    scope = _new_scope(condition='FOO AND bar', test1='parent')
    scopes = [scope, _new_scope(parent_scope=scope, condition='FOO AND bar', test2='child')]

    recursive_evaluate_scope(scope)

    result = merge_scopes(scopes)

    assert len(result) == 1
    r0 = result[0]
    assert r0.parent == None
    assert r0.total_condition == 'FOO AND bar'
    assert r0.getString('test1') == 'parent'
    assert r0.getString('test2') == 'child'


def test_merge_parent_child_scopes_with_on_child_condition():
    scope = _new_scope(condition='FOO AND bar', test1='parent')
    scopes = [scope, _new_scope(parent_scope=scope, condition='ON', test2='child')]

    recursive_evaluate_scope(scope)

    result = merge_scopes(scopes)

    assert len(result) == 1
    r0 = result[0]
    assert r0.parent == None
    assert r0.total_condition == 'FOO AND bar'
    assert r0.getString('test1') == 'parent'
    assert r0.getString('test2') == 'child'

