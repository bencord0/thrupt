import unittest

from thrupt_proxy import Breaker


class TestBreaker(unittest.TestCase):
    def test_new_breaker(self):
        b = Breaker()

        assert b.shouldTry()

    def test_good_breaker(self):
        b = Breaker()
        b.good()

        assert b.shouldTry()
        assert b.isClosed
        assert not b.isOpen

    def test_bad_breaker(self):
        b = Breaker()
        b.bad()
        b.bad()
        b.bad()
        b.bad()
        b.bad()

        assert not b.shouldTry()
        assert b.isOpen
        assert not b.isClosed
        assert not b.isHalfOpen

    def test_recovered_breaker(self):
        b = Breaker()
        b.openCircuit()
        assert not b.shouldTry()
        assert b.isOpen
        assert not b.isHalfOpen
        assert not b.isClosed
        
        # When half open, only try once
        b.openCircuit()
        b.halfOpenCircuit()

        assert b.isHalfOpen
        assert b.isOpen
        assert not b.isClosed

        assert b.shouldTry()

        # assert states don't change
        assert b.isHalfOpen
        assert b.isOpen
        assert not b.isClosed

    def test_recovered_well(self):
        b = Breaker()
        b.openCircuit()
        b.halfOpenCircuit()

        assert b.isHalfOpen
        assert b.shouldTry()
        
        # Recovery is not immediate
        b.good()
        assert b.shouldTry()
        assert b.isHalfOpen
        assert not b.isClosed

        # After a few good runs, close the breakers
        b.good()
        b.good()
        b.good()
        b.good()
        assert b.shouldTry()
        assert b.isClosed

    def test_recovered_badly(self):
        b = Breaker()
        b.openCircuit()
        b.halfOpenCircuit()

        assert b.isHalfOpen
        assert b.shouldTry()

        b.bad()
        assert not b.shouldTry()
        assert b.isOpen

