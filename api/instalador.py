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
from tkinter import ttk, filedialog, messagebox

SERVICE_NAME    = "InvecAPI"
SERVICE_DISPLAY = "Invec - API Inventario"
DEFAULT_DIR     = r"C:\Administracao\Invec"

# ── Utilitários ──────────────────────────────────────────────────────────────

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

# ── Aplicação GUI ────────────────────────────────────────────────────────────

class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Invec - Instalador do Servidor")
        self.root.geometry("600x550")
        self.root.resizable(False, False)
        self.root.configure(bg="#F5F5F5")

        self.v_install    = tk.StringVar(value=DEFAULT_DIR)
        self.v_db         = tk.StringVar()
        self.v_host       = tk.StringVar(value="localhost")
        self.v_user       = tk.StringVar(value="SYSDBA")
        self.v_pass       = tk.StringVar(value="masterkey")
        self.v_port       = tk.StringVar(value="8000")
        self.v_idempresa  = tk.StringVar(value="1")
        self.v_license    = tk.StringVar()
        self.v_status     = tk.StringVar(value="Aguardando...")

        self._build_ui()
        self._load_existing_env()
        self.root.after(200, self._refresh_status)

    # ── Layout ───────────────────────────────────────────────────────────────

    def _build_ui(self):
        hdr = tk.Frame(self.root, bg="#CC5B2A", height=54)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)
        tk.Label(hdr, text="  Invec  |  Instalador do Servidor",
                 bg="#CC5B2A", fg="white",
                 font=("Segoe UI", 13, "bold"), anchor=tk.W).pack(fill=tk.X, pady=13)

        f = ttk.Frame(self.root, padding=(22, 14))
        f.pack(fill=tk.BOTH, expand=True)
        f.columnconfigure(1, weight=1)

        def row_label(r, text, bold=False):
            font = ("Segoe UI", 9, "bold") if bold else ("Segoe UI", 9)
            ttk.Label(f, text=text, font=font).grid(row=r, column=0, sticky=tk.W, pady=4)

        def row_entry(r, var, width=42, show=None):
            kw = dict(textvariable=var, width=width)
            if show:
                kw['show'] = show
            ttk.Entry(f, **kw).grid(row=r, column=1, sticky=tk.EW, padx=(8, 0), pady=4)

        r = 0
        row_label(r, "Diretorio de instalacao:")
        dir_fr = ttk.Frame(f)
        dir_fr.grid(row=r, column=1, sticky=tk.EW, padx=(8, 0), pady=4)
        ttk.Entry(dir_fr, textvariable=self.v_install, width=36).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(dir_fr, text="...", width=3, command=self._browse_install_dir).pack(side=tk.LEFT, padx=(4, 0))
        r += 1

        ttk.Separator(f, orient=tk.HORIZONTAL).grid(row=r, column=0, columnspan=2, sticky=tk.EW, pady=6)
        r += 1

        row_label(r, "Banco de dados Firebird (.FDB):", bold=True)
        db_fr = ttk.Frame(f)
        db_fr.grid(row=r, column=1, sticky=tk.EW, padx=(8, 0), pady=4)
        ttk.Entry(db_fr, textvariable=self.v_db, width=36).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(db_fr, text="...", width=3, command=self._browse_db).pack(side=tk.LEFT, padx=(4, 0))
        r += 1

        row_label(r, "Host Firebird:")
        ttk.Entry(f, textvariable=self.v_host, width=28).grid(row=r, column=1, sticky=tk.W, padx=(8, 0), pady=4)
        r += 1

        row_label(r, "Usuario Firebird:")
        ttk.Entry(f, textvariable=self.v_user, width=20).grid(row=r, column=1, sticky=tk.W, padx=(8, 0), pady=4)
        r += 1

        row_label(r, "Senha Firebird:")
        ttk.Entry(f, textvariable=self.v_pass, width=20, show="*").grid(row=r, column=1, sticky=tk.W, padx=(8, 0), pady=4)
        r += 1

        row_label(r, "Porta da API:")
        ttk.Entry(f, textvariable=self.v_port, width=8).grid(row=r, column=1, sticky=tk.W, padx=(8, 0), pady=4)
        r += 1

        row_label(r, "ID da Empresa (IDEMPRESA):")
        ttk.Entry(f, textvariable=self.v_idempresa, width=8).grid(row=r, column=1, sticky=tk.W, padx=(8, 0), pady=4)
        r += 1

        ttk.Separator(f, orient=tk.HORIZONTAL).grid(row=r, column=0, columnspan=2, sticky=tk.EW, pady=6)
        r += 1

        row_label(r, "Chave de Licenca:", bold=True)
        ttk.Entry(f, textvariable=self.v_license, width=42).grid(row=r, column=1, sticky=tk.EW, padx=(8, 0), pady=4)
        r += 1

        ttk.Label(f, text="Fornecida pela Pontual Tecnologia. Necessaria para o servidor funcionar.",
                  font=("Segoe UI", 8), foreground="#888").grid(
            row=r, column=1, sticky=tk.W, padx=(8, 0))
        r += 1

        ttk.Separator(f, orient=tk.HORIZONTAL).grid(row=r, column=0, columnspan=2, sticky=tk.EW, pady=8)
        r += 1

        self.lbl_status = ttk.Label(f, textvariable=self.v_status, foreground="#666",
                                    font=("Segoe UI", 9), wraplength=520)
        self.lbl_status.grid(row=r, column=0, columnspan=2, sticky=tk.W)
        r += 1

        bf = ttk.Frame(f)
        bf.grid(row=r, column=0, columnspan=2, pady=(12, 0))

        self.btn_install = ttk.Button(bf, text="Instalar / Atualizar",
                                      command=self._on_install, width=22)
        self.btn_install.pack(side=tk.LEFT, padx=4)

        ttk.Button(bf, text="Reiniciar Servico",
                   command=self._on_restart, width=18).pack(side=tk.LEFT, padx=4)

        ttk.Button(bf, text="Desinstalar",
                   command=self._on_uninstall, width=14).pack(side=tk.LEFT, padx=4)

        ttk.Button(bf, text="Fechar",
                   command=self.root.destroy, width=10).pack(side=tk.LEFT, padx=4)

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _browse_install_dir(self):
        p = filedialog.askdirectory(
            title="Selecionar pasta de instalacao",
            initialdir=self.v_install.get() if os.path.exists(self.v_install.get()) else DEFAULT_DIR,
        )
        if p:
            self.v_install.set(os.path.normpath(p))

    def _browse_db(self):
        p = filedialog.askopenfilename(
            title="Selecionar banco Firebird",
            filetypes=[("Firebird Database", "*.fdb *.FDB *.gdb *.GDB"),
                       ("Todos", "*.*")]
        )
        if p:
            self.v_db.set(os.path.normpath(p))

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
                    'FB_USER':     self.v_user,
                    'FB_PASSWORD': self.v_pass,
                    'PORT':        self.v_port,
                    'IDEMPRESA':   self.v_idempresa,
                    'LICENSE_KEY': self.v_license,
                }
                if k in mapping:
                    mapping[k].set(v)

    def _set_status(self, msg: str, color: str = "#444"):
        self.v_status.set(msg)
        self.lbl_status.configure(foreground=color)
        self.root.update_idletasks()

    def _refresh_status(self):
        st = service_status()
        if st == 'running':
            self._set_status(f"Servico RODANDO na porta {self.v_port.get()}.", "#2E7D32")
        elif st == 'stopped':
            self._set_status("Servico instalado mas PARADO. Clique em Reiniciar Servico.", "#E65100")
        else:
            self._set_status("Servico nao instalado. Configure os campos e clique em Instalar.")

    def _write_env(self, install_dir: str):
        env_path = os.path.join(install_dir, ".env")
        # Preserva JWT_SECRET existente; gera novo se não houver
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
                f"FB_USER={self.v_user.get()}\n"
                f"FB_PASSWORD={self.v_pass.get()}\n"
                f"PORT={self.v_port.get()}\n"
                f"IDEMPRESA={self.v_idempresa.get() or '1'}\n"
                f"LICENSE_KEY={self.v_license.get()}\n"
                f"JWT_SECRET={jwt_secret}\n"
            )
        # INST-2: restringe leitura do .env para SYSTEM + Administrators (remove acesso de Others)
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
            "NSSM nao encontrado",
            "O utilitario NSSM (nssm.exe) nao foi encontrado.\n\n"
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

        # Fallback: rodando como script Python direto (sem PyInstaller)
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

        self._set_status("Instalando dependencias Python (pip)...")
        req = os.path.join(install_dir, "requirements.txt")
        python_exe = shutil.which("python") or shutil.which("python3") or sys.executable
        subprocess.run(
            [python_exe, "-m", "pip", "install", "-r", req, "--quiet"],
            check=True,
        )
        return os.path.join(install_dir, "server.py")

    # ── Acoes dos botoes ─────────────────────────────────────────────────────

    def _on_install(self):
        if not self.v_db.get():
            messagebox.showerror("Erro", "Selecione o caminho do banco de dados Firebird (.FDB).")
            return
        if not self.v_license.get().strip():
            messagebox.showerror("Erro", "Informe a Chave de Licenca.\n\nSolicite a chave para a Pontual Tecnologia.")
            return
        try:
            porta_int = int(self.v_port.get())
            if not (1 <= porta_int <= 65535):
                raise ValueError()
        except ValueError:
            messagebox.showerror("Erro", "Porta invalida. Use um numero entre 1 e 65535 (padrao: 8000).")
            return
        if not is_admin():
            messagebox.showerror(
                "Permissao necessaria",
                "Execute o instalador como Administrador.\n"
                "(clique direito no arquivo > Executar como administrador)"
            )
            return
        self.btn_install.config(state=tk.DISABLED)
        threading.Thread(target=self._install_worker, daemon=True).start()

    def _configure_firewall(self, porta: str, log_fw: str) -> bool:
        """
        Cria regra de entrada no Windows Firewall para a porta da API.
        Inicia o serviço MpsSvc se estiver parado.
        Retorna True se a regra foi criada (ou se o firewall está desligado — porta já acessível).
        """
        import time as _time
        sysroot   = os.environ.get("SystemRoot", r"C:\Windows")
        netsh     = os.path.join(sysroot, "System32", "netsh.exe")
        ps_exe    = os.path.join(sysroot, "System32", "WindowsPowerShell", "v1.0", "powershell.exe")

        with open(log_fw, "w", encoding="utf-8") as lfw:
            def log(msg: str):
                lfw.write(msg + "\n")
                lfw.flush()

            # 1. Estado do serviço Windows Firewall (MpsSvc)
            log("=== Estado do Windows Firewall (MpsSvc) ===")
            r_svc = subprocess.run(
                ["sc", "query", "MpsSvc"],
                capture_output=True, text=True, errors="replace"
            )
            log(r_svc.stdout.strip())

            svc_running = "RUNNING" in r_svc.stdout
            svc_stopped = "STOPPED" in r_svc.stdout

            if not svc_running and not svc_stopped:
                # Serviço não encontrado — firewall ausente, porta já acessível
                log("MpsSvc nao encontrado. Firewall nao instalado — porta ja acessivel na rede.")
                return True

            if svc_stopped:
                log("\nMpsSvc PARADO. Tentando iniciar...")
                r_start = subprocess.run(
                    ["sc", "start", "MpsSvc"],
                    capture_output=True, text=True, errors="replace"
                )
                log(f"sc start MpsSvc => exit {r_start.returncode}: {r_start.stdout.strip()}")
                _time.sleep(2)
                r_check = subprocess.run(
                    ["sc", "query", "MpsSvc"],
                    capture_output=True, text=True, errors="replace"
                )
                svc_running = "RUNNING" in r_check.stdout
                log(f"Apos iniciar: {'RUNNING' if svc_running else 'ainda STOPPED'}")

            # 2. Verifica se o firewall está ativo (pode estar ligado mas com state=off)
            log("\n=== Estado dos perfis de firewall ===")
            r_state = subprocess.run(
                [netsh, "advfirewall", "show", "allprofiles", "state"],
                capture_output=True, text=True, errors="replace"
            )
            log(r_state.stdout.strip())
            firewall_off = r_state.stdout.lower().count("off") >= 3  # todos os 3 perfis off

            if firewall_off:
                log("Todos os perfis estao OFF — firewall desativado, porta ja acessivel.")
                return True

            # 3. Método primário: PowerShell New-NetFirewallRule
            log("\n=== PowerShell New-NetFirewallRule ===")
            ps_cmd = (
                f"Remove-NetFirewallRule -DisplayName '{SERVICE_NAME}' -ErrorAction SilentlyContinue; "
                f"New-NetFirewallRule -DisplayName '{SERVICE_NAME}' -Direction Inbound "
                f"-Action Allow -Protocol TCP -LocalPort {porta} -Profile Any -ErrorAction Stop"
            )
            r_ps = subprocess.run(
                [ps_exe, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                 "-Command", ps_cmd],
                capture_output=True, text=True, errors="replace"
            )
            lfw.write(r_ps.stdout)
            lfw.write(r_ps.stderr)
            log(f"exit code: {r_ps.returncode}")

            if r_ps.returncode == 0:
                log("\n=== Verificacao ===")
                r_show = subprocess.run(
                    [netsh, "advfirewall", "firewall", "show", "rule", f"name={SERVICE_NAME}"],
                    capture_output=True, text=True, errors="replace"
                )
                log(r_show.stdout)
                return True

            # 4. Fallback: netsh
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
            lfw.write(r_netsh.stdout)
            lfw.write(r_netsh.stderr)
            log(f"netsh exit code: {r_netsh.returncode}")

            log("\n=== Verificacao ===")
            r_show = subprocess.run(
                [netsh, "advfirewall", "firewall", "show", "rule", f"name={SERVICE_NAME}"],
                capture_output=True, text=True, errors="replace"
            )
            log(r_show.stdout)

            regra_criada = "Nenhuma regra" not in r_show.stdout and SERVICE_NAME in r_show.stdout
            return regra_criada

    def _test_firebird(self) -> str | None:
        """INST-1: testa conexão com o banco antes de registrar o serviço.
        Retorna mensagem de erro ou None se OK."""
        try:
            from firebird.driver import connect as fb_connect
            con = fb_connect(
                database=self.v_db.get(),
                host=self.v_host.get() or "localhost",
                user=self.v_user.get(),
                password=self.v_pass.get(),
            )
            con.close()
            return None
        except ImportError:
            return None  # driver não disponível no contexto do instalador — pula validação
        except Exception as e:
            return str(e)

    def _test_porta(self) -> str | None:
        """Verifica se a porta já está em uso antes de registrar o serviço."""
        import socket
        porta = int(self.v_port.get())
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            if s.connect_ex(("127.0.0.1", porta)) == 0:
                return (
                    f"A porta {porta} ja esta em uso por outro processo.\n"
                    "Encerre o processo que ocupa essa porta ou escolha outra porta."
                )
        return None

    def _install_worker(self):
        install_dir = self.v_install.get()
        porta = self.v_port.get()
        try:
            import time as _time

            self._set_status("Criando pastas...")
            os.makedirs(install_dir, exist_ok=True)
            os.makedirs(os.path.join(install_dir, "logs"), exist_ok=True)

            # INST-1: valida conexão com Firebird antes de qualquer operação destrutiva
            self._set_status("Testando conexao com o banco de dados Firebird...")
            fb_erro = self._test_firebird()
            if fb_erro:
                self._set_status(f"Falha ao conectar ao banco: {fb_erro}", "#C62828")
                if not messagebox.askyesno(
                    "Aviso: banco inacessivel",
                    f"Nao foi possivel conectar ao banco Firebird:\n\n{fb_erro}\n\n"
                    "Verifique o caminho, host e credenciais.\n\n"
                    "Deseja instalar mesmo assim? O servico pode nao iniciar corretamente.",
                ):
                    return

            self._set_status("Verificando NSSM...")
            nssm = self._locate_nssm(install_dir)
            if not nssm:
                return

            # Para e remove o serviço ANTES de copiar arquivos: evita PermissionError
            # quando InvecServidor.exe está bloqueado pelo serviço em execução.
            self._set_status("Parando servico anterior (se houver)...")
            subprocess.run([nssm, "stop",   SERVICE_NAME], capture_output=True)
            subprocess.run([nssm, "remove", SERVICE_NAME, "confirm"], capture_output=True)
            _time.sleep(1)  # aguarda o processo liberar o arquivo

            # Verifica porta APÓS parar o serviço: detecta conflito com OUTROS processos
            self._set_status("Verificando porta...")
            porta_erro = self._test_porta()
            if porta_erro:
                self._set_status(porta_erro, "#C62828")
                messagebox.showerror("Porta em uso", porta_erro)
                return

            # Exclusão no Windows Defender: evita que o Defender quarentine InvecServidor.exe
            self._set_status("Configurando exclusao no antivirus...")
            sysroot_pre = os.environ.get("SystemRoot", r"C:\Windows")
            ps_exe_pre  = os.path.join(sysroot_pre, "System32", "WindowsPowerShell", "v1.0", "powershell.exe")
            subprocess.run(
                [ps_exe_pre, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                 "-Command", f"Add-MpPreference -ExclusionPath '{install_dir}' -ErrorAction SilentlyContinue"],
                capture_output=True
            )

            self._set_status("Copiando arquivos do servidor...")
            server_target = self._copy_server_files(install_dir)

            self._set_status("Salvando configuracao (.env)...")
            self._write_env(install_dir)

            self._set_status("Registrando servico Windows...")
            is_exe = server_target.endswith(".exe")
            if is_exe:
                subprocess.run([nssm, "install", SERVICE_NAME, server_target], check=True)
            else:
                python_exe = shutil.which("python") or shutil.which("python3") or sys.executable
                subprocess.run([nssm, "install", SERVICE_NAME, python_exe, server_target], check=True)

            cmds = [
                ["AppDirectory", install_dir],
                ["DisplayName",  SERVICE_DISPLAY],
                ["Description",  "API de inventario Invec"],
                ["Start",        "SERVICE_AUTO_START"],
                ["AppStdout",    os.path.join(install_dir, "logs", "servico.log")],
                ["AppStderr",    os.path.join(install_dir, "logs", "erro.log")],
                ["AppRotateFiles", "1"],
                ["AppRotateBytes", "10485760"],
            ]
            for key, val in cmds:
                subprocess.run([nssm, "set", SERVICE_NAME, key, val], check=True)

            self._set_status("Iniciando servico...")
            subprocess.run([nssm, "start", SERVICE_NAME])

            # INST-5: aguarda e verifica se o servidor respondeu (inclui verificação de migrations)
            self._set_status("Aguardando servidor iniciar...")
            import urllib.request, urllib.error
            api_ok = False
            for _ in range(20):  # até 20s (máquinas lentas / migrations grandes)
                _time.sleep(1)
                try:
                    urllib.request.urlopen(f"http://localhost:{porta}/ping", timeout=2)
                    api_ok = True
                    break
                except Exception:
                    pass

            # Configura firewall APÓS o serviço iniciar: garante que sobrescrevemos a regra
            # automática que o Windows cria (Domain+Private) quando o exe ouve pela primeira vez.
            self._set_status("Configurando firewall...")
            log_fw = os.path.join(install_dir, "logs", "firewall.log")
            fw_ok = self._configure_firewall(porta, log_fw)
            if not fw_ok:
                messagebox.showwarning(
                    "Aviso: regra de firewall",
                    f"O servico foi instalado e esta rodando normalmente,\n"
                    f"mas nao foi possivel criar a regra de firewall automaticamente.\n\n"
                    f"Dispositivos na rede podem nao conseguir conectar na porta {porta}.\n\n"
                    f"Para resolver, abra o PowerShell como Administrador e execute:\n\n"
                    f"New-NetFirewallRule -DisplayName '{SERVICE_NAME}' "
                    f"-Direction Inbound -Action Allow "
                    f"-Protocol TCP -LocalPort {porta} -Profile Any\n\n"
                    f"Detalhes do erro em:\n{log_fw}"
                )

            if api_ok:
                self._set_status(
                    f"Instalado com sucesso! Servico rodando em http://localhost:{porta}", "#2E7D32"
                )
                fechar = messagebox.askyesno(
                    "Instalacao concluida",
                    f"Servico instalado e iniciado com sucesso!\n\n"
                    f"API disponivel em: http://localhost:{porta}\n"
                    f"Pasta de instalacao: {install_dir}\n\n"
                    f"Deseja fechar o instalador?"
                )
                if fechar:
                    self.root.after(0, self.root.destroy)
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
                msg_extra = f"\n\nUltimas linhas do log de erros:\n{trecho}" if trecho else ""
                self._set_status(
                    "Servico registrado, mas API nao respondeu. Verifique os logs.", "#E65100"
                )
                messagebox.showwarning(
                    "Atencao: servidor nao respondeu",
                    f"O servico foi registrado mas a API nao respondeu em http://localhost:{porta}/ping\n\n"
                    f"Possiveis causas:\n"
                    f"  - Antivirus bloqueou o InvecServidor.exe\n"
                    f"  - Banco de dados inacessivel\n"
                    f"  - Licenca invalida\n"
                    f"  - Erro nas migrations\n\n"
                    f"Verifique: {log_erro}"
                    f"{msg_extra}"
                )

        except subprocess.CalledProcessError as e:
            self._set_status(f"Erro na instalacao: {e}", "#C62828")
            messagebox.showerror("Erro", str(e))
        except Exception as e:
            self._set_status(f"Erro inesperado: {e}", "#C62828")
            messagebox.showerror("Erro inesperado", str(e))
        finally:
            self.btn_install.config(state=tk.NORMAL)
            self.root.after(1000, self._refresh_status)

    def _on_restart(self):
        if not is_admin():
            messagebox.showerror("Permissao necessaria", "Execute como Administrador.")
            return
        install_dir = self.v_install.get()
        if os.path.exists(install_dir):
            self._write_env(install_dir)
        self._set_status("Reiniciando servico...")
        subprocess.run(["net", "stop",  SERVICE_NAME], capture_output=True)
        subprocess.run(["net", "start", SERVICE_NAME], capture_output=True)
        self.root.after(1500, self._refresh_status)

    def _on_uninstall(self):
        if not is_admin():
            messagebox.showerror("Permissao necessaria", "Execute como Administrador.")
            return
        if not messagebox.askyesno(
            "Desinstalar",
            f"Remover o servico '{SERVICE_NAME}'?\n\n"
            "Os arquivos de instalacao e o banco de dados NAO serao apagados.",
        ):
            return
        install_dir = self.v_install.get()
        nssm = os.path.join(install_dir, "nssm.exe")
        if os.path.exists(nssm):
            subprocess.run([nssm, "stop",   SERVICE_NAME],            capture_output=True)
            subprocess.run([nssm, "remove", SERVICE_NAME, "confirm"],  capture_output=True)
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
        self._set_status("Servico removido com sucesso.")
        messagebox.showinfo("Desinstalado", "Servico removido com sucesso.")

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    App().run()
