import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import pandas as pd
import pyautogui
import threading
import time
import os
import json
import socket
import io
import re
import datetime
import webbrowser
from PIL import Image, ImageTk

try:
    from flask import Flask, request, jsonify, render_template_string
    from flask_cors import CORS
    import qrcode
    HAS_SERVER_LIBS = True
except ImportError:
    HAS_SERVER_LIBS = False

try:
    from google import genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

pyautogui.FAILSAFE = True

# --- RUTAS DE CONFIGURACIÓN Y BASE DE DATOS LOCAL ---
def get_appdata_folder():
    appdata = os.environ.get("APPDATA") or os.path.expanduser("~")
    folder = os.path.join(appdata, "FruloverInventario")
    os.makedirs(folder, exist_ok=True)
    return folder

def get_config_path():
    return os.path.join(get_appdata_folder(), "config.json")

def get_catalogo_path():
    return os.path.join(get_appdata_folder(), "catalogo_insumos.json")

def get_historial_path():
    return os.path.join(get_appdata_folder(), "historial_tandas.json")

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def optimizar_imagen_extrema(imagen_pil, max_dim=800):
    """
    Convierte la imagen a Blanco y Negro (Grayscale) y la reduce a 800px max.
    Baja el peso a ~25KB para subida e inferencia ultrarrápida.
    """
    img = imagen_pil.convert("L")
    w, h = img.size
    if max(w, h) > max_dim:
        ratio = max_dim / float(max(w, h))
        new_w = int(w * ratio)
        new_h = int(h * ratio)
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    return img

CATALOGO_BASE = {
    "ACELGA": "999", "AGUACATE": "3", "AJI DULCE ROSA": "4", 
    "AJI JOVITO": "5", "AJI SOVITO": "5", "SOVITO": "5",
    "AJO CRIOLLO": "7", "AJO IMPORTADO": "96", "AJO PORRO": "997", "ALCACHOFA": "9",
    "APIO CRIOLLO": "11", "APIO ESPAÑA": "994", "AUYAMA": "13", "BATATA": "15",
    "BERENGENA": "16", "BERENJENA": "16", "BROCOLI": "17", "BROCOLIS": "17", "CALABACIN": "18",
    "CAMBUR": "19", "CEBOLLA BLANCA": "21", "CEBOLLA": "21", "CEBOLLIN": "993", "CHICORIA": "998",
    "CILANTRO": "991", "COLIFLOR": "29", "COLI FLOR": "29", "COLIFLOS": "29",
    "ESCAROLA": "38", "ESPARRAGOS": "989", "ESPINACA": "988", "ESPINACU": "988", "FRESAS PREMIUN": "864", 
    "FRESA": "864", "FRESAS": "864", "GUAYABA": "36", "HIERBABUENA": "985", 
    "HIERBA BUENA": "985", "JENGIBRE": "40", "JOJOTO PELADO": "1211", "JOJOTO": "1211", 
    "LECHOZA": "43", "LECHOSA": "43", "LECHUGA AMERICANA": "32", "LECHUGA CRIOLLA": "33", 
    "LECHUGA ROMANA": "34", "LECHUGA": "33", "LIMON": "47", "MANI SALADO": "935", "MANI SIN SAL": "889", 
    "MELOCOTON": "55", "MELON": "56", "NARANJA": "60", "OCUMO BLANCO": "63", 
    "OCUMO CHINO": "64", "PAPA LAVADA": "8", "PAPA SUCIA": "66", 
    "PARCHITA": "67", "PATILLA": "68", "PATILLA PICADA": "264", "PEPINO": "69", 
    "PEREJIL": "978", "PERESIL": "978", "PIMENTON ROJO": "74", "PIMENTON VERDE": "75", "PIÑA PICADA": "262", 
    "PIÑA": "10", "PLATANO": "76", "REMOLACHA": "79", "REPOLLO BLANCO": "80", "REPOLLO": "80",
    "REPOLLO CHINO": "975", "REPOLLO MORADO": "82", "TOMATE": "85", "TOMATE DE ARBOL": "84", 
    "YUKA": "87", "YUCA": "87", "ZANAHORIA": "88", "ZANAHOSIA": "88", "ZANA HORIA": "88", "NABO CHINO": "003279",
    "CEBOLLA MORADA": "003279", "MORA": "047886", "GENJIBRE": "40", "AJI DULCE JOVITO": "5", "AJI JOBITO": "5", "SILANDRO": "991",
    "CASABE PARSIFAL PEQUEÑO": "020114", "MANZANA VERDE": "003103", "CILATRNO": "991", "MELÓN": "991", "ALBAHACA": "007034",
    "OCUMOCHINO": "64", "PAPA SUCRA": "66", "CHAYOTA": "001124", "KIWI": "002787", "KIWIS": "002787", "PANELA": "008730","PANELA PAPELON": "008730",
    "PANELA PAPELÓN": "008730","MANDARINA": "003092"
}

def cargar_catalogo_completo():
    cat = CATALOGO_BASE.copy()
    path = get_catalogo_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                custom = json.load(f)
                cat.update(custom)
        except Exception:
            pass
    return cat

def guardar_insumo_personalizado(nombre, codigo):
    path = get_catalogo_path()
    custom = {}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                custom = json.load(f)
        except Exception:
            pass
    
    nombre_clean = str(nombre).strip().upper()
    codigo_clean = str(codigo).strip().upper()
    custom[nombre_clean] = codigo_clean

    with open(path, "w", encoding="utf-8") as f:
        json.dump(custom, f, ensure_ascii=False, indent=2)

def cargar_historial_tandas():
    path = get_historial_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def guardar_tanda_en_historial(tanda_dict):
    historial = cargar_historial_tandas()
    historial.insert(0, tanda_dict) # El más reciente primero
    path = get_historial_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(historial, f, ensure_ascii=False, indent=2)

