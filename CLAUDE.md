# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ZX Answering Assistant (智能答题助手) is an automated quiz interaction system that uses browser automation (Playwright) to authenticate with web-based quiz platforms, extract question banks, and manage data import/export workflows. The system supports both teacher and student portals, with two interface modes: **GUI mode (Flet-based)** and **CLI mode**.

**Key architectural note (v2.6.0+)**: The project uses `BrowserManager` to run multiple isolated browser contexts (student, teacher, course certification) in a single Playwright browser instance. The legacy `extract_answers.py` script can still run independently as a standalone tool with its own browser instance.

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
```

### Install Playwright Browser (Required for automation)
```bash
python -m playwright install chromium
```

### Run Application

**GUI Mode (default):**
```bash
python main.py
# or explicitly
python main.py --mode gui
```

**CLI Mode:**
```bash
python main.py --cli
```

### Standalone Answer Extraction (Runs independently without student portal)
```bash
python -m src.extract_answers <course_id>
```
Extracts answers for a specific course using teacher credentials. Uses separate Playwright instance to avoid conflicts with student portal.

### Build Executable
```bash
# Directory mode (recommended, faster startup)
python build.py --mode onedir

# Single file mode
python build.py --mode onefile

# Build both modes
python build.py --mode both

# With UPX compression (reduces size by 30-50%)
python build.py --upx

# Custom build directory
python build.py --build-dir D:\BuildOutput
```
Creates executable in `dist/`. Playwright browser downloads on first run of the executable.

**Build Options:**
- `--mode {onedir,onefile,both}`: Choose build mode (default: onedir)
- `--upx`: Enable UPX compression to reduce executable size
- `--build-dir`: Custom build output directory

## UI Architecture

### GUI Mode (Flet Framework)
The application features a modern GUI built with **Flet** (`flet>=0.80.0`):

- **[src/main_gui.py](src/main_gui.py)** - Main GUI entry point with `MainApp` class
  - Navigation rail with collapsible sidebar
  - View caching mechanism to preserve state when switching tabs
  - Window cleanup handler for Playwright browser on close

**⚠️ CRITICAL: Flet Version Compatibility**
- **Flet 0.8.0+ has breaking changes** - Many APIs from earlier versions are deprecated
- Common deprecations to watch for:
  - Old: `page.window_center()` → New: `page.window_center` (property, not method)
  - Old: `page.add()` → New: `page.add()` (still works but check parameter changes)
  - Control properties and event handlers may have different signatures
- **Always check Context7 MCP for latest Flet documentation** before writing UI code
- Alternatively, check official Flet documentation or use web search for "flet <component_name> python"
- When using Context7 MCP, query: "flet <component_name> documentation 2026"

**View Architecture** ([src/ui/views/](src/ui/views/)):
- **[answering_view.py](src/ui/views/answering_view.py)** - Student answering workflow
  - Student login with credential input
  - Course list display with progress indicators
  - Course navigation
  - Auto-answer with real-time log display
  - Question bank (JSON) loading
- **[extraction_view.py](src/ui/views/extraction_view.py)** - Teacher-side answer extraction interface
- **[settings_view.py](src/ui/views/settings_view.py)** - Configuration management
- **[course_certification_view.py](src/ui/views/course_certification_view.py)** - Course certification workflow (v2.6.0)
- **[cloud_exam_view.py](src/ui/views/cloud_exam_view.py)** - Cloud exam page (⚠️ **Placeholder only** - not yet implemented)

### CLI Mode
Traditional command-line interface accessed via [main.py](main.py) with hierarchical menu system:
- Main Menu: (1) Start answering, (2) Extract questions, (3) Settings, (4) Exit
- Start Answering Submenu: (1) Batch answering, (2) Get student access_token, (3) Single course answering, (4) Question bank import, (5) Return
- Extract Questions Submenu: (1) Get teacher access_token, (2) Extract all courses, (3) Extract single course, (4) Export results, (5) Return

## Architecture

### Browser Manager (v2.6.0 - Unified Browser Management)
**⚠️ CRITICAL ARCHITECTURAL CHANGE**: The v2.6.0 release introduced a unified browser management system that **replaces** the old subprocess pattern for concurrent Playwright instances.

- **[src/core/browser.py](src/core/browser.py)** - Singleton `BrowserManager` class
  - **Single Browser Instance**: Only one Playwright browser runs for the entire application
  - **Multiple Contexts**: Each module (student, teacher, course certification) gets an isolated `BrowserContext`
  - **Thread-Safe Work Queue**: All Playwright operations execute in a dedicated worker thread
  - **Context Isolation**: Cookie, Session, and LocalStorage are completely separate per context
  - **AsyncIO Compatible**: Works seamlessly with Flet's asyncio event loop

**Usage Pattern:**
```python
from src.core.browser import get_browser_manager, BrowserType

