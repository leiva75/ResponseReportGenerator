# Response Report Generator

A professional web application for creating security and event management reports for venues, hotels, and live shows. Generate Word (.docx) and PDF documents with detailed information about hotels, transportation, venues, and security provisions.

## Features

- **Hotel Section**: Capture hotel details including rooms, facilities, security, parking, and surrounding area
- **Transportation Section**: Document airport transit and transport arrangements
- **Venue Section**: Record venue details, parking, access, branding, and backstage information
- **Venue Security Section**: Detailed security staffing with count and comments for each item
- **AI Assistant**: Optional AI-powered suggestions for hotel and venue information
- **Security Briefs**: AI-generated security intelligence briefs
- **Document Export**: Generate professional Word and PDF reports
- **Report History**: Save and load previous reports

---

## Quick Start for Windows Users

### Option 1: Run from Source (Recommended)

1. **Install Python 3.10 or later**
   - Download from [python.org/downloads](https://python.org/downloads/)
   - **IMPORTANT**: During installation, check ✅ "Add Python to PATH"

2. **Download the Application**
   - Download and extract the project folder to your computer

3. **Install Dependencies**
   - Double-click `scripts/install_dependencies.bat`
   - Wait for the installation to complete

4. **Run the Application**
   - Double-click `scripts/run_windows.bat`
   - Your browser will open automatically to the application

5. **Stop the Application**
   - Press `Ctrl+C` in the command window, or close the window

### Option 2: Use the Pre-built Executable

If you have a pre-built version:

1. Extract the `ResponseReportGenerator` folder
2. Double-click `Start.bat` or `ResponseReportGenerator.exe`
3. The browser will open automatically

**Note**: Windows SmartScreen may show a warning on first run. Click "More info" then "Run anyway" to proceed.

### PDF Export Note

PDF export uses WeasyPrint which requires GTK libraries on Windows. If PDF export doesn't work:
- Word (.docx) export will still function normally
- For PDF support, see [WeasyPrint Windows Installation](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#windows)

---

## Configuration

### Setting Up Your Environment

1. Copy `config_example.env` to `.env`:
   ```
   copy config_example.env .env
   ```

2. Edit `.env` with your settings:
   ```ini
   # Flask Configuration
   FLASK_SECRET_KEY=your_secret_key_here
   HOST=127.0.0.1
   PORT=5000
   
   # Optional: Google Maps API Key
   # GOOGLE_MAPS_API_KEY=your_google_maps_key
   
   # Optional: OpenAI API Key (for AI Assistant)
   # OPENAI_API_KEY=your_openai_api_key
   
   # Optional: SerpAPI Key (for web search)
   # SEARCH_API_KEY=your_serpapi_key
   ```

### API Keys (Optional)

- **OpenAI API Key**: Enables the AI Assistant features
  - Get one at [platform.openai.com](https://platform.openai.com/)
  
- **Google Maps API Key**: Enables detailed hotel/venue data fetching
  - Get one at [Google Cloud Console](https://console.cloud.google.com/)
  
- **SerpAPI Key**: Enables web search for AI Assistant
  - Get one at [serpapi.com](https://serpapi.com/)

Without these keys, the app works normally but with reduced AI features.

---

## Data and Backups

### Data Location

All your data is stored in the `data/` folder:
- `data/history_reports.json` - Your saved reports

### Backing Up Your Data

To backup your reports:
1. Copy the entire `data/` folder to a safe location
2. That's it! Your backup is complete.

To restore:
1. Copy your backed-up `data/` folder back into the application directory

### Generated Reports

- Word and PDF reports are downloaded directly through your browser
- The `exports/` folder is available for any exported files

---

## Developer Guide

### Running in Developer Mode

```bash
# Clone or download the project
cd response-report-generator

# Create virtual environment (recommended)
python -m venv venv
venv\Scripts\activate  # On Windows
source venv/bin/activate  # On Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
copy config_example.env .env
# Edit .env with your settings

# Run the application
python run.py
```

The app will start at `http://127.0.0.1:5000`

### Project Structure

```
response-report-generator/
├── app.py                  # Main Flask application
├── run.py                  # Entry point with browser launcher
├── docx_generator.py       # Word document generation
├── pdf_generator.py        # PDF report generation
├── requirements.txt        # Python dependencies
├── config_example.env      # Configuration template
├── README.md               # This file
│
├── services/               # Business logic modules
│   ├── ai_helper.py        # AI Assistant integration
│   ├── maps_api.py         # Maps API integration
│   ├── history.py          # Report history management
│   ├── form_utils.py       # Form utilities
│   ├── security_intelligence.py  # Security brief generation
│   ├── watchdog.py         # Monitoring system
│   └── flask_middleware.py # Request/response logging
│
├── templates/              # HTML templates
│   ├── index.html          # Main form page
│   └── history.html        # Report history page
│
├── static/                 # Static assets
│   ├── style.css           # Stylesheet
│   ├── img/                # Images
│   └── js/                 # JavaScript
│
├── scripts/                # Utility scripts
│   ├── run_windows.bat     # Windows launcher
│   ├── build_windows.bat   # Build executable
│   └── install_dependencies.bat  # Install packages
│
├── data/                   # User data (auto-created)
│   └── history_reports.json
│
├── logs/                   # Application logs (auto-created)
│   └── runtime_report.log
│
└── exports/                # Exported files (auto-created)
```

### Building Windows Executable

To create a standalone Windows executable:

1. Install build dependencies:
   ```bash
   pip install pyinstaller
   ```

2. Run the build script:
   ```bash
   scripts\build_windows.bat
   ```

3. Find the executable in `dist/ResponseReportGenerator/`

4. To distribute:
   - Zip the entire `dist/ResponseReportGenerator/` folder
   - Users can extract and run without installing Python

---

## Troubleshooting

### "Python is not recognized"
- Reinstall Python and check ✅ "Add Python to PATH"
- Restart your computer after installation

### "Module not found" errors
- Run `scripts/install_dependencies.bat` again
- Or manually: `pip install -r requirements.txt`

### Application won't start
- Check if port 5000 is already in use
- Edit `.env` and change `PORT=5001` or another available port

### AI Assistant not working
- Make sure you have an OpenAI API key in your `.env` file
- Check your API key is valid and has credits

### Browser doesn't open automatically
- Manually open `http://127.0.0.1:5000` in your browser

---

## License

This application is proprietary software for Response security operations.

## Support

For issues or feature requests, contact your system administrator.
