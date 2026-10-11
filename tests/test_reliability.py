import contextlib
import io
import json
import socket
import tempfile
import unittest
import urllib.request
from pathlib import Path
from unittest.mock import Mock, patch

import yaml

from netroute_diagnose.clash import match_domain
from netroute_diagnose.cli import main
from netroute_diagnose.config import ConfigError, bundled_config_path, load_diagnostic_config
from netroute_diagnose.diagnose import run_diagnostics
from netroute_diagnose.dns import resolve_domain
from netroute_diagnose.egress import SafeRedirectHandler, detect_egress
from netroute_diagnose.models import DiagnosticReport, DomainCheck, EgressResult
from netroute_diagnose.privacy import collect_secrets
from netroute_diagnose.report import render_html


class RuleRegressionTests(unittest.TestCase):
    def test_prior_unsupported_rules_reduce_confidence(self):
        for rule in ['DST-PORT,443,REJECT', 'DOMAIN-WILDCARD,*.example.com,REJECT',
                     'SOMETHING,new,DIRECT', 'DOMAIN,example.com', '',
                     'SUB-RULE,(DOMAIN,example.com),nested', 'AND,((NETWORK,UDP)),DIRECT']:
            with self.subTest(rule=rule):
                result = match_domain('example.com', [rule, 'MATCH,DIRECT'])
                self.assertEqual(result.confidence, 'limited')
                self.assertEqual(result.policy, 'DIRECT')

    def test_unknown_only_is_uncertain(self):
        self.assertEqual(match_domain('example.com', ['DST-PORT,443,REJECT']).confidence, 'limited')

    def test_pass_continues_in_main(self):
        for policy in ['PASS', 'PASS-RULE']:
            with self.subTest(policy=policy):
                result = match_domain('example.com', [f'DOMAIN,example.com,{policy}', 'MATCH,DIRECT'])
                self.assertEqual((result.rule_index, result.route_class, result.confidence), (1, 'DIRECT', 'high'))

    def test_subrule_does_not_lose_uncertainty_after_pass(self):
        result = match_domain('example.com', ['SUB-RULE,(NETWORK,tcp),nested',
                                             'DOMAIN,example.com,PASS', 'MATCH,DIRECT'])
        self.assertEqual(result.confidence, 'limited')

    def test_regex_never_executed_or_normalized(self):
        # Even compilation is forbidden: invalid, semantic and ReDoS cases share the safe fallback.
        with patch('re.search', side_effect=AssertionError('No regex execution')), \
             patch('re.compile', side_effect=AssertionError('No regex compilation')):
            for pattern in [r'^\D+\.example\.com$', '[', '^(a+)+$', r'(?i)^example\.com$']:
                result = match_domain('a' * 30 + '.example.com', [f'DOMAIN-REGEX,{pattern},REJECT', 'MATCH,DIRECT'])
                self.assertEqual(result.confidence, 'limited')
                self.assertIn('not executed', result.notes[0])

    def test_direct_mode_ignores_rules(self):
        r = match_domain('example.com', ['MATCH,REJECT'], mode='direct')
        self.assertEqual((r.policy, r.route_class, r.confidence), ('DIRECT', 'DIRECT', 'high'))
        self.assertIsNone(r.rule_index)

    def test_global_mode_unknown_selection(self):
        r = match_domain('example.com', ['MATCH,DIRECT'], mode='global')
        self.assertEqual((r.policy, r.route_class, r.confidence), ('GLOBAL', 'UNKNOWN', 'limited'))

    def test_builtin_policies(self):
        for policy, route in [('DIRECT','DIRECT'), ('COMPATIBLE','DIRECT'), ('REJECT','REJECT'),
                              ('REJECT-DROP','REJECT'), ('OnlyDirect','UNKNOWN'), ('direct','UNKNOWN')]:
            with self.subTest(policy=policy):
                self.assertEqual(match_domain('example.com', [f'MATCH,{policy}']).route_class, route)

    def test_case_and_suffix_matching(self):
        self.assertEqual(match_domain('WWW.Example.COM.', ['DOMAIN-SUFFIX,example.com,DIRECT']).policy, 'DIRECT')
        self.assertIsNone(match_domain('notexample.com', ['DOMAIN-SUFFIX,example.com,DIRECT']).policy)


class ConfigAndCLITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.diag = self.root / 'diag.yaml'
        self.clash = self.root / 'clash.yaml'
        self.base = {'apps':[{'name':'Demo','domains':[{'domain':'example.com','expected':'DIRECT'}]}]}
        self.diag.write_text(yaml.safe_dump(self.base), encoding='utf-8')
        self.clash.write_text('rules: ["MATCH,DIRECT"]', encoding='utf-8')

    def run_cli(self, *args):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()) as err:
            try:
                result = main(list(args))
            except SystemExit as exc:
                result = exc.code
        return result, err.getvalue()

    def test_only_direct_group_is_not_claimed_as_proxy(self):
        self.clash.write_text('proxy-groups: [{name: OnlyDirect, type: select, proxies: [DIRECT]}]\nrules: ["MATCH,OnlyDirect"]', encoding='utf-8')
        r = run_diagnostics(self.diag, self.clash, offline=True).domain_checks[0]
        self.assertEqual((r.rule_match.policy, r.actual, r.status), ('OnlyDirect', 'UNKNOWN', 'UNCERTAIN'))

    def test_direct_mode_integration(self):
        self.clash.write_text('mode: direct\nrules: ["MATCH,REJECT"]', encoding='utf-8')
        self.assertEqual(run_diagnostics(self.diag,self.clash,offline=True).domain_checks[0].status,'PASS')

    def test_invalid_config_types(self):
        changes = [{'dns':None}, {'dns':{'timeout':False}}, {'dns':{'timeout':float('nan')}},
                   {'dns':{'nameservers':'1.1.1.1'}}, {'dns':{'nameservers':[42]}},
                   {'egress':[]}, {'egress':{'checks':[True]}}, {'egress':{'checks':[{'enabled':'yes'}]}},
                   {'egress':{'endpoint':'file:///tmp/private'}},
                   {'apps':[{'name':'Demo','domains':[{'domain':123}]}]}]
        for change in changes:
            with self.subTest(change=change):
                self.diag.write_text(yaml.safe_dump(self.base | change),encoding='utf-8')
                with self.assertRaises(ConfigError):
                    load_diagnostic_config(self.diag)

    def test_invalid_clash_type_and_mode_friendly(self):
        for content in ['rules: [123]', 'mode: invalid', 'proxies: 42', 'proxies: 0', 'proxies: false']:
            self.clash.write_text(content,encoding='utf-8')
            code, error = self.run_cli('--config',str(self.diag),'--clash-config',str(self.clash),'--offline')
            self.assertEqual(code,1)
            self.assertNotIn('Traceback',error)

    def test_yaml_error_does_not_echo_secret(self):
        self.diag.write_text('apps: [password: FAKE_YAML_PASSWORD',encoding='utf-8')
        code,error=self.run_cli('--config',str(self.diag),'--clash-config',str(self.clash),'--offline')
        self.assertEqual(code,1)
        self.assertNotIn('FAKE_YAML_PASSWORD',error)
        self.assertNotIn(str(self.root),error)

    def test_argument_errors_use_one_and_do_not_echo_values(self):
        self.assertEqual(self.run_cli()[0],1)
        code,error=self.run_cli('--token=FAKE_ARGUMENT_SECRET')
        self.assertEqual(code,1)
        self.assertNotIn('FAKE_ARGUMENT_SECRET',error)

    def test_mismatch_uses_two(self):
        self.clash.write_text('rules: ["MATCH,REJECT"]',encoding='utf-8')
        self.assertEqual(self.run_cli('--config',str(self.diag),'--clash-config',str(self.clash),'--offline',
                                      '--output',str(self.root/'r.html'))[0],2)

    def test_demo_and_offline_never_call_network(self):
        with patch('netroute_diagnose.diagnose.resolve_domain',side_effect=AssertionError('DNS')), \
             patch('netroute_diagnose.diagnose.detect_egress',side_effect=AssertionError('HTTP')):
            self.assertEqual(self.run_cli('--demo','--output',str(self.root/'demo.html'),
                                          '--json-output',str(self.root/'demo.json'))[0],0)
            run_diagnostics(self.diag,self.clash,offline=True)
        report=json.loads((self.root/'demo.json').read_text())
        self.assertTrue(report['offline'])
        self.assertEqual(len(report['domain_checks']),10)
        self.assertEqual(report['dns_results'],[])
        self.assertIn('<!doctype html>',(self.root/'demo.html').read_text())

    def test_config_credentials_redacted_from_other_report_fields(self):
        self.base['egress'] = {'endpoint':'https://FAKE_USER:FAKE_PASS@example.invalid/ip?token=FAKE_TOKEN', 'checks':[]}
        self.base['apps'][0]['name'] = 'FAKE_TOKEN'
        self.diag.write_text(yaml.safe_dump(self.base), encoding='utf-8')
        r = run_diagnostics(self.diag, self.clash, offline=True)
        for output in [json.dumps(r.to_dict()), render_html(r)]:
            self.assertNotIn('FAKE_TOKEN', output)
            self.assertNotIn('FAKE_PASS', output)
            self.assertIn('example.com', output)

    def test_output_cannot_overwrite_input(self):
        before=self.clash.read_bytes()
        self.assertEqual(self.run_cli('--config',str(self.diag),'--clash-config',str(self.clash),
                                     '--offline','--output',str(self.clash))[0],1)
        self.assertEqual(before,self.clash.read_bytes())


