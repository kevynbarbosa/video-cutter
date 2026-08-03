import os
import re
import shutil
import subprocess
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


class VideoCutterApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Recortador de Vídeo")
        self.root.geometry("620x360")
        self.root.resizable(False, False)

        self.input_file = tk.StringVar()
        self.output_file = tk.StringVar()
        self.start_time = tk.StringVar(value="00:00:00")
        self.end_time = tk.StringVar(value="00:00:10")
        self.status = tk.StringVar(value="Selecione um arquivo MP4.")

        self.create_widgets()

    def create_widgets(self):
        container = ttk.Frame(self.root, padding=20)
        container.pack(fill="both", expand=True)

        ttk.Label(container, text="Arquivo de entrada:").grid(
            row=0, column=0, sticky="w", pady=(0, 5)
        )

        ttk.Entry(
            container,
            textvariable=self.input_file,
            width=62,
            state="readonly",
        ).grid(row=1, column=0, padx=(0, 10), sticky="ew")

        ttk.Button(
            container,
            text="Selecionar",
            command=self.select_input_file,
        ).grid(row=1, column=1)

        ttk.Label(container, text="Timestamp inicial:").grid(
            row=2, column=0, sticky="w", pady=(20, 5)
        )

        ttk.Entry(
            container,
            textvariable=self.start_time,
            width=20,
        ).grid(row=3, column=0, sticky="w")

        ttk.Label(
            container,
            text="Formato: HH:MM:SS ou HH:MM:SS.mmm",
        ).grid(row=3, column=0, padx=(170, 0), sticky="w")

        ttk.Label(container, text="Timestamp final:").grid(
            row=4, column=0, sticky="w", pady=(20, 5)
        )

        ttk.Entry(
            container,
            textvariable=self.end_time,
            width=20,
        ).grid(row=5, column=0, sticky="w")

        ttk.Label(container, text="Arquivo de saída:").grid(
            row=6, column=0, sticky="w", pady=(20, 5)
        )

        ttk.Entry(
            container,
            textvariable=self.output_file,
            width=62,
            state="readonly",
        ).grid(row=7, column=0, padx=(0, 10), sticky="ew")

        ttk.Button(
            container,
            text="Salvar como",
            command=self.select_output_file,
        ).grid(row=7, column=1)

        self.cut_button = ttk.Button(
            container,
            text="Recortar vídeo",
            command=self.start_cut,
        )
        self.cut_button.grid(
            row=8,
            column=0,
            columnspan=2,
            pady=(25, 10),
            ipadx=25,
            ipady=5,
        )

        self.progress = ttk.Progressbar(
            container,
            mode="indeterminate",
            length=400,
        )
        self.progress.grid(
            row=9,
            column=0,
            columnspan=2,
            pady=(0, 10),
        )

        ttk.Label(
            container,
            textvariable=self.status,
        ).grid(row=10, column=0, columnspan=2)

        container.columnconfigure(0, weight=1)

    def select_input_file(self):
        filename = filedialog.askopenfilename(
            title="Selecione o vídeo",
            filetypes=[
                ("Arquivos MP4", "*.mp4"),
                ("Todos os arquivos", "*.*"),
            ],
        )

        if not filename:
            return

        self.input_file.set(filename)

        input_path = Path(filename)
        suggested_output = input_path.with_name(
            f"{input_path.stem}_recortado.mp4"
        )

        self.output_file.set(str(suggested_output))
        self.status.set("Informe os timestamps e clique em Recortar vídeo.")

    def select_output_file(self):
        initial_file = "video_recortado.mp4"

        if self.input_file.get():
            input_path = Path(self.input_file.get())
            initial_file = f"{input_path.stem}_recortado.mp4"

        filename = filedialog.asksaveasfilename(
            title="Salvar vídeo recortado",
            defaultextension=".mp4",
            initialfile=initial_file,
            filetypes=[("Arquivos MP4", "*.mp4")],
        )

        if filename:
            self.output_file.set(filename)

    def start_cut(self):
        try:
            self.validate_fields()
        except ValueError as error:
            messagebox.showerror("Dados inválidos", str(error))
            return

        self.cut_button.config(state="disabled")
        self.progress.start(10)
        self.status.set("Recortando vídeo...")

        thread = threading.Thread(
            target=self.cut_video,
            daemon=True,
        )
        thread.start()

    def cut_video(self):
        input_file = self.input_file.get()
        output_file = self.output_file.get()
        start_time = self.start_time.get().strip()
        end_time = self.end_time.get().strip()

        command = [
            "ffmpeg",
            "-y",
            "-ss",
            start_time,
            "-i",
            input_file,
            "-to",
            end_time,
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "18",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            output_file,
        ]

        try:
            process = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=self.get_creation_flags(),
            )

            if process.returncode != 0:
                error_message = self.extract_ffmpeg_error(process.stderr)
                raise RuntimeError(error_message)

            self.root.after(
                0,
                lambda: self.on_success(output_file),
            )

        except Exception as error:
            self.root.after(
                0,
                lambda: self.on_error(str(error)),
            )

    def validate_fields(self):
        if not shutil.which("ffmpeg"):
            raise ValueError(
                "O FFmpeg não foi encontrado. Instale o FFmpeg e reinicie o programa."
            )

        input_file = self.input_file.get()
        output_file = self.output_file.get()
        start_time = self.start_time.get().strip()
        end_time = self.end_time.get().strip()

        if not input_file:
            raise ValueError("Selecione um arquivo de entrada.")

        if not os.path.isfile(input_file):
            raise ValueError("O arquivo de entrada não existe.")

        if not output_file:
            raise ValueError("Selecione o arquivo de saída.")

        if Path(input_file).resolve() == Path(output_file).resolve():
            raise ValueError(
                "O arquivo de saída deve ser diferente do arquivo de entrada."
            )

        if not self.is_valid_timestamp(start_time):
            raise ValueError(
                "O timestamp inicial é inválido. Use HH:MM:SS."
            )

        if not self.is_valid_timestamp(end_time):
            raise ValueError(
                "O timestamp final é inválido. Use HH:MM:SS."
            )

        start_seconds = self.timestamp_to_seconds(start_time)
        end_seconds = self.timestamp_to_seconds(end_time)

        if end_seconds <= start_seconds:
            raise ValueError(
                "O timestamp final deve ser maior que o inicial."
            )

    @staticmethod
    def is_valid_timestamp(value: str) -> bool:
        pattern = r"^\d{1,3}:[0-5]\d:[0-5]\d(?:\.\d{1,3})?$"
        return bool(re.match(pattern, value))

    @staticmethod
    def timestamp_to_seconds(value: str) -> float:
        hours, minutes, seconds = value.split(":")

        return (
            int(hours) * 3600
            + int(minutes) * 60
            + float(seconds)
        )

    @staticmethod
    def extract_ffmpeg_error(stderr: str) -> str:
        lines = [
            line.strip()
            for line in stderr.splitlines()
            if line.strip()
        ]

        if not lines:
            return "O FFmpeg não informou detalhes sobre o erro."

        return "\n".join(lines[-8:])

    @staticmethod
    def get_creation_flags() -> int:
        if os.name == "nt":
            return subprocess.CREATE_NO_WINDOW

        return 0

    def on_success(self, output_file: str):
        self.progress.stop()
        self.cut_button.config(state="normal")
        self.status.set("Vídeo recortado com sucesso.")

        messagebox.showinfo(
            "Concluído",
            f"Vídeo salvo em:\n{output_file}",
        )

    def on_error(self, error_message: str):
        self.progress.stop()
        self.cut_button.config(state="normal")
        self.status.set("Não foi possível recortar o vídeo.")

        messagebox.showerror(
            "Erro ao recortar",
            error_message,
        )


def main():
    root = tk.Tk()
    VideoCutterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()