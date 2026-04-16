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
parammap[".dmx2"] = 0x00000002  # gonna kill someone

fuckme = [0, 0, 45, 125, 185, 260, 325, 409, 465, 545, 625, 715, 785, 890, 1005, 1140, 1265, 1390, 1484, 1600, 1700, 1805, 1894, 1970, 2045, 2135, 2220, 2310, 2415, 2505, 2605, 2710, 2820, 2940, 3040, 3140, 3290, 3405, 3475, 3565, 3655, 3745, 3845, 3960, 4135, 4235, 4320, 4400, 4515, 4630, 4745, 4850, 4950, 5055, 5125, 5205, 5295, 5385, 5500, 5605, 5695, 5795, 5885, 5970, 6075, 6180, 6305, 6435, 6540, 6630, 6715, 6805, 6880, 6970, 7085, 7215, 7320, 7410, 7505, 7610, 7720, 7833, 7930, 8030, 8135, 8225, 8325, 8430, 8530, 8645, 8735, 8825, 8930, 9030, 9135, 9235, 9335, 9440, 9540, 9650, 9745, 9850, 9940, 10040, 10155, 10265, 10360, 10475, 10585, 10695, 10795, 10900, 10990, 11080, 11180, 11270, 11375, 11475, 11615, 11730, 11860, 11980, 12075, 12165, 12270, 12360, 12465, 12555, 12665, 12770, 12870, 12960, 13060, 13150, 13230, 13355, 13485, 13615, 13730, 13835, 13935, 14015, 14100, 14195, 14305, 14405, 14515, 14600, 14700, 14790, 14895, 15000, 15095, 15215, 15315, 15415, 15520, 15660, 15765, 15870, 15980, 16070, 16175, 16260, 16350, 16440, 16535, 16625, 16735, 16850, 16965, 17095, 17215, 17330, 17425, 17530, 17610, 17735, 17810, 17915, 18020, 18105, 18200, 18275, 18350, 18440, 18540, 18655, 18770, 18875, 18990, 19090, 19195, 19300, 19400, 19505, 19605, 19705, 19814, 19910, 20015, 20130, 20230, 20350, 20450, 20555, 20655, 20755, 20855, 20975, 21075, 21195, 21305, 21410, 21525, 21615, 21730, 21830, 21945, 22050, 22155, 22240, 22345, 22430, 22535, 22640, 22740, 22840, 22945, 23060, 23165, 23255, 23370, 23470, 23570, 23675, 23775, 23880, 23995, 24095, 24210, 24315, 24405, 24510, 24610, 24695, 24800, 24910, 25005, 25120, 25235, 25335, 25455, 25540, 25655, 25760, 25860, 25990, 26105, 26195, 26300, 26405, 26500, 26595, 26670, 26765, 26860, 26965, 27070, 27170, 27289, 27385, 27475, 27575, 27685, 27785, 27910, 28015, 28120, 28220, 28310, 28425, 28540, 28645, 28745, 28835, 28935, 29025, 29130, 29220, 29320, 29435, 29525, 29630, 29740, 29830, 29935, 30040, 30145, 30240, 30355, 30470, 30575, 30695, 30795, 30910, 31010, 31100, 31200, 31310, 31395, 31500, 31595, 31700, 31790, 31910, 32020, 32135, 32225, 32315, 32420, 32520, 32625, 32730, 32830, 32945, 33050, 33150, 33250, 33335, 33445, 33545, 33638, 33740, 33840, 33930, 34035, 34135, 34240, 34355, 34455, 34570, 34675, 34775, 34865, 34965, 35060, 35170, 35275, 35375, 35480, 35575, 35685, 35780, 35890, 36005, 36105, 36210, 36295, 36400, 36510, 36620, 36720, 36825, 36920, 37025, 37115, 37215, 37324, 37420, 37525, 37630, 37755, 37860, 37960, 38065, 38155, 38280, 38395, 38490, 38565, 38650, 38755, 38855, 38960, 39080, 39175, 39290, 39380, 39495, 39595, 39700, 39790, 39895, 39980, 40070, 40165, 40255, 40350, 40445, 40545, 40645, 40740, 40845, 40940, 41030, 41145, 41235, 41325, 41425, 41530, 41630, 41760, 41855, 41940, 42030, 42145, 42245, 42350, 42450, 42540, 42635, 42785, 42875, 42980, 43090, 43175, 43275, 43375, 43475, 43640, 43745, 43860, 43985, 44105, 44215, 44305, 44370, 44460, 44550, 44655, 44780, 44900, 45015, 45100, 45190, 45295, 45400, 45515, 45605, 45705, 45810, 45905, 46015, 46125, 46230, 46315, 46420, 46510, 46600, 46700, 46810, 46905, 46980, 47070, 47185, 47290, 47380, 47470, 47560, 47650, 47735, 47840, 47955, 48070, 48200, 48295, 48405, 48510, 48595, 48685, 48760, 48890, 49005, 49125, 49210, 49310, 49415, 49505, 49595, 49720, 49800, 49890, 49990, 50105, 50235, 50350, 50465, 50580, 50680, 50770, 50850, 50925, 51015, 51105, 51205, 51310, 51410, 51525, 51630, 51745, 51845, 51950, 52040, 52130, 52230, 52335, 52435, 52535, 52655, 52755, 52875, 52975, 53090, 53190, 53299, 53410, 53535, 53625, 53720, 53805, 53905, 53995, 54085, 54190, 54290, 54430, 54545, 54675, 54780, 54870, 54980, 55075, 55165, 55285, 55355, 55445, 55565, 55675, 55795, 55895, 55995, 56110, 56185, 56300, 56375, 56455, 56545, 56645, 56750, 56850, 56955, 57055, 57170, 57275, 57375, 57480, 57595, 57710, 57810, 57915, 58005, 58120, 58210, 58310, 58400, 58500, 58605, 58705, 58810, 58910, 59000, 59105, 59220, 59310, 59410, 59500, 59605, 59720, 59835, 59935, 60045, 60140, 60245, 60345, 60450, 60535, 60640, 60740, 60845, 60945, 61060, 61165, 61255, 61355, 61460, 61575, 61665, 61770, 61880, 61985, 62085, 62190, 62290]

