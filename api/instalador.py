"""
Instalador GUI - Invec API
Requer execução como Administrador.
"""
import os
import sys
import shutil
import subprocess
import threading
import ctypes
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

ctk.set_appearance_mode("light")

# ── Paleta — espelha o design glassmorphism do app ───────────────────────────
ORANGE      = "#CC5B2A"
ORANGE_HOV  = "#A8431A"
BG_ROOT     = "#F5EDE7"          # peach claro (gradientStart aproximado)
CARD_BG     = "#FFFFFF"
CARD_BORDER = "#E8DDD6"
ENTRY_BG    = "#F5F0ED"
ENTRY_BOR   = "#D8CEC8"
TEXT_PRI    = "#1A1A1A"
TEXT_SEC    = "#777777"
GREEN       = "#2E7D32"
RED_C       = "#C62828"
AMBER       = "#E65100"

SERVICE_NAME    = "InvecAPI"
SERVICE_DISPLAY = "Invec - API Inventario"
DEFAULT_DIR     = r"C:\Administracao\Invec"

_UUID_INVALIDOS = {
    "", "TO BE FILLED BY O.E.M.", "NOT APPLICABLE", "NONE", "N/A",
    "00000000-0000-0000-0000-000000000000",
    "FFFFFFFF-FFFF-FFFF-FFFF-FFFFFFFFFFFF",
}


def get_machine_id() -> str:
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
             "-Command", "(Get-CimInstance -ClassName Win32_ComputerSystemProduct).UUID"],
            capture_output=True, text=True, timeout=10,
        )
        uid = r.stdout.strip().upper()
        if uid and uid not in _UUID_INVALIDOS and len(uid) >= 32:
            return uid
    except Exception:
        pass
    try:
        r = subprocess.run(
            ["wmic", "csproduct", "get", "uuid"],
            capture_output=True, text=True, timeout=5,
        )
        for linha in r.stdout.splitlines():
            uid = linha.strip().upper()
            if uid and uid != "UUID" and uid not in _UUID_INVALIDOS and len(uid) >= 32:
                return uid
    except Exception:
        pass
    return "(nao disponivel)"


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def resource(rel: str) -> str:
    base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


def service_status() -> str:
    r = subprocess.run(['sc', 'query', SERVICE_NAME], capture_output=True, text=True)
    if 'RUNNING' in r.stdout:
        return 'running'
    if 'STOPPED' in r.stdout:
        return 'stopped'
    return 'absent'


# ── Helpers de layout ────────────────────────────────────────────────────────

def _lbl(parent, text, row, bold=False, color=TEXT_PRI):
    font = ctk.CTkFont("Segoe UI", 11, "bold" if bold else "normal")
    ctk.CTkLabel(parent, text=text, font=font, text_color=color, anchor="w").grid(
        row=row, column=0, sticky="w", padx=(4, 12), pady=(10, 2)
    )


def _entry(parent, var, row, state="normal", show=None):
    kw = dict(textvariable=var, fg_color=ENTRY_BG, border_color=ENTRY_BOR,
              border_width=1, corner_radius=10, text_color=TEXT_PRI, state=state)
    if show:
        kw["show"] = show
    w = ctk.CTkEntry(parent, **kw)
    w.grid(row=row, column=1, columnspan=2, sticky="ew", padx=(0, 4), pady=(10, 2))
    return w


def _sep(parent, row):
    ctk.CTkFrame(parent, fg_color="#EAE0DA", height=1, corner_radius=0).grid(
        row=row, column=0, columnspan=3, sticky="ew", padx=4, pady=12
    )