# Get singleton instance
browser_manager = get_browser_manager()

# Start browser (only once)
browser = browser_manager.start_browser(headless=False)

# Get isolated context for specific module
student_context = browser_manager.get_context(BrowserType.STUDENT)
teacher_context = browser_manager.get_context(BrowserType.TEACHER)

# Get page in context
page = browser_manager.get_page(BrowserType.STUDENT)

# Clean up specific context
browser_manager.close_context(BrowserType.STUDENT)

# Shutdown entire browser
browser_manager.stop_browser()
```

**Why This Matters:**
- **Old way (pre-v2.6.0)**: Student and teacher portals ran in separate processes (`subprocess.run([sys.executable, "extract_answers.py"])`)
- **New way (v2.6.0+)**: Everything runs in one process with isolated contexts, reducing resource usage and improving stability

**Thread-Safe Work Queue Pattern:**
The `BrowserManager` implements a work queue to ensure all Playwright operations execute in a dedicated worker thread, avoiding greenlet threading issues:

```python
# Operations are submitted to a queue and executed in the worker thread
result = browser_manager._execute_in_thread(
    lambda: context.new_page()
)
```

**Important Implementation Notes:**
- Always use `get_browser_manager()` to get the singleton instance
- Do NOT instantiate `BrowserManager()` directly
- Context types are defined in `BrowserType` enum: `STUDENT`, `TEACHER`, `COURSE_CERTIFICATION`
- All browser operations are thread-safe via the work queue mechanism
- Remember to call `stop_browser()` on application shutdown to clean up resources

### Authentication Modules
- **[src/auth/teacher.py](src/auth/teacher.py)** - Teacher portal login at `https://admin.cqzuxia.com/#/login`
  - Accepts username/password via input prompts
  - Extracts `smartedu.admin.token` cookie for API authentication
  - Uses button selector `button:has-text('登录')`

- **[src/auth/student.py](src/auth/student.py)** - Student portal login at `https://ai.cqzuxia.com/#/login`
  - Token management via `src/auth/token_manager.py`
  - Accepts username/password via input prompts or from `cli_config.json`
  - Monitors `/connect/token` API endpoint to capture access_token
  - Uses multi-strategy login button click: `.loginbtn` class selector → `text=登录` → JavaScript fallback
  - **⚠️ AsyncIO Compatible**: Implements asyncio detection pattern (v2.2.0) - see "AsyncIO Compatibility Pattern" below
  - **Helper functions**:
    - `get_student_courses(access_token)` - Fetch student's course list
    - `get_uncompleted_chapters(access_token, course_id, delay_ms, max_retries)` - Get incomplete knowledge points
    - `navigate_to_course(course_id)` - Navigate student browser to specific course
    - `get_course_progress_from_page()` - Parse current page to extract completion statistics
    - `get_access_token_from_browser()` - Extract token from active browser context
    - `get_cached_access_token()` - Retrieve cached token without re-login
    - `close_browser()` - Clean up Playwright resources

### Question Extraction Pipeline
- **[src/extraction/extractor.py](src/extraction/extractor.py)** - Core `Extractor` class implementing the data extraction workflow:
  - Standalone function `extract_course_answers(course_id, progress_callback=None)` for single-course extraction
  - `Extractor` class for interactive extraction with user input
  - API call chain: class → course → chapter → knowledge → questions → options
  - **`extract_course_answers(course_id)`** - Standalone function for single-course answer extraction (called by extract_answers.py)
    - Logs in via teacher portal
    - Gets class list → filters by grade → selects class
    - Gets course list → finds matching course_id
    - Extracts chapters, knowledge points, questions, and options
    - Returns structured data with course info and answer key

  - **`Extractor` class** - Full extraction workflow with user interaction:
    1. **Login** via Playwright browser automation
    2. **Get Class List** - `GetClassByTeacherID` API
    3. **Select Grade** - Filters classes by grade (e.g., "2024", "2025")
    4. **Select Class** - User selects from filtered classes
    5. **Get Course List** - `GetEvaluationSummaryByClassID` API
    6. **Get Chapter List** - `GetChapterEvaluationByClassID` API
    7. **Get Knowledge List** - `GetEvaluationKnowledgeSummaryByClass` API
    8. **Get Question List** - `GetKnowQuestionEvaluation` API (per knowledge point)
    9. **Get Question Options** - `GetQuestionAnswerListByQID` API (per question)
    10. **Rate Limiting** - Handled by API client, configurable via `cli_config.json`

  Data flow: `class_list` → `filtered_classes` → `course_list` → `chapter_list` → `knowledge_list` → `knowledge_questions` → `question_options`

  **Important**: All API calls use `get_api_client()` which applies rate limiting automatically. Do not add manual `time.sleep()` calls.

