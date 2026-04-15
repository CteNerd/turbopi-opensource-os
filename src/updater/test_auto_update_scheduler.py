#!/usr/bin/env python3
"""
Tests for the UpdaterService auto-update scheduler:
  _normalize_version
  _is_newer_version
  _should_run_auto_update_now
  maybe_run_auto_update
  _fetch_latest_release
"""

import json
import os
import sys
import unittest
from datetime import datetime, date, timezone
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(__file__))
from main import UpdaterService


def _make_service(**env_overrides):
    """Create an UpdaterService with safe test defaults."""
    defaults = {
        'ROBOT_NAME': 'TestBot',
        'AUTO_UPDATE': 'false',
        'AUTO_UPDATE_CHANNEL': 'stable',
        'AUTO_UPDATE_SCHEDULE_UTC': '03:00',
        'UPDATER_POLL_INTERVAL': '10',
        'DOWNLOAD_DIR': '/tmp/test-turbopi-dl',
        'TRIGGER_DIR': '/tmp/test-turbopi-trigger',
        'GITHUB_RELEASES_URL': 'https://example.com/releases/latest',
    }
    defaults.update(env_overrides)
    with patch.dict(os.environ, defaults, clear=False):
        return UpdaterService()


class TestNormalizeVersion(unittest.TestCase):
    """_normalize_version parses semver strings into (major, minor, patch) tuples."""

    def setUp(self):
        self.svc = _make_service()

    def test_simple_semver(self):
        self.assertEqual(self.svc._normalize_version('1.2.3'), (1, 2, 3))

    def test_v_prefix_stripped(self):
        self.assertEqual(self.svc._normalize_version('v0.1.0'), (0, 1, 0))

    def test_major_only(self):
        self.assertEqual(self.svc._normalize_version('2'), (2, 0, 0))

    def test_major_minor(self):
        self.assertEqual(self.svc._normalize_version('0.5'), (0, 5, 0))

    def test_invalid_string_returns_zeros(self):
        self.assertEqual(self.svc._normalize_version('bad'), (0, 0, 0))

    def test_dev_suffix_returns_zeros(self):
        # '0.1.0-dev'.split('.')[2] = '0-dev'; int('0-dev') raises ValueError
        self.assertEqual(self.svc._normalize_version('0.1.0-dev'), (0, 0, 0))

    def test_empty_string_returns_zeros(self):
        self.assertEqual(self.svc._normalize_version(''), (0, 0, 0))


class TestIsNewerVersion(unittest.TestCase):
    """_is_newer_version compares two version strings."""

    def setUp(self):
        self.svc = _make_service()

    def test_newer_patch(self):
        self.assertTrue(self.svc._is_newer_version('0.1.0', '0.1.1'))

    def test_newer_minor(self):
        self.assertTrue(self.svc._is_newer_version('0.1.0', '0.2.0'))

    def test_newer_major(self):
        self.assertTrue(self.svc._is_newer_version('0.9.9', '1.0.0'))

    def test_same_version_is_not_newer(self):
        self.assertFalse(self.svc._is_newer_version('0.1.0', '0.1.0'))

    def test_older_version_is_not_newer(self):
        self.assertFalse(self.svc._is_newer_version('0.2.0', '0.1.9'))

    def test_dev_current_vs_stable_latest(self):
        # dev builds are treated as (0,0,0) so any stable release looks newer
        self.assertTrue(self.svc._is_newer_version('0.1.0-dev', '0.1.0'))