def obtener_codigo(nombre_producto, catalogo):
    nombre_limpio = str(nombre_producto).strip().upper()
    nombre_normalizado = (nombre_limpio
                          .replace("COLI FLOR", "COLIFLOR")
                          .replace("COLIFLOS", "COLIFLOR")
                          .replace("SOVITO", "JOVITO")
                          .replace("PERESIL", "PEREJIL")
                          .replace("ZANAHOSIA", "ZANAHORIA")
                          .replace("ZANA HORIA", "ZANAHORIA")
                          .replace("ESPINACU", "ESPINACA")
                          .replace("GENJIBRE", "JENGIBRE")
                          .replace("SILANDRO", "CILANTRO")
                          .replace("CILATRNO", "CILANTRO")
                          .replace("AJI JOBITO", "AJI JOVITO"))
    
    codigo_hallado = None
    if nombre_limpio.isdigit():
        codigo_hallado = nombre_limpio
    elif nombre_limpio in catalogo:
        codigo_hallado = catalogo[nombre_limpio]
    elif nombre_normalizado in catalogo:
        codigo_hallado = catalogo[nombre_normalizado]
    else:
        for key, code in catalogo.items():
            if key in nombre_limpio or nombre_limpio in key:
                codigo_hallado = code
                break
                
    if not codigo_hallado:
        codigo_hallado = nombre_limpio
        
    if len(codigo_hallado) == 3 and codigo_hallado.isdigit():
        codigo_hallado = f"0{codigo_hallado}"
        
    return codigo_hallado

def parse_cantidad(val):
    val_str = str(val).lower().replace(',', '.')
    val_limpia = re.sub(r'[^0-9.+]|\.(?=\.)', '', val_str)
    
    if not val_limpia:
        return 0.0

    parts = []
    for p in val_limpia.split('+'):
        p = p.strip()
        if p:
            try:
                parts.append(float(p))
            except ValueError:
                continue

    converted = []
    for p in parts:
        if p >= 10:
            p = p / 1000.0
        converted.append(p)
    return sum(converted)

