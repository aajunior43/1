"""Backends de impressão: Windows (SumatraPDF / ShellExecute), CUPS e simulação."""
import os
import shutil
import subprocess
import sys
from pathlib import Path

from .core import IS_WINDOWS, NO_WINDOW, Options


class Backend:
    name = "base"

    def list_printers(self):
        return [], None

    def problems(self):
        """Avisos de configuração para mostrar ao usuário (lista de str)."""
        return []

    def command(self, path, opts: Options):
        raise NotImplementedError

    def print_file(self, path, opts: Options, title=""):
        raise NotImplementedError


class DryRunBackend(Backend):
    name = "simulação"

    def __init__(self, inner, log=print):
        self.inner, self.log = inner, log

    def list_printers(self):
        return self.inner.list_printers()

    def print_file(self, path, opts, title=""):
        self.log("   ->", " ".join(f'"{c}"' if " " in c else c for c in self.inner.command(Path(path), opts)))
        return ""


class CupsBackend(Backend):
    name = "CUPS"

    def list_printers(self):
        if not shutil.which("lpstat"):
            return [], None
        out = subprocess.run(["lpstat", "-e"], capture_output=True, text=True).stdout.split()
        d = subprocess.run(["lpstat", "-d"], capture_output=True, text=True).stdout
        default = d.split(":")[-1].strip() if ":" in d else None
        return out, default or None

    def problems(self):
        return [] if shutil.which("lp") else ["CUPS ('lp') não encontrado."]

    def command(self, path, o):
        cmd = ["lp", "-n", str(o.copies)]
        if o.printer:
            cmd += ["-d", o.printer]
        if o.duplex:
            cmd += ["-o", "sides=two-sided-" + ("long" if o.duplex == "long" else "short") + "-edge"]
        if o.pages:
            cmd += ["-P", o.pages]
        if o.paper:
            cmd += ["-o", f"media={o.paper}"]
        if o.landscape:
            cmd += ["-o", "landscape"]
        if o.fit:
            cmd += ["-o", "fit-to-page"]
        if o.color is not None:
            cmd += ["-o", "print-color-mode=" + ("color" if o.color else "monochrome")]
        return cmd + ["-t", Path(path).name, str(path)]

    def print_file(self, path, opts, title=""):
        r = subprocess.run(self.command(path, opts), capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError(r.stderr.strip() or "falha no lp")
        return r.stdout.strip()


class WindowsBackend(Backend):
    """Imprime via SumatraPDF (todas as opções). Sem ele, usa o verbo 'printto' do Windows
    (usa o leitor de PDF padrão; cópias, frente e verso e papel não são aplicados)."""
    name = "Windows"

    def __init__(self, sumatra=None):
        self.sumatra = sumatra or self.find_sumatra()

    @staticmethod
    def find_sumatra():
        cands = [Path(getattr(sys, "_MEIPASS", "")) / "SumatraPDF.exe",
                 Path(sys.argv[0]).resolve().parent / "SumatraPDF.exe",
                 Path(__file__).resolve().parent.parent / "SumatraPDF.exe"]
        for base in (os.environ.get("LOCALAPPDATA"), os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)")):
            if base:
                cands += [Path(base) / "SumatraPDF" / "SumatraPDF.exe"]
        p = shutil.which("SumatraPDF") or shutil.which("SumatraPDF.exe")
        if p:
            cands.insert(0, Path(p))
        for c in cands:
            if c.is_file():
                return str(c)
        return None

    def problems(self):
        if self.sumatra:
            return []
        return ["SumatraPDF não encontrado: cópias, frente e verso, papel e páginas NÃO serão aplicados. "
                "Instale com: winget install SumatraPDF.SumatraPDF"]

    def list_printers(self):
        ps = ["powershell", "-NoProfile", "-Command"]
        try:
            names = subprocess.run(ps + ["Get-Printer | Select-Object -ExpandProperty Name"],
                                   capture_output=True, text=True, creationflags=NO_WINDOW, timeout=30).stdout.splitlines()
            default = subprocess.run(
                ps + ["(Get-CimInstance Win32_Printer | Where-Object Default).Name"],
                capture_output=True, text=True, creationflags=NO_WINDOW, timeout=30).stdout.strip()
        except Exception:
            return [], None
        return [n.strip() for n in names if n.strip()], default or None

    @staticmethod
    def settings(o: Options):
        s = []
        if o.copies > 1:
            s.append(f"{o.copies}x")
        if o.duplex:
            s.append("duplex" if o.duplex == "long" else "duplexshort")
        else:
            s.append("simplex")
        if o.pages:
            s.append(o.pages.replace(" ", ""))
        if o.paper:
            s.append(f"paper={o.paper}")
        if o.landscape:
            s.append("landscape")
        s.append("fit" if o.fit else "noscale")
        if o.color is True:
            s.append("color")
        elif o.color is False:
            s.append("monochrome")
        return ",".join(s)

    def command(self, path, o):
        if not self.sumatra:
            return ["ShellExecute", "printto", str(path), o.printer or "(padrão)"]
        cmd = [self.sumatra, "-print-to" if o.printer else "-print-to-default"]
        if o.printer:
            cmd.append(o.printer)
        return cmd + ["-print-settings", self.settings(o), "-silent", "-exit-when-done", str(path)]

    def print_file(self, path, opts, title=""):
        if self.sumatra:
            r = subprocess.run(self.command(path, opts), capture_output=True, text=True,
                               creationflags=NO_WINDOW, timeout=600)
            if r.returncode:
                raise RuntimeError(r.stderr.strip() or f"SumatraPDF retornou {r.returncode}")
            return "enviado"
        import ctypes
        if opts.printer:
            rc = ctypes.windll.shell32.ShellExecuteW(None, "printto", str(path), f'"{opts.printer}"', None, 0)
        else:
            rc = ctypes.windll.shell32.ShellExecuteW(None, "print", str(path), None, None, 0)
        if rc <= 32:
            raise RuntimeError(f"ShellExecute falhou (código {rc}); instale um leitor de PDF ou o SumatraPDF")
        return "enviado (sem opções)"


def get_backend(dry_run=False, log=print):
    real = WindowsBackend() if IS_WINDOWS else CupsBackend()
    return DryRunBackend(real, log) if dry_run else real
