
import os
import tempfile
import time
import unittest
from pathlib import Path

from student_cleanup import cleanup_student_folders


class StudentCleanupTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.batch_root = Path(self.temp_dir.name)

        self.student = self.batch_root / "Student_A"
        self.student.mkdir()

        self.old_time = time.time() - (40 * 86400)
        self.recent_time = time.time()

    def tearDown(self):
        self.temp_dir.cleanup()

    def make_file(self, path, age="old"):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("test content")

        timestamp = (
            self.old_time if age == "old" else self.recent_time
        )
        os.utime(path, (timestamp, timestamp))
        return path

    def make_old_directory(self, path):
        path.mkdir(parents=True, exist_ok=True)
        os.utime(path, (self.old_time, self.old_time))
        return path

    def make_recent_directory(self, path):
        path.mkdir(parents=True, exist_ok=True)
        os.utime(path, (self.recent_time, self.recent_time))
        return path

    def cleanup(self, dry_run=False):
        return cleanup_student_folders(
            self.batch_root,
            retention_days=30,
            dry_run=dry_run,
        )

    def test_dry_run_does_not_delete_files_or_directories(self):
        project = self.student / "Old_Project"
        old_file = self.make_file(project / "old_project.pdf")

        # Age the directory after creating its contents.
        os.utime(project, (self.old_time, self.old_time))

        summary = self.cleanup(dry_run=True)

        self.assertTrue(old_file.exists())
        self.assertTrue(project.exists())
        self.assertIn(str(old_file), summary["expired_files"])
        self.assertIn(str(project), summary["directories_to_remove"])
        self.assertEqual(summary["deleted_files"], [])
        self.assertEqual(summary["removed_directories"], [])
        self.assertTrue(summary["dry_run"])

    def test_old_files_of_any_type_are_deleted(self):
        extensions = [".pdf", ".svg", ".txt", ".png", ".zip"]

        old_files = [
            self.make_file(self.student / f"old_file{extension}")
            for extension in extensions
        ]

        summary = self.cleanup()

        for path in old_files:
            self.assertFalse(path.exists())
            self.assertIn(str(path), summary["deleted_files"])

    def test_hidden_old_files_are_deleted(self):
        hidden_file = self.make_file(
            self.student / ".hidden_file"
        )

        self.cleanup()

        self.assertFalse(hidden_file.exists())

    def test_recent_files_are_preserved(self):
        recent_files = [
            self.make_file(
                self.student / "recent.pdf", age="recent"
            ),
            self.make_file(
                self.student / "recent.svg", age="recent"
            ),
            self.make_file(
                self.student / "recent.txt", age="recent"
            ),
        ]

        self.cleanup()

        for path in recent_files:
            self.assertTrue(path.exists())

    def test_documents_folder_and_all_contents_are_preserved(self):
        documents = self.student / "Documents"
        old_guide = self.make_file(
            documents / "User_Guide.pdf"
        )
        nested_old_file = self.make_file(
            documents / "Archive" / "old_document.pdf"
        )

        # Make the Documents directory itself old as well.
        os.utime(
            documents,
            (self.old_time, self.old_time),
        )

        self.cleanup()

        self.assertTrue(documents.exists())
        self.assertTrue(old_guide.exists())
        self.assertTrue(nested_old_file.exists())

    def test_documents_folder_is_preserved_case_insensitively(self):
        documents = self.student / "DoCuMeNtS"
        old_file = self.make_file(documents / "old.pdf")

        self.cleanup()

        self.assertTrue(documents.exists())
        self.assertTrue(old_file.exists())

    def test_nested_old_files_and_empty_directories_are_removed(self):
        project = self.student / "Project_A"
        nested = project / "Exports"

        old_file = self.make_file(
            nested / "drawing.svg"
        )

        # Age directories after creating their contents.
        os.utime(nested, (self.old_time, self.old_time))
        os.utime(project, (self.old_time, self.old_time))

        summary = self.cleanup()

        self.assertFalse(old_file.exists())
        self.assertFalse(nested.exists())
        self.assertFalse(project.exists())

        self.assertIn(str(nested), summary["removed_directories"])
        self.assertIn(str(project), summary["removed_directories"])

    def test_recent_file_inside_old_directory_is_preserved(self):
        project = self.student / "Old_Project"
        recent_file = self.make_file(
            project / "recent_notes.txt",
            age="recent",
        )

        os.utime(project, (self.old_time, self.old_time))

        self.cleanup()

        self.assertTrue(project.exists())
        self.assertTrue(recent_file.exists())

    def test_old_file_inside_recent_directory_is_deleted(self):
        project = self.make_recent_directory(
            self.student / "Recent_Project"
        )
        old_file = self.make_file(
            project / "old_drawing.svg"
        )

        # Restore the directory's recent mtime after creating the file.
        os.utime(project, (self.recent_time, self.recent_time))

        summary = self.cleanup()

        self.assertFalse(old_file.exists())
        self.assertTrue(project.exists())
        self.assertIn(str(old_file), summary["deleted_files"])
        self.assertNotIn(
            str(project),
            summary["removed_directories"],
        )

    def test_old_empty_directories_are_removed(self):
        project = self.make_old_directory(
            self.student / "Old_Empty_Project"
        )

        summary = self.cleanup()

        self.assertFalse(project.exists())
        self.assertIn(str(project), summary["removed_directories"])

    def test_recent_empty_directories_are_preserved(self):
        project = self.make_recent_directory(
            self.student / "Recent_Empty_Project"
        )

        self.cleanup()

        self.assertTrue(project.exists())

    def test_student_folder_is_never_removed(self):
        old_file = self.make_file(
            self.student / "old_project.pdf"
        )

        self.cleanup()

        self.assertFalse(old_file.exists())
        self.assertTrue(self.student.exists())

    def test_old_symbolic_link_is_deleted_without_deleting_target(self):
        target = self.batch_root / "external_target.txt"
        target.write_text("keep this file")

        link = self.student / "old_link"
        link.symlink_to(target)

        os.utime(
            link,
            (self.old_time, self.old_time),
            follow_symlinks=False,
        )

        self.cleanup()

        self.assertFalse(link.is_symlink())
        self.assertTrue(target.exists())

    def test_missing_batch_root_raises_error(self):
        missing = self.batch_root / "missing"

        with self.assertRaises(FileNotFoundError):
            cleanup_student_folders(missing)


if __name__ == "__main__":
    unittest.main()
