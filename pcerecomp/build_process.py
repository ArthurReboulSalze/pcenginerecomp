"""Fail-closed Windows build subprocess ownership.

The child joins a non-inheritable kill-on-close job *during CreateProcessW*,
before any executable instruction runs. Descendants cannot break away. Only
duplicated standard handles are inherited; neither job nor recovery lock leaks.
There is deliberately no suspended-process/post-creation assignment fallback.

Win32 contracts (structures also checked against the Windows SDK headers):
https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-updateprocthreadattribute
https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createprocessw
https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_limit_information
https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_extended_limit_information
"""

from __future__ import annotations

from contextlib import contextmanager
import ctypes
from ctypes import wintypes as w
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time


_directory_leases = {}


@contextmanager
def directory_lease(root: Path, handle: int):
    """Register the caller-owned share=0 build lock HANDLE for guardian inheritance.

    The caller retains ownership of this handle. It must keep the context and
    handle alive for the entire build. Neither the compiler nor Ninja inherits
    this lease; only the source-only cleanup guardian does.
    """
    name = _job_name(root)
    if name in _directory_leases:
        raise OSError('build directory lease is already registered')
    if not isinstance(handle, int) or handle <= 0:
        raise ValueError('directory lease requires an actual Windows HANDLE')
    _directory_leases[name] = handle
    try:
        yield
    finally:
        del _directory_leases[name]


class _BasicLimits(ctypes.Structure):
    _fields_ = [
        ('PerProcessUserTimeLimit', ctypes.c_longlong),
        ('PerJobUserTimeLimit', ctypes.c_longlong),
        ('LimitFlags', w.DWORD),
        ('MinimumWorkingSetSize', ctypes.c_size_t),
        ('MaximumWorkingSetSize', ctypes.c_size_t),
        ('ActiveProcessLimit', w.DWORD),
        ('Affinity', ctypes.c_size_t),
        ('PriorityClass', w.DWORD),
        ('SchedulingClass', w.DWORD),
    ]


class _IoCounters(ctypes.Structure):
    _fields_ = [(name, ctypes.c_ulonglong) for name in (
        'ReadOperationCount', 'WriteOperationCount', 'OtherOperationCount',
        'ReadTransferCount', 'WriteTransferCount', 'OtherTransferCount')]


class _ExtendedLimits(ctypes.Structure):
    _fields_ = [('BasicLimitInformation', _BasicLimits), ('IoInfo', _IoCounters)] + [
        (name, ctypes.c_size_t) for name in (
            'ProcessMemoryLimit', 'JobMemoryLimit',
            'PeakProcessMemoryUsed', 'PeakJobMemoryUsed')]


class _Accounting(ctypes.Structure):
    _fields_ = [(name, ctypes.c_longlong) for name in (
        'TotalUserTime', 'TotalKernelTime', 'ThisPeriodTotalUserTime',
        'ThisPeriodTotalKernelTime')] + [(name, w.DWORD) for name in (
            'TotalPageFaultCount', 'TotalProcesses', 'ActiveProcesses',
            'TotalTerminatedProcesses')]


class _StartupInfo(ctypes.Structure):
    _fields_ = [('cb', w.DWORD)] + [(name, w.LPWSTR) for name in (
        'lpReserved', 'lpDesktop', 'lpTitle')] + [(name, w.DWORD) for name in (
            'dwX', 'dwY', 'dwXSize', 'dwYSize', 'dwXCountChars',
            'dwYCountChars', 'dwFillAttribute', 'dwFlags')] + [
        ('wShowWindow', w.WORD), ('cbReserved2', w.WORD),
        ('lpReserved2', ctypes.POINTER(w.BYTE)),
        ('hStdInput', w.HANDLE), ('hStdOutput', w.HANDLE),
        ('hStdError', w.HANDLE)]


class _StartupInfoEx(ctypes.Structure):
    _fields_ = [('StartupInfo', _StartupInfo), ('lpAttributeList', w.LPVOID)]


