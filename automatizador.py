import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import pyautogui
import time
import threading
import json
import os
import sys

# Failsafe: Mover el ratón a la esquina superior izquierda aborta cualquier automatización
pyautogui.FAILSAFE = True

def get_config_path():
    appdata = os.environ.get("APPDATA") or os.path.expanduser("~")
    folder = os.path.join(appdata, "FruloverInventario")
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, "config_integral.json")

def detectar_y_cerrar_popup_error():
    """Busca y cierra la ventana modal de error de Java 'Intente menor número de artículos'."""
    popup_encontrado = False
    if sys.platform == "win32":
        try:
            import ctypes
            user32 = ctypes.windll.user32

            def enum_windows_callback(hwnd, lparam):
                nonlocal popup_encontrado
                if user32.IsWindowVisible(hwnd):
                    length = user32.GetWindowTextLengthW(hwnd)
                    if length > 0:
                        buff = ctypes.create_unicode_buffer(length + 1)
                        user32.GetWindowTextW(hwnd, buff, length + 1)
                        title = buff.value
                        if "Intente menor" in title or "suficientes" in title:
                            popup_encontrado = True
                            user32.PostMessageW(hwnd, 0x0100, 0x20, 0) # VK_SPACE
                            user32.PostMessageW(hwnd, 0x0100, 0x0D, 0) # VK_RETURN
                            user32.PostMessageW(hwnd, 0x0010, 0, 0)    # WM_CLOSE
                            return False
                return True

            EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
            user32.EnumWindows(EnumWindowsProc(enum_windows_callback), 0)
        except Exception:
            pass
    return popup_encontrado

def hay_mensaje_error_pantalla():
    """Detección visual de respaldo buscando el ícono rojo de advertencia."""
    try:
        img = pyautogui.screenshot()
        w, h = img.size
        left, top, right, bottom = int(w * 0.25), int(h * 0.25), int(w * 0.75), int(h * 0.75)
        for x in range(left, right, 8):
            for y in range(top, bottom, 8):
                r, g, b = img.getpixel((x, y))[:3]
                if r > 160 and g < 90 and b < 90 and (r - g > 80):
                    return True
        return False
    except Exception:
        return False


