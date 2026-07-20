# example_molecule — the template layout

This folder shows the exact structure every molecule uses. **To start a new
molecule, copy this whole folder** and rename it, e.g.:

```bash
cp -r molecules/example_molecule molecules/CS2
```

Your new folder (anything that isn't `example_molecule`) stays out of git, so
your papers and data live only on your machine.

## What each folder is for

| Folder      | What goes here                                                        |
|-------------|-----------------------------------------------------------------------|
| `papers/`   | The source PDFs you download. Drop them in here first.                 |
| `markdown/` | OCR output — filled in automatically by `scripts/mineru_cloud.py`.    |
| `csv/`      | Extracted numbers and the reviewer's report.                          |
| `output/`   | The finished MARVEL `.txt` files — your results.                      |

The full step-by-step is in the main [README](../../README.md).
