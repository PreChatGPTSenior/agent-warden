"""USD arithmetic/admission fixtures; rates are invented test data, never live prices."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import sys

sys.path.insert(0, str(Path(__file__).absolute().parents[1]))
from execution.budgets import Budgets, snapshot, validate
from execution.core import Blocked
from execution.money import dollars, estimate, micros


class MoneyTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'budgets.sqlite'
        self.selection = {'model': 'fixture', 'provider_config': {'kind': 'builtin', 'provider_id': 'openai'}}
        self.router = {'model': 'fixture', 'provider_config': {'kind': 'responses', 'base_url': 'https://openrouter.ai/api/v1'}}
        self.price = {'basis': 'configured_estimate', 'source': 'https://example.invalid/fixture-only',
                      'valid_until': '2099-01-01T00:00:00+00:00', 'input_usd_per_million': '2.0',
                      'cached_input_usd_per_million': '0.5', 'output_usd_per_million': '6.0'}
        self.policy = {'schema': 2, 'unit': 'usd', 'pools': {
            pool: {'limit_usd': '2.00', 'invocation_allowance_usd': '1.00'} for pool in ('codex', 'openrouter')},
            'prices': {pool + ':fixture': deepcopy(self.price) for pool in ('codex', 'openrouter')}}
        self.addCleanup(patch.stopall)
        patch('subprocess.Popen', side_effect=AssertionError('No real process')).start()
        patch('socket.socket.connect', side_effect=AssertionError('No network')).start()

    def metrics(self, inputs, outputs=0, cached=None, complete=True):
        return {'known_input_tokens': inputs, 'known_output_tokens': outputs, 'cached_input_tokens': cached,
                'status': 'COMPLETE' if complete else 'PARTIAL_OR_UNAVAILABLE'}

    def reserve(self, budget, session='one', selection=None):
        return budget.reserve(session, selection or self.selection, 'T0002-002', 'developer', 'agent')

    def test_exact_decimal_arithmetic_cache_and_reasoning_subsets(self):
        metrics = self.metrics(1000000, 100000, 600000); metrics['reasoning_output_tokens'] = 80000
        self.assertEqual(1700000, estimate(metrics, self.price))
        self.assertEqual('1.700000', dollars(1700000))
        self.assertEqual(1, estimate(self.metrics(1, cached=1), self.price))
        self.assertEqual(2000000, estimate(self.metrics(1000000), self.price))

    def test_invalid_money_and_unknown_basis_block(self):
        for value in (0.1, '-1', 'NaN', 'Infinity', '0.0000001', '1e3'):
            with self.assertRaises(Blocked): micros(value)
        policy = deepcopy(self.policy); policy['prices']['codex:fixture']['basis'] = 'actual_invoice'
        with self.assertRaises(Blocked): validate(policy)

    def test_missing_and_expired_price_block_before_reservation(self):
        for change in ('missing', 'expired'):
            policy = deepcopy(self.policy)
            if change == 'missing': del policy['prices']['codex:fixture']
            else: policy['prices']['codex:fixture']['valid_until'] = '2000-01-01T00:00:00+00:00'
            budget = Budgets(self.path, policy)
            with self.assertRaises(Blocked): self.reserve(budget)
            self.assertEqual(0, snapshot(self.path, policy)['pools']['codex']['unsettled_calls'])

    def test_concurrent_usd_reservations_are_independent_between_pools(self):
        budget = Budgets(self.path, self.policy)
        def claim(number):
            try: self.reserve(budget, str(number)); return True
            except Blocked: return False
        with ThreadPoolExecutor(max_workers=6) as pool: self.assertEqual(2, sum(pool.map(claim, range(6))))
        self.reserve(budget, 'router', self.router)
        state = snapshot(self.path, self.policy)['pools']
        self.assertEqual('2.000000', state['codex']['charged_estimated_usd'])
        self.assertEqual('1.000000', state['openrouter']['charged_estimated_usd'])

    def test_usd_settlement_keeps_tokens_price_snapshot_and_unknown_invoice(self):
        budget = Budgets(self.path, self.policy); reservation = self.reserve(budget)
        receipt = budget.observe('one', self.metrics(100000, 10000, 50000), final=True)
        self.assertEqual('0.185000', receipt['estimated_cost_usd'])
        self.assertEqual(110000, receipt['reservation']['tokens'])
        self.assertEqual(self.price, reservation['price_snapshot'])
        self.assertIsNone(receipt['provider_reported_cost_usd'])
        reopened = Budgets(self.path, self.policy); reopened.guard([self.selection])
        self.assertEqual('0.185000', snapshot(self.path, self.policy)['pools']['codex']['charged_estimated_usd'])

    def test_usd_exact_limit_and_overrun_stop_both_pools(self):
        self.policy['pools']['codex']['limit_usd'] = '1.00'
        budget = Budgets(self.path, self.policy); self.reserve(budget)
        receipt = budget.observe('one', self.metrics(600000), final=True)
        self.assertEqual('1.200000', receipt['estimated_cost_usd'])
        with self.assertRaises(Blocked): budget.guard([self.router])
        with self.assertRaises(Blocked): Budgets(self.path, self.policy).check_stop()

    def test_unknown_usage_holds_dollars_and_does_not_become_free(self):
        budget = Budgets(self.path, self.policy); self.reserve(budget)
        budget.observe('one', self.metrics(10, complete=False), final=True)
        state = snapshot(self.path, self.policy)
        self.assertEqual('1.000000', state['pools']['codex']['charged_estimated_usd'])
        self.assertEqual(10, state['pools']['codex']['observed_tokens'])
        self.assertEqual('STOPPED', state['status'])

    def test_token_history_cannot_silently_reset_when_switching_to_usd(self):
        old = {'schema': 1, 'unit': 'input_plus_output_tokens', 'pools': {
            pool: {'limit_tokens': 1000, 'invocation_allowance_tokens': 100} for pool in ('codex', 'openrouter')}}
        budget = Budgets(self.path, old); self.reserve(budget)
        budget.observe('one', self.metrics(10), final=True)
        with self.assertRaises(Blocked): Budgets(self.path, self.policy)
        with self.assertRaises(Blocked): snapshot(self.path, self.policy)
        self.assertEqual(10, snapshot(self.path, old)['pools']['codex']['observed_tokens'])


if __name__ == '__main__': unittest.main()
