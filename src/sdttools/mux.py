from typing import BinaryIO, Optional
import struct
import os
from string import hexdigits

from .utils import chunks, get_u32_le
from .types import PathType
from .demux import extmap

parammap = {v: k for k, v in extmap.items()}
parammap[".mp4"] = parammap[".m2v"]
parammap[".dmx"] = 0x00000005  # multiple dmx entries in extmap, ensure consistency

INIT = 0  # Initialize stream
HEAD = 1  # Header chunk
DATA = 2  # Other chunks
# (rid, type_to_write, amt_to_write)
# -1 gets substituted on header read when appropriate
# 0 for all in one chunk
expected_order: list[tuple[int, int, int]] = [
    (parammap[".pacb"], INIT, 0),
    (parammap[".pacb"], DATA, 0),
    (parammap[".m2v"],  INIT, 0),
    (parammap[".mtaf"], INIT, 0),
    (parammap[".mtaf"], HEAD, 0x800),
    (parammap[".mtaf"], DATA, 0x3FC0),
    (parammap[".xwma"], INIT, 0),
    (parammap[".xwma"], HEAD, -1),
    (parammap[".xwma"], DATA, -1),
    (parammap[".m2v"],  DATA, 0x10000),
    (parammap[".dmx"],  INIT, 0),
    (0x00010006,        INIT, 0),
    (0x00030006,        INIT, 0),
    (0x00020006,        INIT, 0),
    (0x00040006,        INIT, 0),
    (0x00050006,        INIT, 0),
    (0x00070006,        INIT, 0),
    (0x00010006,        DATA, 0),
    (0x00030006,        DATA, 0),
    (0x00020006,        DATA, 0),
    (0x00040006,        DATA, 0),
    (0x00050006,        DATA, 0),
    (0x00070006,        DATA, 0),
    (parammap[".dmx"],  DATA, -1),
]


def write_record(
    f: BinaryIO,
    rid: int,
    payload: bytes = b"",
    unk: int = 0,
    param: int = 0
) -> None:
    """
    Write an SDT record to a binary file.

    Args:
        f (BinaryIO): The file object to write to.
        rid (int): Record ID.
        payload (bytes): Record payload data.
        unk (int): Unknown header field.
        param (int): Additional parameter field used by some record types.
    """

    # Each SDT record begins with a 16-byte header
    size = 16 + len(payload)
    # Each record is padded, specifying the actual size if necessary
    while size % 0x10 != 0:
        if param == 0:
            param = size
        size += 1
        payload += b"\0"
    
    f.write(struct.pack("<IIII", rid, size, unk, param))
    f.write(payload)


def rid_from_path(inpath: str) -> int:
    """
    Get the corresponding RID from a file name

    Args:
        inpath (str): The file name to check.
    """
    if os.path.splitext(inpath)[1] in parammap:
        return parammap[os.path.splitext(inpath)[1]]
    if inpath.endswith(".bin") and all(c in hexdigits for c in inpath[-12:-4]):
        return int(inpath[-12:-4], 16)
    return 0


def mux(
    outpath: str,
    inpaths: list[PathType]
) -> None:
    """
    Create an SDT container by muxing the given input streams.

    Args:
        outpath (str): Path where the output SDT file will be written.
        inpaths (list[PathType]): Paths of input files (any type).
    """

    read_amts: dict[PathType, int] = {}

    with open(outpath, "wb") as out:
        for rid, mode, size in expected_order:
            if all(rid_from_path(inpath) != rid for inpath in inpaths):
                continue

            inpath: PathType = [x for x in inpaths if rid_from_path(x) == rid][0]

            if mode == INIT:
                # Initialize stream
                read_amts[inpath] = 0
                write_record(out, 0x10, b"", 0, rid)
                continue

            if inpath not in read_amts:
                print(f"Stream for {inpath} not initialized")
                continue

            if size < 0:
                if rid == parammap[".xwma"]:
                    if mode == HEAD:
                        # Get header size from the file
                        with open(inpath, "rb") as f:
                            header: bytes = f.read(0x40)
                            size = 0x36 + 4 * get_u32_le(header, 0x32)
                        # Header is always padded
                        if size % 0x10 != 0:
                            size += 0x10 - (size % 0x10)
                    elif mode == DATA:
                        # Get sample size from the file
                        with open(inpath, "rb") as f:
                            header: bytes = f.read(0x40)
                            size = get_u32_le(header, 0x18)
                elif rid == parammap[".dmx"]:
                    # DATA handled in all-entries loop
                    pass
                else:
                    print("Invalid SDT chunk order configuration")
                    continue

            # Similar behavior for HEAD and DATA, but DATA loops
            with open(inpath, "rb") as f:
                f.seek(read_amts[inpath])
                if size == 0:
                    write_record(out, rid, f.read())
                elif size > 0:
                    if mode == HEAD:
                        write_record(out, rid, f.read(size), 0, size if size % 0x10 != 0 else 0)
                    elif mode == DATA:
                        for chunk in iter(lambda: f.read(size), b""):
                            write_record(out, rid, chunk, 0, size if size % 0x10 != 0 else 0)
                elif size < 0:
                    if rid == parammap[".dmx"]:
                        # Variable-length chunks, because dmx is also an sdt
                        end_pos = os.path.getsize(inpath)
                        i: int = 0
                        while f.tell() < end_pos:
                            header: bytes = f.read(0x10)
                            size = get_u32_le(header, 0x04)
                            entry: bytes = f.read(size - 0x10)
                            write_record(out, rid, header + entry, i)
                            i += 0x6
                    else:
                        print("Invalid SDT chunk order configuration")
                read_amts[inpath] = f.tell()
        
        # Write any other files, why not
        for inpath in inpaths:
            if inpath in read_amts:
                continue
            rid: int = rid_from_path(inpath)
            write_record(out, 0x10, b"", 0, rid)
            with open(inpath, "rb") as f:
                write_record(out, rid, f.read())
        
        # Write SDT end-of-stream marker
        write_record(out, 0xF0, b"", 0, 0)