class TestShouldRunAutoUpdateNow(unittest.TestCase):
    """_should_run_auto_update_now gate logic."""

    def setUp(self):
        self.svc = _make_service()

    def _utc(self, hour, minute, second=0):
        return datetime(2026, 4, 14, hour, minute, second, tzinfo=timezone.utc)

    def test_disabled_always_false(self):
        self.svc.auto_update = False
        self.assertFalse(self.svc._should_run_auto_update_now(self._utc(3, 0)))

    def test_already_ran_today_false(self):
        self.svc.auto_update = True
        self.svc.auto_update_schedule_utc = '03:00'
        self.svc._last_auto_update_date = date(2026, 4, 14)
        self.assertFalse(self.svc._should_run_auto_update_now(self._utc(3, 5)))

    def test_before_scheduled_time_false(self):
        self.svc.auto_update = True
        self.svc.auto_update_schedule_utc = '03:00'
        self.svc._last_auto_update_date = None
        self.assertFalse(self.svc._should_run_auto_update_now(self._utc(2, 59)))

    def test_at_scheduled_time_true(self):
        self.svc.auto_update = True
        self.svc.auto_update_schedule_utc = '03:00'
        self.svc._last_auto_update_date = None
        self.assertTrue(self.svc._should_run_auto_update_now(self._utc(3, 0)))

    def test_after_scheduled_time_true(self):
        self.svc.auto_update = True
        self.svc.auto_update_schedule_utc = '03:00'
        self.svc._last_auto_update_date = None
        # Robot was offline at 03:00 and boots at 04:30 — should still run
        self.assertTrue(self.svc._should_run_auto_update_now(self._utc(4, 30)))

    def test_previous_day_does_not_block(self):
        self.svc.auto_update = True
        self.svc.auto_update_schedule_utc = '03:00'
        self.svc._last_auto_update_date = date(2026, 4, 13)
        self.assertTrue(self.svc._should_run_auto_update_now(self._utc(3, 5)))

    def test_invalid_schedule_false(self):
        self.svc.auto_update = True
        self.svc.auto_update_schedule_utc = 'not-a-time'
        self.svc._last_auto_update_date = None
        self.assertFalse(self.svc._should_run_auto_update_now(self._utc(3, 0)))

    def test_midnight_schedule(self):
        self.svc.auto_update = True
        self.svc.auto_update_schedule_utc = '00:00'
        self.svc._last_auto_update_date = None
        self.assertTrue(self.svc._should_run_auto_update_now(self._utc(0, 0)))

    def test_end_of_day_schedule(self):
        self.svc.auto_update = True
        self.svc.auto_update_schedule_utc = '23:59'
        self.svc._last_auto_update_date = None
        self.assertTrue(self.svc._should_run_auto_update_now(self._utc(23, 59)))


class TestMaybeRunAutoUpdate(unittest.TestCase):
    """maybe_run_auto_update orchestration."""

    def _utc(self, hour=3, minute=0):
        return datetime(2026, 4, 14, hour, minute, 0, tzinfo=timezone.utc)

    def setUp(self):
        self.svc = _make_service(AUTO_UPDATE='true', AUTO_UPDATE_SCHEDULE_UTC='03:00')
        self.svc.auto_update = True
        self.svc._last_auto_update_date = None

    @patch('main._datetime')
    def test_not_time_yet_does_nothing(self, mock_dt):
        mock_dt.now.return_value = self._utc(hour=2, minute=59)
        self.svc._fetch_latest_release = MagicMock()
        self.svc.maybe_run_auto_update()
        self.svc._fetch_latest_release.assert_not_called()

    @patch('main._datetime')
    def test_fetch_failure_no_update_applied(self, mock_dt):
        mock_dt.now.return_value = self._utc()
        self.svc._fetch_latest_release = MagicMock(return_value=None)
        self.svc.apply_update_to_system = MagicMock()
        self.svc.maybe_run_auto_update()
        self.svc.apply_update_to_system.assert_not_called()

    @patch('main._datetime')
    def test_same_version_no_update_applied(self, mock_dt):
        mock_dt.now.return_value = self._utc()
        with patch.dict(os.environ, {'VERSION': '0.1.0'}):
            self.svc._fetch_latest_release = MagicMock(
                return_value={'version': '0.1.0', 'url': 'http://x', 'checksum': 'a' * 64}
            )
            self.svc.apply_update_to_system = MagicMock()
            self.svc.maybe_run_auto_update()
        self.svc.apply_update_to_system.assert_not_called()

    @patch('main._datetime')
    def test_newer_version_calls_apply(self, mock_dt):
        mock_dt.now.return_value = self._utc()
        with patch.dict(os.environ, {'VERSION': '0.1.0'}):
            self.svc._fetch_latest_release = MagicMock(
                return_value={
                    'version': '0.2.0',
                    'url': 'https://example.com/turbopi-0.2.0.tar.gz',
                    'checksum': 'a' * 64,
                }
            )
            self.svc.apply_update_to_system = MagicMock(return_value=True)
            self.svc.maybe_run_auto_update()
        self.svc.apply_update_to_system.assert_called_once_with(
            version='0.2.0',
            url='https://example.com/turbopi-0.2.0.tar.gz',
            checksum='a' * 64,
        )

    @patch('main._datetime')
    def test_missing_checksum_skips_update(self, mock_dt):
        mock_dt.now.return_value = self._utc()
        with patch.dict(os.environ, {'VERSION': '0.1.0'}):
            self.svc._fetch_latest_release = MagicMock(
                return_value={'version': '0.2.0', 'url': 'http://x', 'checksum': None}
            )
            self.svc.apply_update_to_system = MagicMock()
            self.svc.maybe_run_auto_update()
        self.svc.apply_update_to_system.assert_not_called()

    @patch('main._datetime')
    def test_missing_url_skips_update(self, mock_dt):
        mock_dt.now.return_value = self._utc()
        with patch.dict(os.environ, {'VERSION': '0.1.0'}):
            self.svc._fetch_latest_release = MagicMock(
                return_value={'version': '0.2.0', 'url': None, 'checksum': 'a' * 64}
            )
            self.svc.apply_update_to_system = MagicMock()
            self.svc.maybe_run_auto_update()
        self.svc.apply_update_to_system.assert_not_called()

    @patch('main._datetime')
    def test_last_update_date_set_before_fetch(self, mock_dt):
        """Date is marked even on fetch failure so the same day is not retried."""
        now = self._utc()
        mock_dt.now.return_value = now
        self.svc._fetch_latest_release = MagicMock(return_value=None)
        self.svc.maybe_run_auto_update()
        self.assertEqual(self.svc._last_auto_update_date, now.date())

    @patch('main._datetime')
    def test_does_not_run_twice_same_day(self, mock_dt):
        mock_dt.now.return_value = self._utc()
        self.svc._fetch_latest_release = MagicMock(return_value=None)
        self.svc.maybe_run_auto_update()
        self.svc.maybe_run_auto_update()
        self.assertEqual(self.svc._fetch_latest_release.call_count, 1)