# ── Aplicação ────────────────────────────────────────────────────────────────

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Invec — Instalador do Servidor")
        self.geometry("640x720")
        self.resizable(False, False)
        self.configure(fg_color=BG_ROOT)

        self.v_install    = tk.StringVar(value=DEFAULT_DIR)
        self.v_db         = tk.StringVar(value=r"C:\Administracao\DB\MIAUTOMEC.FDB")
        self.v_host       = tk.StringVar(value="localhost")
        self.v_idempresa  = tk.StringVar(value="1")
        self.v_license    = tk.StringVar()
        self.v_machine_id = tk.StringVar(value="Identificando...")
        self.v_status     = tk.StringVar(value="Aguardando...")

        self._build_ui()
        self._load_existing_env()
        self.after(200, self._refresh_status)
        threading.Thread(target=self._load_machine_id, daemon=True).start()

    # ── Layout ───────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Header laranja
        hdr = ctk.CTkFrame(self, fg_color=ORANGE, corner_radius=0, height=60)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        ctk.CTkLabel(
            hdr,
            text="  Invec  ·  Instalador do Servidor",
            text_color="white",
            font=ctk.CTkFont("Segoe UI", 14, "bold"),
            anchor="w",
        ).pack(fill="x", padx=20, pady=18)

        # Card glass principal
        card = ctk.CTkScrollableFrame(
            self,
            fg_color=CARD_BG,
            corner_radius=16,
            border_width=1,
            border_color=CARD_BORDER,
            scrollbar_button_color="#D8CEC8",
            scrollbar_button_hover_color="#C0B0A8",
        )
        card.pack(fill="both", expand=True, padx=16, pady=14)
        card.columnconfigure(1, weight=1)

        r = 0

        # Diretório de instalação
        _lbl(card, "Diretório de instalação", r)
        dir_fr = ctk.CTkFrame(card, fg_color="transparent")
        dir_fr.grid(row=r, column=1, columnspan=2, sticky="ew", padx=(0, 4), pady=(10, 2))
        dir_fr.columnconfigure(0, weight=1)
        ctk.CTkEntry(dir_fr, textvariable=self.v_install, fg_color=ENTRY_BG,
                     border_color=ENTRY_BOR, border_width=1, corner_radius=10,
                     text_color=TEXT_PRI).grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ctk.CTkButton(dir_fr, text="…", width=40, height=34,
                      fg_color=ORANGE, hover_color=ORANGE_HOV,
                      text_color="white", corner_radius=10,
                      command=self._browse_install_dir).grid(row=0, column=1)
        r += 1

        _sep(card, r); r += 1

        # Banco Firebird
        _lbl(card, "Banco de dados Firebird (.FDB)", r, bold=True)
        db_fr = ctk.CTkFrame(card, fg_color="transparent")
        db_fr.grid(row=r, column=1, columnspan=2, sticky="ew", padx=(0, 4), pady=(10, 2))
        db_fr.columnconfigure(0, weight=1)
        ctk.CTkEntry(db_fr, textvariable=self.v_db, fg_color=ENTRY_BG,
                     border_color=ENTRY_BOR, border_width=1, corner_radius=10,
                     text_color=TEXT_PRI).grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ctk.CTkButton(db_fr, text="…", width=40, height=34,
                      fg_color=ORANGE, hover_color=ORANGE_HOV,
                      text_color="white", corner_radius=10,
                      command=self._browse_db).grid(row=0, column=1)
        r += 1

        _lbl(card, "Host Firebird", r)
        _entry(card, self.v_host, r); r += 1

        _lbl(card, "ID da Empresa (IDEMPRESA)", r)
        ctk.CTkEntry(card, textvariable=self.v_idempresa, width=90,
                     fg_color=ENTRY_BG, border_color=ENTRY_BOR, border_width=1,
                     corner_radius=10, text_color=TEXT_PRI).grid(
            row=r, column=1, sticky="w", padx=(0, 4), pady=(10, 2))
        r += 1

        _sep(card, r); r += 1

        # Chave de Licença
        _lbl(card, "Chave de Licença", r, bold=True)
        _entry(card, self.v_license, r); r += 1

        # ID da máquina
        _lbl(card, "ID desta máquina", r)
        mid_fr = ctk.CTkFrame(card, fg_color="transparent")
        mid_fr.grid(row=r, column=1, columnspan=2, sticky="ew", padx=(0, 4), pady=(10, 2))
        mid_fr.columnconfigure(0, weight=1)
        ctk.CTkEntry(mid_fr, textvariable=self.v_machine_id, state="disabled",
                     fg_color=ENTRY_BG, border_color=ENTRY_BOR, border_width=1,
                     corner_radius=10, text_color=TEXT_SEC).grid(
            row=0, column=0, sticky="ew", padx=(0, 8))
        ctk.CTkButton(mid_fr, text="Copiar", width=80, height=34,
                      fg_color="transparent", border_width=1, border_color=ORANGE,
                      text_color=ORANGE, hover_color="#FEF0E8", corner_radius=10,
                      font=ctk.CTkFont("Segoe UI", 11),
                      command=self._copy_machine_id).grid(row=0, column=1)
        r += 1

        ctk.CTkLabel(
            card,
            text="Envie o ID desta máquina à Pontual para receber uma licença vinculada.",
            font=ctk.CTkFont("Segoe UI", 10),
            text_color=TEXT_SEC, anchor="w",
        ).grid(row=r, column=1, columnspan=2, sticky="w", padx=(0, 4), pady=(0, 4))
        r += 1

        _sep(card, r); r += 1

        # Status
        self.lbl_status = ctk.CTkLabel(
            card, textvariable=self.v_status,
            font=ctk.CTkFont("Segoe UI", 11), text_color=TEXT_SEC,
            anchor="w", wraplength=530,
        )
        self.lbl_status.grid(row=r, column=0, columnspan=3, sticky="w", padx=4, pady=(0, 10))
        r += 1

        # Botões
        bf = ctk.CTkFrame(card, fg_color="transparent")
        bf.grid(row=r, column=0, columnspan=3, pady=(4, 12))

        self.btn_install = ctk.CTkButton(
            bf,
            text="Instalar / Atualizar",
            fg_color=ORANGE, hover_color=ORANGE_HOV,
            text_color="white", corner_radius=16,
            height=46, width=210,
            font=ctk.CTkFont("Segoe UI", 13, "bold"),
            command=self._on_install,
        )
        self.btn_install.pack(side="left", padx=(0, 10))

        for txt, cmd in [
            ("Reiniciar Serviço", self._on_restart),
            ("Desinstalar",       self._on_uninstall),
            ("Fechar",            self.destroy),
        ]:
            ctk.CTkButton(
                bf, text=txt, command=cmd,
                fg_color="transparent", border_width=1, border_color="#D0C0B8",
                text_color=TEXT_PRI, hover_color=ENTRY_BG,
                corner_radius=16, height=46,
                font=ctk.CTkFont("Segoe UI", 11),
            ).pack(side="left", padx=4)

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _browse_install_dir(self):
        p = filedialog.askdirectory(
            title="Selecionar pasta de instalação",
            initialdir=self.v_install.get() if os.path.exists(self.v_install.get()) else DEFAULT_DIR,
        )
        if p:
            self.v_install.set(os.path.normpath(p))

    def _browse_db(self):
        p = filedialog.askopenfilename(
            title="Selecionar banco Firebird",
            filetypes=[("Firebird Database", "*.fdb *.FDB *.gdb *.GDB"), ("Todos", "*.*")]
        )
        if p:
            self.v_db.set(os.path.normpath(p))

    def _copy_machine_id(self):
        self.clipboard_clear()
        self.clipboard_append(self.v_machine_id.get())
        self._set_status("ID da máquina copiado para a área de transferência.")

    def _load_existing_env(self):
        env = os.path.join(self.v_install.get(), ".env")
        if not os.path.exists(env):
            return
        with open(env, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if '=' not in line or line.startswith('#'):
                    continue
                k, _, v = line.partition('=')
                k, v = k.strip(), v.strip()
                mapping = {
                    'FB_DATABASE': self.v_db,
                    'FB_HOST':     self.v_host,
                    'IDEMPRESA':   self.v_idempresa,
                    'LICENSE_KEY': self.v_license,
                }
                if k in mapping:
                    mapping[k].set(v)

    def _set_status(self, msg: str, color: str = TEXT_SEC):
        self.v_status.set(msg)
        self.lbl_status.configure(text_color=color)
        self.update_idletasks()

    def _refresh_status(self):
        st = service_status()
        if st == 'running':
            self._set_status("● Serviço RODANDO na porta 8000.", GREEN)
        elif st == 'stopped':
            self._set_status("● Serviço instalado mas PARADO. Clique em Reiniciar Serviço.", AMBER)
        else:
            self._set_status("○ Serviço não instalado. Configure os campos e clique em Instalar.", TEXT_SEC)

    def _load_machine_id(self):
        uid = get_machine_id()
        self.after(0, lambda: self.v_machine_id.set(uid))

    def _write_env(self, install_dir: str):
        env_path = os.path.join(install_dir, ".env")
        jwt_secret = ""
        if os.path.exists(env_path):
            with open(env_path, encoding="utf-8") as fh:
                for line in fh:
                    if line.startswith("JWT_SECRET="):
                        jwt_secret = line.strip()[len("JWT_SECRET="):]
                        break
        if not jwt_secret:
            import secrets
            jwt_secret = secrets.token_hex(32)
        with open(env_path, "w", encoding="utf-8") as fh:
            fh.write(
                f"FB_DATABASE={self.v_db.get()}\n"
                f"FB_HOST={self.v_host.get()}\n"
                f"FB_USER=SYSDBA\n"
                f"FB_PASSWORD=masterkey\n"
                f"PORT=8000\n"
                f"IDEMPRESA={self.v_idempresa.get() or '1'}\n"
                f"LICENSE_KEY={self.v_license.get()}\n"
                f"JWT_SECRET={jwt_secret}\n"
            )
        try:
            subprocess.run(
                ["icacls", env_path, "/inheritance:r",
                 "/grant:r", "SYSTEM:(R)",
                 "/grant:r", "Administrators:(F)"],
                capture_output=True, check=False,
            )
        except Exception:
            pass

    def _locate_nssm(self, install_dir: str) -> str | None:
        candidates = [
            resource("nssm.exe"),
            os.path.join(install_dir, "nssm.exe"),
            shutil.which("nssm") or "",
        ]
        for p in candidates:
            if p and os.path.exists(p):
                dest = os.path.join(install_dir, "nssm.exe")
                if os.path.abspath(p) != os.path.abspath(dest):
                    shutil.copy2(p, dest)
                return dest
        messagebox.showerror(
            "NSSM não encontrado",
            "O utilitário NSSM (nssm.exe) não foi encontrado.\n\n"
            "Baixe em: https://nssm.cc/download\n"
            f"Coloque o nssm.exe em: {install_dir}\n\n"
            "Em seguida clique em Instalar novamente."
        )
        return None

    def _copy_server_files(self, install_dir: str) -> str:
        bundled_exe = resource("InvecServidor.exe")
        if os.path.exists(bundled_exe):
            dest = os.path.join(install_dir, "InvecServidor.exe")
            shutil.copy2(bundled_exe, dest)
            return dest

        src = os.path.dirname(os.path.abspath(__file__))
        for item in ("main.py", "server.py", "requirements.txt", "app"):
            s = os.path.join(src, item)
            d = os.path.join(install_dir, item)
            if os.path.isdir(s):
                if os.path.exists(d):
                    shutil.rmtree(d)
                shutil.copytree(s, d)
            elif os.path.exists(s):
                shutil.copy2(s, d)

        self._set_status("Instalando dependências Python (pip)...")
        req = os.path.join(install_dir, "requirements.txt")
        python_exe = shutil.which("python") or shutil.which("python3") or sys.executable
        subprocess.run(
            [python_exe, "-m", "pip", "install", "-r", req, "--quiet"],
            check=True,
        )
        return os.path.join(install_dir, "server.py")

    # ── Ações dos botões ─────────────────────────────────────────────────────

    def _on_install(self):
        if not self.v_db.get():
            messagebox.showerror("Erro", "Selecione o caminho do banco de dados Firebird (.FDB).")
            return
        if not self.v_license.get().strip():
            messagebox.showerror(
                "Erro",
                "Informe a Chave de Licença.\n\nSolicite a chave para a Pontual Tecnologia."
            )
            return
        if not is_admin():
            messagebox.showerror(
                "Permissão necessária",
                "Execute o instalador como Administrador.\n"
                "(clique direito no arquivo → Executar como administrador)"
            )
            return
        self.btn_install.configure(state="disabled")
        threading.Thread(target=self._install_worker, daemon=True).start()

    def _configure_firewall(self, porta: str, log_fw: str) -> bool:
        import time as _time
        sysroot = os.environ.get("SystemRoot", r"C:\Windows")
        netsh   = os.path.join(sysroot, "System32", "netsh.exe")
        ps_exe  = os.path.join(sysroot, "System32", "WindowsPowerShell", "v1.0", "powershell.exe")

        with open(log_fw, "w", encoding="utf-8") as lfw:
            def log(msg: str):
                lfw.write(msg + "\n"); lfw.flush()

            log("=== Estado do Windows Firewall (MpsSvc) ===")
            r_svc = subprocess.run(["sc", "query", "MpsSvc"], capture_output=True, text=True, errors="replace")
            log(r_svc.stdout.strip())

            svc_running = "RUNNING" in r_svc.stdout
            svc_stopped = "STOPPED" in r_svc.stdout

            if not svc_running and not svc_stopped:
                log("MpsSvc nao encontrado. Firewall nao instalado — porta ja acessivel na rede.")
                return True

            if svc_stopped:
                log("\nMpsSvc PARADO. Tentando iniciar...")
                r_start = subprocess.run(["sc", "start", "MpsSvc"], capture_output=True, text=True, errors="replace")
                log(f"sc start MpsSvc => exit {r_start.returncode}: {r_start.stdout.strip()}")
                _time.sleep(2)
                r_check = subprocess.run(["sc", "query", "MpsSvc"], capture_output=True, text=True, errors="replace")
                svc_running = "RUNNING" in r_check.stdout
                log(f"Apos iniciar: {'RUNNING' if svc_running else 'ainda STOPPED'}")

            log("\n=== Estado dos perfis de firewall ===")
            r_state = subprocess.run(
                [netsh, "advfirewall", "show", "allprofiles", "state"],
                capture_output=True, text=True, errors="replace"
            )
            log(r_state.stdout.strip())
            if r_state.stdout.lower().count("off") >= 3:
                log("Todos os perfis estao OFF — firewall desativado, porta ja acessivel.")
                return True

            log("\n=== PowerShell New-NetFirewallRule ===")
            ps_cmd = (
                f"Remove-NetFirewallRule -DisplayName '{SERVICE_NAME}' -ErrorAction SilentlyContinue; "
                f"New-NetFirewallRule -DisplayName '{SERVICE_NAME}' -Direction Inbound "
                f"-Action Allow -Protocol TCP -LocalPort {porta} -Profile Any -ErrorAction Stop"
            )
            r_ps = subprocess.run(
                [ps_exe, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", ps_cmd],
                capture_output=True, text=True, errors="replace"
            )
            lfw.write(r_ps.stdout); lfw.write(r_ps.stderr)
            log(f"exit code: {r_ps.returncode}")

            if r_ps.returncode == 0:
                r_show = subprocess.run(
                    [netsh, "advfirewall", "firewall", "show", "rule", f"name={SERVICE_NAME}"],
                    capture_output=True, text=True, errors="replace"
                )
                log(r_show.stdout)
                return True

            log("\n=== Fallback netsh ===")
            subprocess.run(
                [netsh, "advfirewall", "firewall", "delete", "rule", f"name={SERVICE_NAME}"],
                capture_output=True
            )
            r_netsh = subprocess.run([
                netsh, "advfirewall", "firewall", "add", "rule",
                f"name={SERVICE_NAME}", "dir=in", "action=allow",
                "protocol=TCP", f"localport={porta}", "profile=any",
            ], capture_output=True, text=True, errors="replace")
            lfw.write(r_netsh.stdout); lfw.write(r_netsh.stderr)
            log(f"netsh exit code: {r_netsh.returncode}")

            r_show = subprocess.run(
                [netsh, "advfirewall", "firewall", "show", "rule", f"name={SERVICE_NAME}"],
                capture_output=True, text=True, errors="replace"
            )
            log(r_show.stdout)
            return "Nenhuma regra" not in r_show.stdout and SERVICE_NAME in r_show.stdout

    def _test_firebird(self) -> str | None:
        try:
            from firebird.driver import connect as fb_connect
            host = self.v_host.get().strip() or "localhost"
            db   = self.v_db.get().strip()
            dsn  = db if host in ("localhost", "127.0.0.1") else f"{host}:{db}"
            con  = fb_connect(database=dsn, user="SYSDBA", password="masterkey")
            con.close()
            return None
        except ImportError:
            return None
        except Exception as e:
            err = str(e)
            if "xnet" in err.lower() or "failed to establish" in err.lower():
                return None
            return err

    def _test_porta(self) -> str | None:
        import socket
        porta = 8000
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            if s.connect_ex(("127.0.0.1", porta)) == 0:
                return (
                    f"A porta {porta} já está em uso por outro processo.\n"
                    "Encerre o processo que ocupa essa porta ou escolha outra porta."
                )
        return None

    def _install_worker(self):
        install_dir = self.v_install.get()
        porta = "8000"
        try:
            import time as _time

            self._set_status("Criando pastas...")
            os.makedirs(install_dir, exist_ok=True)
            os.makedirs(os.path.join(install_dir, "logs"), exist_ok=True)

            self._set_status("Testando conexão com o banco de dados Firebird...")
            fb_erro = self._test_firebird()
            if fb_erro:
                self._set_status(f"Falha ao conectar ao banco: {fb_erro}", RED_C)
                if not messagebox.askyesno(
                    "Aviso: banco inacessível",
                    f"Não foi possível conectar ao banco Firebird:\n\n{fb_erro}\n\n"
                    "Verifique o caminho, host e credenciais.\n\n"
                    "Deseja instalar mesmo assim? O serviço pode não iniciar corretamente.",
                ):
                    return

            self._set_status("Verificando NSSM...")
            nssm = self._locate_nssm(install_dir)
            if not nssm:
                return

            self._set_status("Parando serviço anterior (se houver)...")
            subprocess.run([nssm, "stop",   SERVICE_NAME], capture_output=True)
            subprocess.run([nssm, "remove", SERVICE_NAME, "confirm"], capture_output=True)
            _time.sleep(1)

            self._set_status("Verificando porta...")
            porta_erro = self._test_porta()
            if porta_erro:
                self._set_status(porta_erro, RED_C)
                messagebox.showerror("Porta em uso", porta_erro)
                return

            self._set_status("Configurando exclusão no antivírus...")
            sysroot_pre = os.environ.get("SystemRoot", r"C:\Windows")
            ps_exe_pre  = os.path.join(sysroot_pre, "System32", "WindowsPowerShell", "v1.0", "powershell.exe")
            subprocess.run(
                [ps_exe_pre, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                 "-Command", f"Add-MpPreference -ExclusionPath '{install_dir}' -ErrorAction SilentlyContinue"],
                capture_output=True
            )

            self._set_status("Copiando arquivos do servidor...")
            server_target = self._copy_server_files(install_dir)

            self._set_status("Salvando configuração (.env)...")
            self._write_env(install_dir)

            self._set_status("Registrando serviço Windows...")
            is_exe = server_target.endswith(".exe")
            if is_exe:
                subprocess.run([nssm, "install", SERVICE_NAME, server_target], check=True)
            else:
                python_exe = shutil.which("python") or shutil.which("python3") or sys.executable
                subprocess.run([nssm, "install", SERVICE_NAME, python_exe, server_target], check=True)

            for key, val in [
                ("AppDirectory", install_dir),
                ("DisplayName",  SERVICE_DISPLAY),
                ("Description",  "API de inventário Invec"),
                ("Start",        "SERVICE_AUTO_START"),
                ("AppStdout",    os.path.join(install_dir, "logs", "servico.log")),
                ("AppStderr",    os.path.join(install_dir, "logs", "erro.log")),
                ("AppRotateFiles", "1"),
                ("AppRotateBytes", "10485760"),
            ]:
                subprocess.run([nssm, "set", SERVICE_NAME, key, val], check=True)

            self._set_status("Iniciando serviço...")
            subprocess.run([nssm, "start", SERVICE_NAME])

            self._set_status("Aguardando servidor iniciar...")
            import urllib.request, urllib.error
            api_ok = False
            for _ in range(20):
                _time.sleep(1)
                try:
                    urllib.request.urlopen(f"http://localhost:{porta}/ping", timeout=2)
                    api_ok = True
                    break
                except Exception:
                    pass

            self._set_status("Configurando firewall...")
            log_fw = os.path.join(install_dir, "logs", "firewall.log")
            fw_ok = self._configure_firewall(porta, log_fw)
            if not fw_ok:
                messagebox.showwarning(
                    "Aviso: regra de firewall",
                    f"O serviço foi instalado e está rodando normalmente,\n"
                    f"mas não foi possível criar a regra de firewall automaticamente.\n\n"
                    f"Execute no PowerShell como Administrador:\n\n"
                    f"New-NetFirewallRule -DisplayName '{SERVICE_NAME}' "
                    f"-Direction Inbound -Action Allow "
                    f"-Protocol TCP -LocalPort {porta} -Profile Any\n\n"
                    f"Detalhes em: {log_fw}"
                )

            if api_ok:
                self._set_status(
                    f"● Instalado com sucesso! Serviço rodando em http://localhost:{porta}", GREEN
                )
                if messagebox.askyesno(
                    "Instalação concluída",
                    f"Serviço instalado e iniciado com sucesso!\n\n"
                    f"API disponível em: http://localhost:{porta}\n"
                    f"Pasta de instalação: {install_dir}\n\n"
                    f"Deseja fechar o instalador?"
                ):
                    self.after(0, self.destroy)
            else:
                log_erro = os.path.join(install_dir, "logs", "erro.log")
                trecho = ""
                if os.path.exists(log_erro):
                    try:
                        with open(log_erro, encoding="utf-8", errors="replace") as lf:
                            linhas = lf.readlines()
                            trecho = "".join(linhas[-20:]) if linhas else ""
                    except Exception:
                        pass
                self._set_status(
                    "Serviço registrado, mas API não respondeu. Verifique os logs.", AMBER
                )
                messagebox.showwarning(
                    "Atenção: servidor não respondeu",
                    f"O serviço foi registrado mas a API não respondeu em http://localhost:{porta}/ping\n\n"
                    f"Possíveis causas:\n"
                    f"  • Antivírus bloqueou o InvecServidor.exe\n"
                    f"  • Banco de dados inacessível\n"
                    f"  • Licença inválida\n"
                    f"  • Erro nas migrations\n\n"
                    f"Verifique: {log_erro}"
                    + (f"\n\nÚltimas linhas do log:\n{trecho}" if trecho else "")
                )

        except subprocess.CalledProcessError as e:
            self._set_status(f"Erro na instalação: {e}", RED_C)
            messagebox.showerror("Erro", str(e))
        except Exception as e:
            self._set_status(f"Erro inesperado: {e}", RED_C)
            messagebox.showerror("Erro inesperado", str(e))
        finally:
            self.btn_install.configure(state="normal")
            self.after(1000, self._refresh_status)

    def _on_restart(self):
        if not is_admin():
            messagebox.showerror("Permissão necessária", "Execute como Administrador.")
            return
        install_dir = self.v_install.get()
        if os.path.exists(install_dir):
            self._write_env(install_dir)
        self._set_status("Reiniciando serviço...")
        nssm = os.path.join(install_dir, "nssm.exe")
        if os.path.exists(nssm):
            subprocess.run([nssm, "stop",  SERVICE_NAME], capture_output=True)
            subprocess.run([nssm, "start", SERVICE_NAME], capture_output=True)
        else:
            subprocess.run(["net", "stop",  SERVICE_NAME], capture_output=True)
            subprocess.run(["net", "start", SERVICE_NAME], capture_output=True)
        self.after(1500, self._refresh_status)

    def _on_uninstall(self):
        if not is_admin():
            messagebox.showerror("Permissão necessária", "Execute como Administrador.")
            return
        if not messagebox.askyesno(
            "Desinstalar",
            f"Remover o serviço '{SERVICE_NAME}'?\n\n"
            "Os arquivos de instalação e o banco de dados NÃO serão apagados.",
        ):
            return
        install_dir = self.v_install.get()
        nssm = os.path.join(install_dir, "nssm.exe")
        if os.path.exists(nssm):
            subprocess.run([nssm, "stop",   SERVICE_NAME],           capture_output=True)
            subprocess.run([nssm, "remove", SERVICE_NAME, "confirm"], capture_output=True)
        else:
            subprocess.run(["sc", "stop",   SERVICE_NAME], capture_output=True)
            subprocess.run(["sc", "delete", SERVICE_NAME], capture_output=True)
        sysroot = os.environ.get("SystemRoot", r"C:\Windows")
        netsh   = os.path.join(sysroot, "System32", "netsh.exe")
        ps_exe  = os.path.join(sysroot, "System32", "WindowsPowerShell", "v1.0", "powershell.exe")
        subprocess.run(
            [ps_exe, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
             "-Command", f"Remove-NetFirewallRule -DisplayName '{SERVICE_NAME}' -ErrorAction SilentlyContinue"],
            capture_output=True
        )
        subprocess.run(
            [netsh, "advfirewall", "firewall", "delete", "rule", f"name={SERVICE_NAME}"],
            capture_output=True
        )
        self._set_status("Serviço removido com sucesso.")
        messagebox.showinfo("Desinstalado", "Serviço removido com sucesso.")

    def run(self):
        self.mainloop()


if __name__ == "__main__":
    App().run()