class _ProcessInfo(ctypes.Structure):
    _fields_ = [('hProcess', w.HANDLE), ('hThread', w.HANDLE),
                ('dwProcessId', w.DWORD), ('dwThreadId', w.DWORD)]


def _kernel():
    if (sys.platform != 'win32' or ctypes.sizeof(ctypes.c_void_p) != 8
            or platform.machine().lower() not in ('amd64', 'x86_64')):
        raise OSError('verified build process ownership requires Windows x64')
    if sys.getwindowsversion().major < 10:
        raise OSError('atomic build job assignment requires Windows 10 or newer')
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    signatures = {
        'CreateJobObjectW': (w.HANDLE, [w.LPVOID, w.LPCWSTR]),
        'OpenJobObjectW': (w.HANDLE, [w.DWORD, w.BOOL, w.LPCWSTR]),
        'SetInformationJobObject': (w.BOOL, [w.HANDLE, ctypes.c_int, w.LPVOID, w.DWORD]),
        'QueryInformationJobObject': (w.BOOL, [w.HANDLE, ctypes.c_int, w.LPVOID,
                                              w.DWORD, ctypes.POINTER(w.DWORD)]),
        'TerminateJobObject': (w.BOOL, [w.HANDLE, w.UINT]),
        'GetCurrentProcess': (w.HANDLE, []),
        'OpenProcess': (w.HANDLE, [w.DWORD, w.BOOL, w.DWORD]),
        'IsProcessInJob': (w.BOOL, [w.HANDLE, w.HANDLE, ctypes.POINTER(w.BOOL)]),
        'GetStdHandle': (w.HANDLE, [w.DWORD]),
        'DuplicateHandle': (w.BOOL, [w.HANDLE, w.HANDLE, w.HANDLE,
                                    ctypes.POINTER(w.HANDLE), w.DWORD, w.BOOL, w.DWORD]),
        'CloseHandle': (w.BOOL, [w.HANDLE]),
        'InitializeProcThreadAttributeList': (w.BOOL, [w.LPVOID, w.DWORD, w.DWORD,
                                                      ctypes.POINTER(ctypes.c_size_t)]),
        'UpdateProcThreadAttribute': (w.BOOL, [w.LPVOID, w.DWORD, ctypes.c_size_t,
                                              w.LPVOID, ctypes.c_size_t, w.LPVOID,
                                              ctypes.POINTER(ctypes.c_size_t)]),
        'DeleteProcThreadAttributeList': (None, [w.LPVOID]),
        'CreateProcessW': (w.BOOL, [w.LPCWSTR, w.LPWSTR, w.LPVOID, w.LPVOID,
                                    w.BOOL, w.DWORD, w.LPVOID, w.LPCWSTR,
                                    ctypes.POINTER(_StartupInfoEx),
                                    ctypes.POINTER(_ProcessInfo)]),
        'WaitForSingleObject': (w.DWORD, [w.HANDLE, w.DWORD]),
        'GetExitCodeProcess': (w.BOOL, [w.HANDLE, ctypes.POINTER(w.DWORD)]),
        'CreateEventW': (w.HANDLE, [w.LPVOID, w.BOOL, w.BOOL, w.LPCWSTR]),
        'OpenEventW': (w.HANDLE, [w.DWORD, w.BOOL, w.LPCWSTR]),
        'SetEvent': (w.BOOL, [w.HANDLE]),
        'ResetEvent': (w.BOOL, [w.HANDLE]),
    }
    for name, (restype, argtypes) in signatures.items():
        try:
            function = getattr(kernel, name)
        except AttributeError as exc:
            raise OSError(f'required Windows build ownership API unavailable: {name}') from exc
        function.restype = restype
        function.argtypes = argtypes
    return kernel


def _check(result, operation):
    if not result:
        code = ctypes.get_last_error()
        error = ctypes.WinError(code)
        raise OSError(code, f'{operation}: {error.strerror}', None, code)
    return result