class TestFetchLatestRelease(unittest.TestCase):
    """_fetch_latest_release GitHub API interaction."""

    def setUp(self):
        self.svc = _make_service()

    def _mock_response(self, data_dict):
        """Build a MagicMock that behaves as a urllib context-manager response."""
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.read.return_value = json.dumps(data_dict).encode('utf-8')
        return mock_resp

    @patch('main.urllib.request.urlopen')
    def test_returns_none_on_http_error(self, mock_urlopen):
        import urllib.error
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url='', code=404, msg='Not Found', hdrs=None, fp=None
        )
        self.assertIsNone(self.svc._fetch_latest_release())

    @patch('main.urllib.request.urlopen')
    def test_returns_none_on_network_error(self, mock_urlopen):
        import urllib.error
        mock_urlopen.side_effect = urllib.error.URLError(reason='timeout')
        self.assertIsNone(self.svc._fetch_latest_release())

    @patch('main.urllib.request.urlopen')
    def test_returns_none_when_tag_name_missing(self, mock_urlopen):
        mock_urlopen.return_value = self._mock_response({'assets': []})
        self.assertIsNone(self.svc._fetch_latest_release())

    @patch('main.urllib.request.urlopen')
    def test_extracts_version_and_url(self, mock_urlopen):
        payload = {
            'tag_name': 'v0.2.0',
            'assets': [
                {
                    'name': 'turbopi-0.2.0.tar.gz',
                    'browser_download_url': 'https://example.com/turbopi-0.2.0.tar.gz',
                }
            ],
            'body': 'SHA256: ' + 'a' * 64,
        }
        mock_urlopen.return_value = self._mock_response(payload)
        result = self.svc._fetch_latest_release()
        self.assertIsNotNone(result)
        self.assertEqual(result['version'], '0.2.0')
        self.assertEqual(result['url'], 'https://example.com/turbopi-0.2.0.tar.gz')
        self.assertEqual(result['checksum'], 'a' * 64)

    @patch('main.urllib.request.urlopen')
    def test_strips_v_prefix_from_tag(self, mock_urlopen):
        payload = {
            'tag_name': 'v1.0.0',
            'assets': [],
            'tarball_url': 'https://example.com/v1.0.0.tar.gz',
        }
        mock_urlopen.return_value = self._mock_response(payload)
        result = self.svc._fetch_latest_release()
        self.assertIsNotNone(result)
        self.assertEqual(result['version'], '1.0.0')

    @patch('main.urllib.request.urlopen')
    def test_falls_back_to_tarball_url(self, mock_urlopen):
        payload = {
            'tag_name': 'v0.3.0',
            'assets': [],
            'tarball_url': 'https://example.com/tarball',
            'body': '',
        }
        mock_urlopen.return_value = self._mock_response(payload)
        result = self.svc._fetch_latest_release()
        self.assertEqual(result['url'], 'https://example.com/tarball')
        self.assertIsNone(result['checksum'])

    @patch('main.urllib.request.urlopen')
    def test_returns_none_on_invalid_json(self, mock_urlopen):
        bad_resp = MagicMock()
        bad_resp.__enter__ = lambda s: s
        bad_resp.__exit__ = MagicMock(return_value=False)
        bad_resp.read.return_value = b'not-json'
        mock_urlopen.return_value = bad_resp
        self.assertIsNone(self.svc._fetch_latest_release())


if __name__ == '__main__':
    unittest.main()
