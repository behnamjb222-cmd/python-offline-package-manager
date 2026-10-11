# Troubleshooting

Every error shown by POPM is a `POPMError` with a code, a message and a suggestion (language follows the interface). The log
(*Reports* page, `<data>/logs/popm.log`) contains the technical detail. Install reports: `<data>/logs/install_<id>.txt`.

## Quick answers
| Symptom | Likely cause / fix |
|---|---|
| "Python was not found" / environment shows *invalid* | The interpreter was moved or deleted. *Python environments → Add Python manually…*, then *Re-validate*. |
| "pip is not available (or too old)" | POPM needs pip >= 22.2 in that interpreter: `<python> -m ensurepip --upgrade` or `<python> -m pip install -U pip`. |
| Download says "No compatible wheel was found" | The package has no wheel for the *target* (version/OS/arch). Pick another version, check the target, or allow sdist and build on the target. |
| Bundle refuses: "dependencies are missing" | Download the missing packages for the same target into the repository, or tick *Allow an incomplete bundle* (not recommended). |
| Install plan shows **MISSING** | The repository lacks a dependency for *that* Python/OS. Collect with the correct target; run *Compatibility check*. |
| "The target environment changed since the plan was made" | The interpreter/pip changed between *Check* and *Install*. Create the plan again. |
| Install into system Python: permission denied | Use **New virtual environment**, or run with the privileges that Python's folder requires. |
| New venv creation fails on Debian/Ubuntu | Install `python3-venv` (provides `ensurepip`). |
| "Checksum does not match" | File damaged or modified; do not install. Re-download / re-copy the bundle. |
| "No internet" although the browser works | Proxy needed: Settings → Proxy URL (http/https only). Or corporate TLS inspection: set a CA bundle. |
| Repository shows *invalid* | Run *Health check* / *Verify all files*. Missing files: restore from backup/bundle or hard-delete the record. Unknown files are only reported. |
| App closed during an operation | Next start shows a warning; run *Verify* on the repository. Partial downloads were never registered. Leftover temp folders: *Clean temporary files*. |
| Database locked | Another POPM window is writing. Close it and retry. |
| Compiled package imports fail after a successful install | System libraries/CPU/driver differences; a bundle cannot guarantee run-time behaviour. |
| Windows: SmartScreen blocks POPM.exe | The EXE is unsigned; sign it with your certificate or allow it explicitly. |

