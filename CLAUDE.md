# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ZX Answering Assistant (智能答题助手) is an automated quiz interaction system that uses browser automation (Playwright) to authenticate with web-based quiz platforms, extract question banks, and manage data import/export workflows. The system supports both teacher and student portals, with two interface modes: **GUI mode (Flet-based)** and **CLI mode**.

**Key architectural note**: The project uses `BrowserManager` to run multiple isolated browser contexts (student, teacher, course certification) in a single Playwright browser instance.

## Essential Commands

### Virtual Environment Setup
```bash
# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### Install Dependencies
```bash
pip install -r requirements.txt
python -m playwright install chromium
```

### Run Application

**GUI Mode (default):**
```bash
python main.py
```

**CLI Mode:**
```bash
python main.py --cli
```

## UI Architecture

### GUI Mode (Flet Framework)
The application features a modern GUI built with **Flet** (`flet>=0.80.0`):

- **[src/main_gui.py](src/main_gui.py)** - Main GUI entry point with `MainApp` class
  - Navigation rail with collapsible sidebar
  - View caching mechanism to preserve state when switching tabs
  - Window cleanup handler for Playwright browser on close

**⚠️ CRITICAL: Flet Version Compatibility**

**IMPORTANT: Always verify Flet API documentation before writing UI code!**

Flet 0.8.0+ has **massive breaking changes** from earlier versions. Many commonly-used APIs have completely different signatures or behaviors.

**Before writing ANY Flet UI code, you MUST:**

1. **Use Context7 MCP to check latest documentation:**
   ```
   Query: "flet <component_name> documentation 2026"
   ```

2. **Alternative methods if MCP is unavailable:**
   - Search web: "flet <component_name> python 2026"
   - Check official Flet documentation: https://flet.dev/docs/

3. **Common breaking changes to watch for:**
   - `page.window_center()` → `page.window_center` (changed from method to property)
   - `page.add()` parameters changed in some versions
   - Control properties and event handlers may have different signatures
   - Some controls deprecated or replaced with new ones

**Example workflow when adding UI components:**
```
1. Need to add a new control (e.g., DatePicker, DataTable, etc.)
2. First, use Context7 MCP: "flet DatePicker documentation 2026"
3. Review the latest API and examples
4. Write code using current API, not training data examples
5. Test immediately to catch compatibility issues
```

**Why this is critical:**
- Training data may contain deprecated Flet 0.7.x or earlier examples
- Flet is actively developed with frequent breaking changes
- Using deprecated APIs causes runtime errors and crashes
- Context7 MCP provides up-to-date documentation

**Remember:** When in doubt, **always check the latest docs**. Do not rely on memory or training data for Flet APIs.

**View Architecture** ([src/ui/views/](src/ui/views/)):
- **[answering_view.py](src/ui/views/answering_view.py)** - Student answering workflow
- **[extraction_view.py](src/ui/views/extraction_view.py)** - Teacher-side answer extraction
- **[settings_view.py](src/ui/views/settings_view.py)** - Configuration management
- **[course_certification_view.py](src/ui/views/course_certification_view.py)** - Course certification workflow
- **[cloud_exam_view.py](src/ui/views/cloud_exam_view.py)** - Cloud exam page (⚠️ **Partial implementation** - answer injection blocked by missing ExamMemberID parameter)

### CLI Mode
Traditional command-line interface via [main.py](main.py) with hierarchical menu system:
- Main Menu: (1) Start answering, (2) Extract questions, (3) Settings, (4) Exit
- Start Answering Submenu: (1) Batch answering, (2) Get student access_token, (3) Single course answering, (4) Question bank import, (5) Return
- Extract Questions Submenu: (1) Get teacher access_token, (2) Extract all courses, (3) Extract single course, (4) Export results, (5) Return

## Architecture

### Browser Manager
- **[src/core/browser.py](src/core/browser.py)** - Singleton `BrowserManager` class
  - Single browser instance with multiple isolated contexts
  - Thread-safe work queue for Playwright operations
  - AsyncIO compatible for Flet integration

**Usage Pattern:**
```python
from src.core.browser import get_browser_manager, BrowserType