def _environment(env):
    entries = []
    keys = set()
    for key, value in env.items():
        if (not isinstance(key, str) or not isinstance(value, str)
                or not key or '=' in key or '\0' in key or '\0' in value):
            raise ValueError('build environment requires nonempty names and NUL-free strings')
        folded = key.upper()
        if folded in keys:
            raise ValueError('build environment contains duplicate case-insensitive names')
        keys.add(folded)
        entries.append((folded, f'{key}={value}'))
    # The extra terminator (in addition to create_unicode_buffer's terminator)
    # also makes an empty controlled environment a double-NUL block.
    return ctypes.create_unicode_buffer('\0'.join(v for _, v in sorted(entries)) + '\0')


def _standard_handles(kernel):
    """Duplicate only stdin/out/err without changing the caller's handle flags."""
    import msvcrt

    handles = []
    current = kernel.GetCurrentProcess()
    try:
        for number in (-10, -11, -12):
            original = kernel.GetStdHandle(number & 0xffffffff)
            null_fd = None
            try:
                # Detached parents may have absent standard handles.
                if original in (None, ctypes.c_void_p(-1).value):
                    null_fd = os.open(os.devnull, os.O_RDONLY if number == -10 else os.O_WRONLY)
                    original = msvcrt.get_osfhandle(null_fd)
                duplicate = w.HANDLE()
                _check(kernel.DuplicateHandle(current, original, current,
                                               ctypes.byref(duplicate), 0, True, 2),
                       'DuplicateHandle(standard handle)')
                handles.append(duplicate.value)
            finally:
                if null_fd is not None:
                    os.close(null_fd)
        return handles
    except BaseException:
        for handle in handles:
            kernel.CloseHandle(handle)
        raise


def _active(kernel, job):
    accounting = _Accounting()
    _check(kernel.QueryInformationJobObject(job, 1, ctypes.byref(accounting),
                                           ctypes.sizeof(accounting), None),
           'QueryInformationJobObject')
    return accounting.ActiveProcesses


def _job_name(cwd):
    canonical = os.path.normcase(str(Path.cwd().resolve() if cwd is None
                                     else Path(cwd).resolve()))
    digest = hashlib.sha256(canonical.encode('utf-8', errors='surrogatepass')).hexdigest()
    # Global matches the filesystem lock's cross-session scope. Global job
    # objects do not require the file-mapping-specific SeCreateGlobalPrivilege.
    # https://learn.microsoft.com/en-us/windows/win32/termserv/kernel-object-namespaces
    return 'Global\\pcerecomp-verified-build-v1-' + digest


def _member_handles(kernel, job):
    """Snapshot process handles, validating membership against PID reuse."""
    capacity = 16
    while True:
        class ProcessList(ctypes.Structure):
            _fields_ = [('assigned', w.DWORD), ('count', w.DWORD),
                        ('ids', ctypes.c_size_t * capacity)]
        members = ProcessList()
        ok = kernel.QueryInformationJobObject(job, 3, ctypes.byref(members),
                                              ctypes.sizeof(members), None)
        if not ok and ctypes.get_last_error() != 234:  # ERROR_MORE_DATA
            _check(False, 'QueryInformationJobObject(process list)')
        if not ok or members.assigned > members.count:
            capacity = max(capacity * 2, members.assigned)
            continue
        break
    handles = []
    try:
        for pid in members.ids[:members.count]:
            # SYNCHRONIZE | PROCESS_QUERY_LIMITED_INFORMATION, no terminate right.
            handle = kernel.OpenProcess(0x101000, False, pid)
            if not handle:
                if ctypes.get_last_error() == 87:  # Process has already disappeared.
                    continue
                _check(False, 'OpenProcess(owned build descendant)')
            try:
                belongs = w.BOOL()
                _check(kernel.IsProcessInJob(handle, job, ctypes.byref(belongs)),
                       'IsProcessInJob(owned build descendant)')
                if belongs.value:
                    handles.append(handle)
                    handle = None
            finally:
                if handle:
                    kernel.CloseHandle(handle)
        return handles
    except BaseException:
        for handle in handles:
            kernel.CloseHandle(handle)
        raise


