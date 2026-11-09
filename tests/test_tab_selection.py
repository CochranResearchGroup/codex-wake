import unittest
from codex_wake.tab_selection import select, validate


def row(name, value='codex', status='observed'):
    return dict(target={'workspace':'w'},window={'window_id':name,'panes':[{'pane_id':'%1','process_generation':1}]},traits={'traits':{'harness':dict(value=value,status=status)}})


class SelectionTests(unittest.TestCase):
    def test_boolean_patterns_and_unknown_are_three_valued(self):
        rows=[row('@1'),row('@2','other'),row('@3','codex','stale')]
        self.assertEqual(select(rows,{'not':{'field':'harness','pattern':'cod*'}}),[rows[1]])
        self.assertEqual(select(rows,{'any':[{'field':'harness','eq':'codex'},{'field':'harness','unknown':True}]}),[rows[0],rows[2]])
        self.assertEqual(select(rows,{'all':[{'not':{'field':'harness','eq':'other'}},{'field':'harness','eq':'codex'}]}),[rows[0]])

    def test_validation_rejects_unbounded_and_ambiguous_expressions(self):
        from codex_wake.managed_inventory import InventoryError
        deep={'field':'harness','eq':'codex'}
        for _ in range(10): deep={'not':deep}
        for expression in [deep,{'all':[]},{'any':[{'field':'harness','eq':'x'}]*33},{'field':'secret','eq':'x'},{'field':'health','unknown':False},{'field':'health','eq':'ok','pattern':'*'},{'tabs':['w/@1']}]:
            with self.subTest(expression=expression), self.assertRaises(InventoryError): validate(expression)

    def test_unavailable_and_missing_traits_only_match_explicit_unknown(self):
        rows=[row('@1','codex','unavailable'),row('@2','unknown'),row('@3')]
        rows[2]['traits']['traits']={}
        self.assertEqual(select(rows,{'field':'harness','unknown':True}),rows)
        self.assertEqual(select(rows,{'not':{'not':{'field':'harness','eq':'codex'}}}),[])
        self.assertEqual(select(rows,{'any':[{'field':'harness','eq':'codex'},{'not':{'field':'harness','eq':'codex'}}]}),[])
