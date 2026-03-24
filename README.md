# Robot hand

Hand tracking demo: reads the webcam, draws MediaPipe hand landmarks, and shows finger states and angles on screen.

## Run

1. **Python 3** — use 3.8+ (MediaPipe needs a supported version).

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Start the app**

   ```bash
   python main.py
   ```

4. **Quit** — press `q` in the video window.

## Camera

The script opens camera index `2` using Apple’s AVFoundation backend (`cv2.CAP_AVFOUNDATION`), which matches typical setups on macOS. If you get a black window or an error, edit `main.py` and try `0` or `1` instead of `2`, or drop the second argument on Linux/Windows, for example:

```python
cap = cv2.VideoCapture(0)
```