def quiesce(cwd: Path, *, timeout: float = 10.0) -> None:
    """Require any previous command tree to be dead before recovery touches files.

    The caller MUST hold the build directory's exclusive OS lock first. The
    source-only guardian retains an inherited share=0 lease until command-tree
    cleanup completes, including when the original CLI is hard-killed. The
    completion event additionally supports callers outside the recovery manager.
    Job disappearance and ActiveProcesses==0 alone are NOT completion witnesses.
    """
    if not isinstance(timeout, (int, float)) or not 0 < timeout <= 60:
        raise ValueError('quiescence timeout must be between zero and 60 seconds')
    kernel = _kernel()
    deadline = time.monotonic() + timeout
    event = kernel.OpenEventW(0x100000, False, _job_name(cwd) + '-guardian')
    if event:
        try:
            while True:
                status = kernel.WaitForSingleObject(event, 10)
                if status == 0:
                    break
                if status != 258:
                    _check(False, 'WaitForSingleObject(previous guardian)')
                if time.monotonic() >= deadline:
                    raise OSError('previous owned build guardian remains active; recovery refused')
        finally:
            kernel.CloseHandle(event)
    elif ctypes.get_last_error() != 2:
        _check(False, 'OpenEventW(previous guardian)')
    while True:
        job = kernel.OpenJobObjectW(4, False, _job_name(cwd))  # JOB_OBJECT_QUERY
        if not job:
            if ctypes.get_last_error() == 2:  # ERROR_FILE_NOT_FOUND: no surviving job.
                return
            _check(False, 'OpenJobObjectW(previous build)')
        kernel.CloseHandle(job)
        if time.monotonic() >= deadline:
            raise OSError('previous owned build job remains; recovery refused')
        time.sleep(0.01)


def _drain(kernel, job):
    """Do not return ownership until every command descendant has terminated."""
    # With at least one live member, a limit of one refuses every new child.
    # Existing members remain assigned. If none remain, none can spawn. Seal
    # admission before collecting handles so the death barrier covers the set.
    limits = _ExtendedLimits()
    limits.BasicLimitInformation.LimitFlags = 0x2008  # KILL_ON_CLOSE | ACTIVE_PROCESS
    limits.BasicLimitInformation.ActiveProcessLimit = 1
    _check(kernel.SetInformationJobObject(job, 9, ctypes.byref(limits),
                                         ctypes.sizeof(limits)),
           'SetInformationJobObject(close child admission)')
    members = _member_handles(kernel, job)
    try:
        _check(kernel.TerminateJobObject(job, 1), 'TerminateJobObject')
        for handle in members:
            while True:
                status = kernel.WaitForSingleObject(handle, 100)
                if status == 0:
                    break
                if status != 258:
                    _check(False, 'WaitForSingleObject(owned build descendant)')
    finally:
        for handle in members:
            kernel.CloseHandle(handle)
    # Over-limit process attempts can stay charged while process handles remain
    # open; query accounting only after the signaled snapshot handles close.
    while _active(kernel, job):
        time.sleep(0.01)


class _Cancelled(BaseException):
    pass


class _CleanupFailure(Exception):
    """The guardian must quarantine its lease instead of asserting completion."""


