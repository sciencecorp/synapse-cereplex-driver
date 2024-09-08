import logging
from synapse.generated.api.status_pb2 import (
    Status as PBStatus,
    StatusCode as PBStatusCode,
)

StatusCode = PBStatusCode


class Status(object):
    def __init__(self, code=PBStatusCode.kOk, message=""):
        self._code = code
        self._message = message

    def code(self):
        return self._code

    def message(self):
        return self._message

    def ok(self):
        return self._code == PBStatusCode.kOk

    @staticmethod
    def from_proto(proto: PBStatus):
        return Status(proto.code, proto.message)

    @staticmethod
    def log(code: PBStatusCode, message: str):
        logging.warn(f"({code}): {message}")
        return Status(code, message)

    def to_proto(self):
        return PBStatus(
            code=self._code,
            message=self._message,
        )
