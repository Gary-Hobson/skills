# netlist-query

Parse Cadence Allegro / OrCAD exported PST netlist files and query component connections.

## Dependencies

- Python 3.10+ (no third-party packages)

## Input

Provide a directory with three Allegro-exported PST files: `pstchip.dat`, `pstxprt.dat`, `pstxnet.dat`. The agent parses them once on first use.

## Usage

Ask your agent:

- "What ICs are on the board?"
- "Show the peripheral circuit of U1700"
- "Where does the IMU connect to?"
- "What's on the SPI_MISO net?"