def _run_owned(command: list[str], *, env: dict[str, str],
               cwd: Path | None = None, owner=None, cancel=None) -> subprocess.CompletedProcess:
    """Run one owned command, inheriting stdio and raising on nonzero status.

    Unsupported atomic assignment or a denied nested job is an OSError. No
    process is ever launched without the job attribute. Normal return (and a
    catchable interruption) drains descendants before releasing ownership.
    Hard parent termination closes the only job handle in the kernel.
    """
    if (not isinstance(command, list) or not command
            or any(not isinstance(arg, str) or '\0' in arg for arg in command)
            or not command[0]):
        raise ValueError('build command must be a nonempty list of NUL-free strings')
    kernel = _kernel()
    environment = _environment(env)
    command_line = ctypes.create_unicode_buffer(subprocess.list2cmdline(command))
    directory = None if cwd is None else str(Path(cwd).resolve())
    job = _check(kernel.CreateJobObjectW(None, _job_name(cwd)), 'CreateJobObjectW')
    existing = ctypes.get_last_error() == 183  # ERROR_ALREADY_EXISTS
    handles = []
    attributes = None
    initialized = False
    process = _ProcessInfo()
    try:
        if existing and _active(kernel, job):
            raise OSError('previous owned build process tree remains active; command refused')
        limits = _ExtendedLimits()
        limits.BasicLimitInformation.LimitFlags = 0x2000  # KILL_ON_JOB_CLOSE; no breakaway.
        _check(kernel.SetInformationJobObject(job, 9, ctypes.byref(limits),
                                             ctypes.sizeof(limits)),
               'SetInformationJobObject(KILL_ON_JOB_CLOSE)')
        handles = _standard_handles(kernel)
        size = ctypes.c_size_t()
        kernel.InitializeProcThreadAttributeList(None, 2, 0, ctypes.byref(size))
        if not size.value:
            _check(False, 'InitializeProcThreadAttributeList(size)')
        attributes = ctypes.create_string_buffer(size.value)
        _check(kernel.InitializeProcThreadAttributeList(attributes, 2, 0,
                                                       ctypes.byref(size)),
               'InitializeProcThreadAttributeList')
        initialized = True
        # Keep the attribute value arrays alive until the list is deleted.
        jobs = (w.HANDLE * 1)(job)
        inherited = (w.HANDLE * 3)(*handles)
        _check(kernel.UpdateProcThreadAttribute(attributes, 0, 0x2000d, jobs,
                                                ctypes.sizeof(jobs), None, None),
               'UpdateProcThreadAttribute(JOB_LIST); atomic assignment required')
        _check(kernel.UpdateProcThreadAttribute(attributes, 0, 0x20002, inherited,
                                                ctypes.sizeof(inherited), None, None),
               'UpdateProcThreadAttribute(HANDLE_LIST)')
        startup = _StartupInfoEx()
        startup.StartupInfo.cb = ctypes.sizeof(startup)
        startup.StartupInfo.dwFlags = 0x100  # STARTF_USESTDHANDLES
        startup.StartupInfo.hStdInput, startup.StartupInfo.hStdOutput, startup.StartupInfo.hStdError = handles
        startup.lpAttributeList = ctypes.cast(attributes, w.LPVOID)
        flags = 0x80000 | 0x400 | 0x8000000  # EXTENDED_STARTUPINFO, UNICODE_ENV, NO_WINDOW
        _check(kernel.CreateProcessW(None, command_line, None, None, True, flags,
                                     environment, directory, ctypes.byref(startup),
                                     ctypes.byref(process)),
               'CreateProcessW(atomic build job assignment)')
        # Short waits preserve Python signal/KeyboardInterrupt handling.
        while True:
            if ((owner and kernel.WaitForSingleObject(owner, 0) == 0)
                    or (cancel and kernel.WaitForSingleObject(cancel, 0) == 0)):
                raise _Cancelled()
            status = kernel.WaitForSingleObject(process.hProcess, 100)
            if status == 0:
                break
            if status != 258:  # WAIT_TIMEOUT
                _check(False, 'WaitForSingleObject')
        exit_code = w.DWORD()
        _check(kernel.GetExitCodeProcess(process.hProcess, ctypes.byref(exit_code)),
               'GetExitCodeProcess')
        if exit_code.value:
            raise subprocess.CalledProcessError(exit_code.value, command)
        return subprocess.CompletedProcess(command, 0)
    finally:
        try:
            if process.hProcess:
                try:
                    _drain(kernel, job)
                except BaseException as exc:
                    raise _CleanupFailure(f'command-tree cleanup was not proven: {exc}') from exc
        finally:
            if process.hThread:
                kernel.CloseHandle(process.hThread)
            if process.hProcess:
                kernel.CloseHandle(process.hProcess)
            if initialized:
                kernel.DeleteProcThreadAttributeList(attributes)
            for handle in handles:
                kernel.CloseHandle(handle)
            kernel.CloseHandle(job)


