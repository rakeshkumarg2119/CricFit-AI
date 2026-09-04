# Bowling analysis backend

Generated from the Colab notebook (MediaPipe Task API). Usage:

```python
from analyze_video import load_models, generate_report
load_models()  # once, at startup
report = generate_report(video_path)
```

Or from the CLI:
```bash
pip install -r requirements.txt
python analyze_video.py --video clip.mp4 --annotate --out report.json
```