class AppAsistenteIntegral:
    def __init__(self, root):
        self.root = root
        self.root.title("Asistente Integral - Galerías Hipermarket")
        self.root.geometry("660x760")
        self.root.resizable(False, False)

        self.config = self.cargar_configuracion()
        
        # Estado de Transferencias
        self.lista_transf = []
        self.ejecutando_transf = False

        # Estado de Habladores
        self.ejecutando_impresion_h = False

        self.crear_interfaz()
        self.actualizar_estado_calibraciones()

        # Iniciar hook / escucha de teclado en segundo plano para escáner (Enter) y F9
        threading.Thread(target=self.iniciar_escucha_teclado_nativo, daemon=True).start()

    def cargar_configuracion(self):
        cfg = get_config_path()
        if os.path.exists(cfg):
            try:
                with open(cfg, "r", encoding="utf-8") as f:
                    return json.load(f)
            except: pass
        return {"pos_codigo_transf": None, "pos_art_habla": None, "pos_rep_habla": None}

    def guardar_configuracion(self):
        cfg = get_config_path()
        try:
            with open(cfg, "w", encoding="utf-8") as f:
                json.dump(self.config, f)
            self.actualizar_estado_calibraciones()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar la configuración:\n{e}")

    def toggle_always_on_top(self):
        self.root.attributes("-topmost", self.var_topmost.get())

    def calibrar_posicion(self, clave, nombre_campo):
        messagebox.showinfo("Calibración", f"Al presionar Aceptar, tendrás 3 SEGUNDOS para hacer clic sobre: [{nombre_campo}] en Java.")
        time.sleep(0.5)

        for i in range(3, 0, -1):
            self.lbl_estado_global.config(text=f"⏱️ Haz clic en [{nombre_campo}]... {i}s", fg="#DC3545")
            self.root.update()
            time.sleep(1)

        pos_x, pos_y = pyautogui.position()
        self.config[clave] = {"x": pos_x, "y": pos_y}
        self.guardar_configuracion()
        self.lbl_estado_global.config(text=f"✅ {nombre_campo} calibrado: ({pos_x}, {pos_y})", fg="#28A745")

    def actualizar_estado_calibraciones(self):
        p_transf = self.config.get("pos_codigo_transf")
        p_art = self.config.get("pos_art_habla")
        p_rep = self.config.get("pos_rep_habla")

        self.lbl_cal_transf.config(text=f"Transf. Código: ({p_transf['x']}, {p_transf['y']}) ✓" if p_transf else "Transf. Código: Sin Calibrar ❌",
                                   fg="#28A745" if p_transf else "#DC3545")
        self.lbl_cal_art.config(text=f"Habl. Por Art.: ({p_art['x']}, {p_art['y']}) ✓" if p_art else "Habl. Por Art.: Sin Calibrar ❌",
                                fg="#28A745" if p_art else "#DC3545")
        self.lbl_cal_rep.config(text=f"Habl. Reporte: ({p_rep['x']}, {p_rep['y']}) ✓" if p_rep else "Habl. Reporte: Sin Calibrar ❌",
                                fg="#28A745" if p_rep else "#DC3545")

    def crear_interfaz(self):
        # Cabecera
        frame_header = tk.Frame(self.root, bg="#1F4E79")
        frame_header.pack(fill=tk.X)

        lbl_titulo = tk.Label(frame_header, text="Asistente Integral de Mercancía", font=("Calibri", 14, "bold"), fg="white", bg="#1F4E79")
        lbl_titulo.pack(side=tk.LEFT, padx=15, pady=8)

        self.var_topmost = tk.BooleanVar(value=True)
        chk_top = tk.Checkbutton(frame_header, text="📌 Siempre Visible", variable=self.var_topmost, command=self.toggle_always_on_top,
                                 bg="#1F4E79", fg="white", selectcolor="#2B579A", font=("Calibri", 9, "bold"))
        chk_top.pack(side=tk.RIGHT, padx=15)
        self.toggle_always_on_top()

        # Panel de Calibración
        frame_cal_bar = tk.LabelFrame(self.root, text=" 📍 Calibraciones de Clic en Java ", font=("Calibri", 9, "bold"), padx=10, pady=4)
        frame_cal_bar.pack(fill=tk.X, padx=15, pady=4)

        self.lbl_cal_transf = tk.Label(frame_cal_bar, text="", font=("Calibri", 8, "bold"))
        self.lbl_cal_transf.pack(side=tk.LEFT, expand=True)
        btn_c1 = tk.Button(frame_cal_bar, text="Calibrar", command=lambda: self.calibrar_posicion("pos_codigo_transf", "Código Transferencia"), font=("Calibri", 8))
        btn_c1.pack(side=tk.LEFT, padx=(0, 10))

        self.lbl_cal_art = tk.Label(frame_cal_bar, text="", font=("Calibri", 8, "bold"))
        self.lbl_cal_art.pack(side=tk.LEFT, expand=True)
        btn_c2 = tk.Button(frame_cal_bar, text="Calibrar", command=lambda: self.calibrar_posicion("pos_art_habla", "Habladores Por Artículo"), font=("Calibri", 8))
        btn_c2.pack(side=tk.LEFT, padx=(0, 10))

        self.lbl_cal_rep = tk.Label(frame_cal_bar, text="", font=("Calibri", 8, "bold"))
        self.lbl_cal_rep.pack(side=tk.LEFT, expand=True)
        btn_c3 = tk.Button(frame_cal_bar, text="Calibrar", command=lambda: self.calibrar_posicion("pos_rep_habla", "Habladores Reporte"), font=("Calibri", 8))
        btn_c3.pack(side=tk.LEFT)

        # Notebook de Pestañas
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)

        self.tab_transferencias = ttk.Frame(self.notebook)
        self.tab_habladores = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_transferencias, text="  🚚 Transferencia de Mercancía  ")
        self.notebook.add(self.tab_habladores, text="  🏷️ Habladores (Modo Escucha Directo)  ")

        self.construir_tab_transferencias()
        self.construir_tab_habladores()

        # Barra de Estado Global
        self.lbl_estado_global = tk.Label(self.root, text="Estado: Listo para trabajar", font=("Calibri", 11, "bold"), fg="#333333")
        self.lbl_estado_global.pack(pady=6)

    # --- PESTAÑA 1: TRANSFERENCIAS ---
    def construir_tab_transferencias(self):
        frame_add = tk.LabelFrame(self.tab_transferencias, text=" Entrada de Artículos ", font=("Calibri", 10, "bold"), padx=10, pady=6)
        frame_add.pack(fill=tk.X, padx=10, pady=6)

        tk.Label(frame_add, text="Código:", font=("Calibri", 10)).grid(row=0, column=0, sticky="w", padx=2)
        self.ent_cod_t = tk.Entry(frame_add, font=("Calibri", 11), width=18)
        self.ent_cod_t.grid(row=0, column=1, padx=4)
        self.ent_cod_t.bind("<Return>", lambda e: self.agregar_transf_escucha())

        tk.Label(frame_add, text="Cant:", font=("Calibri", 10)).grid(row=0, column=2, sticky="w", padx=2)
        self.ent_cant_t = tk.Entry(frame_add, font=("Calibri", 11), width=6)
        self.ent_cant_t.grid(row=0, column=3, padx=4)
        self.ent_cant_t.insert(0, "1")

        self.cb_modo_t = ttk.Combobox(frame_add, values=["📦 Bulto", "🔢 Suelto"], width=9, state="readonly")
        self.cb_modo_t.set("📦 Bulto")
        self.cb_modo_t.grid(row=0, column=4, padx=4)

        btn_add = tk.Button(frame_add, text="➕ Agregar", command=self.agregar_transf_escucha, bg="#17A2B8", fg="white", font=("Calibri", 9, "bold"))
        btn_add.grid(row=0, column=5, padx=4)

        btn_masivo = tk.Button(self.tab_transferencias, text="✍ Pegar Bloque de Texto Masivo", command=self.modal_masivo_transf, bg="#6F42C1", fg="white", font=("Calibri", 9, "bold"))
        btn_masivo.pack(fill=tk.X, padx=10, pady=2)

        frame_t = tk.LabelFrame(self.tab_transferencias, text=" Lista de Productos a Transferir ", font=("Calibri", 10, "bold"), padx=10, pady=4)
        frame_t.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)

        cols = ("nro", "codigo", "cantidad", "modo", "estado")
        self.tree_t = ttk.Treeview(frame_t, columns=cols, show="headings", height=8)
        self.tree_t.heading("nro", text="N°")
        self.tree_t.heading("codigo", text="CódigoArtículo")
        self.tree_t.heading("cantidad", text="Cant.")
        self.tree_t.heading("modo", text="Tipo")
        self.tree_t.heading("estado", text="Estado")

        self.tree_t.column("nro", width=35, anchor="center")
        self.tree_t.column("codigo", width=220, anchor="w")
        self.tree_t.column("cantidad", width=60, anchor="center")
        self.tree_t.column("modo", width=100, anchor="center")
        self.tree_t.column("estado", width=130, anchor="center")

        scr_t = ttk.Scrollbar(frame_t, orient=tk.VERTICAL, command=self.tree_t.yview)
        self.tree_t.configure(yscroll=scr_t.set)
        self.tree_t.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scr_t.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree_t.bind("<Delete>", lambda e: self.eliminar_item_transf())

        f_btn = tk.Frame(self.tab_transferencias)
        f_btn.pack(fill=tk.X, padx=10)
        tk.Button(f_btn, text="🗑 Eliminar", command=self.eliminar_item_transf, bg="#6C757D", fg="white", font=("Calibri", 8)).pack(side=tk.LEFT, padx=2)
        tk.Button(f_btn, text="🧹 Vaciar", command=self.vaciar_transf, bg="#DC3545", fg="white", font=("Calibri", 8)).pack(side=tk.LEFT, padx=2)

        f_cfg = tk.Frame(self.tab_transferencias)
        f_cfg.pack(fill=tk.X, padx=10, pady=4)
        tk.Label(f_cfg, text="⏱ Tiempo Búsqueda Java (s):", font=("Calibri", 9, "italic")).pack(side=tk.LEFT)
        self.ent_tiempo_t = tk.Entry(f_cfg, font=("Calibri", 9), width=5)
        self.ent_tiempo_t.pack(side=tk.LEFT, padx=4)
        self.ent_tiempo_t.insert(0, "3.5")

        self.var_auto_error = tk.BooleanVar(value=True)
        chk = tk.Checkbutton(f_cfg, text="Auto-omitir 'Sin Stock'", variable=self.var_auto_error, font=("Calibri", 9, "bold"), fg="#1F4E79")
        chk.pack(side=tk.RIGHT)

        self.btn_ejecutar_t = tk.Button(self.tab_transferencias, text="🚀 PROCESAR TRANSFERENCIA EN JAVA", command=self.iniciar_transf_thread,
                                        bg="#28A745", fg="white", font=("Calibri", 12, "bold"), height=2, cursor="hand2")
        self.btn_ejecutar_t.pack(fill=tk.X, padx=10, pady=6)

    def agregar_transf_escucha(self):
        cod = self.ent_cod_t.get().strip()
        cant = self.ent_cant_t.get().strip()
        modo = "Bulto" if "Bulto" in self.cb_modo_t.get() else "Suelto"
        if not cod: return
        self.lista_transf.append({"codigo": cod, "cantidad": cant if cant else "1", "modo": modo, "estado": "⏳ Pendiente"})
        self.actualizar_tabla_transf()
        self.ent_cod_t.delete(0, tk.END)
        self.ent_cant_t.delete(0, tk.END)
        self.ent_cant_t.insert(0, "1")
        self.ent_cod_t.focus()

    def modal_masivo_transf(self):
        modal = tk.Toplevel(self.root)
        modal.title("Carga Masiva")
        modal.geometry("400x350")
        modal.transient(self.root)
        modal.grab_set()

        tk.Label(modal, text="Pega aquí los códigos (Código y opcional Cantidad):", font=("Calibri", 10, "bold")).pack(anchor="w", padx=15, pady=8)
        txt = tk.Text(modal, font=("Consolas", 10), height=11)
        txt.pack(fill=tk.BOTH, expand=True, padx=15)

        def proc():
            for linea in txt.get("1.0", tk.END).strip().split("\n"):
                if not linea.strip(): continue
                p = linea.strip().split()
                c = p[0]
                q = p[1] if len(p) > 1 and p[1].replace('.', '').isdigit() else "1"
                self.lista_transf.append({"codigo": c, "cantidad": q, "modo": "Bulto", "estado": "⏳ Pendiente"})
            self.actualizar_tabla_transf()
            modal.destroy()

        tk.Button(modal, text="📥 Cargar", command=proc, bg="#28A745", fg="white", font=("Calibri", 10, "bold")).pack(fill=tk.X, padx=15, pady=8)

    def actualizar_tabla_transf(self):
        for item in self.tree_t.get_children(): self.tree_t.delete(item)
        for idx, item in enumerate(self.lista_transf):
            m = "📦 Bulto" if item["modo"] == "Bulto" else "🔢 Suelto"
            self.tree_t.insert("", tk.END, iid=idx, values=(idx + 1, item["codigo"], item["cantidad"], m, item["estado"]))

    def eliminar_item_transf(self):
        s = self.tree_t.selection()
        if not s: return
        del self.lista_transf[int(s[0])]
        self.actualizar_tabla_transf()

    def vaciar_transf(self):
        self.lista_transf = []
        self.actualizar_tabla_transf()

    def iniciar_transf_thread(self):
        if not self.lista_transf:
            messagebox.showwarning("Lista vacía", "Agrega al menos un artículo a la lista.")
            return
        if not self.config.get("pos_codigo_transf"):
            messagebox.showwarning("Falta Calibración", "Debes calibrar 'Código Transferencia' primero.")
            return

        if self.ejecutando_transf:
            self.ejecutando_transf = False
            self.lbl_estado_global.config(text="🛑 Cancelando...", fg="#DC3545")
            return

        self.ejecutando_transf = True
        self.btn_ejecutar_t.config(text="🛑 CANCELAR EJECUCIÓN", bg="#DC3545")
        threading.Thread(target=self.ejecutar_transf_lote, daemon=True).start()

    def ejecutar_transf_lote(self):
        try: t_wait = float(self.ent_tiempo_t.get().strip())
        except: t_wait = 3.5

        p_cod = self.config["pos_codigo_transf"]

        for i in range(5, 0, -1):
            if not self.ejecutando_transf: return
            self.lbl_estado_global.config(text=f"⚠️ Haz Clic en 'Código del artículo' en Java... {i}s", fg="#DC3545")
            time.sleep(1)

        tot = len(self.lista_transf)

        for idx, item in enumerate(self.lista_transf):
            if not self.ejecutando_transf: break
            cod, cant, modo = item["codigo"], item["cantidad"], item["modo"]
            self.lbl_estado_global.config(text=f"⚙️ Transferiendo [{idx + 1}/{tot}]: {cod}...", fg="#0D6EFD")

            try:
                pyautogui.click(p_cod["x"], p_cod["y"])
                time.sleep(0.15)
                pyautogui.hotkey('ctrl', 'a')
                pyautogui.press('backspace')

                pyautogui.write(cod, interval=0.04)
                pyautogui.press('tab')
                time.sleep(t_wait)

                if modo == "Bulto":
                    for _ in range(5): pyautogui.press('tab'); time.sleep(0.03)
                    pyautogui.hotkey('ctrl', 'a')
                    pyautogui.write(str(cant), interval=0.04)
                    pyautogui.press('tab'); pyautogui.press('tab')
                else:
                    pyautogui.press('tab'); pyautogui.press('tab')
                    pyautogui.hotkey('ctrl', 'a')
                    pyautogui.write('1', interval=0.04)
                    pyautogui.press('tab'); pyautogui.press('tab'); pyautogui.press('tab')
                    pyautogui.hotkey('ctrl', 'a')
                    pyautogui.write(str(cant), interval=0.04)
                    pyautogui.press('tab'); pyautogui.press('tab')

                pyautogui.press('enter')

                err = False
                fin = time.time() + 2.5
                if self.var_auto_error.get():
                    while time.time() < fin:
                        if detectar_y_cerrar_popup_error(): err = True; break
                        if hay_mensaje_error_pantalla():
                            err = True; pyautogui.press('space'); pyautogui.press('enter'); pyautogui.press('escape'); break
                        time.sleep(0.15)

                if err:
                    time.sleep(0.3)
                    pyautogui.click(p_cod["x"], p_cod["y"])
                    pyautogui.hotkey('ctrl', 'a'); pyautogui.press('backspace')
                    self.lista_transf[idx]["estado"] = "⚠️ Sin Stock"
                    self.actualizar_tabla_transf()
                else:
                    self.lista_transf[idx]["estado"] = "✅ Incluido"
                    self.actualizar_tabla_transf()

            except pyautogui.FailSafeException:
                self.lbl_estado_global.config(text="🛑 ABORTADO POR EL USUARIO.", fg="#DC3545")
                self.ejecutando_transf = False
                break

        self.ejecutando_transf = False
        self.lbl_estado_global.config(text="✅ ¡LOTE DE TRANSFERENCIA COMPLETADO!", fg="#28A745")
        self.btn_ejecutar_t.config(text="🚀 PROCESAR TRANSFERENCIA EN JAVA", bg="#28A745")

    # --- PESTAÑA 2: HABLADORES (MODO ESCUCHA DIRECTO) ---
    def construir_tab_habladores(self):
        frame_mod = tk.LabelFrame(self.tab_habladores, text=" Control del Modo de Escucha ", font=("Calibri", 10, "bold"), padx=15, pady=10)
        frame_mod.pack(fill=tk.X, padx=15, pady=10)

        self.var_escucha_habladores = tk.BooleanVar(value=False)
        self.btn_toggle_escucha = tk.Button(frame_mod, text="🎧 ACTIVAR MODO ESCUCHA (Auto-TAB + F9)", command=self.toggle_escucha_habladores,
                                             bg="#6C757D", fg="white", font=("Calibri", 11, "bold"), height=2, cursor="hand2")
        self.btn_toggle_escucha.pack(fill=tk.X, pady=4)

        lbl_inst = tk.Label(frame_mod, text="📌 Pasos:\n1. Calibra arriba 'Habladores Reporte'.\n2. Haz clic en '🎧 ACTIVAR MODO ESCUCHA'.\n3. Pon el foco en 'Por artículo' en la ventana de Java.\n4. El pasillero escanea. Cada escaneo enviará TAB automáticamente.\n5. Al terminar el lote, presiona F9 para elegir número de copias e imprimir directo en la POS-80.",
                            font=("Calibri", 9), justify=tk.LEFT, fg="#444444")
        lbl_inst.pack(anchor="w", pady=6)

        frame_opts = tk.LabelFrame(self.tab_habladores, text=" Configuración de Impresora ", font=("Calibri", 10, "bold"), padx=15, pady=10)
        frame_opts.pack(fill=tk.X, padx=15, pady=10)

        self.var_corregir_impresora = tk.BooleanVar(value=True)
        chk = tk.Checkbutton(frame_opts, text="Asegurar Impresora POS-80-Series (Cambia con ➡️ si detecta EPSON)",
                             variable=self.var_corregir_impresora, font=("Calibri", 9, "bold"), fg="#1F4E79")
        chk.pack(anchor="w")

        btn_f9_manual = tk.Button(self.tab_habladores, text="🖨️ PROCESAR E IMPRIMIR AHORA (F9)", command=self.solicitar_copias_e_imprimir_f9,
                                  bg="#28A745", fg="white", font=("Calibri", 12, "bold"), height=2, cursor="hand2")
        btn_f9_manual.pack(fill=tk.X, padx=15, pady=15)

    def toggle_escucha_habladores(self):
        val = not self.var_escucha_habladores.get()
        self.var_escucha_habladores.set(val)
        if val:
            self.btn_toggle_escucha.config(text="🟢 MODO ESCUCHA ACTIVO (Escaneando -> TAB | F9 -> Imprimir)", bg="#28A745")
            self.lbl_estado_global.config(text="🟢 Escuchando escáner en Java... Presiona F9 para imprimir.", fg="#28A745")
        else:
            self.btn_toggle_escucha.config(text="🎧 ACTIVAR MODO ESCUCHA (Auto-TAB + F9)", bg="#6C757D")
            self.lbl_estado_global.config(text="Estado: Modo Escucha desactivado", fg="#333333")

    def pedir_copias_gui(self):
        """Abre un modal ultrarrápido centrado en pantalla solicitando el número de copias."""
        copias_res = [1]

        modal = tk.Toplevel(self.root)
        modal.title("Copias de Habladores")
        modal.geometry("300x180")
        modal.resizable(False, False)
        modal.attributes("-topmost", True)

        # Centrar relativo a la ventana principal
        modal.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 150
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 90
        modal.geometry(f"+{max(0, x)}+{max(0, y)}")

        tk.Label(modal, text="🏷️ ¿Cuántas copias por hablador?", font=("Calibri", 12, "bold"), fg="#1F4E79").pack(pady=(15, 5))

        ent = tk.Entry(modal, font=("Calibri", 16, "bold"), width=5, justify="center")
        ent.pack(pady=5)
        ent.insert(0, "1")
        ent.focus_set()
        ent.selection_range(0, tk.END)

        def confirmar(event=None):
            val = ent.get().strip()
            if val.isdigit() and int(val) > 0:
                copias_res[0] = int(val)
            modal.destroy()

        ent.bind("<Return>", confirmar)
        ent.bind("<KP_Enter>", confirmar) # Enter del teclado numérico

        btn = tk.Button(modal, text="🖨️ Iniciar Impresión (Enter)", command=confirmar, bg="#28A745", fg="white", font=("Calibri", 10, "bold"), cursor="hand2")
        btn.pack(pady=10)

        modal.transient(self.root)
        modal.grab_set()
        modal.wait_window()
        return copias_res[0]

    def iniciar_escucha_teclado_nativo(self):
        """Maneja la captura directa de hardware en Windows para la tecla Enter (Escáner) y F9."""
        if sys.platform != "win32": return

        import ctypes
        user32 = ctypes.windll.user32

        enter_down = False
        f9_down = False

        while True:
            try:
                if self.var_escucha_habladores.get() and not self.ejecutando_transf and not self.ejecutando_impresion_h:
                    # VK_RETURN = 0x0D (Enter)
                    st_enter = user32.GetAsyncKeyState(0x0D)
                    if (st_enter & 0x0001) or (st_enter & 0x8000):
                        if not enter_down:
                            enter_down = True
                            time.sleep(0.08) # Pausa breve para que Java asimile los dígitos
                            pyautogui.press('tab')
                            self.lbl_estado_global.config(text="⚡ Auto-TAB enviado tras escaneo", fg="#0D6EFD")
                    else:
                        enter_down = False

                    # VK_F9 = 0x78 (F9)
                    st_f9 = user32.GetAsyncKeyState(0x78)
                    if (st_f9 & 0x0001) or (st_f9 & 0x8000):
                        if not f9_down:
                            f9_down = True
                            # Solicitar copias e iniciar hilo
                            self.root.after(0, self.solicitar_copias_e_imprimir_f9)
                    else:
                        f9_down = False

            except Exception:
                pass
            time.sleep(0.03)

    def solicitar_copias_e_imprimir_f9(self):
        if not self.config.get("pos_rep_habla"):
            messagebox.showwarning("Sin Calibrar", "Debes calibrar 'Habladores Reporte' en el panel de calibración superior.")
            return

        if self.ejecutando_impresion_h: return

        # Pedir número de copias antes de arrancar
        num_copias = self.pedir_copias_gui()

        self.ejecutando_impresion_h = True
        threading.Thread(target=self.ejecutar_impresion_habladores, args=(num_copias,), daemon=True).start()

    def ejecutar_impresion_habladores(self, num_copias):
        p_rep = self.config["pos_rep_habla"]

        try:
            self.lbl_estado_global.config(text=f"⚙️ Generando Reporte ({num_copias} copias por producto)...", fg="#0D6EFD")

            # 1. Clic directo en el botón 'Reporte' de Java
            pyautogui.click(p_rep["x"], p_rep["y"])
            time.sleep(3.0)

            # 2. Entrar al cuadro de impresión (TAB -> ENTER)
            pyautogui.press('tab')
            time.sleep(0.2)
            pyautogui.press('enter')
            time.sleep(1.5) # Espera a que abra el cuadro modal de selección de impresora

            # 3. Cambiar de EPSON a POS-80 si es necesario
            if self.var_corregir_impresora.get():
                pyautogui.press('right')
                time.sleep(0.2)

            # 4. Avanzar 6 TABs hasta la casilla "Número de copias"
            for _ in range(6):
                pyautogui.press('tab')
                time.sleep(0.04)

            # 5. Escribir el número de copias solicitado
            pyautogui.hotkey('ctrl', 'a')
            pyautogui.write(str(num_copias), interval=0.04)
            time.sleep(0.1)

            # 6. Confirmar impresión en Java
            pyautogui.press('enter')

            self.lbl_estado_global.config(text=f"✅ ¡HABLADORES ENVIADOS A LA POS-80 ({num_copias} COPIAS)! ", fg="#28A745")

        except pyautogui.FailSafeException:
            self.lbl_estado_global.config(text="🛑 ABORTADO POR EL USUARIO", fg="#DC3545")
        except Exception as e:
            self.lbl_estado_global.config(text=f"Error al imprimir: {e}", fg="#DC3545")
        finally:
            self.ejecutando_impresion_h = False


if __name__ == "__main__":
    root = tk.Tk()
    app = AppAsistenteIntegral(root)
    root.mainloop()