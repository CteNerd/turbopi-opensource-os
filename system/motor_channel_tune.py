#!/usr/bin/env python3
"""Interactive wheel tuning utility for TurboPi vendor motor backend.

This tool probes each motor channel to find approximate breakaway duty and
suggests per-channel scale multipliers for HAL_MOTOR_CHANNEL_SCALE_1..4.

Safety:
- Keep wheels lifted off the ground.
- The script requires --confirm-lifted to run.
"""

import argparse
import importlib
import os
import re
import statistics
import sys
import tempfile
import time
from typing import Dict, List


CHANNELS = (1, 2, 3, 4)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='TurboPi motor channel tuning helper')
    parser.add_argument('--confirm-lifted', action='store_true', help='Required safety confirmation')
    parser.add_argument('--min-duty', type=int, default=10, help='First duty value to test (1-100)')
    parser.add_argument('--max-duty', type=int, default=40, help='Highest duty value to test (1-100)')
    parser.add_argument('--step', type=int, default=2, help='Duty step increment')
    parser.add_argument('--pulse', type=float, default=0.30, help='Seconds per pulse')
    parser.add_argument('--settle', type=float, default=0.75, help='Seconds between pulses')
    parser.add_argument('--direction', type=int, choices=(-1, 1), default=1, help='Probe direction sign')
    parser.add_argument('--write-config', action='store_true', help='Write recommendations into config file')
    parser.add_argument('--config-path', default='/etc/turbopi/config.env', help='Config file to update')
    parser.add_argument('--backup-suffix', default='.bak', help='Backup suffix when writing config')
    return parser.parse_args()


def build_board():
    try:
        sdk = importlib.import_module('HiwonderSDK.ros_robot_controller_sdk')
        return sdk.Board()
    except Exception as exc:
        raise RuntimeError('Vendor SDK unavailable: HiwonderSDK.ros_robot_controller_sdk') from exc


def stop_all(board) -> None:
    board.set_motor_duty([[1, 0], [2, 0], [3, 0], [4, 0]])


def prompt_yes_no(message: str) -> bool:
    while True:
        answer = input(message).strip().lower()
        if answer in ('y', 'yes'):
            return True
        if answer in ('n', 'no'):
            return False
        print('Please answer y or n.')


def probe_breakaway_duty(board, channel: int, duty_values: List[int], pulse_s: float, settle_s: float, direction: int) -> int:
    for duty in duty_values:
        signed_duty = duty * direction
        input(f'Press Enter to pulse CH{channel} at duty {signed_duty} ... ')
        board.set_motor_duty([[channel, signed_duty]])
        time.sleep(pulse_s)
        stop_all(board)
        moved = prompt_yes_no(f'Did CH{channel} move clearly at duty {signed_duty}? [y/n]: ')
        time.sleep(settle_s)
        if moved:
            return duty
    return 0


def compute_scales(thresholds: Dict[int, int]) -> Dict[int, float]:
    valid = [value for value in thresholds.values() if value > 0]
    if not valid:
        raise RuntimeError('No channels reported movement; cannot compute scales.')

    baseline = statistics.median(valid)
    if baseline <= 0:
        raise RuntimeError('Invalid baseline computed from thresholds.')

    scales: Dict[int, float] = {}
    for channel in CHANNELS:
        threshold = thresholds[channel]
        if threshold <= 0:
            scales[channel] = 1.0
            continue

        # Higher breakaway threshold means weaker channel -> higher scale.
        raw = baseline / float(threshold)
        scale = max(0.5, min(raw, 1.8))
        scales[channel] = round(scale, 3)

    return scales


def upsert_env_lines(file_path: str, entries: Dict[str, str]) -> None:
    existing_lines: List[str] = []
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as infile:
            existing_lines = infile.readlines()

    keys = set(entries.keys())
    key_pattern = re.compile(r'^([A-Za-z_][A-Za-z0-9_]*)=')
    replaced = set()
    output_lines: List[str] = []

    for line in existing_lines:
        match = key_pattern.match(line)
        if match and match.group(1) in keys:
            key = match.group(1)
            output_lines.append(f'{key}={entries[key]}\n')
            replaced.add(key)
        else:
            output_lines.append(line)

    if output_lines and not output_lines[-1].endswith('\n'):
        output_lines[-1] += '\n'

    missing = [key for key in entries.keys() if key not in replaced]
    if missing:
        output_lines.append('\n# Motor channel tuning (auto-generated)\n')
        for key in missing:
            output_lines.append(f'{key}={entries[key]}\n')

    directory = os.path.dirname(file_path) or '.'
    with tempfile.NamedTemporaryFile('w', delete=False, encoding='utf-8', dir=directory) as tmp:
        tmp.writelines(output_lines)
        tmp_path = tmp.name

    os.replace(tmp_path, file_path)


def main() -> int:
    args = parse_args()

    if not args.confirm_lifted:
        print('Refusing to run without --confirm-lifted safety flag.', file=sys.stderr)
        return 2

    if args.min_duty < 1 or args.max_duty > 100 or args.min_duty > args.max_duty:
        print('Invalid duty bounds. Require 1 <= min-duty <= max-duty <= 100.', file=sys.stderr)
        return 2
    if args.step < 1:
        print('Step must be >= 1.', file=sys.stderr)
        return 2

    board = build_board()
    duty_values = list(range(args.min_duty, args.max_duty + 1, args.step))

    print('Starting interactive channel tuning.')
    print('Keep wheels lifted. Record observations carefully.')
    print('A channel threshold of 0 means no movement observed in tested range.')

    thresholds: Dict[int, int] = {channel: 0 for channel in CHANNELS}

    try:
        stop_all(board)
        time.sleep(0.2)
        for channel in CHANNELS:
            print(f'\n=== Channel {channel} ===')
            thresholds[channel] = probe_breakaway_duty(
                board=board,
                channel=channel,
                duty_values=duty_values,
                pulse_s=max(0.05, args.pulse),
                settle_s=max(0.0, args.settle),
                direction=args.direction,
            )
    finally:
        stop_all(board)

    print('\nBreakaway thresholds (absolute duty):')
    for channel in CHANNELS:
        value = thresholds[channel]
        print(f'- CH{channel}: {value if value > 0 else "not detected"}')

    scales = compute_scales(thresholds)

    print('\nRecommended config values:')
    print('HAL_MOTOR_BACKEND=vendor')
    for channel in CHANNELS:
        print(f'HAL_MOTOR_CHANNEL_SCALE_{channel}={scales[channel]:.3f}')

    if args.write_config:
        backup_path = args.config_path + args.backup_suffix
        if os.path.exists(args.config_path):
            with open(args.config_path, 'rb') as src, open(backup_path, 'wb') as dst:
                dst.write(src.read())
            print(f'Backup written: {backup_path}')

        entries = {'HAL_MOTOR_BACKEND': 'vendor'}
        for channel in CHANNELS:
            entries[f'HAL_MOTOR_CHANNEL_SCALE_{channel}'] = f'{scales[channel]:.3f}'

        upsert_env_lines(args.config_path, entries)
        print(f'Config updated: {args.config_path}')

    print('\nDone.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
