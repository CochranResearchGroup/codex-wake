"""Internal JSON decoder keeps existing values while reducing owner parse cost."""
import json
import math
import unittest

from codex_wake.json_decode import decode_json


class JsonDecodeTests(unittest.TestCase):
    def test_json_values_preserve_large_integer_unicode_and_signed_zero(self):
        raw='{"integer":1267650600228229401496703205377,"values":[-0.0,1.2345678901234567,1e-300,1e300,true,false,null],"literal":"line\\nsemi; #W \\\\ \\" é 中文 \\ud83d\\ude00"}'
        value=decode_json(raw)
        self.assertEqual(value['integer'],1267650600228229401496703205377)
        self.assertEqual(value['values'],[-0.,1.2345678901234567,1e-300,1e300,True,False,None])
        self.assertEqual(math.copysign(1,value['values'][0]),-1)
        self.assertEqual(value['literal'],'line\nsemi; #W \\ " é 中文 😀')
        self.assertEqual(decode_json(raw.encode()),value)

    def test_legacy_nonfinite_numbers_and_lone_surrogate_keep_stdlib_values(self):
        value=decode_json('{"values":[NaN,Infinity,-Infinity,1e999],"surrogate":"\\ud800"}')
        self.assertTrue(math.isnan(value['values'][0]))
        self.assertEqual(value['values'][1:],[math.inf,-math.inf,math.inf])
        self.assertEqual(value['surrogate'],'\ud800')

    def test_each_decoded_result_owns_its_nested_containers(self):
        raw='{"items":[{"value":1}]}'
        first=decode_json(raw);second=decode_json(raw)
        first['items'][0]['value']=2
        self.assertEqual(second,{'items':[{'value':1}]})

    def test_malformed_input_keeps_json_decode_error_contract(self):
        for raw in ('{"unfinished":','{"x":1} trailing',b'\xff'):
            with self.subTest(raw=raw):
                expected=UnicodeDecodeError if isinstance(raw,bytes) else json.JSONDecodeError
                with self.assertRaises(expected):decode_json(raw)
