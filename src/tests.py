import unittest
from src.shell import ShellEmulator
from pathlib import Path
import yaml
import shutil
import os
from datetime import date
from io import StringIO
import sys
import time

# Тестовые данные
CONFIG_PATH = "./src/config.yaml"
TEST_FILESYSTEM_PATH = "./src/test_filesystem"
TEST_ZIP_PATH = "./src/test_filesystem.zip"
LOG_PATH = "./test_log.csv"

# Тестовый конфиг
TEST_CONFIG = {
    'username': 'test_user',
    'filesystem_path': TEST_ZIP_PATH,
    'log_path': LOG_PATH,
    'start_script': "./src/startup_script.txt",
}

class TestShellEmulator(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Настройка тестовой среды."""
        if not Path(TEST_FILESYSTEM_PATH).exists():
            os.makedirs(TEST_FILESYSTEM_PATH)
            with open(f"{TEST_FILESYSTEM_PATH}/file1.txt", "w") as f:
                f.write("Test file 1")
            with open(f"{TEST_FILESYSTEM_PATH}/file2.txt", "w") as f:
                f.write("Test file 2")

        shutil.make_archive(TEST_FILESYSTEM_PATH, 'zip', TEST_FILESYSTEM_PATH)

        with open(CONFIG_PATH, 'w') as f:
            yaml.dump(TEST_CONFIG, f)

        if Path(LOG_PATH).exists():
            os.remove(LOG_PATH)

    @classmethod
    def tearDownClass(cls):
        """Очистка после тестов."""
        if hasattr(cls, 'shell') and cls.shell.zipfile:
            cls.shell.zipfile.close()  # Закрытие zip-файла перед удалением
        time.sleep(1)  # Задержка перед попыткой удалить файл
        if Path(TEST_FILESYSTEM_PATH).exists():
            shutil.rmtree(TEST_FILESYSTEM_PATH)
        # Удаление файлов test_filesystem.zip и config.yaml закомментировано
        # if Path(TEST_ZIP_PATH).exists():
        #     try:
        #         os.remove(TEST_ZIP_PATH)
        #     except PermissionError:
        #         time.sleep(1)  # Повторная попытка удаления
        #         os.remove(TEST_ZIP_PATH)
        # if Path(CONFIG_PATH).exists():
        #     os.remove(CONFIG_PATH)
        if Path(LOG_PATH).exists():
            os.remove(LOG_PATH)

    def setUp(self):
        self.shell = ShellEmulator(CONFIG_PATH)

    def tearDown(self):
        """Очистка после каждого теста."""
        self.shell.close()

    def test_ls(self):
        """Тест команды ls."""
        output = []
        self.shell.ls(is_verbose=False)
        for item in self.shell.pwd.iterdir():
            output.append(item.name)
        self.assertIn("file1.txt", output)
        self.assertIn("file2.txt", output)

    def test_cd(self):
        """Тест команды cd."""
        file_path = self.shell.resolve_path(Path("file1.txt"))
        new_dir = self.shell.cd(file_path)
        self.assertIsNone(new_dir, "cd: файл не является директорией")

    def test_cd_non_existent_dir(self):
        """Тест команды cd с несуществующей директорией."""
        shell = ShellEmulator(CONFIG_PATH)
        file_path = shell.resolve_path(Path("nonexistent_directory"))
        new_dir = shell.cd(file_path)
        self.assertIsNone(new_dir, "cd: директория не существует")

    def test_ls_verbose(self):
        """Тест команды ls с флагом -l (подробный вывод)."""
        shell = ShellEmulator(CONFIG_PATH)
        output = []
        shell.ls(is_verbose=True)
        for item in shell.pwd.iterdir():
            output_str = f"{item.name} {shell.username}:{shell.username}_group"
            output.append(output_str)
        self.assertIn("file1.txt test_user:test_user_group", output)
        self.assertIn("file2.txt test_user:test_user_group", output)

    def test_chown(self):
        """Тест команды chown."""
        self.shell.chown(Path("file1.txt"), "new_user", "new_group")
        self.assertEqual(
            self.shell.owners["file1.txt"],
            ("new_user", "new_group"),
            "chown не изменил владельца",
        )

    def test_chown_non_existent_file(self):
        """Тест команды chown для несуществующего файла."""
        shell = ShellEmulator(CONFIG_PATH)
        non_existent_file = Path("nonexistent_file.txt")
        shell.chown(non_existent_file, "new_user", "new_group")
        self.assertNotIn("non_existent_file.txt", shell.owners)

    def test_cal(self):
        """Тест команды cal."""
        captured_output = StringIO()
        sys.stdout = captured_output
        self.shell.cal(2024)
        sys.stdout = sys.__stdout__
        self.assertIn("2024", captured_output.getvalue(), "Календарь неверен")

    def test_cal_current_year(self):
        """Тест команды cal для текущего года."""
        captured_output = StringIO()
        sys.stdout = captured_output
        shell = ShellEmulator(CONFIG_PATH)
        shell.cal()  # Текущий год
        sys.stdout = sys.__stdout__
        self.assertIn(str(date.today().year), captured_output.getvalue(), "Календарь текущего года неверен")

    def test_chown_invalid_format(self):
        """Тест команды chown с некорректным форматом."""
        shell = ShellEmulator(CONFIG_PATH)
        invalid_user_group = "user_without_colon_format"
        file_path = Path("file1.txt")
        with self.assertRaises(ValueError, msg="chown не обработал некорректный формат пользователя:группы"):
            user, group = invalid_user_group.split(":")
            shell.chown(file_path, user, group)

    def test_log_action(self):
        """Тест команды log_action (запись в лог)."""
        self.shell.log_action('ls')
        with open(self.shell.logfile_path, 'r') as logfile:
            log_content = logfile.readlines()
            self.assertIn("ls", log_content[-1], "Команда не записалась в лог")

if __name__ == "__main__":
    unittest.main()
