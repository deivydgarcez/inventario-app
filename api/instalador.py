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
from PIL import Image

ctk.set_appearance_mode("light")

# ── Paleta — espelha exatamente o glassmorphism do app Android ────────────────
ORANGE     = "#CC5B2A"
ORANGE_HOV = "#A8431A"
CARD_BG    = "#F2F7FC"    # branco com leve tint azul-gelo (simula frosted glass)
GLASS_BOR  = "#FFFFFF"    # borda branca — aresta do vidro
ENTRY_BG   = "#EAF2FA"
ENTRY_BOR  = "#C8DCF0"
TEXT_PRI   = "#1A1A1A"
TEXT_SEC   = "#5A6E80"
GREEN      = "#2E7D32"
RED_C      = "#C62828"
AMBER      = "#E65100"

# Gradiente de fundo: pêssego (topo) → azul-gelo (base) — igual ao bg_gradient.xml
GRAD_TOP = (0xF5, 0xCC, 0xB0)   # #F5CCB0
GRAD_BOT = (0xB8, 0xD4, 0xEC)   # #B8D4EC

try:
    from pontual_secrets import PONTUAL_WEBHOOK as _PONTUAL_WEBHOOK
except ImportError:
    _PONTUAL_WEBHOOK = ""

try:
    from pontual_secrets import PONTUAL_GITHUB_TOKEN as _PONTUAL_GITHUB_TOKEN
except ImportError:
    _PONTUAL_GITHUB_TOKEN = ""

SERVER_VERSION = "1.9.1"


