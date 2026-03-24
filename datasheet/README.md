# datasheet

Convert PDF datasheets to Markdown with bookmark index for efficient querying.

## Dependencies

- Python 3.10+
- `pip install marker-pdf`

## First-Time Setup

Run a small PDF conversion manually to trigger the model download (~1-2GB):

```bash
marker_single references/sample.pdf --output_dir /tmp/test --output_format markdown
```

A sample PDF (`references/sample.pdf`) is included for testing.

Also recommended for large PDFs (>100 pages) — convert manually since it can take a long time and may exceed the agent's timeout.

## Usage

Ask your agent:

- "Convert the MAX31875 datasheet to Markdown"
- "What's the I2C address of MAX31875R0? Check the datasheet"
- "Look up the electrical characteristics in the TPS62840 datasheet"

The agent converts the PDF on first use, then queries via bookmark index without loading the full document.
