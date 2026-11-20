"""Print Star Citizen's local telemetry stream: one line per field whose value changed.

Setup, once, in the folder that holds sc_telemetry_v1.proto (Windows shown; on Linux use python3):
    py -m pip install grpcio grpcio-tools
    py -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. sc_telemetry_v1.proto

Run, with the game running and telemetry switched on (see the README):
    py read_telemetry.py
    py read_telemetry.py --list-actions        (5.0 only: the actions tools may trigger)
Stop with Ctrl+C.
"""
import argparse
import threading

import grpc
from google.protobuf.json_format import MessageToDict

import sc_telemetry_v1_pb2 as pb
import sc_telemetry_v1_pb2_grpc as pb_grpc


def flatten(value, prefix="", out=None):
    """Turn nested dicts and lists into {"actor.vitals.heart_rate": 60.0, ...}."""
    if out is None:
        out = {}
    if isinstance(value, dict):
        for key, item in value.items():
            flatten(item, f"{prefix}{key}.", out)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            flatten(item, f"{prefix}{index}.", out)
    else:
        out[prefix[:-1]] = value
    return out


def stream(stub):
    call = stub.TelemetryStream(pb.TelemetryStreamRequest())
    hint = threading.Timer(15, lambda: print(
        "No frame yet. Frames start once you have spawned; if you have, the game is not sending telemetry.", flush=True))
    hint.daemon = True
    hint.start()
    previous = {}
    try:
        for frame in call:
            hint.cancel()
            # Every frame is a full snapshot. A field holding its default (0, false, "") is not sent at all,
            # so a field that disappears has gone back to its default.
            current = flatten(MessageToDict(frame, preserving_proto_field_name=True))
            for key in sorted(current.keys() | previous.keys()):
                if current.get(key) != previous.get(key):
                    print(f"{key} = {current.get(key, '(not sent: default)')}", flush=True)
            previous = current
        print("The game ended the stream.")
    except KeyboardInterrupt:
        call.cancel()
    finally:
        hint.cancel()


def list_actions(stub):
    reply = stub.ListTriggerableActions(pb.ListTriggerableActionsRequest(), timeout=5)
    for action in reply.actions:
        holdable = ", holdable" if action.holdable else ""
        print(f"{action.action_name}  ({action.category}{holdable})")
    print(f"{len(reply.actions)} actions")


def main():
    parser = argparse.ArgumentParser(description="Read Star Citizen's local telemetry stream.")
    parser.add_argument("--address", default="127.0.0.1:2942", help="host:port of the game (default 127.0.0.1:2942)")
    parser.add_argument("--list-actions", action="store_true", help="list the triggerable actions instead (5.0)")
    args = parser.parse_args()
    with grpc.insecure_channel(args.address) as channel:
        stub = pb_grpc.GameTelemetryServiceStub(channel)
        try:
            if args.list_actions:
                list_actions(stub)
            else:
                stream(stub)
        except grpc.RpcError as error:
            print(f"gRPC error: {error.code().name}: {error.details()}")
            if error.code() == grpc.StatusCode.UNAVAILABLE:
                print(f"Nothing answered on {args.address}. Is the game running with telemetry switched on?")


if __name__ == "__main__":
    main()