browser_manager = get_browser_manager()
browser = browser_manager.start_browser(headless=False)
context = browser_manager.get_context(BrowserType.STUDENT)
page = browser_manager.get_page(BrowserType.STUDENT)
browser_manager.stop_browser()
```

**Important**: Always use `get_browser_manager()` to get the singleton instance. Do NOT instantiate `BrowserManager()` directly.

### Authentication Modules
- **[src/auth/teacher.py](src/auth/teacher.py)** - Teacher portal login
  - Login at `https://admin.cqzuxia.com/#/login`
  - Extracts `smartedu.admin.token` cookie

- **[src/auth/student.py](src/auth/student.py)** - Student portal login
  - Login at `https://ai.cqzuxia.com/#/login`
  - Monitors `/connect/token` API to capture access_token
  - Multi-strategy login button click: `.loginbtn` → `text=登录` → JavaScript fallback
  - **Helper functions**: `get_student_courses()`, `navigate_to_course()`, `get_course_progress_from_page()`, `get_cached_access_token()`

### Question Extraction Pipeline
- **[src/extraction/extractor.py](src/extraction/extractor.py)** - Core extraction workflow
  - `extract_course_answers(course_id)` - Standalone function for single-course extraction
  - `Extractor` class - Interactive extraction with user input
  - API call chain: class → course → chapter → knowledge → questions → options

**Important**: All API calls use `get_api_client()` which applies rate limiting automatically. Do not add manual `time.sleep()` calls.

### Auto-Answering Modules
- **[src/answering/browser_answer.py](src/answering/browser_answer.py)** - Browser-based answering
- **[src/answering/api_answer.py](src/answering/api_answer.py)** - API-based answering (faster)

### Course Certification Modules
- **[src/certification/workflow.py](src/certification/workflow.py)** - Course certification workflow
- **[src/certification/api_answer.py](src/certification/api_answer.py)** - API-based answering for certification

### Cloud Exam Modules (Beta - Partial Implementation)
- **[src/cloud_exam/workflow.py](src/cloud_exam/workflow.py)** - Cloud exam workflow
- **[src/cloud_exam/api_client.py](src/cloud_exam/api_client.py)** - Cloud exam API client
- **[src/cloud_exam/models.py](src/cloud_exam/models.py)** - Cloud exam data models

**⚠️ Known Issue**: Answer injection is blocked by missing `ExamMemberID` parameter. This is a known limitation documented in the code.

### Data Management
- **[src/extraction/exporter.py](src/extraction/exporter.py)** - JSON export
- **[src/extraction/importer.py](src/extraction/importer.py)** - Question bank import
- **[src/extraction/file_handler.py](src/extraction/file_handler.py)** - File I/O utilities

### API Client and Rate Limiting
- **[src/core/api_client.py](src/core/api_client.py)** - Unified HTTP client
  - Singleton instance via `get_api_client()`
  - Request caching with TTL
  - Smart retry with exponential backoff
  - **Rate limiting**: `low` (50ms), `medium` (1s), `medium_high` (2s), `high` (3s)

- **[src/core/config.py](src/core/config.py)** - CLI settings management
  - File: `cli_config.json` (auto-generated)
  - Credentials storage and API rate limiting settings
  - Singleton instance via `get_settings_manager()`

## Key Dependencies
- **playwright** (>=1.57.0) - Browser automation
- **requests** (>=2.31.0) - HTTP client
- **flet** (>=0.80.0) - GUI framework

## Important Architectural Patterns

### Singleton Pattern for Global Services
- **API Client**: Use `get_api_client()` - do NOT instantiate `APIClient()` directly
- **Settings Manager**: Use `get_settings_manager()` - do NOT instantiate `SettingsManager()` directly
- **Browser Manager**: Use `get_browser_manager()` - do NOT instantiate `BrowserManager()` directly

### Rate Limiting Architecture
**Do's:**
- ✅ Use `get_api_client().get/post()` for all HTTP requests
- ✅ Adjust speed via `cli_config.json` → `api_settings.rate_level`

**Don'ts:**
- ❌ Add manual `time.sleep()` in extraction code
- ❌ Use direct `requests.get/post()` calls

### Playwright Browser Path Setup

**Development Environment:**
- Uses system-installed Playwright browsers via `python -m playwright install chromium`

**Packaged Executable Environment:**
- Browser bundled in `dist/playwright_browsers/`
- `main.py` contains `setup_playwright_browser()` to set paths before importing Playwright

**Playwright 1.57.0+ Headless Mode:**
Use `args=['--headless=new']` parameter when launching headless browser to force full Chromium (not `chromium_headless_shell`):