def _duplicate(kernel, handle):
    current = kernel.GetCurrentProcess()
    duplicate = w.HANDLE()
    _check(kernel.DuplicateHandle(current, handle, current, ctypes.byref(duplicate),
                                  0, True, 2), 'DuplicateHandle(guardian capability)')
    return duplicate.value


def run(command: list[str], *, env: dict[str, str],
        cwd: Path | None = None) -> subprocess.CompletedProcess:
    """Run a command through a cleanup guardian that survives CLI hard-death.

    Actual compiler processes use atomic JOB_LIST assignment in _run_owned.
    The guardian runs this absolute source file with Python -I -S -B; no project
    imports, bytecode or site hooks execute. A share=0 directory lease registered
    by the recovery manager is inherited only by the guardian. The completion
    event and private pipes carry ownership/result capabilities, not artifacts.

    This protocol assumes cooperative source and filesystem ownership. A hostile
    process that kills the guardian or changes files outside the directory lock
    is outside the recovery/cache protocol, as is a hostile OS or storage device.
    """
    if (not isinstance(command, list) or not command
            or any(not isinstance(arg, str) or '\0' in arg for arg in command)
            or not command[0]):
        raise ValueError('build command must be a nonempty list of NUL-free strings')
    kernel = _kernel()
    _environment(env)  # Validate before starting even the guardian.
    import msvcrt

    event = _check(kernel.CreateEventW(None, True, False, _job_name(cwd) + '-guardian'),
                   'CreateEventW(guardian completion)')
    existing = ctypes.get_last_error() == 183
    handles, descriptors = [], []
    process = None
    try:
        if existing:
            if kernel.WaitForSingleObject(event, 0) != 0:
                raise OSError('previous owned build guardian remains active; command refused')
            _check(kernel.ResetEvent(event), 'ResetEvent(guardian completion)')
        cancel = _check(kernel.CreateEventW(None, True, False, None), 'CreateEventW(cancel)')
        handles.append(cancel)
        owner = _check(kernel.OpenProcess(0x100000, False, os.getpid()),
                       'OpenProcess(original build owner)')
        handles.append(owner)
        inherited = _standard_handles(kernel)
        handles.extend(inherited)
        request_read, request_write = os.pipe()
        response_read, response_write = os.pipe()
        descriptors.extend((request_read, request_write, response_read, response_write))
        capabilities = []
        for handle in (msvcrt.get_osfhandle(request_read), msvcrt.get_osfhandle(response_write),
                       owner, event, cancel):
            duplicate = _duplicate(kernel, handle)
            handles.append(duplicate)
            capabilities.append(duplicate)
        read_handle, write_handle, owner_handle, event_handle, cancel_handle = capabilities
        lease = _directory_leases.get(_job_name(cwd))
        lease_handle = _duplicate(kernel, lease) if lease is not None else 0
        if lease_handle:
            handles.append(lease_handle)
        startup = subprocess.STARTUPINFO()
        startup.dwFlags |= subprocess.STARTF_USESTDHANDLES
        startup.hStdInput, startup.hStdOutput, startup.hStdError = inherited
        startup.lpAttributeList = {'handle_list': inherited + [read_handle, write_handle,
            owner_handle, event_handle, cancel_handle] + ([lease_handle] if lease_handle else [])}
        guardian = [sys.executable, '-I', '-S', '-B', str(Path(__file__).resolve()),
                    '--guardian', str(read_handle), str(write_handle), str(owner_handle),
                    str(event_handle), str(cancel_handle), str(lease_handle)]
        process = subprocess.Popen(guardian, startupinfo=startup, close_fds=True,
                                   creationflags=subprocess.CREATE_NO_WINDOW)
        # Parent copies of guardian pipe ends must not keep EOF/leases alive.
        for handle in (read_handle, write_handle, owner_handle, event_handle, cancel_handle, lease_handle):
            if handle:
                kernel.CloseHandle(handle)
                handles.remove(handle)
        os.close(request_read)
        descriptors.remove(request_read)
        os.close(response_write)
        descriptors.remove(response_write)
        payload = json.dumps(dict(command=command, env=env,
                                  cwd=None if cwd is None else str(Path(cwd).resolve())),
                             ensure_ascii=False).encode('utf-8')
        with os.fdopen(request_write, 'wb') as stream:
            descriptors.remove(request_write)
            stream.write(payload)
        while True:
            try:
                process.wait(timeout=.1)
                break
            except subprocess.TimeoutExpired:
                pass
        with os.fdopen(response_read, 'rb') as stream:
            descriptors.remove(response_read)
            raw_response = stream.read()
        if kernel.WaitForSingleObject(event, 0) != 0 or not raw_response:
            raise OSError('build guardian exited without proving command-tree cleanup')
        response = json.loads(raw_response)
        if response['kind'] == 'oserror':
            raise OSError(response.get('errno'), response['message'], None, response.get('winerror'))
        if response['kind'] != 'exit':
            raise OSError(response['message'])
        if response['returncode']:
            raise subprocess.CalledProcessError(response['returncode'], command)
        return subprocess.CompletedProcess(command, 0)
    except BaseException:
        if process is not None and process.poll() is None:
            kernel.SetEvent(cancel)
            for descriptor in descriptors[:]:
                os.close(descriptor)
                descriptors.remove(descriptor)
            # Retain both parent and inherited guardian lease until cleanup.
            process.wait()
        raise
    finally:
        for descriptor in descriptors:
            os.close(descriptor)
        for handle in handles:
            kernel.CloseHandle(handle)
        kernel.CloseHandle(event)


