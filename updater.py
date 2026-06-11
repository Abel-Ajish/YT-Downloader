"""
updater.py

Small elevated updater helper used to atomically replace the application executable.

Usage:
  python updater.py --new <path-to-new-exe> --target <path-to-target-exe> [--wait-pid PID] [--launch]

Behavior:
  - If running on Windows and not elevated, re-launches itself with elevation and the same args.
  - If the target file is locked (in use), the updater will wait (with retries) until it can replace it.
  - Performs an atomic replace: moves existing target to a .old backup, moves new file into place using os.replace.
  - Optionally launches the replaced executable when done.

This file intentionally has no external dependencies so it can be bundled with the app.
"""
from __future__ import annotations

import argparse
import ctypes
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


def is_admin() -> bool:
    if os.name != 'nt':
        # On POSIX, assume the user can perform replacements if they have write perms
        return os.geteuid() == 0 if hasattr(os, 'geteuid') else True
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def relaunch_elevated(argv: list[str]) -> None:
    """Relaunch the current Python interpreter with elevated privileges on Windows.
    Raises RuntimeError if ShellExecuteW returns <= 32 (failure)."""
    ctypes.windll.shell32.ShellExecuteW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_int]
    ctypes.windll.shell32.ShellExecuteW.restype = ctypes.c_ssize_t
    params = subprocess.list2cmdline(argv[1:])
    ret = ctypes.windll.shell32.ShellExecuteW(None, 'runas', sys.executable, params, None, 1)
    if ret <= 32:
        raise RuntimeError(f"ShellExecuteW failed with code {ret}")


def replace_file_atomic(new_path: Path, target_path: Path, max_wait: int = 60) -> None:
    """Try to atomically replace target_path with new_path. Retries while the file is locked.

    Creates a backup of the existing target as target_path + '.old'. Both moves use os.replace
    which is atomic on the same filesystem.
    """
    # Ensure absolute paths first
    new_path = new_path.resolve()
    target_path = target_path.resolve()

    deadline = time.time() + max_wait
    backup_path = target_path.with_suffix(target_path.suffix + '.old')

    while True:
        try:
            if target_path.exists():
                # Move existing target to backup (overwriting if exists)
                try:
                    os.replace(str(target_path), str(backup_path))
                except PermissionError:
                    # Target might be in use; fall through to retry logic
                    raise
            # Move new into target location (atomic on same FS)
            try:
                os.replace(str(new_path), str(target_path))
            except Exception:
                # Restore backup if second replace fails
                try:
                    if backup_path.exists():
                        os.replace(str(backup_path), str(target_path))
                except Exception:
                    pass
                raise
            # If we reach here: success. Attempt to remove backup
            try:
                if backup_path.exists():
                    backup_path.unlink()
            except Exception:
                # Non-fatal: leave backup for manual recovery
                pass
            return
        except PermissionError:
            if time.time() > deadline:
                raise
            time.sleep(1)
        except FileNotFoundError:
            # If new_path disappeared, fail fast
            raise
        except Exception:
            # For other errors, re-raise
            raise


def wait_for_pid_exit(pid: int, timeout: int = 60) -> None:
    """Wait for a process id to exit, with a timeout.

    This is a polite wait; if psutil isn't available we poll using os.kill on POSIX and
    a Windows-specific approach for Windows.
    """
    deadline = time.time() + timeout
    if pid <= 0:
        return

    if os.name == 'nt':
        # On Windows, try OpenProcess + WaitForSingleObject via ctypes
        try:
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            PROCESS_SYNCHRONIZE = 0x00100000
            handle = ctypes.windll.kernel32.OpenProcess(PROCESS_SYNCHRONIZE | PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid))
            if handle:
                # Wait for the process handle to be signaled (process exit)
                INFINITE = 0xFFFFFFFF
                # Wait in short intervals so we can timeout
                while time.time() < deadline:
                    res = ctypes.windll.kernel32.WaitForSingleObject(handle, 1000)  # 1 second
                    if res == 0:  # WAIT_OBJECT_0
                        ctypes.windll.kernel32.CloseHandle(handle)
                        return
                ctypes.windll.kernel32.CloseHandle(handle)
        except Exception:
            # Fallback to polling
            pass
    # POSIX or fallback: poll
    while time.time() < deadline:
        try:
            # signal 0 checks for existence on POSIX; on Windows it will raise OSError
            os.kill(pid, 0)
        except OSError:
            return
        except Exception:
            # On Windows, os.kill may raise; try using tasklist as last resort
            try:
                subprocess.check_output(['tasklist', '/FI', f'PID eq {pid}'])
            except Exception:
                return
        time.sleep(1)


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv
    parser = argparse.ArgumentParser(description="Atomic updater for YT-Downloader")
    parser.add_argument('--new', required=True, help='Path to the new executable file')
    parser.add_argument('--target', required=True, help='Path of the target executable to replace')
    parser.add_argument('--wait-pid', type=int, default=0, help='PID to wait for before replacing (optional)')
    parser.add_argument('--launch', action='store_true', help='Launch the target after replacement')
    parser.add_argument('--timeout', type=int, default=60, help='Seconds to wait for file/process to become free')

    args = parser.parse_args(argv[1:])

    new_path = Path(args.new)
    target_path = Path(args.target)

    if not new_path.exists():
        print(f"New file not found: {new_path}", file=sys.stderr)
        return 2

    # On Windows, ensure elevated if needed
    if os.name == 'nt' and not is_admin():
        # Relaunch self with elevation
        relaunch_elevated(argv)
        return 0

    # Optionally wait for provided PID to exit
    if args.wait_pid:
        try:
            wait_for_pid_exit(args.wait_pid, timeout=args.timeout)
        except Exception as e:
            print(f"Timeout waiting for process {args.wait_pid} to exit: {e}", file=sys.stderr)

    # Try to replace the file atomically
    try:
        replace_file_atomic(new_path, target_path, max_wait=args.timeout)
    except Exception as e:
        print(f"Failed to replace target: {e}", file=sys.stderr)
        return 3

    # Optionally launch the replaced program
    if args.launch:
        try:
            if os.name == 'nt':
                os.startfile(str(target_path))
            else:
                subprocess.Popen([str(target_path)])
        except Exception as e:
            print(f"Replacement succeeded but failed to launch target: {e}", file=sys.stderr)
            # Not fatal

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
