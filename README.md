# QBO Sankey Dashboard

A secure, standalone desktop application that extracts data from QuickBooks Online via API and displays financial flows using interactive Sankey diagrams.

## Features

- **Secure Authentication**: OAuth 2.0 integration with QuickBooks Online
- **Interactive Visualizations**: Sankey diagrams showing money flow from revenue to expenses
- **Real-time Data**: Direct API integration with QBO for up-to-date financial data
- **Standalone Application**: Packaged as a single executable for easy deployment
- **Secure Storage**: Credentials and tokens stored using OS-level keyring

## Quick Start

1. **Setup Environment**:
   ```bash
   python -m venv .venv
   source .venv/Scripts/activate  # On Windows
   # or
   source .venv/bin/activate      # On macOS/Linux
   pip install -r requirements.txt
   ```

2. **First Run Setup**:
   ```bash
   python app.py
   ```
   The application will guide you through the initial credential setup.

3. **Development**:
   ```bash
   python app.py
   ```
   Open your browser to `http://localhost:8050`

## Development

This project follows a ground-up development approach with security and user experience built in from the start.

### Project Structure

```
qbo-sankey-diagram-copilot/
├── app.py                   # Main Dash application
├── setup_wizard.py          # First-run credential setup
├── qbo_api/
│   ├── auth.py             # OAuth and token management
│   └── data_fetcher.py     # QBO API calls and parsing
├── visualization/
│   └── sankey.py           # Sankey diagram creation
└── utils/
    ├── logging_config.py   # Logging setup
    └── credentials.py      # Keyring credential management
```

### Technology Stack

- **Framework**: Python Dash (plotly/dash)
- **QBO Integration**: intuitlib
- **Visualization**: Plotly (Sankey diagrams)
- **Security**: keyring library for credential storage
- **GUI**: tkinter for setup wizard
- **Packaging**: PyInstaller