### Auto-Answering Modules
- **[src/answering/browser_answer.py](src/answering/browser_answer.py)** - Browser-compatible mode answering
  - `AutoAnswer` class simulates user interactions by clicking UI elements
  - Supports keyboard interrupt ('Q' key) for graceful shutdown

- **[src/answering/api_answer.py](src/answering/api_answer.py)** - API暴力模式
  - `APIAutoAnswer` class for direct API calls (faster than browser mode)
  - Network retry mechanism (up to 3 retries)
  - Supports graceful shutdown with keyboard listener

### Course Certification Modules (课程认证)
- **[src/certification/workflow.py](src/certification/workflow.py)** - Course certification workflow module
  - `get_access_token()` - Teacher authentication for course certification
  - `start_answering()` - Main answering entry point
  - `import_question_bank()` - Load JSON question banks
  - Uses `APICourseAnswer` for automated answering

- **[src/certification/api_answer.py](src/certification/api_answer.py)** - API-based course certification answering
  - `APICourseAnswer` class for direct API submission
  - Text normalization (removes HTML entities, extra whitespace)
  - Text similarity matching for answer selection
  - Uses different API base: `https://zxsz.cqzuxia.com/teacherCertifiApi/api/TeacherCourseEvaluate`
  - Much faster than browser-based answering

### Data Management
- **[src/extraction/exporter.py](src/extraction/exporter.py)** - `DataExporter` class exports extracted data to JSON
- **[src/extraction/importer.py](src/extraction/importer.py)** - `QuestionBankImporter` class imports and parses exported JSON
- **[src/extraction/file_handler.py](src/extraction/file_handler.py)** - File I/O utilities for JSON read/write operations

### API Client and Rate Limiting
- **[src/core/api_client.py](src/core/api_client.py)** - Unified API request client with configurable rate limiting:
  - Singleton instance via `get_api_client()`
  - Request caching with TTL
  - Smart retry with exponential backoff
  - **Rate Limiting**: Applies delays before **every** API request (not just on retry)
  - **Configurable Levels**: `low` (50ms), `medium` (1s), `medium_high` (2s), `high` (3s)
  - **Automatic Retry**: Network errors trigger exponential backoff (1s, 2s, 4s...)
  - **Smart Detection**: Auto-retries on connection errors, 5xx errors, and 429 rate limits
  - **Global Instance**: Use `get_api_client()` to get the singleton instance
  - **Usage**: All API calls should go through this client, not direct `requests` calls

- **[src/core/config.py](src/core/config.py)** - CLI settings management with persistent configuration:
  - **File**: `cli_config.json` (auto-generated on first run)
  - **Credentials Storage**: Saves student/teacher usernames and passwords
  - **API Settings**: Configurable rate level and max retry count
  - **APIRateLevel Enum**: LOW, MEDIUM, MEDIUM_HIGH, HIGH
  - Usage: `settings_manager = get_settings_manager()` to get singleton instance

### Configuration
- **Configuration is managed through `cli_config.json`** (auto-generated on first run)
  - Student/teacher credentials storage
  - API rate limiting settings
  - Max retry count configuration
- **No YAML config needed** - The project uses JSON for configuration (simplified from earlier versions)
  - App settings are managed in code
  - Logging uses loguru with programmatic configuration
  - Data directories are created automatically as needed

### Build System
- **[build.py](build.py)** - Simplified PyInstaller build script:
  - Installs PyInstaller if missing
  - Installs dependencies from `requirements.txt`
  - Installs Playwright Chromium browser
  - Creates standalone executable with hidden imports for Playwright modules
  - Bundles `src/` directory into executable
  - Supports onedir and onefile build modes