def _load_logo(height: int) -> ctk.CTkImage | None:
    path = resource("logo_pontual.png")
    if not os.path.exists(path):
        return None
    try:
        img = Image.open(path).convert("RGBA")
        ratio = img.width / img.height
        w = int(height * ratio)
        return ctk.CTkImage(light_image=img, size=(w, height))
    except Exception:
        return None


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


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Invec — Instalador do Servidor")
        self.geometry("700x760")
        self.resizable(False, False)
        self.configure(fg_color="#F5CCB0")

        # Ícone da janela
        try:
            ico = tk.PhotoImage(file=resource("logo_pontual.png"))
            self.iconphoto(True, ico)
            self._ico_ref = ico
        except Exception:
            pass

        # Canvas de gradiente
        self._bg = tk.Canvas(self, bd=0, highlightthickness=0)
        self._bg.place(x=0, y=0, relwidth=1, relheight=1)
        self.after(5, self._draw_gradient)

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

    def _draw_gradient(self):
        w = self.winfo_width() or 700
        h = self.winfo_height() or 760
        self._bg.delete("all")
        steps = 120
        for i in range(steps):
            t = i / steps
            r = int(GRAD_TOP[0] + (GRAD_BOT[0] - GRAD_TOP[0]) * t)
            g = int(GRAD_TOP[1] + (GRAD_BOT[1] - GRAD_TOP[1]) * t)
            b = int(GRAD_TOP[2] + (GRAD_BOT[2] - GRAD_TOP[2]) * t)
            y0 = int(h * i / steps)
            y1 = int(h * (i + 1) / steps) + 1
            self._bg.create_rectangle(0, y0, w, y1, fill=f"#{r:02x}{g:02x}{b:02x}", outline="")
        self._bg.lower("all")

    # ── Layout ───────────────────────────────────────────────────────────────

    def _build_ui(self):
        logo_img = _load_logo(46)

        # ── Cabeçalho ─────────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color=CARD_BG, corner_radius=0, height=78, border_width=0)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        ctk.CTkFrame(hdr, fg_color=ORANGE, width=6, corner_radius=0).pack(side="left", fill="y")

        if logo_img:
            ctk.CTkLabel(hdr, image=logo_img, text="").pack(side="left", padx=(18, 0), pady=14)
            ctk.CTkFrame(hdr, fg_color=ENTRY_BOR, width=1, corner_radius=0).pack(
                side="left", fill="y", padx=(18, 0), pady=12)

        hdr_txt = ctk.CTkFrame(hdr, fg_color="transparent")
        hdr_txt.pack(side="left", fill="both", expand=True, padx=18, pady=10)
        ctk.CTkLabel(hdr_txt, text="Instalador do Servidor",
                     font=ctk.CTkFont("Segoe UI", 16, "bold"),
                     text_color=TEXT_PRI, anchor="w").pack(anchor="w")
        ctk.CTkLabel(hdr_txt, text="Invec — Inventário  ·  Porta 8000",
                     font=ctk.CTkFont("Segoe UI", 11),
                     text_color=TEXT_SEC, anchor="w").pack(anchor="w")

        ctk.CTkLabel(hdr, text=f"v{SERVER_VERSION}",
                     font=ctk.CTkFont("Segoe UI", 10),
                     text_color=TEXT_SEC).pack(side="right", padx=20)

        ctk.CTkFrame(self, fg_color=ORANGE, height=3, corner_radius=0).pack(fill="x")

        # ── Card glass ────────────────────────────────────────────────────────
        outer = ctk.CTkFrame(self, fg_color=GLASS_BOR, corner_radius=18, border_width=0)
        outer.pack(fill="both", expand=True, padx=16, pady=14)

        card = ctk.CTkFrame(outer, fg_color=CARD_BG, corner_radius=16, border_width=0)
        card.pack(fill="both", expand=True, padx=3, pady=3)

        # ── Helpers locais ────────────────────────────────────────────────────
        def _section(icon: str, title: str):
            wrap = ctk.CTkFrame(card, fg_color="transparent")
            wrap.pack(fill="x", padx=14, pady=(14, 6))
            ctk.CTkLabel(wrap, text=f"{icon}  {title}",
                         font=ctk.CTkFont("Segoe UI", 9, "bold"),
                         text_color=ORANGE).pack(side="left")
            ctk.CTkFrame(wrap, fg_color=ENTRY_BOR, height=1,
                         corner_radius=0).pack(side="left", fill="x", expand=True, padx=(10, 0))

        def _row(icon: str, label: str) -> ctk.CTkFrame:
            f = ctk.CTkFrame(card, fg_color="transparent")
            f.pack(fill="x", padx=14, pady=(0, 6))
            ctk.CTkLabel(f, text=f"{icon}  {label}", width=180,
                         font=ctk.CTkFont("Segoe UI", 11),
                         text_color=TEXT_SEC, anchor="w").pack(side="left")
            return f

        def _entry(parent, var, state="normal", width=None):
            kw = dict(textvariable=var, fg_color=ENTRY_BG, border_color=ENTRY_BOR,
                      border_width=1, corner_radius=8, text_color=TEXT_PRI, state=state)
            if width:
                kw["width"] = width
            e = ctk.CTkEntry(parent, **kw)
            e.pack(side="left", fill="x" if not width else None, expand=not bool(width))
            return e

        def _browse_btn(parent, cmd):
            ctk.CTkButton(parent, text="…", width=40, height=34,
                          fg_color=ORANGE, hover_color=ORANGE_HOV,
                          text_color="white", corner_radius=8,
                          command=cmd).pack(side="left", padx=(8, 0))

        def _hint(text: str):
            ctk.CTkLabel(card, text=text,
                         font=ctk.CTkFont("Segoe UI", 9),
                         text_color=TEXT_SEC, anchor="w").pack(
                fill="x", padx=(194 + 14, 14), pady=(0, 4))

        def _divider():
            ctk.CTkFrame(card, fg_color=ENTRY_BOR, height=1,
                         corner_radius=0).pack(fill="x", padx=14, pady=(10, 0))

        # ─── Seções ───────────────────────────────────────────────────────────
        _section("⚙", "INSTALAÇÃO")
        r = _row("📂", "Diretório")
        _entry(r, self.v_install)
        _browse_btn(r, self._browse_install_dir)

        _section("🗄", "BANCO DE DADOS FIREBIRD")
        r = _row("📄", "Arquivo .FDB")
        _entry(r, self.v_db)
        _browse_btn(r, self._browse_db)

        r = _row("🌐", "Host")
        _entry(r, self.v_host)

        r = _row("🏢", "ID da Empresa")
        _entry(r, self.v_idempresa, width=90)

        _section("🔐", "LICENÇA PONTUAL TECNOLOGIA")
        r = _row("🔑", "Chave de Licença")
        _entry(r, self.v_license)
        _hint("O limite de dispositivos móveis está codificado na chave de licença.")

        r = _row("🖥", "ID desta máquina")
        _entry(r, self.v_machine_id, state="disabled")
        ctk.CTkButton(r, text="Copiar", width=80, height=34,
                      fg_color="transparent", border_width=1,
                      border_color=ORANGE, text_color=ORANGE,
                      hover_color=ENTRY_BG, corner_radius=8,
                      font=ctk.CTkFont("Segoe UI", 11),
                      command=self._copy_machine_id).pack(side="left", padx=(8, 0))
        _hint("Envie este ID à Pontual Tecnologia para uma licença vinculada a esta máquina.")

        # ─── Status ───────────────────────────────────────────────────────────
        _divider()
        self.lbl_status = ctk.CTkLabel(
            card, textvariable=self.v_status,
            font=ctk.CTkFont("Segoe UI", 11),
            text_color=TEXT_SEC, anchor="w", wraplength=620)
        self.lbl_status.pack(fill="x", padx=14, pady=(10, 8))

        # ─── Botões ───────────────────────────────────────────────────────────
        _divider()
        self.btn_install = ctk.CTkButton(
            card, text="⬇  Instalar / Atualizar",
            fg_color=ORANGE, hover_color=ORANGE_HOV,
            text_color="white", corner_radius=12,
            height=48, font=ctk.CTkFont("Segoe UI", 13, "bold"),
            command=self._on_install)
        self.btn_install.pack(fill="x", padx=14, pady=(10, 8))

        ghost_row = ctk.CTkFrame(card, fg_color="transparent")
        ghost_row.pack(fill="x", padx=14, pady=(0, 14))
        ghost_btns = [
            ("↺  Reiniciar Serviço", self._on_restart),
            ("✕  Desinstalar",        self._on_uninstall),
            ("╳  Fechar",             self.destroy),
        ]
        for i, (txt, cmd) in enumerate(ghost_btns):
            ctk.CTkButton(
                ghost_row, text=txt, command=cmd,
                fg_color="transparent", border_width=1,
                border_color=ENTRY_BOR, text_color=TEXT_PRI,
                hover_color=ENTRY_BG, corner_radius=10, height=40,
                font=ctk.CTkFont("Segoe UI", 11),
            ).pack(side="left", fill="x", expand=True,
                   padx=(0, 0 if i == len(ghost_btns) - 1 else 8))

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
                f"DISCORD_WEBHOOK={_PONTUAL_WEBHOOK}\n"
                f"GITHUB_TOKEN={_PONTUAL_GITHUB_TOKEN}\n"
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

    def _write_update_script(self, install_dir: str):
        src = resource("update_server.ps1")
        dest = os.path.join(install_dir, "update_server.ps1")
        if os.path.exists(src):
            shutil.copy2(src, dest)
        # Escreve a versão atual do servidor para referência do updater
        with open(os.path.join(install_dir, "server_version.txt"), "w", encoding="utf-8") as fh:
            fh.write(SERVER_VERSION)

    def _criar_agendamento(self, install_dir: str):
        ps_script = os.path.join(install_dir, "update_server.ps1")
        if not os.path.exists(ps_script):
            return
        sysroot = os.environ.get("SystemRoot", r"C:\Windows")
        ps_exe  = os.path.join(sysroot, "System32", "WindowsPowerShell", "v1.0", "powershell.exe")
        cmd = (
            f"$a = New-ScheduledTaskAction -Execute '{ps_exe}' "
            f"-Argument '-NonInteractive -ExecutionPolicy Bypass -File \"{ps_script}\"'; "
            f"$t1 = New-ScheduledTaskTrigger -AtStartup; $t1.Delay = 'PT5M'; "
            f"$t2 = New-ScheduledTaskTrigger -Daily -At '17:00'; "
            f"$s = New-ScheduledTaskSettingsSet -StartWhenAvailable "
            f"-RunOnlyIfNetworkAvailable -MultipleInstances IgnoreNew; "
            f"$p = New-ScheduledTaskPrincipal -UserId 'SYSTEM' "
            f"-LogonType ServiceAccount -RunLevel Highest; "
            f"Register-ScheduledTask -TaskName 'InvecAutoUpdate' "
            f"-Action $a -Trigger $t1,$t2 -Settings $s -Principal $p -Force | Out-Null"
        )
        subprocess.run(
            [ps_exe, "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", cmd],
            capture_output=True, timeout=30,
        )

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
        subprocess.run([python_exe, "-m", "pip", "install", "-r", req, "--quiet"], check=True)
        return os.path.join(install_dir, "server.py")

    # ── Ações dos botões ─────────────────────────────────────────────────────

    def _on_install(self):
        if not self.v_db.get():
            messagebox.showerror("Erro", "Selecione o caminho do banco de dados Firebird (.FDB).")
            return
        if not self.v_license.get().strip():
            messagebox.showerror("Erro",
                "Informe a Chave de Licença.\n\nSolicite a chave para a Pontual Tecnologia.")
            return
        if not is_admin():
            messagebox.showerror("Permissão necessária",
                "Execute o instalador como Administrador.\n"
                "(clique direito no arquivo → Executar como administrador)")
            return
        self.btn_install.configure(state="disabled")
        threading.Thread(target=self._install_worker, daemon=True).start()

    def _configure_firewall(self, porta: str, log_fw: str) -> bool:
        import time as _time
        sysroot = os.environ.get("SystemRoot", r"C:\Windows")
        netsh   = os.path.join(sysroot, "System32", "netsh.exe")
        ps_exe  = os.path.join(sysroot, "System32", "WindowsPowerShell", "v1.0", "powershell.exe")

        with open(log_fw, "w", encoding="utf-8") as lfw:
            def log(msg):
                lfw.write(msg + "\n"); lfw.flush()

            r_svc = subprocess.run(["sc", "query", "MpsSvc"], capture_output=True, text=True, errors="replace")
            svc_running = "RUNNING" in r_svc.stdout
            svc_stopped = "STOPPED" in r_svc.stdout
            if not svc_running and not svc_stopped:
                return True
            if svc_stopped:
                subprocess.run(["sc", "start", "MpsSvc"], capture_output=True)
                _time.sleep(2)

            r_state = subprocess.run([netsh, "advfirewall", "show", "allprofiles", "state"],
                                     capture_output=True, text=True, errors="replace")
            if r_state.stdout.lower().count("off") >= 3:
                return True

            ps_cmd = (
                f"Remove-NetFirewallRule -DisplayName '{SERVICE_NAME}' -ErrorAction SilentlyContinue; "
                f"New-NetFirewallRule -DisplayName '{SERVICE_NAME}' -Direction Inbound "
                f"-Action Allow -Protocol TCP -LocalPort {porta} -Profile Any -ErrorAction Stop"
            )
            r_ps = subprocess.run(
                [ps_exe, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", ps_cmd],
                capture_output=True, text=True, errors="replace")
            log(r_ps.stdout + r_ps.stderr)
            if r_ps.returncode == 0:
                return True

            subprocess.run([netsh, "advfirewall", "firewall", "delete", "rule",
                            f"name={SERVICE_NAME}"], capture_output=True)
            r_netsh = subprocess.run([
                netsh, "advfirewall", "firewall", "add", "rule",
                f"name={SERVICE_NAME}", "dir=in", "action=allow",
                "protocol=TCP", f"localport={porta}", "profile=any",
            ], capture_output=True, text=True, errors="replace")
            log(r_netsh.stdout)
            r_show = subprocess.run(
                [netsh, "advfirewall", "firewall", "show", "rule", f"name={SERVICE_NAME}"],
                capture_output=True, text=True, errors="replace")
            return SERVICE_NAME in r_show.stdout

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
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            if s.connect_ex(("127.0.0.1", 8000)) == 0:
                return "A porta 8000 já está em uso. Encerre o processo que a ocupa."
        return None

    def _install_worker(self):
        install_dir = self.v_install.get()
        porta = "8000"
        try:
            import time as _time
            self._set_status("Criando pastas...")
            os.makedirs(install_dir, exist_ok=True)
            os.makedirs(os.path.join(install_dir, "logs"), exist_ok=True)

            self._set_status("Testando banco de dados Firebird...")
            fb_erro = self._test_firebird()
            if fb_erro:
                self._set_status(f"Falha no banco: {fb_erro}", RED_C)
                if not messagebox.askyesno("Aviso: banco inacessível",
                    f"Não foi possível conectar ao banco:\n\n{fb_erro}\n\nInstalar mesmo assim?"):
                    return

            self._set_status("Verificando NSSM...")
            nssm = self._locate_nssm(install_dir)
            if not nssm:
                return

            self._set_status("Parando serviço anterior...")
            subprocess.run([nssm, "stop",   SERVICE_NAME], capture_output=True)
            subprocess.run([nssm, "remove", SERVICE_NAME, "confirm"], capture_output=True)
            _time.sleep(1)

            self._set_status("Verificando porta...")
            porta_erro = self._test_porta()
            if porta_erro:
                self._set_status(porta_erro, RED_C)
                messagebox.showerror("Porta em uso", porta_erro)
                return

            sysroot_pre = os.environ.get("SystemRoot", r"C:\Windows")
            ps_pre = os.path.join(sysroot_pre, "System32", "WindowsPowerShell", "v1.0", "powershell.exe")
            subprocess.run([ps_pre, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                "-Command", f"Add-MpPreference -ExclusionPath '{install_dir}' -ErrorAction SilentlyContinue"],
                capture_output=True)

            self._set_status("Copiando arquivos do servidor...")
            server_target = self._copy_server_files(install_dir)

            self._set_status("Salvando configuração (.env)...")
            self._write_env(install_dir)

            self._set_status("Configurando atualização automática...")
            self._write_update_script(install_dir)
            self._criar_agendamento(install_dir)

            self._set_status("Registrando serviço Windows...")
            if server_target.endswith(".exe"):
                subprocess.run([nssm, "install", SERVICE_NAME, server_target], check=True)
            else:
                python_exe = shutil.which("python") or shutil.which("python3") or sys.executable
                subprocess.run([nssm, "install", SERVICE_NAME, python_exe, server_target], check=True)

            for key, val in [
                ("AppDirectory",   install_dir),
                ("DisplayName",    SERVICE_DISPLAY),
                ("Description",    "API de inventário Invec"),
                ("Start",          "SERVICE_AUTO_START"),
                ("AppStdout",      os.path.join(install_dir, "logs", "servico.log")),
                ("AppStderr",      os.path.join(install_dir, "logs", "erro.log")),
                ("AppRotateFiles", "1"),
                ("AppRotateBytes", "10485760"),
            ]:
                subprocess.run([nssm, "set", SERVICE_NAME, key, val], check=True)

            self._set_status("Iniciando serviço...")
            subprocess.run([nssm, "start", SERVICE_NAME])

            self._set_status("Aguardando servidor iniciar...")
            import urllib.request
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
                messagebox.showwarning("Aviso: firewall",
                    f"Serviço rodando, mas regra de firewall não criada.\n\n"
                    f"Execute no PowerShell como Admin:\n"
                    f"New-NetFirewallRule -DisplayName '{SERVICE_NAME}' "
                    f"-Direction Inbound -Action Allow -Protocol TCP -LocalPort {porta} -Profile Any")

            if api_ok:
                self._set_status(f"● Instalado! Serviço rodando em http://localhost:{porta}", GREEN)
                if messagebox.askyesno("Instalação concluída",
                    f"Serviço instalado com sucesso!\n\nAPI: http://localhost:{porta}\n"
                    f"Pasta: {install_dir}\n\nFechar o instalador?"):
                    self.after(0, self.destroy)
            else:
                log_erro = os.path.join(install_dir, "logs", "erro.log")
                trecho = ""
                if os.path.exists(log_erro):
                    try:
                        with open(log_erro, encoding="utf-8", errors="replace") as lf:
                            linhas = lf.readlines()
                            trecho = "".join(linhas[-20:])
                    except Exception:
                        pass
                self._set_status("Serviço registrado mas API não respondeu. Verifique os logs.", AMBER)
                messagebox.showwarning("Atenção",
                    f"API não respondeu em http://localhost:{porta}/ping\n\n"
                    f"Verifique: {log_erro}"
                    + (f"\n\n{trecho}" if trecho else ""))

        except subprocess.CalledProcessError as e:
            self._set_status(f"Erro: {e}", RED_C)
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
        if not messagebox.askyesno("Desinstalar",
            f"Remover o serviço '{SERVICE_NAME}'?\n\n"
            "Os arquivos e banco de dados NÃO serão apagados."):
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
        netsh  = os.path.join(sysroot, "System32", "netsh.exe")
        ps_exe = os.path.join(sysroot, "System32", "WindowsPowerShell", "v1.0", "powershell.exe")
        subprocess.run([ps_exe, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
            "-Command", f"Remove-NetFirewallRule -DisplayName '{SERVICE_NAME}' -ErrorAction SilentlyContinue"],
            capture_output=True)
        subprocess.run([netsh, "advfirewall", "firewall", "delete", "rule",
                        f"name={SERVICE_NAME}"], capture_output=True)
        sysroot = os.environ.get("SystemRoot", r"C:\Windows")
        ps_exe  = os.path.join(sysroot, "System32", "WindowsPowerShell", "v1.0", "powershell.exe")
        subprocess.run(
            [ps_exe, "-NonInteractive", "-ExecutionPolicy", "Bypass",
             "-Command", "Unregister-ScheduledTask -TaskName 'InvecAutoUpdate' -Confirm:$false -ErrorAction SilentlyContinue"],
            capture_output=True,
        )
        self._set_status("Serviço removido.")
        messagebox.showinfo("Desinstalado", "Serviço removido com sucesso.")

    def run(self):
        self.mainloop()


if __name__ == "__main__":
    App().run()