```python
browser = playwright.chromium.launch(
    headless=headless,
    args=['--headless=new'] if headless else None
)
```

### GUI View Caching Pattern
The GUI implements view caching to preserve state when switching tabs:

```python
self.cached_contents = {
    0: None,  # Answering view
    1: None,  # Extraction view
    2: None,  # Settings view
}
```

### AsyncIO Compatibility Pattern
Flet uses asyncio, but Playwright's sync API cannot run inside an asyncio event loop. Detect asyncio environment and run Playwright in a separate thread:

```python
try:
    import asyncio
    asyncio.get_running_loop()
    # Run Playwright in separate thread with new event loop
    import threading

    def run_in_new_loop():
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        # Run Playwright sync code here

    thread = threading.Thread(target=run_in_new_loop)
    thread.start()
    thread.join()

except RuntimeError:
    # No asyncio loop - run directly
    pass
```

## API Endpoints

### Teacher Portal (`https://admin.cqzuxia.com/evaluation/api/TeacherEvaluation/`)
- `GetClassByTeacherID` - Get teacher's class list
- `GetEvaluationSummaryByClassID?classID={id}` - Get course summary
- `GetChapterEvaluationByClassID?classID={id}` - Get chapter list
- `GetEvaluationKnowledgeSummaryByClass?classID={id}` - Get knowledge points
- `GetKnowQuestionEvaluation?classID={id}&knowledgeID={id}` - Get questions
- `GetQuestionAnswerListByQID?classID={id}&questionID={id}` - Get options

### Student Portal (`https://ai.cqzuxia.com/`)
- `/connect/token` - OAuth2 token endpoint (POST) - returns access_token
- Course list and progress APIs (accessed via Bearer token)

### Course Certification Portal (`https://zxsz.cqzuxia.com/teacherCertifiApi/api/TeacherCourseEvaluate`)
- Different from teacher/student portal APIs
- Requires Bearer token authentication

### Cloud Exam Portal (`https://ai.cqzuxia.com/exam/api/StudentExam`)
- Uses student portal access_token
- **Note**: API response contains `questiionList` with **3 i's** (intentional backend typo)
- `GetQuestionsByExpId?expID={exp_id}` - Get exam questions
- `GetStudentAnswerList?expID={exp_id}` - Get submitted answers
- `StudentAnswer` (POST) - Submit single answer

## Common Issues

### SSL Certificate Verification Issues

**Problem**: SSL certificate verification failures on Windows, especially in new environments.

**Error message**:
```
<urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed:
unable to get local issuer certificate (_ssl.c:1000)>
```

**Solutions**:

**Solution 1: Automatic configuration (v3.2.0+)**

The program now automatically configures SSL certificates on startup using the `certifi` package. No manual intervention required.

**Solution 2: Update certifi**

```bash
pip install --upgrade certifi
```

**Solution 3: Set environment variables (temporary)**

PowerShell:
```powershell
$env:SSL_CERT_FILE = python -c "import certifi; print(certifi.where())"
python main.py
```

CMD:
```cmd
for /f %i in ('python -c "import certifi; print(certifi.where())"') do set SSL_CERT_FILE=%i
python main.py
```

**Solution 4: Manual configuration**

See detailed guide: [SSL_SETUP.md](docs/SSL_SETUP.md)

**Technical details**:
- SSL auto-configuration module: `src/core/ssl_helper.py`
- Configured at startup in `main.py` before any network operations
- Uses `certifi` package for root certificates
- Affects urllib, requests, and all HTTPS connections

### Flet Library Installation Issues

**Problem**: Flet library not installed or version incompatible.

**Solutions**:

1. **Auto-install**: The program will automatically detect and install Flet on startup
2. **Manual install**:
   ```bash
   pip install flet>=0.82.0
   pip install flet-desktop
   ```
3. **Use requirements.txt**:
   ```bash
   pip install -r requirements.txt
   ```
4. **Domestic mirrors** (China):
   ```bash
   pip install flet -i https://pypi.tuna.tsinghua.edu.cn/simple
   pip install flet-desktop -i https://pypi.tuna.tsinghua.edu.cn/simple
   ```

**⚠️ Important: Flet 0.8.0+ requires flet-desktop**

Starting from Flet 0.8.0, you need to install both `flet` and `flet-desktop` packages:

```bash
pip install flet>=0.82.0 flet-desktop
```

