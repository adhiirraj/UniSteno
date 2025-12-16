# UniSteno

UniSteno is a steganalysis toolkit that automatically detects file types and allows
the user to analyze, embed, and extract files through a web-based GUI.
(Drag and drop supported)

The goal of UniSteno is to unify common steganographic methods for
cybersecurity learning, CTFs, and digital forensics.

## Features
- Detects images, audio, video, text, and documents using MIME detection
- Routes files to appropriate analyzer plugins automatically

## For Images
- LSB distribution analysis
- Bitplane histograms (R/G/B)
- Chi-square statistical testing
- Suspiciousness scoring

Each analyzer or steganography algorithm is implemented as a standalone plugin.
New algorithms can be added without modifying the core logic.

## Embedding & Extraction
- Password-based PRNG-scattered LSB embedding
- CRC32 integrity verification
- Original payload filename preserved on extraction
- Alpha-safe embedding (transparent pixels preserved)

## Tech Stack

### Backend
- Python
- Flask
- NumPy
- Pillow
- python-magic

### Frontend
- HTML5
- CSS3
- Bootstrap 5
- Vanilla JavaScript

## Project Structure

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
│   └── image_lsb_stego.py
├── uploads/
├── README.md
├── requirements.txt
└── .gitignore
```


## Setup & Running

git clone <repo-url>
cd Unisteno
pip install -r requirements.txt
python server.py

Open in browser:
http://127.0.0.1:5000

## Usage

### Analyze
- Upload a file
- Select Analyze
- View steganalysis results

### Embed
- Upload a cover file
- Select Embed
- Choose payload file
- (Optional) Enter password
- Download embedded file

### Extract
- Upload embedded file
- Select Extract
- Enter password
- Payload downloads with original filename