class PrivacyAndNetworkTests(unittest.TestCase):
    def test_file_endpoint_rejected_before_open(self):
        with patch('urllib.request.build_opener',side_effect=AssertionError('No I/O')):
            r=detect_egress('demo','file:///tmp/FAKE_PRIVATE_FILE')
        self.assertIsNotNone(r.error)
        self.assertNotIn('FAKE_PRIVATE_FILE',r.endpoint+r.error)

    def test_redirect_rejects_non_http_schemes(self):
        handler=SafeRedirectHandler()
        req=urllib.request.Request('https://example.invalid/ip')
        for target in ['file:///tmp/FAKE_FILE','ftp://example.invalid/ip','data:text/plain,FAKE_TOKEN']:
            with self.subTest(target=target), self.assertRaises(ConfigError):
                handler.redirect_request(req,None,302,'Found',{},target)
        redirected=handler.redirect_request(req,None,302,'Found',{},'https://example.invalid/json')
        self.assertEqual(redirected.full_url,'https://example.invalid/json')

    def test_real_opener_blocks_unsafe_redirect_without_network(self):
        from email.message import Message
        from urllib.response import addinfourl
        for target in ['ftp://example.invalid/FAKE_REDIRECT_SECRET', 'file:///tmp/FAKE_REDIRECT_SECRET']:
            with self.subTest(target=target):
                headers = Message()
                headers['Location'] = target
                response = addinfourl(io.BytesIO(b''), headers, 'http://example.invalid/ip', 302)
                response.msg = 'Found'
                with patch('urllib.request.HTTPHandler.http_open', return_value=response), \
                     patch('urllib.request.FTPHandler.ftp_open', side_effect=AssertionError('No FTP')) as ftp, \
                     patch('urllib.request.FileHandler.file_open', side_effect=AssertionError('No file')) as local:
                    result = detect_egress('demo', 'http://example.invalid/ip')
                self.assertIsNotNone(result.error)
                self.assertNotIn('FAKE_REDIRECT_SECRET', result.error)
                ftp.assert_not_called()
                local.assert_not_called()

    def test_final_response_protocol_checked_before_read(self):
        response=Mock();response.geturl.return_value='file:///tmp/FAKE_FILE'
        response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=False)
        with patch('urllib.request.build_opener') as builder:
            builder.return_value.open.return_value=response
            result=detect_egress('demo','https://example.invalid/ip')
        response.read.assert_not_called()
        self.assertIsNotNone(result.error)
        self.assertTrue(any(isinstance(x,SafeRedirectHandler) for x in builder.call_args.args))

    def test_backend_exception_not_echoed(self):
        with patch('urllib.request.build_opener') as builder:
            builder.return_value.open.side_effect=RuntimeError('FAKE_RESPONSE_SECRET /home/private/file')
            r=detect_egress('demo','https://example.invalid/ip')
        self.assertNotIn('FAKE_RESPONSE_SECRET',r.error)
        self.assertNotIn('/home/private',r.error)

    def test_html_json_and_embedded_data_share_redaction(self):
        url='https://FAKE_USER:FAKE_PASSWORD@example.invalid/private/FAKE_PATH_TOKEN?token=FAKE_QUERY_TOKEN&format=json#FAKE_FRAGMENT'
        secret='FAKE_BARE_TOKEN'
        report=DiagnosticReport('now','config.yaml','clash.yaml',False,
            egress_results=[EgressResult('demo','system',url,error='Authorization: Bearer FAKE_HEADER_TOKEN')],
            warnings=['/home/FAKE_ACCOUNT/private/file',r'C:\Users\FAKE_WINDOWS\secret.txt', r'C:\Program Files\FAKE_SPACED_PATH\app',
                      'token=FAKE_ASSIGN_TOKEN', secret],sensitive_values=[secret])
        for output in [json.dumps(report.to_dict()),render_html(report)]:
            for marker in ['FAKE_USER','FAKE_PASSWORD','FAKE_PATH_TOKEN','FAKE_QUERY_TOKEN','FAKE_FRAGMENT',
                           'FAKE_HEADER_TOKEN','FAKE_ACCOUNT','FAKE_WINDOWS','FAKE_SPACED_PATH','FAKE_ASSIGN_TOKEN',secret]:
                self.assertNotIn(marker,output)
            self.assertIn('example.invalid',output)
            self.assertIn('format=json',output)
        self.assertNotIn('sensitive_values',report.to_dict())

    def test_process_rule_path_not_copied(self):
        r=match_domain('example.com',['PROCESS-PATH,/home/FAKE_ACCOUNT/app,DIRECT','MATCH,DIRECT'])
        self.assertNotIn('FAKE_ACCOUNT',str(r.notes))
        self.assertIn('#1',str(r.notes))

    def test_collect_credentials_and_yaml_cycles(self):
        data={'password':'FAKE_PASSWORD','url':'http://FAKE_USER:FAKE_PASS@example.invalid/?token=FAKE_TOKEN'}
        data['cycle']=data
        secrets=collect_secrets(data)
        self.assertTrue(set(['FAKE_PASSWORD','FAKE_USER','FAKE_PASS','FAKE_TOKEN'])<=set(secrets))

    def test_html_escapes_preserved_diagnostic_fields(self):
        r=match_domain('example.com',['MATCH,DIRECT'])
        report=DiagnosticReport('now','config.yaml','clash.yaml',True,
            domain_checks=[DomainCheck('<img onerror=alert(1)>','example.com','DIRECT','DIRECT','PASS',r)])
        text=render_html(report)
        self.assertNotIn('<img onerror',text)
        self.assertIn('&lt;img',text)
        self.assertIn('example.com',text)

    def test_dns_partial_failure_preserved(self):
        resolver=Mock();resolver.resolve.side_effect=[['192.0.2.1'],RuntimeError('FAKE_DNS_SECRET')]
        with patch('dns.resolver.Resolver',return_value=resolver):
            r=resolve_domain('example.com','192.0.2.53',timeout=0.5)
        self.assertEqual(r.addresses,['192.0.2.1'])
        self.assertIn('AAAA: RuntimeError',r.error)
        self.assertNotIn('FAKE_DNS_SECRET',r.error)
        self.assertEqual(resolver.lifetime,0.5)

    def test_system_dns_does_not_change_global_timeout(self):
        with patch('socket.getaddrinfo',return_value=[]), patch('socket.setdefaulttimeout') as setter:
            resolve_domain('example.com')
        setter.assert_not_called()