INIT = 0  # Initialize stream
HEAD = 1  # Header chunk
DATA = 2  # Other chunks, looped in block size
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
    (parammap[".dmx"],  INIT, 0),
    (parammap[".dmx"],  DATA, -1),
    (parammap[".dmx2"],  INIT, 0),
    (parammap[".dmx2"],  DATA, -1),
    (parammap[".xwma"], DATA, -1),
    (parammap[".m2v"],  DATA, 0x10000),
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
]

allchunks = []

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
    global allchunks

    # Each SDT record begins with a 16-byte header
    size = 16 + len(payload)
    
    allchunks.append((rid, size, unk, param, payload))
    
    #f.write(struct.pack("<IIII", rid, size, unk, param))
    #f.write(payload)


def rid_from_path(inpath: str) -> int:
    """
    Get the corresponding RID from a file name

    Args:
        inpath (str): The file name to check.
    """
    inpath = inpath.lower()
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
    global allchunks

    read_amts: dict[PathType, int] = {}
    allchunks = []
    i: int = 0  # Some sort of duration indicator, most important with dmx

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
                        youtoo = 0
                    elif mode == DATA:
                        # Get sample size from the file
                        with open(inpath, "rb") as f:
                            header: bytes = f.read(0x40)
                            size = get_u32_le(header, 0x18)
                        # Compute padded size
                        padding_data: bytes = b""
                        if size % 0x10 != 0:
                            padding_data = b"\0" * (0x10 - (padded_size % 0x10))
                elif rid in {parammap[".dmx"], parammap[".dmx2"]}:
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
                        write_record(out, rid, f.read(size))
                    elif mode == DATA:
                        for chunk in iter(lambda: f.read(size), b""):
                            if rid == parammap[".xwma"]:
                                # Pad chunk, store real size in param
                                write_record(out, rid, chunk + padding_data, fuckme[youtoo], size)
                                #youtoo += 1
                            else:
                                write_record(out, rid, chunk)
                elif size < 0:
                    if rid == parammap[".dmx"]:
                        # Variable-length chunks, because dmx is also an sdt
                        end_pos = os.path.getsize(inpath)
                        i = 0
                        while f.tell() < end_pos:
                            header: bytes = f.read(0x10)
                            size = get_u32_le(header, 0x04)
                            entry: bytes = f.read(size - 0x10)
                            write_record(out, rid, header + entry, i)
                            i += 0x6
                                
                    elif rid == parammap[".dmx2"]:
                        # Variable-length chunks, because dmx is also an sdt
                        end_pos = os.path.getsize(inpath)
                        i = 0
                        data: bytes = b""
                        while f.tell() < end_pos:
                            header: bytes = f.read(0x10)
                            size = get_u32_le(header, 0x04)
                            data += header
                            # Read through until a dummy record
                            if size <= 0x10:
                                # Submit
                                write_record(out, rid, data, i)
                                data = b""
                                i += 0x5
                            else:
                                data += f.read(size - 0x10)
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
        #write_record(out, 0xF0, b"", 0, 0)
        
        # Write chunks to file
        rid_order = [parammap[".pacb"],parammap[".m2v"],parammap[".mtaf"],parammap[".xwma"],parammap[".dmx"]]
        allchunks = sorted(allchunks, key=lambda x: x[2])
        for rid, size, unk, param, payload in allchunks:
            out.write(struct.pack("<IIII", rid, size, unk, param))
            out.write(payload)
        out.write(struct.pack("<IIII", 0xF0, 0x10, i, 0))

