RealTimeConApp — README
=======================

WHAT THIS APP DOES
------------------
RealTimeConApp generates a two-speaker AI conversation from script files using
voice cloning, then plays it back with synchronized scrolling captions.


FIRST LAUNCH
------------
On first launch, the app will download the voice model (~1.5 GB).
An internet connection is required for this one-time download.
All subsequent launches start immediately with no download needed.


WHERE TO PUT YOUR FILES
-----------------------
Place your script and voice files in the "scripts" folder next to the .exe:

  scripts\speaker1.txt        — Speaker 1 dialogue (one line per turn)
  scripts\speaker2.txt        — Speaker 2 dialogue (one line per turn)
  scripts\speaker1_ref.wav    — Speaker 1 voice reference clip (10-20 seconds)
  scripts\speaker2_ref.wav    — Speaker 2 voice reference clip (10-20 seconds)

Script format: plain text, one spoken line per row, no special tags needed.
Lines alternate between speakers — S1 line 1, S2 line 1, S1 line 2, etc.


GENERATING A CONVERSATION
-------------------------
1. Double-click RealTimeConApp.exe
2. Use the file pickers to select your script files and voice clips
3. Click "Generate Conversation"
4. Wait for the render to complete (~28 min for a 10-minute conversation on CPU)
5. The player opens automatically when done


STARTING A NEW CONVERSATION
----------------------------
If output files already exist, the app opens the player directly.
To render a new conversation, either:
  - Delete the contents of the "output" folder, or
  - Run: RealTimeConApp.exe --setup


OUTPUT FILES
------------
Generated files are saved to the "output" folder next to the .exe:
  output\conversation_final.wav   — the stitched audio
  output\captions.json            — word timestamps for caption display


KNOWN LIMITATIONS
-----------------
- Render time: approximately 28 minutes for a 10-minute conversation (CPU-only)
- Voice cloning quality depends on reference clip quality — use a clean,
  noise-free recording of 10-20 seconds for best results
- The app uses all available CPU cores during rendering