def _guardian_main():
    import msvcrt

    read_handle, write_handle, owner, completed, cancelled, lease = map(int, sys.argv[2:])
    kernel = _kernel()
    response = None
    clean = False
    try:
        with os.fdopen(msvcrt.open_osfhandle(read_handle, os.O_RDONLY | os.O_BINARY), 'rb') as stream:
            request = json.load(stream)
        if kernel.WaitForSingleObject(owner, 0) == 0:
            response = dict(kind='exit', returncode=1)
            clean = True  # No command launched after owner death.
        else:
            try:
                _run_owned(request['command'], env=request['env'],
                           cwd=None if request['cwd'] is None else Path(request['cwd']),
                           owner=owner, cancel=cancelled)
                response = dict(kind='exit', returncode=0)
            except subprocess.CalledProcessError as exc:
                response = dict(kind='exit', returncode=exc.returncode)
            except _Cancelled:
                response = dict(kind='exit', returncode=1)
            except OSError as exc:
                response = dict(kind='oserror', errno=exc.errno,
                                winerror=getattr(exc, 'winerror', None), message=str(exc)[:500])
            clean = True
    except BaseException as exc:
        response = dict(kind='error', message=f'guardian: {type(exc).__name__}: {str(exc)[:500]}')
    finally:
        if clean:
            kernel.SetEvent(completed)
        elif lease:
            # Preserve refusal across the guardian/CLI lifetime. The recovery
            # manager accepts only an empty share=0 lockfile, so a failed drain
            # can never become a later successful "job no longer exists" check.
            marker = _duplicate(kernel, lease)
            with os.fdopen(msvcrt.open_osfhandle(marker, os.O_BINARY | os.O_WRONLY), 'wb',
                           buffering=0) as stream:
                stream.seek(0)
                stream.write(b'PCERECOMP_UNPROVEN_PROCESS_CLEANUP_V1\n')
                stream.flush()
                os.fsync(stream.fileno())
        try:
            with os.fdopen(msvcrt.open_osfhandle(write_handle, os.O_WRONLY | os.O_BINARY), 'wb') as stream:
                stream.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))
        except OSError:
            pass  # Original owner may already be dead; the inherited lease still drains.
        for handle in (owner, completed, cancelled, lease):
            if handle:
                kernel.CloseHandle(handle)
    return 0 if clean else 1


if __name__ == '__main__':
    if len(sys.argv) != 8 or sys.argv[1] != '--guardian':
        raise SystemExit('This source entry point is reserved for the build guardian')
    raise SystemExit(_guardian_main())
