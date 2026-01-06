# UniSteno  
Universal Steganography Toolkit  

UniSteno is a comprehensive steganography and steganalysis toolkit that automatically detects file types and allows users to analyze, embed, and extract hidden data through a unified web-based GUI (drag-and-drop supported).  

The goal of UniSteno is to unify common and advanced steganographic techniques into a single extensible platform for cybersecurity learning, CTF challenges, and digital forensics.  

------------------------------------------------------------  

FEATURES  

• Automatic file type detection using MIME analysis  
• Unified Analyze / Embed / Extract workflow  
• Modular plugin-based architecture  
• Supports Images, Text, Audio, PDFs, and Videos  
• Password-protected PRNG-scattered embedding  
• Web-based visualization and analysis dashboard  

------------------------------------------------------------  

SUPPORTED MEDIA & CAPABILITIES  

IMAGES  
Analysis:  
• RGB bitplane visualization  
• Bitplane histograms  
• LSB distribution & entropy analysis  
• Chi-square statistical testing  
• Suspiciousness scoring  

Embedding & Extraction:  
• Password-seeded PRNG-scattered LSB embedding  
• CRC32 integrity verification  
• Original payload filename preserved  
• Alpha-safe embedding (transparent pixels preserved)  

------------------------------------------------------------  

TEXT FILES  
Analysis:  
• Zero-width Unicode character detection  
• Homoglyph substitution detection  
• Entropy-based anomaly detection  

Embedding & Extraction:  
• Zero-width character based steganography  
• Password-protected encoding  
• Invisible to normal text rendering  

------------------------------------------------------------  

PDF DOCUMENTS  
Analysis:  
• Metadata inspection  
• Appended data detection  
• Structural anomaly detection  

Embedding & Extraction:  
• Payload embedded in unused objects / metadata  
• Visual appearance preserved  
• Reliable extraction with password validation  

------------------------------------------------------------  

AUDIO FILES  
Analysis:  
• LSB distribution analysis on PCM samples  
• Appended data detection  
• Spectrogram visualization  

Embedding & Extraction:  
• LSB-based audio steganography  
• PRNG-scattered embedding using password  
• Minimal audible distortion  
• Payload integrity verification  

------------------------------------------------------------  

VIDEO FILES  
Analysis:  
• RGB and SUPER bitplane visualization  
• Frame-wise bitplane inspection  
• Statistical anomaly detection  

Embedding & Extraction (Optimized):  
• Only the FIRST video frame is used for embedding  
• Image-style PRNG-scattered LSB embedding  
• Remaining frames remain unchanged  
• First frame stitched back into the video  
• Extremely fast embed and extract  
• Secure even if attacker knows the first-frame strategy  

------------------------------------------------------------  

PLUGIN SYSTEM  

Each analyzer or steganography method is implemented as a standalone plugin.  

• Plugins are auto-discovered from the plugins/ directory  
• No core server modification required  
• Each plugin may implement:  
  - analyze()  
  - embed()  
  - extract()  

------------------------------------------------------------  

TECHNOLOGY STACK  

Backend:  
• Python  
• Flask  
• NumPy  
• Pillow  
• SciPy  
• PyPDF2  
• python-magic / python-magic-bin (Windows)  
• pydub  
• matplotlib  

Frontend:  
• HTML5  
• CSS3  
• Bootstrap 5  
• Vanilla JavaScript  

------------------------------------------------------------  

PROJECT STRUCTURE  
```
Unisteno/
├── server.py
├── index.html
├── static/
│   ├── css/
│   │   └── solve.css
│   ├── img/
│   │   └── logo.svg
│   └── js/
│       └── solve.js
├── plugins/
│   ├── __init__.py
│   ├── image_lsb_advanced.py
│   ├── image_lsb_stego.py
│   ├── image_bitplane_visualizer.py
│   ├── image_bitplane_superimposed.py
│   ├── text_stego_analyzer.py
│   ├── text_lsb_stego.py
│   ├── audio_lsb_analyzer.py
│   ├── audio_lsb_stego.py
│   ├── audio_spectrogram_visualizer.py
│   ├── video_bitplane_visualizer.py
│   ├── video_lsb_analyzer.py
│   └── video_lsb_stego.py
├── uploads/
├── requirements.txt
├── README.md
└── .gitignore
```
------------------------------------------------------------  

SETUP & RUNNING  

1. Clone the repository  
   git clone <repo-url>  
   cd UniSteno  

2. Install dependencies  
   pip install -r requirements.txt  

3. Run the server  
   python server.py  

4. Open in browser  
   http://127.0.0.1:5000  

------------------------------------------------------------  

USAGE  

Analyze:  
• Upload a file  
• Select Analyze  
• View metadata, statistics, visualizations, and scores  

Embed:  
• Upload a cover file  
• Select Embed  
• Choose payload file  
• (Optional) Enter password  
• Download embedded output  

Extract:  
• Upload embedded file  
• Select Extract  
• Enter password  
• Payload downloads with original filename  

------------------------------------------------------------  
