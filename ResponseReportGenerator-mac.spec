# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Response Report Generator

To build:
    pyinstaller ResponseReportGenerator.spec

Or use the build script:
    scripts/build_windows.bat
"""

import os
from PyInstaller.utils.hooks import collect_all, collect_data_files

block_cipher = None

docx_datas, docx_binaries, docx_hiddenimports = collect_all('docx')
reportlab_datas, reportlab_binaries, reportlab_hiddenimports = collect_all('reportlab')

a = Analysis(
    ['run.py'],
    pathex=[],
    binaries=docx_binaries + reportlab_binaries,
    datas=[
        ('templates', 'templates'),
        ('static', 'static'),
        ('config_example.env', '.'),
    ] + docx_datas + reportlab_datas,
    hiddenimports=[
        'flask',
        'flask.json',
        'jinja2',
        'werkzeug',
        'werkzeug.serving',
        'werkzeug.debug',
        'docx',
        'docx.oxml',
        'docx.oxml.ns',
        'docx.shared',
        'reportlab',
        'reportlab.lib',
        'reportlab.lib.colors',
        'reportlab.lib.pagesizes',
        'reportlab.lib.units',
        'reportlab.platypus',
        'reportlab.pdfgen',
        'openai',
        'dotenv',
        'requests',
        'json',
        'logging',
        'threading',
        'webbrowser',
        'services',
        'services.paths',
        'services.history',
        'services.watchdog',
        'services.ai_helper',
        'services.security_cache',
        'services.security_intelligence_v2',
        'services.security_intel_cache',
        'services.security_questionnaire',
        'services.location_service',
        'services.intel_providers',
        'services.intel_providers.acled_provider',
        'services.intel_providers.gdelt_provider',
        'services.intel_providers.mediastack_provider',
        'services.intel_providers.rss_provider',
        'services.intel_providers.official_provider',
        'services.maps_api',
        'services.mediastack',
        'services.riskbrief',
        'docx_generator',
        'pdf_generator',
        'feedparser',
        'bs4',
        'beautifulsoup4',
        'dateutil',
        'python_dateutil',
    ] + docx_hiddenimports + reportlab_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'tkinter',
        'PIL',
        'cv2',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ResponseReportGenerator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='static/img/app_icon.ico' if os.path.exists('static/img/app_icon.ico') else None,
)
app = BUNDLE(exe, name='ResponseReportGenerator.app', icon=None, bundle_identifier='com.leiva75.responsereportgenerator')

coll = COLLECT(
    app,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ResponseReportGenerator',
)
