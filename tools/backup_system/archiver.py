#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\tools\backup_system\archiver.py
# PERBAIKAN: Menambahkan logika untuk memeriksa nama file secara eksplisit
#            (seperti 'Dockerfile') agar dapat diikutsertakan dalam backup,
#            selain hanya memeriksa ekstensi file.
#######################################################################

import os
import time
import logging
import shutil
import re
import traceback


class Archiver:
    """Encapsulates all logic for cleaning source files and creating the REFACTORY.md archive."""

    def __init__(self, project_root):
        self.project_root = project_root

        self.backup_filename = "hasil_revactory.md"
        self.backup_dir = os.path.join(self.project_root, "backup", "plan")
        self.backup_file_path = os.path.join(self.backup_dir, self.backup_filename)

        self.excluded_dirs_entirely = {
            ".git",
            "themes",
            ".vscode",
            "node_modules",
            "scripts",
            "documentation_service",
            ".idea",
            "__pycache__",
            "build",
            "dist",
            "flowork.egg-info",
            "generated_services",
            "data",
            "assets",
            "flowork_engine.dist",
            "vendor",
            "docs",
            "python",
            "supabase",
            "logs",
            ".venv",
            "backup",
            "ai_models",
            "users",
            "generated_images_by_service",
            "python",
            "scripts",
            ".git",
            ".gitignore",
            ".idea",
            ".vscode",
            ".cloudflared",
            ".venv",
            "venv/",
            "vendor",
            "/__pycache__/"
            ".pyc"
            ".pyo"
            "pytest_cache"
            "mypy_cache"
            "ruff_cache"
            "node_modules"
            "ai_models"
            "backup"
            "build"
            "dist"
            ".egg-info"
            "flowork-gui"
            "data"
            "logs"
            "_logs"
            "monitoring"
            "migrations"

        }

        self.excluded_files = {
            self.backup_filename,
self.backup_filename,
            "backup.py",
            ".gitignore",
            "refactor_scanners.py",
            "run_scanners_cli.py",
            "get-pip.py",
            "mkdocs.yml",
            "nuitka-crash-report.xml",
            "cleaner_tool.py",
            "pip_core_log.txt",
            "pip_gateway_log.txt",
            "pip_momod_api_log.txt",
            "npm_gui_build_log.txt",
            "id.json",
            "en.json",
            "2-STOP_DOCKER_(SAFE).bat",
            "3-STOP_DOCKER_(RESET_DATABASE).bat",
            "4-DOCKER_LOGS.bat",
            "5-UPLOAD_MOMOD_GUI.bat",
            "6-UPLOAD_FLOWORK_GUI.bat",
            "7-upload-docs.bat",
            "8.PUBLISH.bat",
            "9.UPLOAD_ALL_PROJECT.bat",
            "site_file.txt",
            "datasets.json",
            "license.lic",
            "metrics_history.jsonl",
            "settings.json",
            "state.json",
            "trigger_index.cache",
        }

        self.allowed_extensions_for_content = {
           ".py",
            ".json",
            ".html",
            ".js",
            ".vue",
            ".yml",
            ".txt",
            ".env",
            ".stable",
            ".sh",
            ".conf",
            ".bat",
            ".yaml",
            "Dockerfile",
        }

        self.included_specific_files_for_content = set()
        self.excluded_extensions_for_map = {
            ".awenkaudico",
            ".teetah",
            ".pyd",
            ".aola",
            ".so",
            ".c",
            ".egg-info",
            "get-pip.py",
            ".vendor_hash",
            ".module.flowork",
            ".plugin.flowork",
            ".flowork",
            ".env",
            ".log",
            ".db",
            ".sqlite3",
            ".sh",
        }

    def _get_line_count(self, file_path):
        """
        Counts the total number of lines in a file, including empty ones.
        """
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                line_count = sum(1 for line in f)
            return line_count
        except Exception as e:
            logging.error(f"ARCHIVER: Could not count lines for {file_path}: {e}")
            return 0

    def clean_pycache(self):
        logging.info("Starting Python cache cleanup...")
        cleaned_count = 0
        for root, dirs, _ in os.walk(self.project_root):
            if "__pycache__" in dirs:
                pycache_path = os.path.join(root, "__pycache__")
                try:
                    shutil.rmtree(pycache_path)
                    cleaned_count += 1
                except Exception as e:
                    logging.error(
                        f"FAILED TO DELETE CACHE: {pycache_path} | Error: {e}"
                    )
        if cleaned_count > 0:
            logging.info(
                f"Cache cleanup complete. {cleaned_count} __pycache__ folders deleted."
            )
        else:
            logging.info("No __pycache__ folders found.")

    def clean_python_comments(self, content):
        pattern = re.compile(r"^\s*#.*$")
        return "\n".join(
            [line for line in content.splitlines() if not pattern.match(line)]
        )

    def fix_file_spacing(self, source_code: str) -> str:
        lines = source_code.splitlines()
        non_blank_lines = [line for line in lines if line.strip()]
        return "\n".join(non_blank_lines)

    def process_source_files(self):
        logging.info(
            "--- STARTING SOURCE FILE FIX & STAMP OPERATION (EDIT MASAL UNTUK .PY) ---"
        )
        files_to_process = [
            f for f in self.get_content_backup_files() if f.endswith(".py")
        ]

        old_header_footer_pattern = re.compile(
            r"#######################################################################.*?awenk audico.*?#######################################################################\n?",
            re.DOTALL,
        )

        for file_path in files_to_process:
            if os.path.abspath(file_path) == os.path.abspath(__file__):
                continue
            try:
                logging.info(f"PROCESSING .PY FILE: {os.path.basename(file_path)}")
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    original_content = f.read()

                core_code = old_header_footer_pattern.sub("", original_content).strip()

                if not core_code:
                    logging.info(
                        f"Skipping .py file with no core code: {os.path.basename(file_path)}"
                    )
                    continue

                content_no_comments = self.clean_python_comments(core_code)
                content_fixed_spacing = self.fix_file_spacing(content_no_comments)

                absolute_path = os.path.abspath(file_path)
                core_code_line_count = len(content_fixed_spacing.splitlines())
                total_lines_after_write = 7 + core_code_line_count

                # (PENAMBAHAN KODE) Logika untuk menentukan URL website
                normalized_path = absolute_path.replace(os.sep, "/")
                if "/momod/" in normalized_path:
                    website_url = "https://momod.flowork.cloud"
                else:
                    website_url = "https://flowork.cloud"


                header_footer_block = (
                    "#######################################################################\n"
                    f"# WEBSITE {website_url}\n"
                    f"# File NAME : {absolute_path} JUMLAH BARIS {total_lines_after_write} \n"
                    "#######################################################################"
                )

                final_content = f"{header_footer_block}\n\n{content_fixed_spacing}\n"

                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(final_content)
            except Exception as e:
                logging.error(
                    f"MODIFICATION FAILED: {os.path.basename(file_path)} | Error: {e}"
                )
                logging.error(traceback.format_exc())
        logging.info("--- SOURCE FILE FIX & STAMP OPERATION COMPLETE ---")

    def get_content_backup_files(self):
        content_files = []
        logging.info("--- STARTING DETAILED FILE SCAN ---")

        for root, dirs, files in os.walk(self.project_root):
            # Log direktori yang dilewati (excluded)
            original_dirs = list(dirs)
            dirs[:] = [d for d in dirs if d not in self.excluded_dirs_entirely]
            for d in original_dirs:
                if d not in dirs:
                    logging.info(
                        f"SKIPPING DIRECTORY (excluded): {os.path.join(root, d)}"
                    )

            # Log file yang dilewati atau ditambahkan
            for file in files:
                file_path = os.path.join(root, file)

                if file in self.excluded_files:
                    logging.info(f"SKIPPING FILE (excluded name): {file_path}")
                    continue

                file_extension = os.path.splitext(file)[1]
                # (PENAMBAHAN KODE) Menambahkan 'or file in self.allowed_extensions_for_content'
                # Ini penting untuk menangani file tanpa ekstensi seperti 'Dockerfile'
                if (
                    file_extension in self.allowed_extensions_for_content
                    or file in self.allowed_extensions_for_content
                ):
                    logging.info(f"ADDING FILE: {file_path}")
                    content_files.append(file_path)
                else:
                    # Log file yang ekstensinya tidak diizinkan, agar kita tahu
                    # Gunakan logging.warning agar lebih menonjol
                    if (
                        file_extension not in self.excluded_extensions_for_map
                    ):  # Cek agar tidak terlalu 'berisik'
                        logging.warning(
                            f"SKIPPING FILE (extension not allowed): {file_path}"
                        )

        logging.info("--- DETAILED FILE SCAN COMPLETE ---")
        return content_files

    def format_backup_content(self, file_path):
        # (PENAMBAHAN KODE) Logika untuk file tanpa ekstensi seperti Dockerfile
        file_name = os.path.basename(file_path)
        if "." in file_name:
            file_extension = os.path.splitext(file_path)[1].lstrip(".")
        else:
            file_extension = file_name.lower() # Gunakan nama file sebagai 'ekstensi' untuk syntax highlighting

        absolute_path = os.path.abspath(file_path)
        total_lines_after_write = self._get_line_count(file_path)

        # (PENAMBAHAN KODE KUNCI) Logika untuk menentukan URL website
        normalized_path = absolute_path.replace(os.sep, "/")
        if "/momod/" in normalized_path:
            website_url = "https://momod.flowork.cloud"
        else:
            website_url = "https://flowork.cloud"


        header_block = (
            "#######################################################################\n"
            f"# WEBSITE {website_url}\n"
            f"# File NAME : {absolute_path} JUMLAH BARIS {total_lines_after_write} \n"
            "#######################################################################"
        )

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read().strip()

            if file_path.endswith(".py"):
                old_header_pattern = re.compile(
                    r"#######################################################################.*?awenk audico.*?#######################################################################\n?",
                    re.DOTALL,
                )
                content = old_header_pattern.sub("", content).strip()

            # Jika konten kosong, tetap masukkan ke backup dengan sebuah catatan.
            if not content:
                return f"{header_block}\n\n```\n# FILE INI KOSONG (EMPTY FILE)\n```"
            else:
                return f"{header_block}\n\n```{file_extension}\n{content}\n```"

        except Exception as e:
            logging.error(f"FAILED TO READ (for backup): {file_path} | Error: {e}")
            return None

    def run_backup_cycle(self):
        logging.info("--- STARTING MAIN CYCLE ---")
        self.clean_pycache()
        logging.info("Waiting 1 second after cache cleanup.")
        time.sleep(1)

        self.process_source_files()
        logging.info("Waiting 1 second after source file modification.")
        time.sleep(1)

        logging.info(
            f"Starting archive creation process to '{self.backup_file_path}'..."
        )
        os.makedirs(self.backup_dir, exist_ok=True)

        files_to_archive = self.get_content_backup_files()

        with open(self.backup_file_path, "w", encoding="utf-8") as backup_f:
            all_content_blocks = []
            for file_path in files_to_archive:
                formatted_content = self.format_backup_content(file_path)
                if formatted_content:
                    all_content_blocks.append(formatted_content)

            backup_f.write("\n\n".join(all_content_blocks))

        logging.info(
            f"Archive '{self.backup_filename}' successfully created in data/plan folder. {len(all_content_blocks)} file contents were archived."
        )
        logging.info("--- MAIN CYCLE COMPLETE ---\n")