**Error: `No module named 'flet_desktop'`**

If you see this error, install flet-desktop:

```bash
pip install flet-desktop
```

**Flet Executable Download Issues**:

If Flet desktop executable fails to download automatically:
- **Manual download**: [FLET_MANUAL_DOWNLOAD.md](FLET_MANUAL_DOWNLOAD.md)
- **Download links**:
  - Windows: https://github.com/flet-dev/flet/releases/latest/download/flet-latest-windows-x64.zip
  - Linux: https://github.com/flet-dev/flet/releases/latest/download/flet-latest-linux-x64.tar.gz
  - macOS: https://github.com/flet-dev/flet/releases/latest/download/flet-latest-macos-x64.tar.gz
- **Install location**:
  - Windows: `C:\Users\YourName\.flet\bin\flet.exe`
  - Linux/Mac: `~/.flet/bin/flet`

**Detailed guides**: See `FLET_INSTALL_GUIDE.md` and `FLET_MANUAL_DOWNLOAD.md`

**Version compatibility**:
- Minimum: 0.80.0
- Recommended: 0.82.0+
- **Important**: 0.8.0+ has breaking API changes

### Playwright Browser Installation Issues

**Problem**: Playwright browser fails to install, especially in packaged executables.

**Solutions**:

1. **Auto-install**: The program will automatically detect and install the browser on startup
2. **Manual install**:
   ```bash
   python -m playwright install chromium
   ```
3. **Use local browser**: Add to `cli_config.json`:
   ```json
   {
     "browser_settings": {
       "local_browser_path": "C:\\Path\\To\\chrome.exe"
     }
   }
   ```
4. **Detailed guide**: See `docs/BROWSER_SETUP.md`

**Common browser paths**:
- Windows: `C:\Program Files\Google\Chrome\Application\chrome.exe`
- Linux: `/usr/bin/chromium`
- macOS: `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`

### Login and Token Issues
- **Login button click failure**: Student portal uses `<div class="loginbtn">` instead of button element. Handled by multi-strategy click approach.
- **Token not captured**: Ensure network listeners are attached before page navigation

### Browser and Playwright Issues
- **Playwright instance conflicts**: Use `BrowserManager` instead of trying to run multiple browser instances
- **Playwright 1.57.0+ headless mode error**: Use `args=['--headless=new']` to force full Chromium
- **Playwright error in GUI mode**: "Playwright Sync API inside the asyncio loop" - Use AsyncIO Compatibility Pattern

### API and Rate Limiting Issues
- **API rate limit not working**: Ensure you're using `get_api_client()` instead of direct `requests` calls
- **Rate limiting**: Adjust speed via `cli_config.json` → `api_settings.rate_level`

### Encoding Issues
- **Chinese characters garbled on Windows**: The project uses `UTF8StreamHandler` in [src/auth/student.py](src/auth/student.py) for proper encoding

## Git Workflow

**Current branches:**
- `main` - Primary development branch
- `dev` - Development branch

**Commit format:**
```
<type>(<scope>): <description>

Types: feat, fix, gui, refactor, docs, test, chore

Examples:
feat(gui): add remember password feature
fix(api): resolve rate limiting issue
```

## Project Structure

```
src/
├── core/               # Core utilities and singletons
│   ├── api_client.py   # Unified HTTP client with rate limiting
│   ├── app_state.py    # Thread-safe global state manager
│   ├── browser.py      # BrowserManager singleton
│   ├── config.py       # CLI settings management
│   └── constants.py    # Application constants
├── auth/               # Authentication modules
│   ├── student.py      # Student portal login
│   ├── teacher.py      # Teacher portal login
│   └── token_manager.py # Token caching
├── certification/      # Course certification workflow
│   ├── workflow.py
│   └── api_answer.py
├── cloud_exam/         # Cloud exam workflow (Beta)
│   ├── workflow.py
│   ├── api_client.py
│   └── models.py
├── extraction/         # Data extraction pipeline
│   ├── extractor.py
│   ├── exporter.py
│   ├── importer.py
│   └── file_handler.py
├── answering/          # Auto-answering modules
│   ├── browser_answer.py
│   └── api_answer.py
├── ui/                 # GUI components (Flet)
│   ├── main_gui.py
│   └── views/
├── modules/            # Extended modules
├── utils/              # General utilities
└── extract_answers.py  # Standalone extraction script
```
