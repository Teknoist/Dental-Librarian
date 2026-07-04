# Dental Librarian

Dental Librarian is a local desktop tool for collecting, reviewing, packaging, and archiving public dental CAD/CAM library resources.

The app is designed for a safe workflow:

1. Add public website or Google Drive folder links.
2. Scan sources and create candidate records.
3. Review candidates in the UI.
4. Download and package approved public resources.
5. Generate manifests, checksums, and `archive.json`.
6. Upload approved packages to Internet Archive when configured.

## Important rules

Dental Librarian is not a paywall, login, CAPTCHA, or access-control bypass tool.

Use it only for resources that are public and allowed to be redistributed or archived. The app keeps source URLs and metadata for attribution.

## Local AI with Ollama

Dental Librarian can use a local Ollama model to classify candidate files and produce short decision summaries.

Install Ollama, then pull a model:

```bash
ollama pull qwen2.5:7b
```

Test it:

```bash
ollama run qwen2.5:7b
```

The default config uses:

```yaml
ai:
  provider: ollama
  base_url: http://localhost:11434
  model: qwen2.5:7b
```

The app calls Ollama through the local HTTP API and expects JSON classification output. It does not display hidden chain-of-thought; it only shows action logs and short decision summaries.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

On Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

## Internet Archive setup

Install and configure the Internet Archive CLI once:

```bash
ia configure
```

Then enable uploads in `config.yaml`:

```yaml
internet_archive:
  enabled: true
```

Uploads still require candidate approval in the UI by default.

## Project layout

```text
app.py
config.yaml
requirements.txt
src/
  ai/
  core/
  ui/
  utils/
data/
downloads/
archives/
logs/
```

## MVP status

Current MVP includes:

- PySide6 desktop UI
- Live action log panel
- Ollama local AI classifier client
- Public website candidate scanner
- Public Google Drive folder handler via `gdown`
- ZIP packer with manifest and SHA256 checksums
- Internet Archive uploader module
- `archive_candidates.json` and `archive.json` writers