HTML_MOBILE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Frulover - Envío de Inventario</title>
    <style>
        body { font-family: sans-serif; background: #f0f4f8; text-align: center; padding: 20px; color: #333; }
        .card { background: white; border-radius: 12px; padding: 25px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); max-width: 400px; margin: auto; }
        h2 { color: #1F4E79; margin-top: 0; }
        input[type="file"] { display: none; }
        .btn-upload { background: #17A2B8; color: white; padding: 15px 25px; border-radius: 8px; font-size: 16px; font-weight: bold; display: inline-block; cursor: pointer; margin-top: 15px; }
        .btn-submit { background: #28A745; color: white; border: none; padding: 15px; border-radius: 8px; font-size: 16px; font-weight: bold; width: 100%; margin-top: 20px; cursor: pointer; display: none; }
        #status { margin-top: 15px; font-weight: bold; color: #0D6EFD; }
    </style>
</head>
<body>
    <div class="card">
        <h2>Frulover 🍎</h2>
        <p>Selecciona 1 foto de tu galería o tómala directamente con la cámara.</p>
        <form id="uploadForm" enctype="multipart/form-data">
            <label class="btn-upload">
                📷 Tomar 1 Foto / Galería
                <input type="file" name="photo" id="photoInput" accept="image/*" onchange="onFileSelected()">
            </label>
            <div id="fileCount" style="margin-top: 10px; font-weight: bold;"></div>
            <button type="button" id="submitBtn" class="btn-submit" onclick="uploadPhotos()">🚀 Enviar a la PC</button>
        </form>
        <div id="status"></div>
    </div>
    <script>
        function onFileSelected() {
            const input = document.getElementById('photoInput');
            const btn = document.getElementById('submitBtn');
            const count = document.getElementById('fileCount');
            if(input.files.length > 0) {
                count.innerText = "Foto seleccionada: " + input.files[0].name;
                btn.style.display = "block";
            }
        }
        async function uploadPhotos() {
            const input = document.getElementById('photoInput');
            const status = document.getElementById('status');
            const btn = document.getElementById('submitBtn');
            if(input.files.length === 0) return;

            const formData = new FormData();
            formData.append('photo', input.files[0]);

            status.innerText = "⏳ Enviando foto a la PC...";
            btn.disabled = true;

            try {
                const response = await fetch('/upload', { method: 'POST', body: formData });
                const res = await response.json();
                if(res.status === 'ok') {
                    status.innerHTML = "✅ ¡Enviada con éxito!<br>Puedes tomar otra foto si deseas sumar más.";
                    status.style.color = "#28A745";
                } else {
                    status.innerText = "❌ Error: " + res.message;
                    status.style.color = "#DC3545";
                }
            } catch(e) {
                status.innerText = "❌ Error de conexión con la PC.";
                status.style.color = "#DC3545";
            } finally {
                btn.disabled = false;
            }
        }
    </script>
</body>
</html>
"""


class AppCargaInventario:
    def __init__(self, root):
        self.root = root
        self.root.title("Asistente Integral - GaleriasHipermarket v0.1 (Beta)")
        self.root.geometry("860x760")
        self.root.resizable(False, False)
        
        if os.path.exists("icono.ico"):
            try:
                self.root.iconbitmap("icono.ico")
            except:
                pass
                
        self.api_key = self.cargar_api_key()
        self.catalogo = cargar_catalogo_completo()
        self.historial_tandas = cargar_historial_tandas()
        
        self.df_raw = None
        self.df_consolidado = None
        self.local_ip = get_local_ip()
        self.ejecutando_carga = False
        self.ejecutando_ocr = False
        
        self.crear_interfaz()
        self.actualizar_estado_key_btn()
        
        if HAS_SERVER_LIBS:
            self.iniciar_servidor_local()

    def cargar_api_key(self):
        config_path = get_config_path()
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("api_key", "")
            except:
                return ""
        return ""

    def guardar_api_key(self, key):
        config_path = get_config_path()
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump({"api_key": key}, f)
            self.api_key = key
            self.actualizar_estado_key_btn()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar la clave:\n{e}")

    def actualizar_estado_key_btn(self):
        if self.api_key:
            self.btn_key.config(text="🔑 API Key: Guardada ✓", bg="#28A745")
        else:
            self.btn_key.config(text="🔑 Configurar API Key", bg="#DC3545")

    def solicitar_api_key_gui(self):
        key = simpledialog.askstring("Configurar Gemini API Key", 
                                     "Ingrese su API Key de Google Gemini:\n(Se guardará permanentemente)", 
                                     initialvalue=self.api_key)
        if key is not None and key.strip() != "":
            self.guardar_api_key(key.strip())
            messagebox.showinfo("Éxito", "¡API Key guardada correctamente!")

    def abrir_modal_nuevo_insumo(self):
        modal = tk.Toplevel(self.root)
        modal.title("➕ Añadir Nuevo Insumo a la BD")
        modal.geometry("420x250")
        modal.resizable(False, False)
        modal.transient(self.root)
        modal.grab_set()

        tk.Label(modal, text="Registrar Nuevo Insumo / Ingrediente", font=("Calibri", 12, "bold"), fg="#1F4E79").pack(pady=(15, 5))

        tk.Label(modal, text="Nombre del Insumo / Alias (ej: MORA 0800 o MORA):", font=("Calibri", 10)).pack(anchor="w", padx=20, pady=(8, 2))
        ent_nombre = tk.Entry(modal, font=("Calibri", 11))
        ent_nombre.pack(fill=tk.X, padx=20)
        ent_nombre.focus_set()

        tk.Label(modal, text="Código de Sistema Java (ej: 047886):", font=("Calibri", 10)).pack(anchor="w", padx=20, pady=(8, 2))
        ent_codigo = tk.Entry(modal, font=("Calibri", 11))
        ent_codigo.pack(fill=tk.X, padx=20)

        def guardar():
            nom = ent_nombre.get().strip()
            cod = ent_codigo.get().strip()

            if not nom or not cod:
                messagebox.showwarning("Campos vacíos", "Debes ingresar tanto el Nombre como el Código del insumo.")
                return

            guardar_insumo_personalizado(nom, cod)
            self.catalogo = cargar_catalogo_completo()
            
            # Reevaluar la lista actual inmediatamente para actualizar el código en vivo
            if self.df_raw is not None and not self.df_raw.empty:
                self.procesar_df_crudo()

            messagebox.showinfo("Éxito", f"¡Insumo registrado correctamente!\n\n• {nom.upper()} ➔ Código: {cod}")
            modal.destroy()

        btn_guardar = tk.Button(modal, text="💾 Guardar Insumo", command=guardar, bg="#28A745", fg="white", font=("Calibri", 11, "bold"), cursor="hand2")
        btn_guardar.pack(fill=tk.X, padx=20, pady=20)

    def crear_interfaz(self):
        frame_header = tk.Frame(self.root, bg="#1F4E79", height=60)
        frame_header.pack(fill=tk.X)
        
        lbl_titulo = tk.Label(frame_header, text="Asistente Integral Automatizado v0.1 (Beta)", 
                              font=("Calibri", 15, "bold"), fg="white", bg="#1F4E79")
        lbl_titulo.pack(side=tk.LEFT, padx=15, pady=12)

        # Botones de Acción en Cabecera
        self.btn_key = tk.Button(frame_header, text="🔑 API Key", command=self.solicitar_api_key_gui, 
                                 font=("Calibri", 9, "bold"), bg="#2B579A", fg="white", cursor="hand2")
        self.btn_key.pack(side=tk.RIGHT, padx=10, pady=12)

        btn_add_insumo = tk.Button(frame_header, text="➕ Añadir Insumo", command=self.abrir_modal_nuevo_insumo, 
                                   font=("Calibri", 9, "bold"), bg="#FF8C00", fg="white", cursor="hand2")
        btn_add_insumo.pack(side=tk.RIGHT, padx=5, pady=12)

        # 1. Entrada de Datos
        frame_input = tk.LabelFrame(self.root, text=" 1. Captura / Entrada de Datos ", font=("Calibri", 11, "bold"), padx=10, pady=10)
        frame_input.pack(fill=tk.X, padx=15, pady=8)

        btn_qr = tk.Button(frame_input, text="📱 Capturar 1 Foto (QR)", command=self.mostrar_modal_qr, 
                           font=("Calibri", 9, "bold"), bg="#6F42C1", fg="white", height=2, cursor="hand2")
        btn_qr.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        btn_foto = tk.Button(frame_input, text="📷 Buscar 1 Foto PC", command=self.procesar_foto_thread, 
                             font=("Calibri", 9, "bold"), bg="#17A2B8", fg="white", height=2, cursor="hand2")
        btn_foto.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        btn_manual = tk.Button(frame_input, text="✍️ Carga Manual (Offline)", command=self.abrir_carga_manual, 
                               font=("Calibri", 9, "bold"), bg="#28A745", fg="white", height=2, cursor="hand2")
        btn_manual.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        btn_archivo = tk.Button(frame_input, text="📁 Abrir CSV/Excel", command=self.cargar_archivo, 
                                font=("Calibri", 9, "bold"), bg="#6C757D", fg="white", height=2, cursor="hand2")
        btn_archivo.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        btn_limpiar = tk.Button(frame_input, text="🧹 Vaciar Tarea", command=self.limpiar_datos, 
                                font=("Calibri", 9, "bold"), bg="#DC3545", fg="white", height=2, cursor="hand2")
        btn_limpiar.pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=2)

        self.lbl_archivo = tk.Label(self.root, text="Ninguna foto o archivo cargado", font=("Calibri", 10, "italic"), fg="#555555")
        self.lbl_archivo.pack(anchor="w", padx=20)

        # 2. Pestañas de Revisión y Historial
        frame_tabs = tk.LabelFrame(self.root, text=" 2. Revisión de Datos e Historial de Tandas ", font=("Calibri", 11, "bold"), padx=10, pady=10)
        frame_tabs.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)

        self.notebook = ttk.Notebook(frame_tabs)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Tab 1: Consolidado Final
        self.frame_tab_consol = ttk.Frame(self.notebook)
        self.notebook.add(self.frame_tab_consol, text="  ✅ Consolidado Final (Java)  ")

        columns = ("codigo", "producto", "cantidad")
        self.tree = ttk.Treeview(self.frame_tab_consol, columns=columns, show="headings", height=8)
        self.tree.heading("codigo", text="Código")
        self.tree.heading("producto", text="Producto")
        self.tree.heading("cantidad", text="Cantidad Consolidada")
        self.tree.column("codigo", width=110, anchor="center")
        self.tree.column("producto", width=380, anchor="w")
        self.tree.column("cantidad", width=160, anchor="e")

        scrollbar = ttk.Scrollbar(self.frame_tab_consol, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.bind("<Double-1>", self.editar_item_tabla_consol)

        # Tab 2: Lectura Cruda
        self.frame_tab_raw = ttk.Frame(self.notebook)
        self.notebook.add(self.frame_tab_raw, text="  📝 Lectura Cruda / Anotaciones  ")

        columns_raw = ("linea", "producto", "cantidad")
        self.tree_raw = ttk.Treeview(self.frame_tab_raw, columns=columns_raw, show="headings", height=8)
        self.tree_raw.heading("linea", text="N°")
        self.tree_raw.heading("producto", text="Producto Ingresado")
        self.tree_raw.heading("cantidad", text="Anotación Original")
        self.tree_raw.column("linea", width=60, anchor="center")
        self.tree_raw.column("producto", width=380, anchor="w")
        self.tree_raw.column("cantidad", width=180, anchor="e")

        scrollbar_raw = ttk.Scrollbar(self.frame_tab_raw, orient=tk.VERTICAL, command=self.tree_raw.yview)
        self.tree_raw.configure(yscroll=scrollbar_raw.set)
        self.tree_raw.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_raw.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree_raw.bind("<Double-1>", self.editar_item_tabla_raw)
        self.tree_raw.bind("<Delete>", self.eliminar_item_tecla_raw)

        # Tab 3: Historial de Tandas
        self.frame_tab_historial = ttk.Frame(self.notebook)
        self.notebook.add(self.frame_tab_historial, text="  📜 Historial de Tandas  ")

        columns_hist = ("id", "fecha", "crudo", "consol")
        self.tree_hist = ttk.Treeview(self.frame_tab_historial, columns=columns_hist, show="headings", height=8)
        self.tree_hist.heading("id", text="ID Tanda")
        self.tree_hist.heading("fecha", text="Fecha y Hora")
        self.tree_hist.heading("crudo", text="Renglones Crudos")
        self.tree_hist.heading("consol", text="Items Consolidados")

        self.tree_hist.column("id", width=160, anchor="center")
        self.tree_hist.column("fecha", width=200, anchor="center")
        self.tree_hist.column("crudo", width=130, anchor="center")
        self.tree_hist.column("consol", width=130, anchor="center")

        scrollbar_hist = ttk.Scrollbar(self.frame_tab_historial, orient=tk.VERTICAL, command=self.tree_hist.yview)
        self.tree_hist.configure(yscroll=scrollbar_hist.set)
        self.tree_hist.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_hist.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree_hist.bind("<Double-1>", self.ver_detalle_tanda_historial)
        self.actualizar_tabla_historial_gui()

        # Control Inferior
        frame_control = tk.Frame(self.root, pady=6)
        frame_control.pack(fill=tk.X, padx=15)

        self.lbl_status = tk.Label(frame_control, text="Estado: Seleccione un método de entrada para comenzar", 
                                   font=("Calibri", 11, "bold"), fg="#333333")
        self.lbl_status.pack(pady=4)

        frame_btns_exec = tk.Frame(frame_control)
        frame_btns_exec.pack(fill=tk.X)

        self.btn_guardar_tanda = tk.Button(frame_btns_exec, text="💾 Guardar Tanda", command=self.guardar_tanda_actual, 
                                           font=("Calibri", 11, "bold"), bg="#17A2B8", fg="white", state=tk.DISABLED, 
                                           height=2, cursor="hand2")
        self.btn_guardar_tanda.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))

        self.btn_iniciar = tk.Button(frame_btns_exec, text="🚀 INICIAR CARGA EN JAVA", command=self.iniciar_proceso_thread, 
                                     font=("Calibri", 13, "bold"), bg="#28A745", fg="white", state=tk.DISABLED, 
                                     height=2, cursor="hand2")
        self.btn_iniciar.pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=(5, 0))

    def actualizar_tabla_historial_gui(self):
        for item in self.tree_hist.get_children(): self.tree_hist.delete(item)
        self.historial_tandas = cargar_historial_tandas()

        for idx, tanda in enumerate(self.historial_tandas):
            self.tree_hist.insert("", tk.END, iid=idx, values=(
                tanda.get("id", f"TANDA-{idx+1}"),
                tanda.get("fecha", "N/A"),
                tanda.get("total_crudo", 0),
                tanda.get("total_consolidado", 0)
            ))

    def guardar_tanda_actual(self, es_autoguardado=False):
        if self.df_raw is None or self.df_raw.empty or self.df_consolidado is None or self.df_consolidado.empty:
            if not es_autoguardado:
                messagebox.showwarning("Sin datos", "No hay ninguna tanda activa para guardar.")
            return None

        now_str = datetime.datetime.now().strftime("%d/%m/%Y %I:%M:%S %p")
        id_str = f"TANDA-{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"

        raw_list = self.df_raw[['producto', 'cantidad']].to_dict(orient='records')
        
        consol_list = []
        for _, row in self.df_consolidado.iterrows():
            consol_list.append({
                "codigo": str(row['Codigo']),
                "producto": str(row['Producto_Original']),
                "cantidad": f"{row['Cantidad_Num']:.3f}".rstrip('0').rstrip('.')
            })

        tanda_dict = {
            "id": id_str,
            "fecha": now_str,
            "total_crudo": len(raw_list),
            "total_consolidado": len(consol_list),
            "raw_data": raw_list,
            "consol_data": consol_list
        }

        guardar_tanda_en_historial(tanda_dict)
        self.actualizar_tabla_historial_gui()

        if not es_autoguardado:
            messagebox.showinfo("Tanda Guardada", f"¡Tanda guardada con éxito!\n\nID: {id_str}\nFecha: {now_str}")

        return tanda_dict

    def ver_detalle_tanda_historial(self, event):
        selected = self.tree_hist.selection()
        if not selected: return
        idx = int(selected[0])
        tanda = self.historial_tandas[idx]

        modal = tk.Toplevel(self.root)
        modal.title(f"Detalle de Tanda - {tanda.get('id')}")
        modal.geometry("640x520")
        modal.transient(self.root)
        modal.grab_set()

        # Encabezado Modal
        frame_top = tk.Frame(modal, bg="#1F4E79", pady=10)
        frame_top.pack(fill=tk.X)
        
        lbl_m_tit = tk.Label(frame_top, text=f"Registro: {tanda.get('id')}", font=("Calibri", 13, "bold"), fg="white", bg="#1F4E79")
        lbl_m_tit.pack()
        lbl_m_sub = tk.Label(frame_top, text=f"Fecha: {tanda.get('fecha')} | Items: {tanda.get('total_consolidado')}", font=("Calibri", 10), fg="#E0E0E0", bg="#1F4E79")
        lbl_m_sub.pack()

        # Tabs de Tablas Internas
        notebook_m = ttk.Notebook(modal)
        notebook_m.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Tab Consolidado
        tab_c = ttk.Frame(notebook_m)
        notebook_m.add(tab_c, text="  ✅ Items Consolidados  ")

        tree_c = ttk.Treeview(tab_c, columns=("cod", "prod", "cant"), show="headings", height=10)
        tree_c.heading("cod", text="Código")
        tree_c.heading("prod", text="Producto")
        tree_c.heading("cant", text="Cantidad")
        tree_c.column("cod", width=100, anchor="center")
        tree_c.column("prod", width=340, anchor="w")
        tree_c.column("cant", width=120, anchor="e")

        scr_c = ttk.Scrollbar(tab_c, orient=tk.VERTICAL, command=tree_c.yview)
        tree_c.configure(yscroll=scr_c.set)
        tree_c.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scr_c.pack(side=tk.RIGHT, fill=tk.Y)

        for item in tanda.get("consol_data", []):
            tree_c.insert("", tk.END, values=(item.get("codigo"), item.get("producto"), item.get("cantidad")))

        # Tab Crudo
        tab_r = ttk.Frame(notebook_m)
        notebook_m.add(tab_r, text="  📝 Lectura Cruda  ")

        tree_r = ttk.Treeview(tab_r, columns=("nro", "prod", "cant"), show="headings", height=10)
        tree_r.heading("nro", text="N°")
        tree_r.heading("prod", text="Producto")
        tree_r.heading("cant", text="Anotación")
        tree_r.column("nro", width=50, anchor="center")
        tree_r.column("prod", width=360, anchor="w")
        tree_r.column("cant", width=140, anchor="e")

        scr_r = ttk.Scrollbar(tab_r, orient=tk.VERTICAL, command=tree_r.yview)
        tree_r.configure(yscroll=scr_r.set)
        tree_r.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scr_r.pack(side=tk.RIGHT, fill=tk.Y)

        for i, item in enumerate(tanda.get("raw_data", [])):
            tree_r.insert("", tk.END, values=(i+1, item.get("producto"), item.get("cantidad")))

        # Acciones
        frame_btns = tk.Frame(modal, pady=10)
        frame_btns.pack(fill=tk.X, padx=10)

        def imprimir_reporte_html():
            html_content = f"""
            <!DOCTYPE html>
            <html lang="es">
            <head>
                <meta charset="UTF-8">
                <title>Reporte Tanda - {tanda.get('id')}</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 25px; color: #333; }}
                    h2 {{ color: #1F4E79; text-align: center; margin-bottom: 5px; }}
                    p.sub {{ text-align: center; color: #666; font-size: 13px; margin-top: 0; }}
                    .box {{ border: 1px solid #ccc; border-radius: 6px; padding: 12px; margin-bottom: 20px; background: #f9f9f9; }}
                    table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; font-size: 13px; }}
                    th {{ background-color: #1F4E79; color: white; }}
                    .no-print {{ text-align: right; margin-bottom: 15px; }}
                    .btn-print {{ background: #28A745; color: white; border: none; padding: 10px 18px; border-radius: 5px; font-weight: bold; cursor: pointer; }}
                    @media print {{ .no-print {{ display: none; }} }}
                </style>
            </head>
            <body>
                <div class="no-print">
                    <button class="btn-print" onclick="window.print()">🖨️ Imprimir Documento</button>
                </div>
                <h2>Galerías Hipermarket - Reporte de Tanda</h2>
                <p class="sub">Frulover Inventario v0.1 (Beta)</p>
                <div class="box">
                    <strong>ID Tanda:</strong> {tanda.get('id')}<br>
                    <strong>Fecha y Hora:</strong> {tanda.get('fecha')}<br>
                    <strong>Total Renglones Crudos:</strong> {tanda.get('total_crudo')}<br>
                    <strong>Total Consolidado:</strong> {tanda.get('total_consolidado')}
                </div>
                
                <h3>✅ Consolidado Final (Cargado en Java)</h3>
                <table>
                    <tr><th>Código</th><th>Producto</th><th>Cantidad Consolidada</th></tr>
                    {"".join(f"<tr><td>{item.get('codigo')}</td><td>{item.get('producto')}</td><td>{item.get('cantidad')}</td></tr>" for item in tanda.get('consol_data', []))}
                </table>

                <h3 style="margin-top:25px;">📝 Lectura Cruda de Origen</h3>
                <table>
                    <tr><th>N°</th><th>Producto Ingresado</th><th>Anotación Original</th></tr>
                    {"".join(f"<tr><td>{i+1}</td><td>{item.get('producto')}</td><td>{item.get('cantidad')}</td></tr>" for i, item in enumerate(tanda.get('raw_data', [])))}
                </table>
            </body>
            </html>
            """
            temp_path = os.path.join(get_appdata_folder(), f"reporte_{tanda.get('id')}.html")
            with open(temp_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            webbrowser.open(f"file://{os.path.abspath(temp_path)}")

        def cargar_en_trabajo():
            if messagebox.askyesno("Reabrir Tanda", "¿Deseas cargar los datos de esta tanda en la pantalla principal para modificarlos o re-procesarlos?"):
                self.df_raw = pd.DataFrame(tanda.get("raw_data", []))
                self.procesar_df_crudo()
                self.lbl_archivo.config(text=f"📜 Tanda {tanda.get('id')} cargada en pantalla", fg="#17A2B8")
                self.lbl_status.config(text="✓ Listo para Cargar en Java.", fg="#28A745")
                self.btn_iniciar.config(state=tk.NORMAL)
                modal.destroy()

        btn_imp = tk.Button(frame_btns, text="🖨️ Imprimir Reporte", command=imprimir_reporte_html, bg="#17A2B8", fg="white", font=("Calibri", 10, "bold"), cursor="hand2")
        btn_imp.pack(side=tk.LEFT, padx=5)

        btn_reopen = tk.Button(frame_btns, text="📋 Cargar en Pantalla Principal", command=cargar_en_trabajo, bg="#6F42C1", fg="white", font=("Calibri", 10, "bold"), cursor="hand2")
        btn_reopen.pack(side=tk.LEFT, padx=5)

        btn_close = tk.Button(frame_btns, text="Cerrar", command=modal.destroy, bg="#6C757D", fg="white", font=("Calibri", 10), cursor="hand2")
        btn_close.pack(side=tk.RIGHT, padx=5)

    def limpiar_datos(self):
        self.ejecutando_ocr = False
        self.ejecutando_carga = False
        self.df_raw = None
        self.df_consolidado = None
        for item in self.tree.get_children(): self.tree.delete(item)
        for item in self.tree_raw.get_children(): self.tree_raw.delete(item)
        self.lbl_archivo.config(text="Ninguna foto o archivo cargado", fg="#555555")
        self.lbl_status.config(text="Estado: Seleccione un método de entrada", fg="#333333")
        self.btn_iniciar.config(state=tk.DISABLED, text="🚀 INICIAR CARGA EN JAVA", bg="#28A745")
        self.btn_guardar_tanda.config(state=tk.DISABLED)

    def mostrar_modal_qr(self):
        if not HAS_SERVER_LIBS:
            messagebox.showerror("Librerías faltantes", "Falta flask o qrcode.")
            return

        url_local = f"http://{self.local_ip}:5000"
        qr = qrcode.QRCode(box_size=8, border=2)
        qr.add_data(url_local)
        qr.make(fit=True)
        img_qr = qr.make_image(fill_color="black", back_color="white")
        
        modal = tk.Toplevel(self.root)
        modal.title("Escanear QR")
        modal.geometry("380x420")
        modal.resizable(False, False)
        modal.transient(self.root)
        modal.grab_set()

        lbl_info = tk.Label(modal, text="Escanea este QR con el celular:", font=("Calibri", 12, "bold"), fg="#1F4E79")
        lbl_info.pack(pady=10)

        buf = io.BytesIO()
        img_qr.save(buf, format="PNG")
        buf.seek(0)
        img_tk = ImageTk.PhotoImage(Image.open(buf))
        
        lbl_img = tk.Label(modal, image=img_tk)
        lbl_img.image = img_tk
        lbl_img.pack(pady=5)
        lbl_url = tk.Label(modal, text=url_local, font=("Calibri", 10, "italic"))
        lbl_url.pack(pady=10)

    def iniciar_servidor_local(self):
        app = Flask(__name__)
        CORS(app)

        @app.route('/')
        def index(): return render_template_string(HTML_MOBILE)

        @app.route('/upload', methods=['POST'])
        def upload():
            file = request.files.get('photo')
            if not file and request.files.getlist('photos'):
                file = request.files.getlist('photos')[0]
                
            if not file: return jsonify({"status": "error", "message": "No se recibió ninguna foto"}), 400
            
            try:
                img = Image.open(io.BytesIO(file.read())).convert("RGB")
                img.load()
                threading.Thread(target=self.ejecutar_ocr_ia_pil, args=(img,), daemon=True).start()
                return jsonify({"status": "ok", "message": "Foto recibida"})
            except Exception as e:
                return jsonify({"status": "error", "message": str(e)}), 500

        threading.Thread(target=lambda: app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False), daemon=True).start()

    def abrir_carga_manual(self):
        modal = tk.Toplevel(self.root)
        modal.title("Carga Manual Rápida (Offline)")
        modal.geometry("500x450")
        modal.transient(self.root)
        modal.grab_set()

        lbl_inst = tk.Label(modal, text="Escribe un producto y cantidad por línea.\nEj: cebolla blanca 1800+1900\nzanahoria 2200", 
                            font=("Calibri", 10), justify=tk.LEFT)
        lbl_inst.pack(pady=10, padx=10, anchor="w")

        txt_input = tk.Text(modal, font=("Consolas", 11), height=15)
        txt_input.pack(fill=tk.BOTH, expand=True, padx=10)

        def procesar_manual():
            texto = txt_input.get("1.0", tk.END).strip()
            if not texto: return
            
            lineas = texto.split('\n')
            datos_manuales = []
            
            for linea in lineas:
                linea = linea.strip()
                if not linea: continue
                
                match = re.search(r'([\d.,+]+.*)', linea)
                if match:
                    cant_str = match.group(1).strip()
                    prod_str = linea[:match.start()].strip()
                    datos_manuales.append({"producto": prod_str, "cantidad": cant_str})
                else:
                    datos_manuales.append({"producto": linea, "cantidad": "0"})

            if datos_manuales:
                df_nuevo = pd.DataFrame(datos_manuales)
                if self.df_raw is None or self.df_raw.empty:
                    self.df_raw = df_nuevo
                else:
                    self.df_raw = pd.concat([self.df_raw, df_nuevo], ignore_index=True)
                
                self.procesar_df_crudo()
                self.lbl_archivo.config(text=f"✍️ Carga manual procesada | Total: {len(self.df_raw)} líneas", fg="#FF8C00")
                self.lbl_status.config(text="✓ Listo para Cargar en Java.", fg="#28A745")
                self.btn_iniciar.config(state=tk.NORMAL)
                self.btn_guardar_tanda.config(state=tk.NORMAL)
            
            modal.destroy()

        btn_guardar = tk.Button(modal, text="Procesar Texto", command=procesar_manual, bg="#28A745", fg="white", font=("Calibri", 11, "bold"))
        btn_guardar.pack(fill=tk.X, padx=10, pady=10)

    def procesar_foto_thread(self):
        if not HAS_GENAI:
            messagebox.showerror("Falta Librería", "Falta google-genai.")
            return
        if not self.api_key:
            self.solicitar_api_key_gui()
            if not self.api_key: return
        threading.Thread(target=self.ejecutar_ocr_ia_archivos, daemon=True).start()

    def consultar_gemini_con_reintento(self, client, contents):
        modelos_candidatos = ['gemini-3.6-flash']
        ultimo_error = None

        for modelo in modelos_candidatos:
            for intento in range(1, 4):
                if not self.ejecutando_ocr: raise Exception("Cancelado por el usuario.")
                try:
                    response = client.models.generate_content(model=modelo, contents=contents)
                    if response and response.text: return response.text.strip()
                except Exception as e:
                    ultimo_error = e
                    err_str = str(e)
                    if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                        tiempo = intento * 5
                        self.lbl_status.config(text=f"⏳ Límite de cuota alcanzado. Pausando {tiempo}s...", fg="#FF8C00")
                        time.sleep(tiempo)
                        continue
                    elif "503" in err_str:
                        self.lbl_status.config(text=f"⏳ Servidor ocupado. Reintentando...", fg="#FF8C00")
                        time.sleep(3)
                        continue
                    else:
                        break
        raise ultimo_error

    def ejecutar_ocr_ia_pil(self, imagen_pil):
        if not self.api_key:
            self.lbl_status.config(text="❌ Falta configurar la API Key", fg="#DC3545")
            return

        self.ejecutando_ocr = True

        try:
            client = genai.Client(api_key=self.api_key)
            self.lbl_status.config(text="⚡ Comprimiendo a B/N (~25KB) y procesando foto en Gemini 3.6...", fg="#0D6EFD")

            img_opt = optimizar_imagen_extrema(imagen_pil, max_dim=800)

            prompt = """
            Eres un asistente de inventario. Examina esta imagen de una lista manuscrita de frutas/verduras.
            Extrae TODOS los renglones en orden estricto de arriba hacia abajo sin sumar ni consolidar duplicados.
            Responde ÚNICAMENTE con un arreglo JSON de objetos con las llaves "producto" y "cantidad".
            Escribe únicamente el número o la expresión en la cantidad, sin añadir letras ni unidades como "KG", "kilos", "und".
            Ejemplo:
            [
              {"producto": "Lechuga romana", "cantidad": "0.450"},
              {"producto": "Repollo blanco", "cantidad": "4200"},
              {"producto": "Cebolla Blanca", "cantidad": "1800 + 1900"}
            ]
            """

            contents = [img_opt, prompt]
            res_text = self.consultar_gemini_con_reintento(client, contents)

            if "```json" in res_text: res_text = res_text.split("```json")[1].split("```")[0].strip()
            elif "```" in res_text: res_text = res_text.split("```")[1].split("```")[0].strip()

            datos = json.loads(res_text)
            df_nuevo = pd.DataFrame(datos)

            if self.df_raw is None or self.df_raw.empty:
                self.df_raw = df_nuevo
            else:
                self.df_raw = pd.concat([self.df_raw, df_nuevo], ignore_index=True)

            self.procesar_df_crudo()

            total_lineas = len(self.df_raw)
            self.lbl_archivo.config(text=f"📷 Foto procesada con éxito | Total acumulado: {total_lineas} líneas", fg="#6F42C1")
            self.lbl_status.config(text="✓ Análisis completo. Listo para Cargar en Java.", fg="#28A745")
            self.btn_iniciar.config(state=tk.NORMAL)
            self.btn_guardar_tanda.config(state=tk.NORMAL)

        except Exception as e:
            if self.ejecutando_ocr:
                self.lbl_status.config(text=f"Error en IA: {e}", fg="#DC3545")
        finally:
            self.ejecutando_ocr = False

    def ejecutar_ocr_ia_archivos(self):
        filepath = filedialog.askopenfilename(
            title="Seleccionar 1 foto en la PC",
            filetypes=[("Imágenes", "*.jpg *.jpeg *.png"), ("Todos los archivos", "*.*")]
        )
        if filepath:
            self.ejecutar_ocr_ia_pil(Image.open(filepath))

    def procesar_df_crudo(self):
        for item in self.tree_raw.get_children(): self.tree_raw.delete(item)
        for item in self.tree.get_children(): self.tree.delete(item)

        if self.df_raw is None or self.df_raw.empty:
            self.df_consolidado = None
            self.lbl_status.config(text="Estado: Lista vacía", fg="#333333")
            self.btn_iniciar.config(state=tk.DISABLED)
            self.btn_guardar_tanda.config(state=tk.DISABLED)
            return

        for idx, row in self.df_raw.iterrows():
            self.tree_raw.insert("", tk.END, values=(idx + 1, str(row['producto']), str(row['cantidad'])))

        df_temp = self.df_raw.copy()
        df_temp['Producto_Original'] = df_temp['producto'].astype(str).str.strip()
        df_temp['Codigo'] = df_temp['Producto_Original'].apply(lambda x: obtener_codigo(x, self.catalogo))
        df_temp['Cantidad_Num'] = df_temp['cantidad'].apply(parse_cantidad)

        self.df_consolidado = df_temp.groupby(['Codigo'], as_index=False).agg({
            'Cantidad_Num': 'sum',
            'Producto_Original': 'first'
        })
        self.actualizar_tabla_gui()
        self.btn_guardar_tanda.config(state=tk.NORMAL)

    def cargar_archivo(self):
        filepath = filedialog.askopenfilename(filetypes=[("Archivos CSV o Excel", "*.csv *.xlsx")])
        if not filepath: return
        try:
            if filepath.endswith('.xlsx'): df = pd.read_excel(filepath)
            else: df = pd.read_csv(filepath)
            self.df_raw = df[['Producto', 'Cantidad']].rename(columns={'Producto': 'producto', 'Cantidad': 'cantidad'})
            self.procesar_df_crudo()
            self.lbl_archivo.config(text=f"📄 Archivo cargado", fg="#1F4E79")
            self.lbl_status.config(text="✓ Listo. Presione INICIAR.", fg="#28A745")
            self.btn_iniciar.config(state=tk.NORMAL)
            self.btn_guardar_tanda.config(state=tk.NORMAL)
        except Exception as e:
            messagebox.showerror("Error", f"Error archivo:\n{e}")

    def actualizar_tabla_gui(self):
        for item in self.tree.get_children(): self.tree.delete(item)
        if self.df_consolidado is None or self.df_consolidado.empty: return

        for idx, row in self.df_consolidado.iterrows():
            codigo = str(row['Codigo'])
            nombre = str(row['Producto_Original'])
            cant_str = f"{row['Cantidad_Num']:.3f}".rstrip('0').rstrip('.')
            self.tree.insert("", tk.END, iid=idx, values=(codigo, nombre, cant_str))

    def editar_item_tabla_consol(self, event):
        selected = self.tree.selection()
        if not selected or self.df_consolidado is None: return
        idx = int(selected[0])
        producto_nombre = self.df_consolidado.loc[idx, 'Producto_Original']
        cantidad_actual = self.df_consolidado.loc[idx, 'Cantidad_Num']
        nueva_cant = simpledialog.askfloat("Editar Cantidad", f"Producto: {producto_nombre}", initialvalue=float(cantidad_actual))
        if nueva_cant is not None:
            self.df_consolidado.loc[idx, 'Cantidad_Num'] = nueva_cant
            self.actualizar_tabla_gui()

    def editar_item_tabla_raw(self, event):
        selected = self.tree_raw.selection()
        if not selected or self.df_raw is None: return
        idx = self.tree_raw.index(selected[0])
        prod_actual = str(self.df_raw.loc[idx, 'producto'])
        cant_actual = str(self.df_raw.loc[idx, 'cantidad'])

        modal = tk.Toplevel(self.root)
        modal.title(f"Editar Renglón N° {idx + 1}")
        modal.geometry("440x230")
        modal.resizable(False, False)
        modal.transient(self.root)
        modal.grab_set()

        tk.Label(modal, text="Nombre del Producto:", font=("Calibri", 10, "bold")).pack(anchor="w", padx=15, pady=(15, 2))
        ent_prod = tk.Entry(modal, font=("Calibri", 11))
        ent_prod.pack(fill=tk.X, padx=15)
        ent_prod.insert(0, prod_actual)

        tk.Label(modal, text="Anotación / Cantidad:", font=("Calibri", 10, "bold")).pack(anchor="w", padx=15, pady=(10, 2))
        ent_cant = tk.Entry(modal, font=("Calibri", 11))
        ent_cant.pack(fill=tk.X, padx=15)
        ent_cant.insert(0, cant_actual)

        def guardar():
            nuevo_prod = ent_prod.get().strip()
            nueva_cant = ent_cant.get().strip()
            if nuevo_prod != "" and nueva_cant != "":
                self.df_raw.loc[idx, 'producto'] = nuevo_prod
                self.df_raw.loc[idx, 'cantidad'] = nueva_cant
                self.procesar_df_crudo()
                modal.destroy()
            else:
                messagebox.showwarning("Campos vacíos", "Ni el producto ni la cantidad pueden quedar vacíos.")

        def eliminar():
            if messagebox.askyesno("Confirmar eliminación", f"¿Seguro que deseas eliminar el renglón N° {idx + 1} ({prod_actual})?"):
                self.df_raw = self.df_raw.drop(index=idx).reset_index(drop=True)
                self.procesar_df_crudo()
                total_lineas = len(self.df_raw) if self.df_raw is not None else 0
                self.lbl_archivo.config(text=f"📋 Lista actualizada | Total: {total_lineas} líneas", fg="#6F42C1")
                modal.destroy()

        btn_frame = tk.Frame(modal)
        btn_frame.pack(fill=tk.X, padx=15, pady=18)
        
        btn_guardar = tk.Button(btn_frame, text="💾 Guardar", command=guardar, bg="#28A745", fg="white", font=("Calibri", 10, "bold"), cursor="hand2")
        btn_guardar.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        
        btn_eliminar = tk.Button(btn_frame, text="🗑️ Eliminar", command=eliminar, bg="#DC3545", fg="white", font=("Calibri", 10, "bold"), cursor="hand2")
        btn_eliminar.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        btn_cancelar = tk.Button(btn_frame, text="Cancelar", command=modal.destroy, bg="#6C757D", fg="white", font=("Calibri", 10), cursor="hand2")
        btn_cancelar.pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=2)

    def eliminar_item_tecla_raw(self, event):
        selected = self.tree_raw.selection()
        if not selected or self.df_raw is None or self.df_raw.empty: return
        idx = self.tree_raw.index(selected[0])
        prod_actual = str(self.df_raw.loc[idx, 'producto'])
        
        if messagebox.askyesno("Confirmar eliminación", f"¿Deseas eliminar el renglón N° {idx + 1} ({prod_actual})?"):
            self.df_raw = self.df_raw.drop(index=idx).reset_index(drop=True)
            self.procesar_df_crudo()
            total_lineas = len(self.df_raw) if self.df_raw is not None else 0
            self.lbl_archivo.config(text=f"📋 Lista actualizada | Total: {total_lineas} líneas", fg="#6F42C1")

    def iniciar_proceso_thread(self):
        if self.ejecutando_carga:
            self.ejecutando_carga = False
            self.lbl_status.config(text="🛑 Cancelando...", fg="#DC3545")
            return

        # Auto-guardar tanda en historial antes de iniciar la carga en Java
        self.guardar_tanda_actual(es_autoguardado=True)

        self.ejecutando_carga = True
        self.btn_iniciar.config(text="🛑 CANCELAR EJECUCIÓN", bg="#DC3545")
        threading.Thread(target=self.ejecutar_carga_java, daemon=True).start()

    def ejecutar_carga_java(self):
        try:
            for i in range(5, 0, -1):
                if not self.ejecutando_carga: return
                self.lbl_status.config(text=f"⚠️ INICIANDO EN {i}S... Haz clic en 'Artículo:' en Java", fg="#DC3545")
                time.sleep(1)

            if not self.ejecutando_carga: return
            self.lbl_status.config(text="⚙️ Carga automática en progreso...", fg="#0D6EFD")
            
            for idx, row in self.df_consolidado.iterrows():
                if not self.ejecutando_carga: break
                
                codigo = str(row['Codigo'])
                cantidad = f"{row['Cantidad_Num']:.3f}".rstrip('0').rstrip('.')
                
                pyautogui.write(codigo, interval=0.08)
                pyautogui.press('tab')
                
                for _ in range(35):
                    if not self.ejecutando_carga: break
                    time.sleep(0.1)
                    
                if not self.ejecutando_carga: break
                pyautogui.write(cantidad, interval=0.08)
                pyautogui.press('tab')
                pyautogui.press('enter')
                time.sleep(0.5)

            if self.ejecutando_carga:
                self.lbl_status.config(text="✅ ¡CARGA FINALIZADA CON ÉXITO!", fg="#28A745")
            else:
                self.lbl_status.config(text="🛑 Carga cancelada.", fg="#DC3545")

        except pyautogui.FailSafeException:
            self.lbl_status.config(text="🛑 CARGA ABORTADA.", fg="#DC3545")
        except Exception as e:
            self.lbl_status.config(text=f"Error: {e}", fg="#DC3545")
        finally:
            self.ejecutando_carga = False
            self.btn_iniciar.config(state=tk.NORMAL, text="🚀 INICIAR CARGA EN JAVA", bg="#28A745")

if __name__ == "__main__":
    root = tk.Tk()
    app = AppCargaInventario(root)
    root.mainloop()