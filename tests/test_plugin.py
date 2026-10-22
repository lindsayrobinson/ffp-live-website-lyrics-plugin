#!/usr/bin/env python3
"""Exercise the plugin supervisor without touching FPP or sending network requests."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT if (ROOT / 'supervisor.py').is_file() else ROOT / 'integrations/fpp-plugin-loe-lyrics'

class PluginTests(unittest.TestCase):
    def test_supervisor_toggle_reload_and_single_instance(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            shutil.copy(PLUGIN / 'supervisor.py', tmp / 'supervisor.py')
            (tmp / 'sender.py').write_text('import time\nprint("CHILD_STARTED", flush=True)\ntime.sleep(60)\n')
            config, log = tmp / 'config.json', tmp / 'plugin.log'
            config.write_text(json.dumps({'enabled': False}))
            command = [sys.executable, str(tmp / 'supervisor.py'), '--config', str(config), '--log', str(log)]
            process = subprocess.Popen(command)
            def count():
                return log.read_text().count('CHILD_STARTED') if log.exists() else 0
            def wait_count(expected):
                until = time.monotonic() + 6
                while time.monotonic() < until:
                    if count() == expected:
                        return
                    time.sleep(.1)
                self.assertEqual(count(), expected)
            try:
                time.sleep(.3)
                self.assertEqual(count(), 0)
                config.write_text(json.dumps({'enabled': True}))
                wait_count(1)
                duplicate = subprocess.run(command, timeout=3)
                self.assertEqual(duplicate.returncode, 0)
                self.assertEqual(count(), 1)
                config.write_text(json.dumps({'enabled': False}))
                time.sleep(1.2)
                self.assertEqual(count(), 1)
                config.write_text(json.dumps({'enabled': True, 'interval_seconds': 3}))
                wait_count(2)
            finally:
                process.terminate()
                self.assertEqual(process.wait(timeout=10), 0)

    def test_settings_preserve_private_key_and_mapping(self):
        php = os.environ.get('PHP_BIN', '/opt/homebrew/opt/php@8.4/bin/php')
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            shutil.copy(PLUGIN / 'settings.php', tmp / 'settings.php')
            private = tmp / '.private'
            private.mkdir()
            csrf, key = 'a' * 64, 'b' * 64
            (private / 'csrf.key').write_text(csrf)
            config = private / 'config.json'
            initial = {'token': key, 'enabled': True, 'sequence_media': {'song.fseq': 'song.mp3'}}
            config.write_text(json.dumps(initial))
            harness = tmp / 'test.php'
            harness.write_text('''<?php
$_SERVER['REQUEST_METHOD']='POST';
$_POST=['loe_csrf'=>$argv[1], 'loe_endpoint'=>'https://lightsonelizabeth.com/api/lyrics/status','loe_token'=>'','loe_interval'=>'2'];
include __DIR__.'/settings.php';
''')
            rejected = subprocess.run([php, str(harness), 'wrong'], capture_output=True, text=True, check=True)
            self.assertEqual(json.loads(config.read_text()), initial)
            self.assertNotIn(key, rejected.stdout)
            result = subprocess.run([php, str(harness), csrf], capture_output=True, text=True, check=True)
            saved = json.loads(config.read_text())
            self.assertEqual(saved['token'], key)
            self.assertEqual(saved['sequence_media'], initial['sequence_media'])
            self.assertFalse(saved['enabled'])
            self.assertEqual(config.stat().st_mode & 0o777, 0o600)
            self.assertNotIn(key, result.stdout)
            self.assertEqual(result.stderr, '')

if __name__ == '__main__':
    unittest.main()
