import asyncio
import os as sos
import re
from datetime import datetime
from pathlib import Path
from shutil import rmtree
from typing import Generator

import __main__ as main
from aiofiles import open as aopen
from aiologger import Logger
from aiologger.formatters.base import Formatter
from aiologger.handlers.files import AsyncFileHandler

import quickbolt.utils.directory as dh


class AsyncLogger(object):
    """
    This is a wrapper around the async aio logging module.
    """

    def __init__(self, root_dir: None | str = None, by_time: bool = False) -> Logger:
        """
        This gets the logger.

        Args:
            by_time: Whether to keep all successive runs by time.
            root_dir: The specified root directory.

        Returns:
            logger: The logger to use for logging.
        """
        self.logger = Logger(level="INFO")

        self.root_dir = root_dir or dh.get_root_dir()
        self.log_file_path = self.get_log_path(by_time)

        log_file_path_parts = Path(self.log_file_path).parts
        index = log_file_path_parts.index("run_info")
        run_info_path = Path(*log_file_path_parts[: index + 1]).as_posix()
        self.run_info_path = str(run_info_path)

        self.set_logger_handler(filename=self.log_file_path)

    def get_log_path(self, by_time: bool = False) -> str:
        """
        This gets the logging directories and file paths.

        Args:
            by_time: Whether to keep all successive runs by time.

        Returns:
            log_file_path: The path of the log file to write to.
        """
        calling_test = (
            sos.environ.get("PYTEST_CURRENT_TEST")
            or getattr(main, "__file__", None)
            or getattr(main, "path", None)
        )
        calling_test = Path(calling_test.split("::")[0])

        root_path = Path(self.root_dir)
        file_path = next(
            (f for f in root_path.rglob("*") if str(calling_test) in str(f)), None
        )

        if file_path:
            tests_index = next(
                (
                    i
                    for i in reversed(range(len(file_path.parts)))
                    if "tests" in file_path.parts[i]
                ),
                None,
            )

            file_path = (
                root_path
                / "run_info/run_logs"
                / Path(*file_path.parts[tests_index + 1 :])
            )
        else:
            file_path = root_path / "run_info/run_logs" / Path(*calling_test.parts[1:])

        log_dir = file_path.parent
        log_dir_path_pass = log_dir / "pass"
        log_dir_path_fail = log_dir / "fail"
        self.log_dir = str(log_dir)

        dh.safe_mkdirs_sync(str(log_dir_path_pass))
        dh.safe_mkdirs_sync(str(log_dir_path_fail))

        filename = re.sub(r"test_|.py", "", file_path.name)
        if by_time:
            filename += f"_{datetime.now().strftime('%Y-%m-%d_%H:%M:%S')}"

        return f"{log_dir_path_pass}/{filename}.log"

    def set_logger_handler(self, filename: str, options: None | str = None):
        """
        This (re)sets the logging handler.

        Args:
            filename: The filename of the log file.
            options: The logging options for each line written.

        Returns:
            logging: The updated logging module.
        """
        if not options:
            options = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"

        handler = AsyncFileHandler(filename)
        handler.formatter = Formatter(options)
        self.logger.add_handler(handler)

    async def shutdown(self):
        await self.logger.shutdown()

    async def delete_run_info(self, path: None | str = None):
        """
        This deletes the run info folder.

        Args:
            path: A custom path that contains logs to be deleted.
        """
        path = path or self.run_info_path
        await asyncio.to_thread(rmtree, path)

    async def read_log_file(self, path: None | str = None) -> Generator:
        """
        This reads a log file.

        Args:
            path: A custom path to a log file.

        Returns:
            file: A generator to the log file
        """
        path = path or self.log_file_path
        async with aopen(path) as f:
            async for line in f:
                yield line
