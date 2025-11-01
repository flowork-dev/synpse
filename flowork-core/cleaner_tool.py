#######################################################################
# dev : awenk audico
# EMAIL SAHIDINAOLA@GMAIL.COM
# WEBSITE https://github.com/FLOWORK-gif/FLOWORK
# File NAME : C:\FLOWORK\flowork-core\cleaner_tool.py
# JUMLAH BARIS : 105
#######################################################################

import os
import shutil
class ArtifactCleaner:
    """
    Handles the logic for aggressively cleaning specific build artifacts
    from component folders to force a complete rebuild.
    [MODE SAPU JAGAT V3] Now also deletes all manager index caches from the data folder.
    """
    def __init__(self, project_folder, report_callback=print):
        self.project_folder = project_folder
        self.report = report_callback
        self.component_base_dirs = ['modules', 'plugins', 'widgets', 'triggers', 'ai_providers', 'formatters', 'scanners', 'template']
        self.files_to_delete_exact = [
            '.vendor_hash', 'build_fingerprint.json', 'TES_build_fingerprint.json',
            'widget_index.cache', 'module_index.cache', 'trigger_index.cache'
        ]
        self.files_to_delete_endswith = ['.pyi', '.pyd', '.original','.service', '.kernel', '.aola', '.ai', '.flow', '.teetah','.aola_flowork','.module.flowork','.plugin.flowork','.widget.flowork','.trigger.flowork','.scanner.flowork']
        self.folders_to_delete = ['vendor']
        self.folders_to_delete_endswith = ['.py.tmp.build', '.build']
        self.deleted_files = 0
        self.deleted_folders = 0
        self.deleted_pycache_folders = 0
    def run_cleanup(self):
        """Executes the entire aggressive cleanup process."""
        self.report("Scanning for ALL build artifacts and caches to clean...", "INFO")
        self._clean_component_artifacts()
        self._clean_root_caches() # [ADDED] New step to clean root caches
        self.report("\nCleaning up general Python cache (__pycache__)...", "INFO")
        self._clean_pycache()
        self._report_summary()
    def _clean_root_caches(self):
        """Cleans cache files from the data directory."""
        data_dir = os.path.join(self.project_folder, 'data')
        if not os.path.isdir(data_dir):
            return
        self.report(f"Scanning for caches in: '{os.path.relpath(data_dir, self.project_folder)}'...", "INFO")
        for file_name in self.files_to_delete_exact:
            file_path = os.path.join(data_dir, file_name)
            if os.path.exists(file_path):
                self._delete_file(file_path)
    def _clean_component_artifacts(self):
        for base_dir in self.component_base_dirs:
            full_base_path = os.path.join(self.project_folder, base_dir)
            if not os.path.isdir(full_base_path):
                continue
            for component_name in os.listdir(full_base_path):
                component_path = os.path.join(full_base_path, component_name)
                if not os.path.isdir(component_path):
                    continue
                for root, dirs, files in os.walk(component_path, topdown=False):
                    for dir_name in list(dirs):
                        path_to_delete = os.path.join(root, dir_name)
                        if dir_name in self.folders_to_delete or any(dir_name.endswith(p) for p in self.folders_to_delete_endswith):
                            self._delete_folder(path_to_delete)
                    for file_name in files:
                        if file_name in self.files_to_delete_exact or any(file_name.endswith(p) for p in self.files_to_delete_endswith):
                            if file_name == '__init__.pyi': continue
                            self._delete_file(os.path.join(root, file_name))
    def _clean_pycache(self):
        for root, dirs, files in os.walk(self.project_folder, topdown=False):
            if '__pycache__' in dirs:
                self._delete_folder(os.path.join(root, '__pycache__'), is_pycache=True)
    def _delete_folder(self, path, is_pycache=False):
        try:
            shutil.rmtree(path)
            if is_pycache: self.deleted_pycache_folders += 1
            else: self.deleted_folders += 1
            self.report(f"[DELETED] Folder: {os.path.relpath(path, self.project_folder)}", "SUCCESS")
        except OSError as e:
            self.report(f"[ERROR] Failed to delete folder {path}: {e}", "ERROR")
    def _delete_file(self, path):
        try:
            os.remove(path)
            self.deleted_files += 1
            self.report(f"[DELETED] File: {os.path.relpath(path, self.project_folder)}", "SUCCESS")
        except OSError as e:
            self.report(f"[ERROR] Failed to delete file {path}: {e}", "ERROR")
    def _report_summary(self):
        self.report("\n--- CLEANUP PROCESS FINISHED ---", "INFO")
        self.report(f"Total artifact/cache folders deleted: {self.deleted_folders}", "INFO")
        self.report(f"Total artifact/cache files deleted: {self.deleted_files}", "INFO")
        self.report(f"Total __pycache__ folders deleted: {self.deleted_pycache_folders}", "INFO")
        self.report("Your components are now clean and ready for a fresh build!", "SUCCESS")
def main():
    """Main execution block for when this script is run directly from the console."""
    project_folder = os.getcwd()
    print("--- Flowork Build Artifact Cleaner (Sapu Jagat Mode) ---")
    print(f"This script will clean ALL build artifacts AND caches to force a full rebuild inside: {project_folder}")
    confirm = input("Are you sure you want to continue? (y/n): ")
    if confirm.lower() != 'y':
        print("Cleaning process cancelled by user.")
        return
    def console_reporter(message, level="INFO"):
        print(message)
    cleaner = ArtifactCleaner(project_folder, console_reporter)
    cleaner.run_cleanup()
if __name__ == "__main__":
    main()