**Build Features:**

1. **Build Modes**:
   - `onedir`: Directory mode (recommended, faster startup)
   - `onefile`: Single file mode (portable)
   - `both`: Build both versions

2. **UPX Compression** (`--upx` flag):
   - Compresses executable and DLLs to reduce size by 30-50%
   - Requires UPX to be installed and in system PATH

- **[version.py](version.py)** - Version information management:
  - `VERSION`: Main version number (e.g., "2.6.6")
  - `VERSION_NAME`: Application name
  - `BUILD_DATE/TIME`: Auto-updated during build
  - `GIT_COMMIT`: Git hash (auto-updated during build)
  - `BUILD_MODE`: "development" or "release"

## Key Dependencies
- **playwright** (>=1.57.0) - Browser automation for login and token extraction
- **requests** (>=2.31.0) - HTTP client for API calls
- **flet** (>=0.80.0) - GUI framework for desktop application
- **keyboard** (>=0.13.5) - Keyboard listener for graceful shutdown

**Note**: The project uses minimal dependencies as listed in [requirements.txt](requirements.txt). Only these 4 core packages are required for the application to run.

**Not actively used** (mentioned in older documentation but not in current codebase):
- `loguru` - Not used; logging uses Python's built-in `logging` module
- `pyyaml` - Not used; configuration uses JSON format
- `pandas`/`openpyxl` - Not used; question banks use JSON format
- `aiohttp`, `tqdm`, `python-dotenv` - Not used in current implementation

## Important Architectural Patterns

### Singleton Pattern for Global Services
The codebase uses singleton instances for critical services to maintain consistency:

1. **API Client** (`src/core/api_client.py`)
   ```python
   from src.core.api_client import get_api_client
   api_client = get_api_client()  # Returns singleton instance
   response = api_client.get(url, headers=headers)
   ```
   - Do NOT instantiate `APIClient()` directly
   - Always use `get_api_client()` to get the global instance
   - The singleton ensures rate limiting works across all API calls

2. **Settings Manager** (`src/core/config.py`)
   ```python
   from src.core.config import get_settings_manager
   settings = get_settings_manager()  # Returns singleton instance
   rate_level = settings.get_rate_level()
   ```
   - Do NOT instantiate `SettingsManager()` directly
   - Always use `get_settings_manager()` to get the global instance
   - The singleton ensures configuration consistency

### Rate Limiting Architecture
Rate limiting is centralized in the API client layer:

**Do's:**
- ✅ Use `get_api_client().get/post()` for all HTTP requests
- ✅ Adjust speed via `cli_config.json` → `api_settings.rate_level`
- ✅ Trust that the client handles delays automatically

**Don'ts:**
- ❌ Add manual `time.sleep()` in extraction code
- ❌ Use direct `requests.get/post()` calls (bypasses rate limiting)
- ❌ Try to implement custom rate limiting logic

### Progress Callback Pattern for GUI Updates
The GUI uses callback functions to update UI with real-time progress from long-running operations:

```python
def progress_callback(message: str, level: str = "info"):
    """Callback for GUI progress updates"""
    # Updates log display in the UI
    pass

# Usage in extraction/answering functions
extract_course_answers(course_id, progress_callback=progress_callback)
```

- **Callback parameters**: `message` (str) - text to display, `level` (str) - "info", "success", "warning", "error"
- **Threading**: Long-running operations should run in separate threads to avoid blocking UI
- **Thread-safe updates**: Flet UI updates from background threads must use `page.update()` or similar thread-safe mechanisms

### Playwright Browser Path Setup
The project handles Playwright browser paths differently in development vs packaged environments:

**Development Environment:**
- Uses system-installed Playwright browsers (via `python -m playwright install chromium`)
- No special configuration needed

**Packaged Executable Environment:**
- Browser is bundled in `dist/playwright_browsers/` directory
- `main.py` contains `setup_playwright_browser()` function that:
  - Detects if running in packaged mode (`sys.frozen` flag)
  - Sets `PLAYWRIGHT_BROWSERS_PATH` environment variable to bundled browser location
  - Must be called **before** importing any Playwright modules
- `copy_browser.py` script prepares browser for packaging (copies from system to project directory)

**Playwright 1.57.0+ Headless Mode Compatibility (v2.6.5+)**
Playwright 1.57.0 introduced `chromium_headless_shell` which doesn't work with bundled browsers in packaged executables. Use `args=['--headless=new']` parameter when launching headless browser to force full Chromium.

