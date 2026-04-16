import argparse
import os
import sys
from typing import List, Optional

from .sdt import SDT, create_sdt


def main() -> None:
    """
    Entry point for the sdttools command-line interface.

    Parses command-line arguments and determines whether to extract
    streams from an SDT file or create a new SDT container from
    provided input streams.
    """

    parser = argparse.ArgumentParser(
        prog="sdttools",
        description=(
            "Extract or repack SDT container files used in Metal Gear Solid games.\n\n"
            "Basic usage:\n"
            "  sdttools movie.sdt                Extract all streams\n"
            "  sdttools movie.sdt -o video.m2v   Extract specific streams\n"
            "  sdttools video.m2v audio.mtaf     Create output.sdt\n"
            "  sdttools video.m2v -o movie.sdt   Create custom SDT\n\n"
            "Drag-and-drop is supported when using the executable version."
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument(
        "inputs",
        nargs="+",
        help="Input files (.sdt, .m2v, .mp4, .mtaf, .pacb)",
    )

    parser.add_argument(
        "-o",
        "--output",
        action="append",
        help=(
            "Output file(s).\n"
            "Extraction: specify filenames or use 'all'.\n"
            "Repacking: specify the output .sdt file."
        ),
    )

    args: argparse.Namespace = parser.parse_args()

    inputs: List[str] = args.inputs
    outputs: List[str] = args.output or []

    # Determine operation mode based on whether an SDT file was provided
    sdt_inputs: List[str] = [i for i in inputs if i.lower().endswith(".sdt")]

    if sdt_inputs:
        mode: str = "extract"
    else:
        mode = "pack"

    if mode == "extract":  # Demuxing / extracting

        if len(sdt_inputs) > 1:
            sys.exit("Error: Only one SDT file can be extracted at a time.")

        sdt_path: str = sdt_inputs[0]

        if os.path.exists(sdt_path):
            sdt = SDT(sdt_path)
        else:
            sys.exit(f"Error: SDT file not found: {sdt_path}")

        # Default behavior is to extract everything
        if not outputs:
            outputs = ["all"]

        if outputs == ["all"]:
            sdt.extract_all()
        elif len(outputs) == 1 and os.path.isdir(outputs[0]):
            sdt.extract_all(outputs[0])
        else:
            sdt.extract(outputs)

    else:  # Muxing / packing

        video: Optional[str] = None
        audio: Optional[str] = None
        subs: Optional[str] = None
        other: list[str] = []
        
        # Folder repack
        if len(inputs) == 1 and os.path.isdir(inputs[0]):
            input_dir = inputs[0]
            inputs = os.listdir(input_dir)
            inputs = [os.path.join(input_dir, i) for i in inputs]

        # Identify input streams based on file extensions
        for i in inputs:

            ext = os.path.splitext(i)[1].lower()

            if ext in {".m2v", ".mp4"}:

                if video:
                    print(
                        f"Warning: Multiple video files detected. "
                        f"Using '{video}', ignoring '{i}'."
                    )
                else:
                    video = i

                # MP4 compatibility warning
                if ext == ".mp4":
                    print(
                        "WARNING: MP4 files are likely only supported in the "
                        "Master Collection version of Metal Gear Solid 2 and 3.\n"
                        "Use MPEG-2 .m2v for PS3 HD versions."
                    )

            elif ext in {".mtaf", ".xwma"}:

                if audio:
                    print(
                        f"Warning: Multiple audio files detected. "
                        f"Using '{audio}', ignoring '{i}'."
                    )
                else:
                    audio = i

            elif ext == ".pacb":

                if subs:
                    print(
                        f"Warning: Multiple subtitle files detected. "
                        f"Using '{subs}', ignoring '{i}'."
                    )
                else:
                    subs = i

            else:
                other.append(i)

        # Validate input files before attempting to mux
        checked_inputs = other
        if video: checked_inputs.append(video)
        if audio: checked_inputs.append(audio)
        if subs: checked_inputs.append(subs)

        for f in checked_inputs:
            if f and not os.path.exists(f):
                sys.exit(f"Error: Input file not found: {f}")

        # Default output filename if none was provided
        if not outputs:
            out_sdt: str = "output.sdt"
        else:

            if len(outputs) > 1:
                sys.exit("Error: Only one output .sdt can be specified.")

            out_sdt = outputs[0]

        create_sdt(out_sdt, checked_inputs)

        print("Created:", out_sdt)
