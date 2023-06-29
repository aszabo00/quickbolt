import asyncio
import re
import sys
import traceback
from pathlib import Path
from shutil import move

import aiofiles.os as aos
import pytest

import quickbolt.reporting.response_csv as rc
import quickbolt.utils.directory as dh
import quickbolt.utils.json as jh
from quickbolt.validations import Validations


class CorePytestBase(object):
    root_dir: str = dh.get_root_dir()
    csv_path: None | str = None
    tests_data: None | dict = None
    credentials_data: None | dict = None
    error_file_path: None | str = None

    # Custom on-end options to be run as part of the teardown
    purge_run_info: bool = False
    debug: bool = False
    validate: bool = True
    validations: None | Validations = None

    async def set_data(self, dir_path: str):
        data_dir = Path(self.root_dir) / dir_path
        files = [p for p in data_dir.rglob("*") if p.suffix == ".json"]

        data = {
            f.stem: {
                "data": await dh.load_json(str(f)),
                "path": str(f),
            }
            for f in files
        }

        setattr(CorePytestBase, f"{dir_path}_data", data)

    async def handle_errors(self):
        trace = [
            t for t in traceback.format_tb(sys.last_traceback) if self.root_dir in t
        ]
        trace = "".join(trace + [f"\t{sys.last_value}"])
        self.validations.logger.error(f"\n{trace}")

        log_file_path = Path(self.validations.logging.log_file_path)
        new_log_file_path = log_file_path.parent.parent / "fail" / log_file_path.name
        await asyncio.to_thread(move, log_file_path, new_log_file_path)

        csv_path = Path(self.csv_path)
        new_csv_path = csv_path.parent.parent / "fail" / csv_path.name
        asyncio.to_thread(move, csv_path, new_csv_path)

        scrubbed_csv_path = csv_path.with_stem(csv_path.stem + "_scrubbed")
        new_scrubbed_csv_path = new_csv_path.with_stem(new_csv_path.stem + "_scrubbed")
        asyncio.to_thread(move, scrubbed_csv_path, new_scrubbed_csv_path)

        self.csv_path = str(new_csv_path)

        await rc.add_rows_to_csv_report(self.csv_path, f"{trace}")
        await rc.add_rows_to_csv_report(
            self.csv_path.replace(".csv", "_scrubbed.csv"), f"{trace}"
        )

    async def validate_mismatches(self):
        if not getattr(CorePytestBase, "validations"):
            self.validations = Validations(debug=self.debug, root_dir=self.root_dir)

        mismatches = await self.validations.validate_references(
            self.csv_path.replace(".csv", "_scrubbed.csv")
        )
        if mismatches:
            rows = []
            for m in mismatches:
                header_set = set(m["actual_refs"].keys()) | set(
                    m["expected_refs"].keys()
                )
                headers = [""] + list(header_set)
                if not rows:
                    rows.append(headers)

                keys_set = set(
                    ["expected_refs", "actual_refs", "unscrubbed_refs"]
                ) | set(m.keys())
                for k in keys_set:
                    if "skip" not in k:
                        if isinstance(m[k], dict):
                            rows.append([k] + [m[k].get(h, "") for h in headers[1:]])
                        else:
                            rows.append([f"error_{k}"] + [jh.serialize((m[k]))])
                rows.append([""])

            error_file_path = re.sub(
                r"/run_logs/",
                "/run_errors/",
                self.csv_path.replace(".csv", "_errors.csv"),
            )
            self.error_file_path = re.sub(r"/pass/|/fail/", "/", error_file_path)
            error_dir = Path(self.error_file_path).parent

            await dh.safe_mkdirs(error_dir)
            await rc.add_rows_to_csv_report(self.error_file_path, rows)

    async def purge_run_info_dirs(self):
        run_info_path = self.validations.logging.run_info_path
        await self.validations.logging.delete_run_info()
        assert not await aos.path.exists(run_info_path)

    async def core_teardown(self):
        last_value = sys.__dict__.get("last_value")
        if last_value and "exit" not in last_value.args[0]:
            await self.handle_errors()

        if self.validate and "/fail/" not in self.csv_path:
            await self.validate_mismatches()

        if self.purge_run_info:
            await self.purge_run_info_dirs()

    @pytest.fixture(autouse=True, scope="class")
    async def core_setup_teardown(self):
        await self.set_data("tests")
        await self.set_data("credentials")

        yield

        await self.core_teardown()