```python
# In src/core/browser.py
browser = playwright.chromium.launch(
    headless=headless,
    args=['--headless=new'] if headless else None  # Force full Chromium
)
```

**Important:** When working on Playwright-related code, always use `args=['--headless=new']` for headless mode to ensure compatibility. Test both in development and after packaging.

### GUI View Caching Pattern
The GUI implements view caching to preserve state when switching between navigation tabs:

```python
# In MainApp.__init__
self.cached_contents = {
    0: None,  # Answering view
    1: None,  # Extraction view
    2: None,  # Settings view
}

# Initial load caches all views
self._cache_all_contents()

# Navigation switches between cached content
self.content_area.content = self.cached_contents[destination_index]
```

- **Why**: Prevents re-creating views on each navigation (preserves scroll position, input fields, etc.)
- **Trade-off**: Slightly slower initial load, faster subsequent navigation
- **When implementing new views**: Add to `cached_contents` dict and call in `_cache_all_contents()`

### Subprocess Pattern for Concurrent Playwright Instances (DEPRECATED - Pre-v2.6.0)

**⚠️ This pattern is DEPRECATED**. The v2.6.0 release introduced `BrowserManager` (see above) which replaces subprocess-based isolation.

**Old Pattern (for reference only when working with legacy code):**
Since Playwright cannot run multiple browser instances in the same process:
- Student portal (answering) and teacher portal (extraction) both need active browsers
- Old solution: Run extraction in separate process via `subprocess.run([sys.executable, "extract_answers.py", str(course_id)])`

**Current Approach (v2.6.0+):**
- Use `BrowserManager` with multiple isolated contexts in a single browser instance
- See "Browser Manager (v2.6.0)" section above for details

### AsyncIO Compatibility Pattern (v2.2.0)
**Problem**: Flet framework uses asyncio, but Playwright's sync API cannot run inside an asyncio event loop.
**Solution**: Detect asyncio environment and run Playwright in a separate thread with a new event loop.

```python
# In src/auth/student.py and other Playwright modules
try:
    import asyncio
    asyncio.get_running_loop()
    # Detected asyncio environment - use separate thread
    import threading

    def run_in_new_loop():
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        # Run Playwright sync code here
        result[0] = _function_with_playwright()

    thread = threading.Thread(target=run_in_new_loop)
    thread.start()
    thread.join()
    return result[0]

except RuntimeError:
    # No asyncio loop - run directly
    pass
```

**When implementing new Playwright code**: Always use this pattern in modules that might be called from Flet GUI.

### Browser Health Monitoring and Recovery (v2.2.0)
The system implements automatic browser crash detection and recovery:

**Detection Pattern**:
```python
def check_browser_alive():
    """Check if browser is still connected"""
    global _browser_instance
    if _browser_instance is None:
        return False
    try:
        # Try to access browser context
        _browser_instance.contexts
        return True
    except Exception:
        return False
```

**Recovery Flow**:
1. Before any browser operation, check if browser is alive
2. If not alive, clean up resources (close browser, stop Playwright)
3. Notify user (GUI: dialog, CLI: prompt)
4. Re-login to restart browser
5. Continue operation

**Multi-layer Cleanup**:
- Close browser instance: `browser.close()`
- Stop Playwright: `playwright.stop()`
- Reset global variables: `_browser_instance = None`
- Force cleanup on errors

**Important**: Always check browser health before operations in GUI mode to prevent crashes.

## Authentication Flow
1. Playwright launches Chromium browser (headless=False for visibility)
2. Navigates to login URL and waits for input fields
3. Fills username/password using selector `input[placeholder='请输入账户']` and `input[placeholder='请输入密码']`
4. Clicks login button using fallback strategy
5. Monitors network requests/responses or extracts cookies for `access_token`
6. Token validity: 5 hours (18000 seconds)
7. Token format: Bearer authentication header

## Data Structures
- **Single Course Export**: `{ class: { course: { chapters: [...] } } }`
- **Multi Course Export**: `{ class: {...}, course_list: [...], chapters: [...] }`
- **Question Options**: Array of objects with `id`, `oppentionContent`, `isTrue` (boolean), `oppentionOrder`
- **Knowledge Questions**: Grouped by `KnowledgeID`, nested under chapter hierarchy

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
- **Note**: Different from teacher/student portal APIs
- Used by `src/course_api_answer.py` for course certification answering
- Endpoints include question submission and answer retrieval
- Requires Bearer token authentication

