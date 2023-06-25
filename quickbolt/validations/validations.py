import re
from difflib import Differ
from pathlib import Path
from typing import Any

import quickbolt.reporting.response_csv as rc
import quickbolt.utils.dictionary as dh
import quickbolt.utils.directory as drh
from quickbolt.logging import AsyncLogger


class Validations(object):
    """
    This is the class that hold all the ways we gather and use information for validations.
    """

    def __init__(self, debug: bool = False, root_dir: None | str = None):
        """
        The constructor for Validations.

        Args:
            debug: Whether to catch exceptions in the fail method.
            root_dir: The specified root directory.
        """
        self.debug = debug
        self.logging = AsyncLogger(root_dir=root_dir)
        self.logger = self.logging.logger

        root_dir = root_dir or drh.get_root_dir()
        root_dir = Path(root_dir)

        app_dir = drh.get_src_app_dir(root_dir=root_dir)
        app_dir = Path(app_dir)

        path_diff = app_dir.relative_to(root_dir)
        path_diff = Path(str(path_diff).replace("tests/", ""))

        validations_dir = str(root_dir / "validations" / path_diff)
        refs_dir = next(
            (ref for ref in root_dir.rglob("*") if validations_dir in str(ref)),
            None,
        )
        self.refs_paths = (
            [str(ref) for ref in refs_dir.rglob("*.csv")] if refs_dir else []
        )

    async def validate_references(
        self,
        actual_refs: str,
        expected_refs: None | str = None,
        safe: bool = True,
    ) -> list[dict]:
        """
        This validates stored json responses. Unfortunately if actual_refs is a string
        the expected_refs must be passed.

        Args:
            actual_refs: The actual (current) path of refs to validate.
            expected_refs: The expected (stored) path of refs to use as a reference.
            safe: Whether to raise an error on mismatches.

        Returns:
            mismatches: A record of any mismatching keys and or values.
        """
        await self.logger.info(f"Validating references for {actual_refs}.")

        live_file = Path(actual_refs).name
        _actual_refs = await rc.csv_to_dict(str(actual_refs))

        _expected_refs = expected_refs or next(
            (Path(r) for r in self.refs_paths if Path(r).name == live_file), []
        )
        if _expected_refs:
            _expected_refs = await rc.csv_to_dict(str(_expected_refs))

        if len(_actual_refs) != len(_expected_refs):
            message = (
                f"Test completed HOWEVER, verification isn't possible as the "
                f"actual and expected reference files aren't the same size."
            )
            await self.fail(message)

        unscrubbed_refs = await rc.csv_to_dict(
            actual_refs.replace("_scrubbed.csv", ".csv")
        )

        differ = Differ()
        mismatches = []
        for u_refs, a_refs, e_refs in zip(
            unscrubbed_refs, _actual_refs, _expected_refs
        ):
            errors = dh.compare_dictionaries(
                a_refs, e_refs, exclusive_keys=["ACTUAL_CODE", "MESSAGE"]
            )

            e_values = errors.get("values")
            if e_values:
                e_val_copy = e_values[:]
                for e in e_val_copy:
                    if "json." in e["key"].lower() and re.findall(
                        r"[._](url|icon|manifest)", e["key"].lower()
                    ):
                        diffs = differ.compare(e["d1"], e["d2"])
                        diffs = [
                            re.sub(r"[-+]\s+", "", d)
                            for d in diffs
                            if "- " in d or "+ " in d
                        ]

                        if not all(keyword in diffs for keyword in ["stg", "dev"]):
                            e_values = [ev for ev in e_values if ev != e]

            if errors.get("keys") or e_values:
                errors["unscrubbed_refs"] = u_refs
                errors["actual_refs"] = a_refs
                errors["expected_refs"] = e_refs
                mismatches.append(errors)

        if mismatches and not safe:
            await self.fail(f"Validated references with mismatches {mismatches}.")

        await self.logger.info(f"Validated references for {actual_refs}.")
        return mismatches

    async def fail(self, error_message: str, exception: Any = Exception):
        """
        This fails a test.

        Args:
            error_message: The failure message to log.
            exception: The python exception to raise.
        """
        await self.logger.error(error_message)
        try:
            raise exception(error_message)
        except exception:
            if self.debug:
                await self.logger.error("Debugging the raise.\n")
            else:
                raise
