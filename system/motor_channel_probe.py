#!/usr/bin/env python3
"""Manual-step motor channel probe for TurboPi bring-up.

Safety:
- Intended for bench testing with robot wheels lifted off ground.
- Sends low-duty, short-duration commands with stop between each step.
- Requires explicit confirmation flag to run.
"""

import argparse
import importlib
import sys
import time


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='TurboPi motor channel probe')
    parser.add_argument('--duty', type=int, default=20, help='Absolute duty to apply per step (1-100)')
    parser.add_argument('--duration', type=float, default=0.35, help='Duration in seconds for each pulse')
    parser.add_argument(
        '--confirm-lifted',
        action='store_true',
        help='Required safety confirmation that wheels are lifted',
    )
    return parser.parse_args()


def _build_board():
    try:
        sdk = importlib.import_module('HiwonderSDK.ros_robot_controller_sdk')
        return sdk.Board()
    except Exception as exc:
        raise RuntimeError('Vendor SDK unavailable: HiwonderSDK.ros_robot_controller_sdk') from exc


def _stop_all(board):
    board.set_motor_duty([[1, 0], [2, 0], [3, 0], [4, 0]])


def main() -> int:
    args = _parse_args()
    if not args.confirm_lifted:
        print('Refusing to run without --confirm-lifted safety flag.', file=sys.stderr)
        return 2

    duty = max(1, min(abs(args.duty), 100))
    duration = max(0.05, args.duration)

    board = _build_board()
    tests = [
        (1, duty), (1, -duty),
        (2, duty), (2, -duty),
        (3, duty), (3, -duty),
        (4, duty), (4, -duty),
    ]

    print('Starting manual-step motor channel probe.')
    print('Expected recording format: CHx +/-duty -> wheel position + direction.')
    _stop_all(board)
    time.sleep(0.2)

    try:
        for channel, command_duty in tests:
            input(f'Press Enter to run CH{channel} duty {command_duty} ... ')
            board.set_motor_duty([[channel, command_duty]])
            time.sleep(duration)
            _stop_all(board)
            print('Stopped.')
    finally:
        _stop_all(board)
        print('Probe complete. Motors stopped.')

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