## Common Issues
- **Login button click failure**: The student portal uses a generic `<div class="loginbtn">` instead of a button element. The multi-strategy click approach (class selector → text selector → JS fallback) handles this.
- **Token not captured**: Ensure network listeners are attached before page navigation
- **Rate limiting**: All API calls respect the rate limit configured in `cli_config.json`. To adjust speed, modify `api_settings.rate_level`:
  - `low` (50ms) - for APIs without rate limits
  - `medium` (1s) - default, balanced speed
  - `medium_high` (2s) or `high` (3s) - for strict rate limits
- **Browser installation**: Playwright downloads Chromium on first run; requires network connection
- **Playwright instance conflicts (pre-v2.6.0)**: Cannot run multiple Playwright browsers in same process. Use `BrowserManager` (v2.6.0+) instead which handles multiple isolated contexts in a single browser instance.
- **API rate limit not working**: Ensure you're using `get_api_client()` instead of direct `requests` calls. The rate limit is applied in `APIClient.request()` before every request.
- **Playwright error in GUI mode**: "Playwright Sync API inside the asyncio loop" - Use the AsyncIO Compatibility Pattern (see Architectural Patterns) to run Playwright code in a separate thread with its own event loop.
- **Browser crashes in GUI**: The v2.2.0 recovery system automatically detects and recovers from browser crashes. Users will see a re-login prompt. Implement health checks before browser operations using `check_browser_alive()` pattern.
- **Chinese characters garbled on Windows**: The `UTF8StreamHandler` in student_login.py handles console encoding. Ensure all log files use UTF-8 encoding.
- **Playwright 1.57.0+ headless mode error** (v2.6.5+): "Executable doesn't exist at chromium_headless_shell" - This occurs because Playwright 1.57.0+ defaults to `chromium_headless_shell` which isn't included in bundled browsers. **Solution**: The codebase now uses `args=['--headless=new']` to force full Chromium. Ensure you're using v2.6.5 or later.
- **Missing .py files after build** (v2.6.6+): When using `--compile-src` flag, source .py files are automatically deleted after packaging, leaving only .pyc bytecode files. This is intentional behavior. The `__init__.py` files are preserved for package imports.

## Platform-Specific Considerations

### Windows Console Encoding
Windows console may not support UTF-8 by default, causing encoding issues when displaying Chinese characters or logging.

**Solution Implemented**: The project uses `UTF8StreamHandler` in [src/auth/student.py](src/auth/student.py) for proper encoding:

```python
class UTF8StreamHandler(logging.StreamHandler):
    def emit(self, record):
        try:
            msg = self.format(record)
            stream = self.stream
            # Try UTF-8 encoding first
            if hasattr(stream, 'buffer'):
                stream.buffer.write(msg.encode('utf-8') + b'\n')
            else:
                stream.write(msg + self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)
```

**When adding new logging**: Always use UTF-8 encoding for file handlers and console output on Windows. The build system also sets UTF-8 console encoding in `main.py`.

### Playwright Browser Paths
See "Playwright Browser Path Setup" section in Architectural Patterns above.

## Course Progress Monitoring
The system includes real-time course progress tracking:
- `display_progress_bar(progress_info)` - Visual progress bar with completion statistics
- `monitor_course_progress(interval=5)` - Continuous monitoring loop (Ctrl+C to stop)
- Progress info includes: `total`, `completed`, `failed`, `not_started`, `progress_percentage`
- Data extracted from student portal page DOM via `get_course_progress_from_page()`

## Git Workflow
Current branches:
- `main` - Primary development branch, production-ready code
- `GUI` - GUI development branch (active branch for Flet interface)
- `dev` - Development branch for experimental features

When committing changes, use conventional commit format:
```
<type>(<scope>): <description>

Types:
- feat: New feature
- fix: Bug fix
- gui: GUI-related changes (use for Flet/UI work)
- refactor: Code refactoring
- docs: Documentation changes
- test: Test-related changes
- chore: Build/configuration changes

Examples:
feat(gui): add remember password feature
fix(api): resolve rate limiting issue
refactor(extraction): improve data flow
feat(course_certification): add API-based answering module
fix(recovery): implement browser crash detection and recovery
```

## Testing

### Test Structure
⚠️ **Note**: As of v2.6.6, the project does not have a formal test suite. Tests should be added to improve code quality and catch regressions.

