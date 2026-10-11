import unittest
from copy import deepcopy

from codex_wake.native_clock import from_response


def response():
    return {
        'contract_version': '1.0', 'epoch': 'c357309d-c209-4467-b757-e1488e6b1aaa',
        'counter_policy': {'rate_ppm': 5000, 'maximum_age_ns': 10000000000},
        'measurement': {'counter': '10000000', 'frequency_hz': '10000000'},
        'status': 'qualified_live', 'authentication': 'NTS-verified',
        'time_scale': 'UTC-step; announced-leaps-unavailable', 'operators': ['a', 'b'],
        'acquisition_age_ns': 0, 'evidence_generation': 1, 'reason': None,
        'estimate': {'earliest_utc': '2027-01-15T12:00:00.001Z',
                     'utc': '2027-01-15T12:00:00.100Z',
                     'latest_utc': '2027-01-15T12:00:00.199Z',
                     'maximum_error_ns': 99000000, 'maximum_error_ms': 99.0},
    }


class NativeClockTests(unittest.TestCase):
    def test_wake_tolerance_does_not_relax_service_utc_qualification(self):
        valid = response()
        self.assertIsNotNone(from_response(valid, counter=10000010, frequency=10000000)['utc'])
        invalid = deepcopy(valid)
        invalid['estimate'].update(earliest_utc='2027-01-15T12:00:00Z',
                                   latest_utc='2027-01-15T12:00:00.200Z',
                                   maximum_error_ns=100000000, maximum_error_ms=100.0)
        with self.assertRaises(ValueError):
            from_response(invalid, counter=10000010, frequency=10000000)

    def test_authenticated_unavailable_response_can_only_supply_elapsed_evidence(self):
        value = response()
        value.update(status='unavailable', authentication='NTS-required', estimate=None,
                     acquisition_age_ns=None, operators=[], reason='uncertainty_exceeded')
        result = from_response(value, counter=10000010, frequency=10000000)
        self.assertIsNone(result['utc'])
        self.assertEqual(result['counter']['epoch'], value['epoch'])
        self.assertEqual(result['reason'], 'authenticated_counter_only')
        for invalid, count, frequency in [
            (dict(value, counter_policy=None), 10000010, 10000000),
            (value, 9999999, 10000000), (value, 10000010, 1000),
            (value, 200000000, 10000000),
        ]:
            with self.subTest(counter=count, frequency=frequency):
                with self.assertRaises((ValueError, TypeError)):
                    from_response(invalid, counter=count, frequency=frequency)

    def test_holdover_and_stale_provenance_remain_bounded(self):
        value = response()
        value['status'] = 'qualified_holdover'
        self.assertIsNotNone(from_response(value, counter=10000010, frequency=10000000)['utc'])
        for field, replacement in [('operators', ['a', 'a']), ('authentication', 'unverified'),
                                   ('acquisition_age_ns', 10000000000), ('evidence_generation', 0)]:
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    from_response(dict(value, **{field: replacement}), counter=10000010, frequency=10000000)

    def test_malformed_counter_and_unavailable_estimate_are_never_admitted(self):
        for field, value in [('counter', True), ('frequency_hz', 10000000), ('counter', '1e7')]:
            with self.subTest(field=field, value=value):
                invalid = response()
                invalid['measurement'][field] = value
                with self.assertRaises(ValueError):
                    from_response(invalid, counter=10000010, frequency=10000000)
        invalid = response()
        invalid.update(status='unavailable', authentication='NTS-required')
        with self.assertRaises(ValueError):
            from_response(invalid, counter=10000010, frequency=10000000)
