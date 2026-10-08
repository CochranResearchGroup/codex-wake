import unittest
from codex_wake.time_provider import Observation, select_time


def sample(source, utc=100, operator=None, **kwargs):
    fields = dict(source=source, operator=source if operator is None else operator, lower=utc-.1, upper=utc+.1,
                  age=0, boot='boot', round_id='round', kind='network', scale='utc-step', healthy=True)
    fields.update(kwargs)
    return Observation(**fields)


def choose(*samples):
    return select_time(samples, boot='boot', round_id='round', tolerance=1, max_age=30, scale='utc-step')


class TimeProviderTests(unittest.TestCase):
    def test_network_consensus_overrides_windows_outlier(self):
        result=choose(sample('a'),sample('b',100.1),sample('windows',200,kind='windows'))
        self.assertEqual(result.status,'network')
        self.assertEqual(result.sources,('a','b'))
        self.assertAlmostEqual(result.lower,99.9)
        self.assertAlmostEqual(result.upper,100.2)

    def test_three_agreeing_sources_beat_one_outlier(self):
        result=choose(sample('a'),sample('b'),sample('c'),sample('d',200))
        self.assertEqual(result.status,'network')
        self.assertEqual(result.sources,('a','b','c'))

    def test_two_against_two_is_uncertain_even_when_windows_picks_a_side(self):
        result=choose(sample('a'),sample('b'),sample('c',200),sample('d',200),sample('win',kind='windows'))
        self.assertEqual(result.status,'uncertain')
        self.assertEqual(result.reason,'competing_network_consensuses')

    def test_aliases_from_one_operator_do_not_form_consensus(self):
        self.assertEqual(choose(sample('a',operator='same'),sample('b',operator='same')).status,'uncertain')

    def test_unusable_observations_cannot_vote(self):
        cases=[dict(age=31),dict(age=-1),dict(boot='previous'),dict(round_id='old'),dict(scale='smear'),dict(healthy=False),dict(lower=float('nan')),dict(upper=float('inf')),dict(lower=102,upper=100),dict(lower=99,upper=101),dict(operator='')]
        for changes in cases:
            with self.subTest(changes=changes):
                self.assertEqual(choose(sample('a'),sample('b',**changes)).status,'uncertain')

    def test_only_healthy_consistent_windows_can_be_fallback(self):
        self.assertEqual(choose(sample('win',kind='windows')).status,'windows')
        self.assertEqual(choose(sample('win',kind='windows',healthy=False)).status,'uncertain')
        self.assertEqual(choose(sample('win',kind='windows'),sample('a')).status,'windows')
        self.assertEqual(choose(sample('win',200,kind='windows'),sample('a')).status,'uncertain')

    def test_deadline_waits_at_boundary_and_is_due_after_sleep_with_fresh_evidence(self):
        from codex_wake.time_provider import deadline_status
        self.assertEqual(deadline_status(choose(sample('a',300),sample('b',300)),300),'uncertain')
        self.assertEqual(deadline_status(choose(sample('a',3600),sample('b',3600)),300),'due')
        self.assertEqual(deadline_status(choose(sample('a',100),sample('b',100)),300),'pending')
        self.assertEqual(deadline_status(choose(sample('a',3600,boot='old'),sample('b',3600,boot='old')),300),'uncertain')

    def test_policy_is_finite_and_work_is_bounded(self):
        for kwargs in [dict(tolerance=float('nan')),dict(max_age=-1),dict(tolerance=True)]:
            with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):
                policy=dict(boot='boot',round_id='round',tolerance=1,max_age=30,scale='utc-step')
                policy.update(kwargs)
                select_time([],**policy)
        with self.assertRaises(ValueError):
            choose(*(sample(str(i)) for i in range(6)))

    def test_ambiguous_overlapping_groups_pause(self):
        self.assertEqual(choose(sample('a',100),sample('b',100.7),sample('c',101.4)).status,'uncertain')

    def test_two_sources_survive_two_outages(self):
        self.assertEqual(choose(sample('a'),sample('b')).status,'network')
        self.assertEqual(choose(sample('a')).status,'uncertain')

    def test_input_order_never_breaks_ties(self):
        from itertools import permutations
        for order in permutations([sample('a'),sample('b'),sample('c',200),sample('d',200)]):
            self.assertEqual(choose(*order).status,'uncertain')

    def test_deadline_exact_lower_bound_is_due_and_invalid_deadline_refuses(self):
        from codex_wake.time_provider import deadline_status
        decision=choose(sample('a',lower=300,upper=300.2),sample('b',lower=300,upper=300.2))
        self.assertEqual(deadline_status(decision,300),'due')
        with self.assertRaises(ValueError):
            deadline_status(decision,float('nan'))

    def test_duplicate_operator_conflict_still_blocks_windows_fallback(self):
        result = choose(sample('a',200,operator='same'), sample('b',200,operator='same'), sample('win',kind='windows'))
        self.assertEqual(result.status,'uncertain')

    def test_observation_kind_limits_are_enforced(self):
        for observations in [[sample(str(i)) for i in range(5)], [sample('w1',kind='windows'),sample('w2',kind='windows')]]:
            with self.subTest(observations=observations), self.assertRaises(ValueError):
                choose(*observations)

    def test_duplicate_source_identity_cannot_supply_two_votes(self):
        self.assertEqual(choose(sample('same',operator='a'),sample('same',operator='b')).status,'uncertain')

    def test_malformed_decision_cannot_release_deadline(self):
        from codex_wake.time_provider import TimeDecision, deadline_status
        for lower, upper in [(301,300),(float('inf'),float('inf')),(300,float('nan'))]:
            with self.subTest(lower=lower,upper=upper):
                self.assertEqual(deadline_status(TimeDecision('network',lower=lower,upper=upper),300),'uncertain')
