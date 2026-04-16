from typing import Optional, Iterable, Dict
import os
import tempfile
import shutil

from .demux import demux_sdt
from .mux import mux
from .types import PathType


class SDT:
    """
    Represents an SDT file and provides methods for extracting its contents.
    """

    def __init__(self, path: PathType) -> None:
        """
        Initialize the SDT object with the given file path.

        Args:
            path (PathType): Path to the SDT file.

        Raises:
            FileNotFoundError: If the specified SDT file does not exist.
        """

        # Normalize to string in case a pathlib.Path was provided
        self.path: str = os.fspath(path)

        if not os.path.exists(self.path):
            raise FileNotFoundError(self.path)


    def extract_all(self, out_dir: Optional[PathType] = None) -> None:
        """
        Extract all streams from the SDT file.

        Args:
            out_dir (Optional[PathType]): Directory where extracted files will
                be written. If None, files are extracted to the same directory
                as the SDT file.
        """

        if out_dir is None:
            out_dir = os.path.dirname(os.path.abspath(self.path))

        demux_sdt(self.path, os.fspath(out_dir))


    def extract(self, outputs: Iterable[PathType]) -> Dict[str, bool]:
        """
        Extract specific streams from the SDT file.

        The SDT file is first fully demuxed into a temporary directory,
        after which the requested files are copied to the specified
        output paths.

        Args:
            outputs (Iterable[PathType]): Output file paths. The file
                extension determines which stream type will be extracted
                (e.g., .m2v, .mtaf, .pacb).

        Returns:
            Dict[str, bool]: A mapping of output paths (str) to extraction
                status (bool). True indicates the requested stream was found
                and copied.
        """

        with tempfile.TemporaryDirectory() as tmp:

            # Demux the entire SDT into a temporary directory
            demux_sdt(self.path, tmp)

            extracted: Dict[str, bool] = {}

            for f in os.listdir(tmp):

                ext = os.path.splitext(f)[1].lower()
                src = os.path.join(tmp, f)

                for out in outputs:

                    out_str = os.fspath(out)
                    oext = os.path.splitext(out_str)[1].lower()

                    # Allow extracting .m2v streams as .mp4 (simple rename)
                    if ext == oext or (ext == ".m2v" and oext == ".mp4"):

                        shutil.copy(src, out_str)
                        extracted[out_str] = True

            return extracted


def create_sdt(
    output: PathType,
    inputs: list[PathType]
) -> None:
    """
    Create an SDT file by muxing the given input streams.

    Args:
        output (PathType): Path to the output SDT file.
        inputs (list[PathType]): Paths to input files to mux.
    """

    # Convert PathLike inputs to strings before passing to mux()
    mux(
        os.fspath(output),
        [os.fspath(infile) for infile in inputs]
    )
