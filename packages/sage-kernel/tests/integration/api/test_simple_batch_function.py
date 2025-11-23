"""Integration-style tests for the batch iterator helpers."""

from __future__ import annotations

import pytest

from sage.kernel.api.function.simple_batch_function import (
    IterableBatchIteratorFunction,
    SimpleBatchIteratorFunction,
)
from sage.kernel.api.local_environment import LocalEnvironment


def _get_last_transformation(env: LocalEnvironment):
    assert env.pipeline, "Environment pipeline should not be empty"
    return env.pipeline[-1]


def test_from_batch_collection_uses_simple_iterator_and_yields_all_items():
    env = LocalEnvironment(name="batch-list-test")
    data = ["alpha", "beta", "gamma"]

    env.from_batch(data)
    transformation = _get_last_transformation(env)

    assert transformation.function_class is SimpleBatchIteratorFunction
    assert transformation.function_kwargs["data"] == data

    function = transformation.function_class(**transformation.function_kwargs)
    assert [function.execute(), function.execute(), function.execute(), function.execute()] == [
        "alpha",
        "beta",
        "gamma",
        None,
    ]
    assert len(function) == len(data)
    assert list(SimpleBatchIteratorFunction(data=data)) == data


def test_from_batch_iterable_infers_total_count_when_available():
    env = LocalEnvironment(name="batch-iterable-test")
    source = range(4)

    env.from_batch(source)
    transformation = _get_last_transformation(env)

    assert transformation.function_class is IterableBatchIteratorFunction
    assert transformation.function_kwargs["total_count"] == len(source)

    function = transformation.function_class(**transformation.function_kwargs)
    assert [function.execute() for _ in range(5)] == [0, 1, 2, 3, None]
    assert len(function) == len(source)


def test_from_batch_generator_without_total_count_requires_len_override():
    env = LocalEnvironment(name="batch-generator-test")
    generator = (i for i in range(3))

    env.from_batch(generator)
    transformation = _get_last_transformation(env)
    assert transformation.function_class is IterableBatchIteratorFunction
    assert transformation.function_kwargs["total_count"] is None

    function = transformation.function_class(**transformation.function_kwargs)
    assert [function.execute() for _ in range(4)] == [0, 1, 2, None]

    with pytest.raises(TypeError):
        len(function)


def test_from_batch_generator_with_total_count_supports_len():
    env = LocalEnvironment(name="batch-generator-len-test")
    generator = (i for i in range(2))

    env.from_batch(generator, total_count=2)
    transformation = _get_last_transformation(env)

    assert transformation.function_kwargs["total_count"] == 2

    function = transformation.function_class(**transformation.function_kwargs)
    assert [function.execute() for _ in range(3)] == [0, 1, None]
    assert len(function) == 2
