#!/usr/bin/env python3
"""Read FPP 10.2 status and send outbound lyric timing updates. No FPP writes."""
import argparse
import json
import math
from pathlib import Path
import sys
import time
from urllib.parse import urlsplit
from urllib.request import Request
import uuid

MAX_RESPONSE = 1024 * 1024

def normalise_status(status, sequence_media=None):
    """Use only observed media playback. Aircraft status is deliberately ignored."""
    name = str(status.get('status_name', '')).strip().lower()
    media = status.get('current_song') or status.get('media_filename') or ''
    if not isinstance(media, str):
        raise ValueError('Missing media identity')
    media = media.replace('\\', '/').rsplit('/', 1)[-1]
    if not media and sequence_media:
        sequence = status.get('current_sequence') or status.get('sequence_filename') or ''
        if isinstance(sequence, str):
            media = sequence_media.get(sequence.replace('\\', '/').rsplit('/', 1)[-1], '')
    if len(media.encode()) > 255 or any(ord(c) < 32 for c in media):
        raise ValueError('Invalid media identity')
    if name == 'idle':
        return {'state': 'stopped', 'media_filename': '', 'position_ms': 0}
    if name not in ('playing', 'playing media', 'playing background', 'stopping gracefully', 'stopping after loop', 'paused'):
        raise ValueError('Unrecognised player state')
    # An unmapped playlist pause/sequence-only item is not a known song. Missing timing must
    # never be invented as zero while the audio may already be midway through.
    if not media:
        return {'state': 'stopped', 'media_filename': '', 'position_ms': 0}
    milliseconds = status.get('milliseconds_elapsed')
    raw = milliseconds if milliseconds is not None else status.get('seconds_played')
    if isinstance(raw, bool) or raw is None:
        raise ValueError('Media playback position unavailable')
    elapsed = float(raw) if milliseconds is not None else float(raw) * 1000
    if not math.isfinite(elapsed) or not 0 <= elapsed <= 86400000:
        raise ValueError('Invalid playback position')
    return {'state': 'paused' if name == 'paused' else 'playing', 'media_filename': media, 'position_ms': elapsed}

def payload(status, previous, session, observed_at, sequence_media=None):
    row = normalise_status(status, sequence_media)
    if row['state'] in ('playing', 'paused'):
        if not previous or previous['media_filename'] != row['media_filename'] or previous['state'] not in ('playing', 'paused') or row['position_ms'] < previous['position_ms'] - 1200:
            session = str(uuid.uuid4())
    else:
        session = ''
    return {'schema': 1, 'observed_at': observed_at, 'session_id': session, **row}, session

def main():
    from urllib.request import HTTPRedirectHandler, build_opener
    class RefuseRedirects(HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True, type=Path)
    parser.add_argument('--once', action='store_true', help='Read and upload one snapshot, then exit')
    parser.add_argument('--allow-local-receiver', action='store_true', help='Permit HTTP only for a loopback test receiver')
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    endpoint, token = config['endpoint'], config['token']
    parsed = urlsplit(endpoint)
    local_test = args.allow_local_receiver and parsed.hostname in ('127.0.0.1', 'localhost', '::1')
    if parsed.scheme != 'https' and not (local_test and parsed.scheme == 'http'):
        parser.error('The website receiver requires HTTPS')
    if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path != '/api/lyrics/status':
        parser.error('Use the exact website /api/lyrics/status endpoint without credentials or query parameters')
    if not isinstance(token, str) or len(token) != 64 or any(c not in '0123456789abcdef' for c in token):
        parser.error('Configure the separate 64-character lyrics key')
    fpp = config.get('fpp_url', 'http://127.0.0.1').rstrip('/')
    fpp_parts = urlsplit(fpp)
    if fpp_parts.scheme not in ('http', 'https') or not fpp_parts.hostname or fpp_parts.username or fpp_parts.password or fpp_parts.query or fpp_parts.fragment:
        parser.error('Invalid FPP base URL')
    sequence_media = config.get('sequence_media', {})
    if not isinstance(sequence_media, dict) or any(not isinstance(k, str) or not isinstance(v, str) or not k or not v or any(c in k + v for c in '/\\') for k, v in sequence_media.items()):
        parser.error('sequence_media must map exact sequence basenames to exact media basenames')
    interval = float(config.get('interval_seconds', 2))
    if not 1 <= interval <= 5:
        parser.error('interval_seconds must be between 1 and 5')
    opener = build_opener(RefuseRedirects())
    previous, session, failures = None, '', 0
    while True:
        started = time.monotonic()
        try:
            before = time.time()
            with opener.open(fpp + '/api/fppd/status', timeout=2) as response:
                body = response.read(MAX_RESPONSE + 1)
            if len(body) > MAX_RESPONSE:
                raise ValueError('FPP status response too large')
            observed = (before + time.time()) / 2
            status = json.loads(body)
            if not isinstance(status, dict):
                raise ValueError('Invalid FPP status response')
            update, session = payload(status, previous, session, observed, sequence_media)
            previous = update
        except Exception:
            # Expire the display promptly instead of replaying the last song.
            update = {'schema': 1, 'observed_at': time.time(), 'session_id': '', 'state': 'unavailable', 'media_filename': '', 'position_ms': 0}
            previous, session = None, ''
        try:
            request = Request(endpoint, data=json.dumps(update).encode(), method='POST', headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'})
            with opener.open(request, timeout=3) as response:
                if response.status != 200:
                    raise ValueError('Upload refused')
            if failures:
                print('Lyrics updates resumed.', flush=True)
            failures = 0
            if args.once:
                print('Playback update accepted (' + update['state'] + ').')
                return 0 if update['state'] != 'unavailable' else 1
        except Exception:
            failures += 1
            if failures == 1 or failures % 30 == 0:
                print('Lyrics upload unavailable; retrying. Check connectivity and private configuration.', file=sys.stderr, flush=True)
            if args.once:
                return 1
        time.sleep(max(0, interval - (time.monotonic() - started)))

if __name__ == '__main__':
    raise SystemExit(main())