**Recommended Test Structure** (to be implemented):
- `tests/test_auth_teacher.py` - Teacher portal login tests
- `tests/test_auth_student.py` - Student portal login tests
- `tests/test_core_api_client.py` - API client and rate limiting tests
- `tests/test_core_browser.py` - Browser manager tests
- `tests/test_extraction_extractor.py` - Answer extraction workflow tests

### Running Tests (when implemented)
```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_auth_student.py -v

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=html
```

### Writing Tests (guidelines for future implementation)
- Place all test code in the `tests/` directory
- Use pytest as the test framework
- Name test files as `test_*.py` and test functions as `test_*()`
- Mock Playwright browser operations to avoid actual browser launches in tests
- Use fixtures for common test setup (e.g., test access tokens, mock API responses)

## Version History and Architecture Evolution

Understanding the version history helps when working with older code or debugging version-specific issues:

### v2.8.0 - UI Polish and Configuration Updates
- CLI mode interface beautification with emojis and better formatting
- Logging disabled in CLI mode for cleaner output
- Updated PyYAML dependency added to requirements.txt
- GUI view caching initialization fixed
- Removed code redundancy (379 lines of duplicate code in main.py)

### v2.7.0 - Build System Simplification
- Removed complex build tools module (`src/build_tools/`)
- Simplified build.py with essential features only
- Removed build-time browser and Flet bundling
- Cleaner .gitignore and project structure

### v2.6.0 - v2.6.6 - Legacy Build Features
- Source code pre-compilation to .pyc bytecode (removed in v2.7.0)
- Complex build tools with browser/Flet handlers (removed in v2.7.0)
- Playwright 1.57.0+ compatibility fix with `args=['--headless=new']`

### v2.6.0 - Major Architecture Overhaul
- **Introduced BrowserManager**: Single browser instance with multiple isolated contexts
- **Replaced subprocess pattern**: No longer need separate processes for student/teacher portals
- **Added course certification module**: New `course_certification.py` and `course_api_answer.py`
- **Thread-safe work queue**: All Playwright operations execute in dedicated worker thread

### v2.2.0 - Browser Robustness
- Browser crash detection and recovery system
- AsyncIO compatibility pattern for Flet GUI
- Browser health monitoring

### Pre-v2.2.0 - Legacy Patterns
- Direct browser instantiation without health monitoring
- No AsyncIO compatibility (would crash in Flet GUI)
- Subprocess pattern for concurrent browsers (replaced in v2.6.0)

**When Working with Legacy Code:**
- If you see subprocess calls to `src.extract_answers`, it's pre-v2.6.0 code
- If you see direct `playwright.sync_api().start()` calls without BrowserManager, it's pre-v2.6.0 code
- Always prefer BrowserManager for new code unless working on legacy compatibility

## Project Structure (Current as of v2.8.0)

```
src/
├── core/               # Core utilities and singletons
│   ├── api_client.py   # Unified HTTP client with rate limiting & caching
│   ├── app_state.py    # Thread-safe global state manager
│   ├── browser.py      # BrowserManager singleton for Playwright
│   ├── config.py       # CLI settings management (cli_config.json)
│   └── constants.py    # Application constants
├── auth/               # Authentication modules
│   ├── student.py      # Student portal login & token management
│   ├── teacher.py      # Teacher portal login
│   └── token_manager.py # Token caching and management
├── certification/      # Course certification workflow
│   ├── workflow.py     # Main certification workflow
│   └── api_answer.py   # API-based answering for certification
├── extraction/         # Data extraction pipeline
│   ├── extractor.py    # Answer extraction logic
│   ├── exporter.py     # JSON export functionality
│   ├── importer.py     # Question bank import
│   └── file_handler.py # File I/O utilities
├── answering/          # Auto-answering modules
│   ├── browser_answer.py # Browser-based answering
│   └── api_answer.py     # API-based answering
├── ui/                 # GUI components (Flet)
│   ├── main_gui.py     # GUI entry point
│   └── views/          # Individual view components
│       ├── answering_view.py
│       ├── extraction_view.py
│       ├── course_certification_view.py
│       ├── settings_view.py
│       └── cloud_exam_view.py (placeholder)
├── build_tools/        # Build system utilities
├── utils/              # General utilities
├── caching/            # Caching utilities
└── extract_answers.py  # Standalone extraction script (legacy)
```
