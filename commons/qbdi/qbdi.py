import os
import shutil
import stat
import typing

import docker
from docker.models.containers import ExecResult

from commons.arguments import ArgumentsPair

IMAGE_TAG = "qbdi_args_fuzzing"
HOST_FOLDER = "/tmp/qbdi/"
HOST_DICTIONARIES_FOLDER = HOST_FOLDER + "dictionaries/"
HOST_EXECUTABLE_FOLDER = HOST_FOLDER + "target/"
HOST_EXECUTABLE = HOST_EXECUTABLE_FOLDER + "target"
HOST_RESULTS_FOLDER = HOST_FOLDER + "results/"
CONTAINER_EXECUTABLE_FOLDER = "/home/docker/target/"
CONTAINER_EXECUTABLE = CONTAINER_EXECUTABLE_FOLDER + "target"
CONTAINER_RESULTS_FOLDER = "/home/docker/results/"
CONTAINER_TEMP_FILE = "/tmp/canary.opencrs"


class RawQBDIAnalysisResult:
    bbs_count: int
    bbs_hash: int
    uses_file: bool
    exit_code: int

    def __init__(
        self, bbs_count: int, bbs_hash: int, uses_file: bool, exit_code: int
    ) -> None:
        self.bbs_count = bbs_count
        self.bbs_hash = bbs_hash
        self.uses_file = uses_file
        self.exit_code = exit_code


class QBDIAnalysisResult(RawQBDIAnalysisResult):
    uses_stdin: bool

    def __init__(
        self,
        bbs_count: int,
        bbs_hash: int,
        uses_file: bool,
        exit_code: int,
        uses_stdin: bool,
    ) -> None:
        super().__init__(bbs_count, bbs_hash, uses_file, exit_code)

        self.uses_stdin = uses_stdin


class QBDIAnalysis:
    __docker_client: docker.client
    __container: docker.api.container
    executable_filename: str
    timeout: int

    def __init__(self, executable_filename: str, timeout: int) -> None:
        self.executable_filename = executable_filename
        self.timeout = timeout

        self.__docker_client = docker.from_env()
        self.__create_container()

    def __del__(self) -> None:
        self.__container.remove(force=True)

    def __touch_nested_folder(self, folder_name: str) -> None:
        try:
            os.makedirs(folder_name)
        except FileExistsError:
            shutil.rmtree(folder_name)
            os.makedirs(folder_name)

    def __create_temporary_folder_structure(self) -> None:
        self.__touch_nested_folder(HOST_FOLDER)
        self.__touch_nested_folder(HOST_EXECUTABLE_FOLDER)
        self.__touch_nested_folder(HOST_RESULTS_FOLDER)
        shutil.copyfile(self.executable_filename, HOST_EXECUTABLE)
        os.chmod(HOST_EXECUTABLE, stat.S_IXUSR)

    def __create_container(self) -> None:
        self.__create_temporary_folder_structure()

        self.__container = self.__docker_client.containers.run(
            IMAGE_TAG,
            command="tail -f /dev/null",
            detach=True,
            tty=True,
            volumes={
                HOST_EXECUTABLE_FOLDER: {
                    "bind": CONTAINER_EXECUTABLE_FOLDER,
                    "mode": "rw",
                },
                HOST_RESULTS_FOLDER: {
                    "bind": CONTAINER_RESULTS_FOLDER,
                    "mode": "rw",
                },
            },
        )

        self.__container.exec_run(f"sudo chmod 555 {CONTAINER_EXECUTABLE}")

    def create_temp_file_inside_container(self) -> str:
        self.__container.exec_run(f"touch {CONTAINER_TEMP_FILE}")

        return CONTAINER_TEMP_FILE

    def __build_and_run_analyze_command(
        self, argument: ArgumentsPair, timeout_retry: bool
    ) -> ExecResult:
        command = self.__build_analyze_command(argument, timeout_retry)

        return self.__container.exec_run(
            command,
            workdir="/home/docker",
        )

    def __build_analyze_command(
        self, argument: ArgumentsPair, timeout_retry: bool
    ) -> str:
        stringified_arguments = argument.to_str()
        stdin_avoidance_command = "echo '\n' |" if timeout_retry else ""

        return (
            f"timeout {self.timeout} sh -c "
            f"'{stdin_avoidance_command} LD_BIND_NOW=1 "
            "LD_PRELOAD=./libqbdi_tracer.so "
            f"{CONTAINER_EXECUTABLE} "
            f"{stringified_arguments}'"
        )

    def __get_analysis_result_filename(self, argument: ArgumentsPair) -> str:
        argument_identifier = argument.to_hex_id()

        return os.path.join(HOST_RESULTS_FOLDER, argument_identifier)

    @staticmethod
    def __parse_raw_output(filename: str) -> typing.Tuple[int, int, int]:
        try:
            with open(filename, "r", encoding="utf-8") as qbdi_output:
                analysis = qbdi_output.read()

                info = analysis.split(" ")
                info = [int(e) for e in info]

                return tuple(info)
        except FileNotFoundError:
            return (None, None, None)

    def __run_analysis(
        self, argument: ArgumentsPair, timeout_retry: bool = False
    ) -> RawQBDIAnalysisResult:
        raw_result = self.__build_and_run_analyze_command(
            argument, timeout_retry
        )

        result_filename = self.__get_analysis_result_filename(argument)
        bbs_count, bbs_hash, uses_file = self.__parse_raw_output(
            result_filename
        )

        return RawQBDIAnalysisResult(
            bbs_count, bbs_hash, uses_file, raw_result.exit_code
        )

    def __detect_stdin_usage(
        self,
        argument: ArgumentsPair,
        raw_analysis: RawQBDIAnalysisResult,
        timeout_retry: bool,
    ) -> bool:
        is_timeout = raw_analysis.exit_code == 124
        if timeout_retry and not is_timeout:
            return True
        elif not timeout_retry and is_timeout:
            return self.analyze(argument, timeout_retry=True)
        else:
            return False

    def analyze(
        self, argument: ArgumentsPair, timeout_retry: bool = False
    ) -> QBDIAnalysisResult:
        raw_analysis = self.__run_analysis(argument, timeout_retry)
        uses_stdin = self.__detect_stdin_usage(
            argument,
            raw_analysis,
            timeout_retry,
        )

        return QBDIAnalysisResult(
            raw_analysis.bbs_count,
            raw_analysis.bbs_hash,
            raw_analysis.uses_file,
            raw_analysis.exit_code,
            uses_stdin,
        )
