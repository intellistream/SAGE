# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.


import unittest

import faiss


class TestOpenMP(unittest.TestCase):
    def test_openmp(self):
        assert faiss.check_openmp()
