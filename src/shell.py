import zipfile
import csv
import yaml
from pathlib import Path
from calendar import TextCalendar
from datetime import date, datetime

CONFIG_PATH = "./src/config.yaml"
LOGFILE_PATH = "./log.csv"
START_SCRIPT = "./src/startup_script.txt"

class ShellEmulator:
    def __init__(self, configfile) -> None:
        with open(configfile, 'r') as yamlfile:
            config = yaml.safe_load(yamlfile)
            self.username = config['username']
            self.filesystem_path = Path(config['filesystem_path'])
            self.logfile_path = Path(config['log_path'])
            self.start_script_path = Path(config['start_script'])

        # Проверка файлов
        if not self.filesystem_path.exists():
            raise FileNotFoundError(f"Filesystem not found at {self.filesystem_path}")
        if not self.logfile_path.exists():
            with open(self.logfile_path, 'w'):  # Создаем пустой лог-файл
                pass

        self.zipfile = zipfile.ZipFile(self.filesystem_path, mode='a')
        self.pwd = zipfile.Path(self.zipfile)

        # Добавляем информацию о владельцах
        self.owners = {file.filename: (self.username, f"{self.username}_group") for file in self.zipfile.infolist()}

    def resolve_path(self, path: Path):
        temp = self.pwd
        for part in path.parts:
            if part == '/':
                temp = zipfile.Path(self.zipfile)
            elif part == '..':
                temp = temp.parent if temp != zipfile.Path(self.zipfile) else temp
            elif part == '.':
                continue
            else:
                temp = temp / part
                if not temp.exists():
                    print(f"No such file or directory: {part}")
                    return None
        return temp

    def ls(self, is_verbose=False):
        for item in self.pwd.iterdir():
            if not is_verbose:
                print(item.name, end=" ")
            else:
                ownership = self.owners.get(item.name, (self.username, f"{self.username}_group"))
                print(f"{item.name} {ownership[0]}:{ownership[1]}")
        print("")

    def cd(self, path):
        if path is None or not path.exists() or not path.is_dir():
            print(f"cd: {path} не существует или не является директорией")
            return None
        self.pwd = path
        return self.pwd

    def chown(self, filepath: Path, user, group):
        resolved_path = self.resolve_path(filepath)
        if resolved_path:
            self.owners[resolved_path.name] = (user, group)

    def cal(self, year=None):
        year = int(year) if year else date.today().year
        print(TextCalendar().formatyear(year))

    def log_action(self, command, args=""):
        with open(self.logfile_path, 'a', newline='') as logfile:
            writer = csv.writer(logfile)
            writer.writerow([datetime.now(), self.username, command, args])

    def close(self):
        self.zipfile.close()

def main():
    shell = ShellEmulator(CONFIG_PATH)

    # Читаем стартовый скрипт
    commands = []
    if shell.start_script_path.exists():
        with open(shell.start_script_path) as script_file:
            commands = script_file.read().splitlines()

    # Основной цикл
    while True:
        if commands:
            command = commands.pop(0)
        else:
            command = input(f"{shell.username}@{shell.pwd}> ")

        if not command.strip():
            continue

        parts = command.split()
        cmd = parts[0]
        args = parts[1:]

        shell.log_action(cmd, " ".join(args))

        if cmd == "exit":
            shell.close()
            break
        elif cmd == "ls":
            shell.ls("-l" in args)
        elif cmd == "cd":
            if args:
                path = shell.resolve_path(Path(args[0]))
                if path:
                    shell.cd(path)
            else:
                print("cd: missing argument")
        elif cmd == "chown":
            if len(args) == 2:
                user, group = args[0].split(":")
                shell.chown(Path(args[1]), user, group)
            else:
                print("chown: missing arguments")
        elif cmd == "cal":
            shell.cal(args[0] if args else None)
        else:
            print(f"Unknown command: {cmd}")

if __name__ == "__main__":
    main()
