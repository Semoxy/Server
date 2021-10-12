"""
A class for abstracting away sending commands to and receiving output from the server
"""
import asyncio
import locale
import os
import subprocess
import threading
from typing import Tuple, Optional

import psutil

CPU_COUNT = psutil.cpu_count()
PYTHON_PROCESS = psutil.Process(os.getpid())
SYSTEM_RAM = int(psutil.virtual_memory().total / 1000)


class ServerCommunication:
    """
    A class for abstracting away sending commands to and receiving output from the server
    """
    __slots__ = "loop", "command", "cwd", "process", "on_output", "on_close", "running", "on_stderr", "shell"

    @classmethod
    def get_system_resource_usage(cls) -> Tuple[int, float]:
        """
        collects information about the current resource usage of this python process

        Return Values:
            ram: the ram that is currently used by this python process (in kB)
            cpu: the cpu usage of this python process (in percent)

        :return: Tuple[ram, system_ram, cpu]
        """

        with PYTHON_PROCESS.oneshot():
            cpu = round(PYTHON_PROCESS.cpu_percent() / CPU_COUNT, 2)
            ram = int(PYTHON_PROCESS.memory_info().rss / 1000)

        return ram, cpu

    def __init__(self, loop, command, on_output, on_stderr, on_close, cwd=".", shell=False):
        """
        :param command: the command to start the server with
        :param cwd: the working directory for the server
        :param on_output: called with the line as only argument on server console output
        :param on_close: called when the server closed
        """
        self.loop = loop
        self.command = command
        self.cwd = cwd
        self.process: Optional[psutil.Popen] = None
        self.on_output = on_output
        self.on_close = on_close
        self.running = False
        self.on_stderr = on_stderr
        self.shell = shell

    async def begin(self) -> None:
        """
        starts the server
        """
        self.process = psutil.Popen(self.command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, cwd=self.cwd, stderr=subprocess.PIPE, shell=self.shell)
        self.running = True
        StreamWatcher(self.loop, self.process.stdout, self.process, self.on_output, self.on_close).start()
        StreamWatcher(self.loop, self.process.stdout, self.process, self.on_stderr, None).start()

    def get_resource_usage(self) -> Tuple[int, float]:
        """
        gets the ram usage and cpu time of the process

        Return Values:
            ram: the ram that is used by the subprocess (in kB)
            cpu: the cpu usage of the subprocess (in percent)

        :return: Tuple[ram, cpu]
        """
        with self.process.oneshot():
            cpu = round(self.process.cpu_percent() / CPU_COUNT, 2)
            ram = int(self.process.memory_info().rss / 1000)
        return ram, cpu

    async def process_end(self):
        self.running = False
        await self.on_close()

    def write_stdin_sync(self, cmd):
        """
        writes a command to server stdin and flushes it
        :param cmd: the command to send
        """
        if not self.running:
            return

        line = str(cmd).encode(locale.getpreferredencoding()) + b'\n'
        self.process.stdin.write(line)
        self.process.stdin.flush()

    async def write_stdin(self, cmd) -> None:
        self.write_stdin_sync(cmd)


class StreamWatcher(threading.Thread):
    """
    watches a stream like a stdout for new lines and calls callbacks
    """
    __slots__ = "loop", "stream", "proc", "on_close", "on_out"

    def __init__(self, loop, stream, proc, on_out, on_close):
        super(StreamWatcher, self).__init__()
        self.loop = loop
        self.stream = stream
        self.proc = proc
        self.on_close = on_close
        self.on_out = on_out

    def run(self) -> None:
        for line in iter(self.stream.readline, ""):
            if self.proc.poll() is not None:
                break
            if line:
                line = line.decode(locale.getpreferredencoding())
                asyncio.run_coroutine_threadsafe(self.on_out(line), self.loop)
        if self.on_close is not None:
            asyncio.run_coroutine_threadsafe(self.on_close(), self.loop)