## Error codes
| Code | Class | Message (EN) | Suggestion (EN) | پیام (FA) | پیشنهاد (FA) |
|---|---|---|---|---|---|
| `E_CANCELLED` | `OperationCancelledError` | The operation was cancelled. |  | عملیات لغو شد. |  |
| `E_CHECKSUM` | `ChecksumMismatchError` | Checksum does not match. | The file changed or was damaged. Do not install it; re-download it. | checksum مطابقت ندارد. | فایل تغییر کرده یا آسیب دیده است؛ نصبش نکنید و دوباره دانلود کنید. |
| `E_CONFIRM` | `ConfirmationRequiredError` | This action needs explicit confirmation. | Confirm the action in the dialog. | این عملیات نیاز به تأیید صریح دارد. | عملیات را در پنجره تأیید کنید. |
| `E_DB_LOCKED` | `DatabaseLockedError` | The database is locked. | Close other POPM windows and retry. | پایگاه داده قفل شده است. | سایر پنجره‌های POPM را ببندید و دوباره تلاش کنید. |
| `E_DEP_CONFLICT` | `VersionConflictError` | Version requirements conflict. | Relax the pinned versions. | نسخه‌ها با یکدیگر تعارض دارند. | قید نسخه‌ها را شل‌تر کنید. |
| `E_DEP_MISSING` | `MissingDependencyError` | One or more dependencies are missing. | Download the missing dependencies into the repository. | وابستگی مفقود است. | وابستگی‌های مفقود را در مخزن دانلود کنید. |
| `E_DISK_SPACE` | `InsufficientDiskSpaceError` | Not enough free disk space. | Free up space or choose another destination. | فضای دیسک کافی نیست. | فضا آزاد کنید یا مقصد دیگری انتخاب کنید. |
| `E_DOWNLOAD_INCOMPLETE` | `IncompleteDownloadError` | A download was incomplete. | Retry the failed files. | دانلود ناقص است. | فایل‌های ناموفق را دوباره امتحان کنید. |
| `E_ENV_CHANGED` | `EnvironmentChangedError` | The target environment changed since the plan was made. | Create the install plan again. | محیط مقصد پس از ساخت طرح تغییر کرده است. | طرح نصب را دوباره بسازید. |
| `E_FILE_CORRUPT` | `CorruptFileError` | A file is corrupt. | Re-download the file. | فایل خراب است. | فایل را دوباره دانلود کنید. |
| `E_INSTALL_FAILED` | `InstallFailedError` | The installation failed. | See the install report for the pip error. | نصب با خطا مواجه شد. | گزارش نصب را برای خطای pip ببینید. |
| `E_NOT_FOUND` | `NotFoundError` | The requested item was not found. |  | مورد درخواستی پیدا نشد. |  |
| `E_NO_INTERNET` | `NoInternetError` | No internet connection. | Connect to the internet, or use a local index (--find-links). | اینترنت در دسترس نیست. | به اینترنت وصل شوید یا از مخزن محلی استفاده کنید. |
| `E_NO_WHEEL` | `NoCompatibleWheelError` | No compatible wheel was found for the target. | Choose another version or accept an sdist that must be built on the target. | Wheel سازگار برای مقصد پیدا نشد. | نسخه دیگری انتخاب کنید یا sdist را بپذیرید (روی مقصد باید ساخته شود). |
| `E_OVERWRITE` | `OverwriteBlockedError` | Extraction would overwrite existing files. | Choose an empty folder or allow overwriting. | استخراج فایل‌های موجود را بازنویسی می‌کند. | پوشه خالی انتخاب کنید یا بازنویسی را مجاز کنید. |
| `E_PACKAGE_NOT_FOUND` | `PackageNotFoundError` | Package not found. | Check the package name and the index in use. | پکیج پیدا نشد. | نام پکیج و منبع را بررسی کنید. |
| `E_PERMISSION` | `PermissionDeniedError` | Permission denied. | Use a new virtual environment or a folder you own. | مجوز دسترسی کافی نیست. | از محیط مجازی جدید یا پوشه‌ای که مالکش هستید استفاده کنید. |
| `E_PIP_UNAVAILABLE` | `PipUnavailableError` | pip is not available (or too old) in this Python. | Install/upgrade pip (>= 22.2) in that environment. | pip در این Python در دسترس نیست (یا قدیمی است). | pip نسخه ۲۲.۲ یا بالاتر را در آن محیط نصب کنید. |
| `E_PROXY_INVALID` | `InvalidProxyError` | The proxy setting is invalid. | Use the form http://host:port in Settings. | تنظیم Proxy نامعتبر است. | در تنظیمات از قالب http://host:port استفاده کنید. |
| `E_PYTHON_NOT_FOUND` | `PythonNotFoundError` | Python was not found. | Add a Python executable manually on the Environments page. | Python پیدا نشد. | مسیر Python را به‌صورت دستی در صفحه «محیط‌های پایتون» اضافه کنید. |
| `E_PYTHON_UNSUPPORTED` | `UnsupportedPythonError` | This Python version is not supported. | Use Python 3.8 or newer as a target. | این نسخه Python پشتیبانی نمی‌شود. | از Python نسخه ۳.۸ یا بالاتر استفاده کنید. |
| `E_REPO_PATH` | `InvalidRepositoryPathError` | The repository path is invalid. | Choose an existing, writable folder. | مسیر مخزن نامعتبر است. | پوشه‌ای موجود و قابل‌نوشتن انتخاب کنید. |
| `E_UNSAFE_ARCHIVE` | `UnsafeArchiveError` | The archive contains an unsafe path or entry. | Do not extract this archive. | آرشیو شامل مسیر یا ورودی ناامن است. | این آرشیو را استخراج نکنید. |
| `E_VALIDATION` | `ValidationError` | Invalid input. | Correct the value and try again. | ورودی نامعتبر است. | مقدار را اصلاح کنید و دوباره تلاش کنید. |
| `E_VERSION_NOT_FOUND` | `VersionNotFoundError` | The requested version does not exist. | Pick an available version. | نسخه درخواستی وجود ندارد. | یکی از نسخه‌های موجود را انتخاب کنید. |
